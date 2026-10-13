"""
Módulo de Serviço de Decupagem Narrativa & Direção Cinematográfica — Tríade Studio
Executa o Diretor de Fotografia IA com divisão em atos, regras dos 180°, lente 35mm e planos de 6s.
"""
import os
import re
import json
from pathlib import Path
from typing import Dict, List, Optional

import sys
BASE_DIR = Path(__file__).resolve().parent.parent.parent
SCRIPTS_DIR = BASE_DIR / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import project_context as pc
from server.storage import atomic_write_json, SCENES_LOCK
from llm_client import LLMClient, extract_json_from_text
from server.services.book_service import get_chapter_detail
from server.services.audio_service import generate_scene_audio

from schemas.director_prompts import (
    DIRECTOR_SYSTEM_PROMPT,
    normalize_scene_id,
    format_prompt_with_book_content,
    format_visual_bible_context
)

def split_chapter_into_acts(body_text: str, target_acts: int = 3) -> List[str]:
    """Divide o corpo do capítulo em blocos dramáticos para cobrir toda a extensão sem cortes."""
    paragraphs = [p.strip() for p in body_text.split("\n") if p.strip()]
    if len(paragraphs) <= target_acts:
        return ["\n\n".join(paragraphs)]

    total_chars = sum(len(p) for p in paragraphs)
    chars_per_act = total_chars / target_acts

    acts = []
    current_act = []
    current_len = 0

    for p in paragraphs:
        current_act.append(p)
        current_len += len(p)
        if current_len >= chars_per_act and len(acts) < target_acts - 1:
            acts.append("\n\n".join(current_act))
            current_act = []
            current_len = 0

    if current_act:
        acts.append("\n\n".join(current_act))

    return acts

def decoupage_chapter(
    chapter_num: int,
    provider: Optional[str] = None,
    model: Optional[str] = None,
    project_id: Optional[str] = None
) -> Dict:
    """
    Decupa o capítulo em planos de 6 segundos utilizando o LLM e gera os áudios correspondentes.
    """
    paths = pc.get_current_project_paths(project_id)
    chapter_info = get_chapter_detail(chapter_num, project_id)
    
    # Usa o texto original ou traduzido como base de decupagem
    text_to_decoupage = chapter_info["translated_text"] if chapter_info.get("has_translation") else chapter_info["original_text"]
    title = chapter_info["title"]
    scene_id = normalize_scene_id(chapter_num)

    if not text_to_decoupage.strip():
        raise ValueError(f"Texto do capítulo {chapter_num} vazio ou inexistente.")

    # Carrega Bíblia Visual se existir
    manifest_file = paths.manifest_path
    bible_data = {}
    bible_chars_map = {}
    if manifest_file.exists():
        try:
            with open(manifest_file, "r", encoding="utf-8") as mf:
                bible_data = json.load(mf)
            for c in bible_data.get("characters", []):
                tag = c.get("tag") or f"@{c.get('name', '').lower().replace(' ', '_')}"
                bible_chars_map[tag.lower()] = c
        except Exception:
            pass

    visual_bible_ctx = format_visual_bible_context(bible_data)

    client = LLMClient(provider=provider, model=model)
    acts = split_chapter_into_acts(text_to_decoupage, target_acts=3 if len(text_to_decoupage) > 2500 else 1)
    
    all_beats = []
    scene_location = "Sala de aula do 30º andar da Escola Wayside"
    scene_characters = set()
    scene_props = set()
    scene_rhythm = "Dramatic Suspense & Narrative Flow"

    global_shot_counter = 1

    for act_idx, act_text in enumerate(acts, start=1):
        prompt_user = format_prompt_with_book_content(
            act_text,
            extra_notes=(
                f"Capítulo: {title}\n"
                f"Cena ID: {scene_id}\n"
                f"Ato Dramático: {act_idx} de {len(acts)}\n"
                "Gere entre 3 e 5 planos cinematográficos de 6.0 segundos cobrindo este ato com PROMPTS ULTRA-DETALHADOS.\n"
                "OBRIGATÓRIO: 'characters_present' com tags (@) e descrições físicas ricas; 'scene_environment' e 'props_in_shot'.\n"
                "Lembre-se: 'action_pt' e 'narration' em Português do Brasil; "
                "'image_prompt_en' e 'video_prompt_en' em Inglês técnico de cinema com DNA dos personagens."
            ),
            visual_bible_context=visual_bible_ctx
        )

        messages = [
            {"role": "system", "content": DIRECTOR_SYSTEM_PROMPT},
            {"role": "user", "content": prompt_user}
        ]

        raw_response = client.chat_completion(
            messages=messages,
            temperature=0.4,
            json_mode=True,
            max_tokens=4096
        )

        data = extract_json_from_text(raw_response)
        if not data or "beats" not in data:
            print(f"[Decoupage] Erro no parsing JSON do ato {act_idx}. Tentando recuperação simples.")
            continue

        if data.get("location"):
            scene_location = data["location"]
        if data.get("characters"):
            scene_characters.update(data["characters"])
        if data.get("props"):
            scene_props.update(data["props"])
        if data.get("scene_rhythm"):
            scene_rhythm = data["scene_rhythm"]

        for b in data.get("beats", []):
            shot_id = f"{scene_id}_SH{global_shot_counter:02d}"
            b["shot_id"] = shot_id
            b["target_duration_s"] = 6.0
            
            # Garante que characters_present esteja preenchido
            if "characters_present" not in b or not b["characters_present"]:
                found_tags = re.findall(r"@\w+", f"{b.get('action_pt', '')} {b.get('prompt_en', '')} {b.get('video_prompt_en', '')}")
                b_chars = []
                for t in set(found_tags):
                    tl = t.lower()
                    if tl in bible_chars_map:
                        c_info = bible_chars_map[tl]
                        b_chars.append({
                            "tag": t,
                            "name": c_info.get("name", t),
                            "physical_description": c_info.get("physical_description", "")
                        })
                if b_chars:
                    b["characters_present"] = b_chars

            if "scene_environment" not in b or not b["scene_environment"]:
                b["scene_environment"] = scene_location

            # Garante que os prompts existam
            if "prompt_en" not in b:
                b["prompt_en"] = b.get("video_prompt_en", b.get("image_prompt_en", ""))
                
            all_beats.append(b)
            global_shot_counter += 1

    if not all_beats:
        raise RuntimeError("A IA não retornou nenhum plano válido para este capítulo.")

    final_scene_data = {
        "scene_id": scene_id,
        "title": title,
        "location": scene_location,
        "characters": list(scene_characters),
        "props": list(scene_props),
        "scene_rhythm": scene_rhythm,
        "audio_continuous_block": True,
        "beats": all_beats
    }

    # Salva o arquivo de cena
    paths.scenes_dir.mkdir(parents=True, exist_ok=True)
    scene_file = paths.scenes_dir / f"{scene_id}.json"
    with SCENES_LOCK:
        atomic_write_json(scene_file, final_scene_data, make_backup=True)

    # Dispara a geração dos áudios e cálculo de pacing automaticamente
    try:
        generate_scene_audio(scene_id, project_id=project_id)
    except Exception as e:
        print(f"[Decoupage] Aviso ao gerar áudio automático da cena {scene_id}: {e}")

    return {
        "status": "ok",
        "scene_id": scene_id,
        "total_shots": len(all_beats),
        "message": f"Capítulo {chapter_num} decupado com sucesso em {len(all_beats)} planos de 6s!"
    }
