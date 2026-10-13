"""
Módulo de Serviço de Exportação para Linha do Tempo — Tríade Studio
Gera manifestos de montagem sincronizados e estrutura de projeto pronta para CapCut Desktop.
"""
import os
import json
from pathlib import Path
from typing import Dict, List, Optional

import sys
BASE_DIR = Path(__file__).resolve().parent.parent.parent
SCRIPTS_DIR = BASE_DIR / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import project_context as pc

def export_timeline_manifest(scene_id: Optional[str] = None, project_id: Optional[str] = None) -> Dict:
    """
    Exporta a linha do tempo sincronizada (áudios contínuos + cortes de vídeo em milissegundos).
    """
    paths = pc.get_current_project_paths(project_id)
    paths.timeline_dir.mkdir(parents=True, exist_ok=True)

    scenes_to_export = []
    if scene_id:
        pacing_file = paths.audio_dir / f"pacing_report_{scene_id}.json"
        if pacing_file.exists():
            scenes_to_export.append((scene_id, pacing_file))
    else:
        # Pega todas as cenas com áudio gerado
        for pf in sorted(paths.audio_dir.glob("pacing_report_*.json")):
            s_id = pf.stem.replace("pacing_report_", "")
            scenes_to_export.append((s_id, pf))

    if not scenes_to_export:
        # Fallback: pega cenas diretas de 03_scenes se não houver pacing ainda
        for sf in sorted(paths.scenes_dir.glob("*.json")):
            s_id = sf.stem
            scenes_to_export.append((s_id, None))

    results = []

    for s_id, pf in scenes_to_export:
        manifest = {
            "project_name": f"Triade_{s_id}",
            "target_editor": "CapCut Desktop",
            "fps": 24,
            "tracks": {
                "video_v1": [],
                "audio_a1_voice": []
            }
        }

        current_time_ms = 0
        pacing_data = []

        if pf and pf.exists():
            try:
                with open(pf, "r", encoding="utf-8") as f:
                    pacing_data = json.load(f)
            except Exception:
                pass

        if not pacing_data:
            # Carrega do JSON da cena
            scene_file = paths.scenes_dir / f"{s_id}.json"
            if scene_file.exists():
                try:
                    with open(scene_file, "r", encoding="utf-8") as f:
                        sc_raw = json.load(f)
                        for b in sc_raw.get("beats", []):
                            pacing_data.append({
                                "shot_id": b.get("shot_id", "SH_01"),
                                "recommended_video_duration_s": b.get("duration_s", 6.0),
                                "audio_file": f"{b.get('shot_id', 'SH_01')}.mp3",
                                "audio_duration_s": b.get("duration_s", 6.0)
                            })
                except Exception:
                    pass

        for item in pacing_data:
            shot_id = item["shot_id"]
            dur_s = item.get("recommended_video_duration_s", 6.0)
            dur_ms = int(dur_s * 1000)

            video_filename = f"{shot_id}.mp4"
            video_path = paths.renders_dir / video_filename

            manifest["tracks"]["video_v1"].append({
                "shot_id": shot_id,
                "filename": video_filename,
                "expected_path": str(video_path),
                "start_time_ms": current_time_ms,
                "duration_ms": dur_ms,
                "exists_on_disk": video_path.exists()
            })

            audio_filename = item.get("audio_file", f"{shot_id}.mp3")
            audio_path = paths.audio_dir / audio_filename

            manifest["tracks"]["audio_a1_voice"].append({
                "shot_id": shot_id,
                "filename": audio_filename,
                "path": str(audio_path),
                "start_time_ms": current_time_ms,
                "duration_ms": int(item.get("audio_duration_s", dur_s) * 1000)
            })

            current_time_ms += dur_ms

        manifest_file = paths.timeline_dir / f"timeline_manifest_{s_id}.json"
        with open(manifest_file, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2, ensure_ascii=False)

        # Gera o rascunho nativo do CapCut Desktop (draft_content.json + draft_meta_info.json)
        capcut_draft_dir = paths.timeline_dir / f"capcut_draft_{s_id}"
        generate_capcut_draft_files(s_id, pacing_data, paths, capcut_draft_dir)

        # Sincroniza opcionalmente com a pasta do CapCut Desktop se o usuário tiver no Windows
        local_app_data = os.environ.get("LOCALAPPDATA")
        capcut_installed_dir = None
        if local_app_data:
            capcut_root = Path(local_app_data) / "CapCut" / "User Data" / "Projects" / "com.lveditor.draft"
            if capcut_root.parent.exists():
                capcut_root.mkdir(parents=True, exist_ok=True)
                capcut_installed_dir = capcut_root / f"Triade_{s_id}"
                generate_capcut_draft_files(s_id, pacing_data, paths, capcut_installed_dir)

        results.append({
            "scene_id": s_id,
            "manifest_file": manifest_file.name,
            "capcut_draft_folder": capcut_draft_dir.name,
            "capcut_installed_sync": str(capcut_installed_dir) if capcut_installed_dir else None,
            "total_duration_s": round(current_time_ms / 1000, 2),
            "total_clips": len(pacing_data)
        })

    return {
        "status": "ok",
        "message": "Manifestos e Rascunhos do CapCut Desktop exportados com sucesso em 07_timeline_export!",
        "exports": results
    }


