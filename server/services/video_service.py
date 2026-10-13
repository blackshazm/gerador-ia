"""
Módulo de Serviço de Renderização de Vídeo IA — Tríade Studio
Orquestra a geração de vídeos (Image-to-Video) por plano, chaining temporal (Tail-to-Head)
e sincronização com a decupagem de cena e tarefas em background.
"""
import os
import sys
import re
import json
import shutil
import subprocess
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List

BASE_DIR = Path(__file__).resolve().parent.parent.parent
SCRIPTS_DIR = BASE_DIR / "scripts"
WEB_DIR = BASE_DIR / "web"

if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

import project_context as pc
import fal_client
from server.storage import atomic_write_json, SCENES_LOCK
from server.services import task_service

logger = logging.getLogger("VideoService")


def sanitize_id(identifier: str) -> str:
    """Sanitiza identificadores para evitar ataques de Path Traversal."""
    return re.sub(r'[^a-zA-Z0-9_\-]', '', str(identifier)).strip("_")


def extract_video_last_frame(video_path: Path, output_image_path: Path) -> bool:
    """
    Extrai o último frame do vídeo usando FFmpeg com fallback resiliente.
    Usado para garantir continuidade perfeita (Tail-to-Head Chaining) no próximo plano.
    """
    video_path = Path(video_path)
    output_image_path = Path(output_image_path)
    output_image_path.parent.mkdir(parents=True, exist_ok=True)

    if not video_path.exists() or video_path.stat().st_size == 0:
        logger.warning(f"Vídeo de origem não existe ou está vazio: {video_path}")
        return False

    ffmpeg_bin = shutil.which("ffmpeg")
    if ffmpeg_bin:
        try:
            cmd = [
                ffmpeg_bin,
                "-y",
                "-sseof", "-0.1",
                "-i", str(video_path),
                "-update", "1",
                "-q:v", "2",
                str(output_image_path)
            ]
            res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=15)
            if res.returncode == 0 and output_image_path.exists() and output_image_path.stat().st_size > 0:
                logger.info(f"Último frame extraído com sucesso: {output_image_path}")
                return True
            else:
                logger.warning(f"FFmpeg retornou código {res.returncode}: {res.stderr.decode('utf-8', errors='ignore')[:200]}")
        except Exception as e:
            logger.warning(f"Erro ao extrair último frame com FFmpeg: {e}")

    return False


def get_shot_reference_image(scene_id: str, shot_id: str, project_id: Optional[str] = None, use_chaining: bool = True) -> Optional[Path]:
    """
    Localiza a melhor imagem de referência para o plano.
    Se use_chaining for True e o plano anterior tiver um 'last_frame' gravado, dá preferência a ele.
    """
    paths = pc.get_current_project_paths(project_id)
    clean_shot = sanitize_id(shot_id)
    renders_dir = paths.renders_dir

    # Se chaining habilitado, verifica se o plano imediatamente anterior gerou um tail frame
    if use_chaining:
        scene_file = paths.scenes_dir / f"{sanitize_id(scene_id)}.json"
        if scene_file.exists():
            try:
                with open(scene_file, "r", encoding="utf-8") as sf:
                    s_data = json.load(sf)
                beats = s_data.get("beats", [])
                for idx, b in enumerate(beats):
                    if b.get("shot_id") == clean_shot and idx > 0:
                        prev_shot = sanitize_id(beats[idx - 1].get("shot_id", ""))
                        prev_tail = renders_dir / f"{prev_shot}_tail.jpg"
                        if prev_tail.exists() and prev_tail.stat().st_size > 0:
                            logger.info(f"Usando Chaining Tail-to-Head: {prev_tail.name} -> {clean_shot}")
                            return prev_tail
            except Exception as ex:
                logger.warning(f"Aviso ao calcular chaining de cena: {ex}")

    # Imagem direta do plano
    candidate_shot = renders_dir / f"{clean_shot}.jpg"
    if candidate_shot.exists() and candidate_shot.stat().st_size > 0:
        return candidate_shot

    # Busca no JSON da cena por caminhos declarados
    scene_file = paths.scenes_dir / f"{sanitize_id(scene_id)}.json"
    if scene_file.exists():
        try:
            with open(scene_file, "r", encoding="utf-8") as sf:
                s_data = json.load(sf)
            for b in s_data.get("beats", []):
                if b.get("shot_id") == clean_shot:
                    for k in ["generated_image", "actor_image", "reference_image"]:
                        val = b.get(k)
                        if val:
                            val_p = (WEB_DIR / val).resolve() if "assets/" in val else (paths.project_dir / val).resolve()
                            if val_p.exists() and val_p.stat().st_size > 0:
                                return val_p
        except Exception:
            pass

    return None