def generate_capcut_draft_files(scene_id: str, pacing_data: List[Dict], paths, output_draft_dir: Path):
    """
    Gera draft_content.json e draft_meta_info.json com resolução 1080p, 24fps e tracks V1 e A1.
    """
    import uuid
    import time

    output_draft_dir.mkdir(parents=True, exist_ok=True)
    draft_id = str(uuid.uuid4()).upper()

    video_materials = []
    audio_materials = []
    video_segments = []
    audio_segments = []

    current_time_us = 0

    for idx, item in enumerate(pacing_data):
        shot_id = item.get("shot_id", f"SH_{idx+1:02d}")
        dur_s = float(item.get("recommended_video_duration_s") or item.get("audio_duration_s") or 5.0)
        dur_us = int(dur_s * 1_000_000)

        # Vídeo ou Imagem de storyboard
        video_filename = f"{shot_id}.mp4"
        video_path = paths.renders_dir / video_filename
        is_video = video_path.exists()

        if not is_video:
            # Fallback para imagem storyboard se o vídeo ainda não foi renderizado
            image_path = paths.renders_dir / f"{shot_id}.jpg"
            if image_path.exists():
                media_path = str(image_path)
                mat_type = "photo"
            else:
                media_path = str(video_path)
                mat_type = "video"
        else:
            media_path = str(video_path)
            mat_type = "video"

        v_mat_id = f"mat_v_{shot_id}_{idx}"
        video_materials.append({
            "id": v_mat_id,
            "path": media_path,
            "material_name": Path(media_path).name,
            "type": mat_type,
            "duration": dur_us,
            "width": 1920,
            "height": 1080
        })

        v_seg_id = f"seg_v_{shot_id}_{idx}"
        video_segments.append({
            "id": v_seg_id,
            "material_id": v_mat_id,
            "source_timerange": {"start": 0, "duration": dur_us},
            "target_timerange": {"start": current_time_us, "duration": dur_us},
            "speed": 1.0,
            "volume": 1.0,
            "render_index": idx
        })

        # Áudio
        audio_filename = item.get("audio_file", f"{shot_id}.mp3")
        audio_path = paths.audio_dir / audio_filename
        a_dur_s = float(item.get("audio_duration_s") or dur_s)
        a_dur_us = int(a_dur_s * 1_000_000)

        a_mat_id = f"mat_a_{shot_id}_{idx}"
        audio_materials.append({
            "id": a_mat_id,
            "path": str(audio_path),
            "name": audio_filename,
            "type": "extract_music",
            "duration": a_dur_us
        })

        a_seg_id = f"seg_a_{shot_id}_{idx}"
        audio_segments.append({
            "id": a_seg_id,
            "material_id": a_mat_id,
            "source_timerange": {"start": 0, "duration": a_dur_us},
            "target_timerange": {"start": current_time_us, "duration": a_dur_us},
            "speed": 1.0,
            "volume": 1.0,
            "render_index": idx
        })

        current_time_us += dur_us

    draft_content = {
        "id": draft_id,
        "fps": 24.0,
        "duration": current_time_us,
        "canvas_config": {"width": 1920, "height": 1080, "ratio": "original"},
        "materials": {
            "videos": video_materials,
            "audios": audio_materials
        },
        "tracks": [
            {
                "id": f"track_v1_{draft_id[:8]}",
                "type": "video",
                "name": "V1",
                "segments": video_segments
            },
            {
                "id": f"track_a1_{draft_id[:8]}",
                "type": "audio",
                "name": "A1_Voz",
                "segments": audio_segments
            }
        ]
    }

    draft_meta = {
        "draft_id": draft_id,
        "draft_name": f"Triade_{scene_id}",
        "draft_fold_path": str(output_draft_dir),
        "tm_duration": current_time_us,
        "tm_draft_create": int(time.time()),
        "tm_draft_modify": int(time.time())
    }

    with open(output_draft_dir / "draft_content.json", "w", encoding="utf-8") as f:
        json.dump(draft_content, f, indent=2, ensure_ascii=False)

    with open(output_draft_dir / "draft_meta_info.json", "w", encoding="utf-8") as f:
        json.dump(draft_meta, f, indent=2, ensure_ascii=False)