def generate_shot_video(
    scene_id: str,
    shot_id: str,
    project_id: Optional[str] = None,
    prompt_override: Optional[str] = None,
    use_chaining: bool = True
) -> Dict[str, Any]:
    """
    Gera o clipe de vídeo em formato MP4 para o plano especificado.
    Atualiza metadados e sincroniza com o assets web.
    """
    clean_scene = sanitize_id(scene_id)
    clean_shot = sanitize_id(shot_id)
    paths = pc.get_current_project_paths(project_id)

    scene_file = paths.scenes_dir / f"{clean_scene}.json"
    if not scene_file.exists():
        return {"status": "error", "message": f"Cena {clean_scene} não encontrada."}

    with open(scene_file, "r", encoding="utf-8") as sf:
        scene_data = json.load(sf)

    beat_target = next((b for b in scene_data.get("beats", []) if b.get("shot_id") == clean_shot), None)
    if not beat_target:
        return {"status": "error", "message": f"Plano {clean_shot} não encontrado na cena {clean_scene}."}

    # Prompt de vídeo
    prompt = prompt_override or beat_target.get("video_prompt") or beat_target.get("prompt_visual") or beat_target.get("action_description", "")
    if not prompt:
        prompt = f"Cinematic film shot, smooth camera movement, highly detailed, dramatic lighting"

    # Duração (padrão 5s ou calculada pelo pacing)
    duration_s = float(beat_target.get("recommended_video_duration_s") or beat_target.get("duration_s") or 5.0)
    duration_s = max(3.0, min(10.0, duration_s))

    # Imagem de referência (com ou sem Tail Chaining)
    ref_image = get_shot_reference_image(clean_scene, clean_shot, project_id=project_id, use_chaining=use_chaining)
    if not ref_image or not ref_image.exists():
        return {
            "status": "error",
            "message": f"Imagem de referência para o plano {clean_shot} não encontrada. Gere a imagem do plano primeiro."
        }

    paths.renders_dir.mkdir(parents=True, exist_ok=True)
    out_video = paths.renders_dir / f"{clean_shot}.mp4"
    out_tail = paths.renders_dir / f"{clean_shot}_tail.jpg"

    logger.info(f"Disparando geração de vídeo para {clean_shot} (duração: {duration_s}s, ref: {ref_image.name})...")
    ok, msg_or_url = fal_client.generate_fal_video(
        image_path=ref_image,
        prompt=prompt,
        duration_s=duration_s,
        output_path=out_video
    )

    if not ok:
        beat_target["video_status"] = "error"
        beat_target["video_error"] = msg_or_url
        with SCENES_LOCK:
            atomic_write_json(scene_file, scene_data, make_backup=False)
        return {"status": "error", "message": f"Falha na geração de vídeo IA: {msg_or_url}"}

    # Extrai o Tail Frame para encadeamento
    has_tail = extract_video_last_frame(out_video, out_tail)

    # Sincroniza mídias com a pasta web/assets
    web_video_file = WEB_DIR / "assets" / f"{clean_shot}.mp4"
    web_tail_file = WEB_DIR / "assets" / f"{clean_shot}_tail.jpg"

    try:
        shutil.copy2(out_video, web_video_file)
        if has_tail and out_tail.exists():
            shutil.copy2(out_tail, web_tail_file)
    except Exception as ex_sync:
        logger.warning(f"Aviso ao sincronizar mídias na web: {ex_sync}")

    rel_video_url = f"assets/{clean_shot}.mp4"
    rel_tail_url = f"assets/{clean_shot}_tail.jpg" if has_tail else None

    # Atualiza a cena
    beat_target["video_status"] = "completed"
    beat_target["video_url"] = rel_video_url
    beat_target["video_duration_s"] = duration_s
    if rel_tail_url:
        beat_target["last_frame_url"] = rel_tail_url

    with SCENES_LOCK:
        atomic_write_json(scene_file, scene_data, make_backup=False)

    return {
        "status": "ok",
        "shot_id": clean_shot,
        "video_url": rel_video_url,
        "last_frame_url": rel_tail_url,
        "duration_s": duration_s,
        "message": f"Vídeo do plano {clean_shot} gerado com sucesso!"
    }


def generate_scene_videos_batch(scene_id: str, project_id: Optional[str] = None) -> str:
    """
    Submete a renderização sequencial de todos os planos de uma cena em lote via task_service.
    Garante encadeamento automático (Tail-to-Head) entre planos consecutivos.
    """
    clean_scene = sanitize_id(scene_id)
    paths = pc.get_current_project_paths(project_id)
    scene_file = paths.scenes_dir / f"{clean_scene}.json"

    if not scene_file.exists():
        raise FileNotFoundError(f"Cena {clean_scene} não encontrada.")

    with open(scene_file, "r", encoding="utf-8") as sf:
        scene_data = json.load(sf)

    beats = scene_data.get("beats", [])
    if not beats:
        raise ValueError(f"Cena {clean_scene} não possui planos decupados.")

    def _batch_runner():
        total = len(beats)
        logger.info(f"[BATCH VÍDEO] Iniciando render de {total} planos para cena {clean_scene}...")
        completed = 0
        errors = []

        for idx, b in enumerate(beats):
            shot_id = b.get("shot_id")
            if not shot_id:
                continue

            current_num = idx + 1
            progress_pct = int((idx / total) * 100)
            task_service.update_task_progress(
                task_id=t_id,
                progress=progress_pct,
                message=f"Renderizando plano {shot_id} ({current_num}/{total})..."
            )

            res = generate_shot_video(
                scene_id=clean_scene,
                shot_id=shot_id,
                project_id=project_id,
                use_chaining=True
            )

            if res.get("status") == "ok":
                completed += 1
            else:
                errors.append(f"{shot_id}: {res.get('message')}")

        logger.info(f"[BATCH VÍDEO] Concluído: {completed}/{total} gerados com sucesso.")
        return {
            "scene_id": clean_scene,
            "total_shots": total,
            "completed": completed,
            "errors": errors
        }

    # Submete a tarefa assíncrona
    t_id = task_service.submit_task(_batch_runner)
    return t_id
