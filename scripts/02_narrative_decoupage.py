"""
Módulo de Decupagem Narrativa & Regras Cinematográficas de 6 Segundos com IA
Pipeline da Tríade Studio — Versão 2.0.0 (Autônomo com LLM)

Integra smixs + DirectorSKILL + Regras dos 180° + 6 Segundos por plano.
Consome OpenRouter, NVIDIA NIM ou Ollama local.
"""
import os
import re
import sys
import json
import argparse
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = BASE_DIR / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

import project_context as pc
paths = pc.get_current_project_paths()
NORMALIZED_DIR = paths.normalized_dir
SCENES_DIR = paths.scenes_dir
BIBLE_DIR = paths.bible_dir
MANIFEST_PATH = paths.manifest_path

def get_default_book_path() -> Path:
    md_files = list(NORMALIZED_DIR.glob("*.md"))
    if md_files:
        return md_files[0]
    return NORMALIZED_DIR / "livro_limpo.md"

try:
    from llm_client import LLMClient, extract_json_from_text, load_env
except ImportError:
    from scripts.llm_client import LLMClient, extract_json_from_text, load_env

from schemas.director_prompts import (
    DIRECTOR_SYSTEM_PROMPT,
    normalize_scene_id,
    format_prompt_with_book_content,
    format_visual_bible_context
)

def extract_chapter_text(markdown_path: Path, chapter_num: int) -> dict:
    """Extrai o texto integral de um capítulo específico, ignorando índices/sumários."""
    if not markdown_path.exists():
        raise FileNotFoundError(f"Arquivo de texto não encontrado: {markdown_path}")

    with open(markdown_path, "r", encoding="utf-8") as f:
        content = f.read()

    next_ch = chapter_num + 1
    # Padrão universal agnóstico que captura o bloco do capítulo até o próximo ou fim do arquivo
    pattern = rf"(?:^|\n)\s*(?:g\s+)?(?:#+\s*)?(?:Chapter|Capítulo|Capitulo|Cena|Scene)\s+{chapter_num}\b[\s\S]*?(?=(?:^|\n)\s*(?:g\s+)?(?:#+\s*)?(?:Chapter|Capítulo|Capitulo|Cena|Scene)\s+{next_ch}\b|\Z)"
    matches = [m.group(0).strip() for m in re.finditer(pattern, content, re.IGNORECASE) if len(m.group(0).strip()) > 50]

    if not matches:
        # Fallback tolerante para o último capítulo até o fim do documento
        pattern_last = rf"(?:^|\n)\s*(?:g\s+)?(?:#+\s*)?(?:Chapter|Capítulo|Capitulo)\s+{chapter_num}\b[\s\S]*?\Z"
        matches = [m.group(0).strip() for m in re.finditer(pattern_last, content, re.IGNORECASE) if len(m.group(0).strip()) > 50]

    if not matches:
        raise ValueError(f"Capítulo {chapter_num} não encontrado no texto com conteúdo substancial.")

    full_chunk = matches[-1]
    # Extrai título na primeira linha
    lines = [line.strip() for line in full_chunk.split("\n") if line.strip()]
    raw_title = lines[0] if lines else f"Capítulo {chapter_num}"
    # Remove prefixos 'g' soltos
    raw_title = re.sub(r"^g\s+", "", raw_title).strip()
    body = "\n".join(lines[1:]) if len(lines) > 1 else full_chunk

    return {
        "chapter_num": chapter_num,
        "title": raw_title,
        "body": body
    }

def load_visual_bible():
    """Carrega referências da Bíblia Visual se existirem."""
    if MANIFEST_PATH.exists():
        try:
            with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"characters": {}, "locations": {}, "props": {}}

def split_chapter_into_acts(body_text: str, target_acts: int = 4) -> list:
    """Divide o corpo do capítulo em blocos dramáticos mantendo parágrafos e diálogos íntegros."""
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

def decoupage_act_with_ai(client: LLMClient, scene_id: str, chapter_title: str, act_num: int, total_acts: int, act_text: str, visual_bible_context: str = "") -> list:
    """Decupa um ato dramático específico gerando entre 4 e 5 planos cinematográficos ricos com prompts ultra-detalhados."""
    book_block = format_prompt_with_book_content(
        act_text,
        extra_notes=(
            f"Capítulo: {chapter_title}\n"
            f"Ato: {act_num}/{total_acts}\n"
            "Gere exatamente 4 a 5 planos de 6.0 segundos cobrindo TODOS os diálogos e ações físicas deste trecho.\n"
            "OBRIGATÓRIO: Identifique 'characters_present' com tags (@) e descrições físicas ricas; inclua 'scene_environment' e 'props_in_shot'.\n"
            "Os campos 'image_prompt_en' e 'video_prompt_en' DEVEM incluir a descrição física detalhada dos personagens, iluminação volumétrica e lentes 35mm.\n"
            "Responda APENAS com um objeto JSON contendo o array 'beats'."
        ),
        visual_bible_context=visual_bible_context
    )
    user_prompt = f"IMPORTANTE: Inicie sua resposta imediatamente com '{{' e termine com '}}'. Sem thinking process.\n\n{book_block}"

    messages = [
        {"role": "system", "content": DIRECTOR_SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt}
    ]

    print(f"  -> Decupando Ato {act_num}/{total_acts} ({len(act_text)} caracteres)...")
    raw_response = client.chat_completion(messages, temperature=0.3, json_mode=True, max_tokens=6000)
    act_json = extract_json_from_text(raw_response)
    return act_json.get("beats", [])

def decoupage_full_chapter(chapter_data: dict, provider: str = None, model: str = None) -> dict:
    """
    Decupagem cinematográfica COMPLETA do capítulo:
    Segmenta a narrativa em atos e decupa cada um com a IA, gerando uma sequência contínua de 16 a 24 planos.
    """
    client = LLMClient(provider=provider, model=model)
    scene_id = normalize_scene_id(chapter_data['chapter_num'])
    acts = split_chapter_into_acts(chapter_data["body"], target_acts=4)

    # Carrega Bíblia Visual
    bible_data = load_visual_bible()
    bible_context = format_visual_bible_context(bible_data)

    bible_chars_map = {}
    for c in bible_data.get("characters", []):
        tag = c.get("tag") or f"@{c.get('name', '').lower().replace(' ', '_')}"
        bible_chars_map[tag.lower()] = c

    bible_locations_map = {}
    for l in bible_data.get("locations", []):
        tag = l.get("tag") or f"@{l.get('name', '').lower().replace(' ', '_')}"
        bible_locations_map[tag.lower()] = l

    bible_props_map = {}
    for p in bible_data.get("props", []):
        tag = p.get("tag") or f"@{p.get('name', '').lower().replace(' ', '_')}"
        bible_props_map[tag.lower()] = p

    print(f"\n[DECUPAGEM COMPLETA] Capítulo {chapter_data['chapter_num']} dividido em {len(acts)} atos dramáticos.")
    if bible_context:
        print(f"  -> Bíblia Visual carregada ({len(bible_chars_map)} personagens, {len(bible_locations_map)} cenários, {len(bible_props_map)} props).")

    all_beats = []

    for act_idx, act_text in enumerate(acts, start=1):
        try:
            beats = decoupage_act_with_ai(client, scene_id, chapter_data["title"], act_idx, len(acts), act_text, visual_bible_context=bible_context)
            all_beats.extend(beats)
        except Exception as e:
            print(f"  [Aviso] Falha no Ato {act_idx}: {e}. Continuando com os demais atos...")

    # Se nenhum beat foi gerado por falha de API, fallback de segurança
    if not all_beats:
        raise RuntimeError("Não foi possível gerar planos para o capítulo.")

    # Renumera e enriquece todos os planos sequencialmente com tags canônicas (@)
    for idx, beat in enumerate(all_beats, start=1):
        beat["shot_id"] = f"{scene_id}_SH{idx:02d}"
        if "target_duration_s" not in beat:
            beat["target_duration_s"] = 6.0
        if "kling_camera_controls" not in beat:
            beat["kling_camera_controls"] = {"zoom": 0.0, "horizontal": 0.0, "vertical": 0.0, "tilt": 0.0, "pan": 0.0, "roll": 0.0}

        # 1. Enriquecimento de Locação / Cenário com @
        loc_tag = beat.get("location_tag") or "@sala_30_andar"
        if not loc_tag.startswith("@"):
            loc_tag = f"@{loc_tag}"
        beat["location_tag"] = loc_tag
        loc_info = bible_locations_map.get(loc_tag.lower()) or bible_locations_map.get("@sala_30_andar", {})
        beat["location_name"] = loc_info.get("name", "Sala do 30º Andar (Wayside School)")
        beat["location_image"] = loc_info.get("image_primary", "assets/sala_30_andar.jpg")

        if "scene_environment" not in beat or not beat["scene_environment"]:
            beat["scene_environment"] = loc_info.get("description", "Sala de aula do 30º andar da Escola Wayside, janelas altas de guilhotina, carteiras escolares de madeira, luz volumétrica de fim de tarde.")

        # 2. Garante enriquecimento dos personagens presentes a partir da Bíblia se omitido
        if "characters_present" not in beat or not beat["characters_present"]:
            found_tags = re.findall(r"@\w+", f"{beat.get('action_pt', '')} {beat.get('prompt_en', '')} {beat.get('video_prompt_en', '')}")
            beat_chars = []
            for t in set(found_tags):
                tl = t.lower()
                if tl in bible_chars_map:
                    c_info = bible_chars_map[tl]
                    beat_chars.append({
                        "tag": t,
                        "name": c_info.get("name", t),
                        "physical_description": c_info.get("physical_description", "")
                    })
            if beat_chars:
                beat["characters_present"] = beat_chars

        # 3. Enriquecimento Completo de Objetos / Props com tags @
        beat_text = f"{beat.get('action_pt', '')} {beat.get('narration', '')} {beat.get('prompt_en', '')} {beat.get('video_prompt_en', '')}".lower()
        detected_props = list(beat.get("props_in_shot") or [])

        # Detecção inteligente por palavras-chave dramáticas
        if any(w in beat_text for w in ["maçã", "maca", "apple"]):
            detected_props.append("@maca_vermelha")
        if any(w in beat_text for w in ["giz", "lousa", "quadro", "chalk", "blackboard"]):
            detected_props.append("@giz_lousa")
        if any(w in beat_text for w in ["prova", "caderno", "copiou", "copiar", "aritmética", "somar", "test", "notebook"]):
            detected_props.append("@caderno_prova")
        if any(w in beat_text for w in ["lápis", "lapis", "pencil"]):
            detected_props.append("@lapis_amarelo")
        if any(w in beat_text for w in ["espelho", "bolsa", "mirror", "reflexo"]):
            detected_props.append("@espelho_bolsa")
        if any(w in beat_text for w in ["patins", "skate", "roller"]):
            detected_props.append("@patins_vintage")
        if any(w in beat_text for w in ["apito", "recreio", "louis", "whistle"]):
            detected_props.append("@apito_louis")
        if any(w in beat_text for w in ["orelha", "orelhas", "ear", "ears"]):
            detected_props.append("@orelhasgorf")
        if any(w in beat_text for w in ["língua", "lingua", "tongue"]):
            detected_props.append("@lingua_gorf")
        if any(w in beat_text for w in ["carteira", "mesa", "desk"]):
            detected_props.append("@carteira_escolar")

        # Fallback para garantir que NENHUM plano fique sem props essenciais
        if not detected_props:
            detected_props = ["@maca_vermelha", "@giz_lousa"]

        normalized_props = []
        for p in detected_props:
            p_tag = p if p.startswith("@") else f"@{p}"
            if p_tag not in normalized_props:
                normalized_props.append(p_tag)
        beat["props_in_shot"] = normalized_props

        # Constrói objetos detalhados de props_present
        props_present = []
        for pt in normalized_props:
            p_info = bible_props_map.get(pt.lower()) or {}
            props_present.append({
                "tag": pt,
                "name": p_info.get("name", pt.replace("@", "").replace("_", " ").title()),
                "description": p_info.get("description", "Objeto/adereço físico em cena.")
            })
        beat["props_present"] = props_present

        # Garante prompts enriquecidos de imagem e vídeo
        v_prompt = beat.get("video_prompt_en") or beat.get("prompt_en", "")
        i_prompt = beat.get("image_prompt_en") or beat.get("prompt_en", "")
        beat["video_prompt_en"] = v_prompt
        beat["image_prompt_en"] = i_prompt
        beat["prompt_en"] = v_prompt or i_prompt
        if "negative_prompt" not in beat:
            beat["negative_prompt"] = "cartoon, 3d render, CGI, smooth plastic skin, deformed hands, extra fingers, morphing face, temporal flicker, low bitrate, modern technology, oversaturated, watermark, blurry background"

    # Extrai personagens e locações presentes nos beats
    characters = list(set(re.findall(r"@\w+", json.dumps(all_beats))))
    if not characters:
        characters = ["@dona_gorf", "@joe", "@todd"]

    all_scene_props = []
    for b in all_beats:
        for p in b.get("props_in_shot", []):
            if p not in all_scene_props:
                all_scene_props.append(p)

    full_scene_json = {
        "scene_id": scene_id,
        "title": chapter_data["title"],
        "location": "Sala do 30º Andar (Wayside School)",
        "location_tag": "@sala_30_andar",
        "locations": ["@sala_30_andar"],
        "characters": characters[:5],
        "props": all_scene_props,
        "scene_rhythm": "Dramatic Suspense & Fast Cuts",
        "audio_continuous_block": True,
        "beats": all_beats
    }

    return full_scene_json

def generate_decoupage_for_chapter(chapter_num: int, provider: str = None, model: str = None, output_file: Path = None) -> Path:
    """Executa a decupagem completa e detalhada de todo o capítulo."""
    SCENES_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Extrai o texto integral
    book_file = get_default_book_path()
    chapter_data = extract_chapter_text(book_file, chapter_num)
    print(f"-> Capítulo {chapter_num}: {chapter_data['title']} ({len(chapter_data['body'])} caracteres)")

    # 2. Decupa todos os atos narrativos com IA
    scene_json = decoupage_full_chapter(chapter_data, provider=provider, model=model)

    # 3. Salva a cena completa
    scene_id = scene_json["scene_id"]
    if not output_file:
        output_file = SCENES_DIR / f"{scene_id}.json"

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(scene_json, f, indent=2, ensure_ascii=False)

    print(f"\n[OK] Decupagem COMPLETA finalizada com SUCESSO!")
    print(f"     Total de Planos de 6s: {len(scene_json['beats'])} planos")
    print(f"     Duração Estimada: {len(scene_json['beats']) * 6} segundos (~{round((len(scene_json['beats']) * 6)/60, 1)} minutos)")
    print(f"     Arquivo salvo em: {output_file.relative_to(BASE_DIR)}")
    return output_file

def main():
    parser = argparse.ArgumentParser(description="Decupador Narrativo Completo com IA da Tríade Studio")
    parser.add_argument("--chapter", type=int, default=1, help="Número do capítulo a decupar (default: 1)")
    parser.add_argument("--provider", type=str, default=None, help="Provedor de IA (gemini, openrouter, nvidia, ollama)")
    parser.add_argument("--model", type=str, default=None, help="Modelo específico a utilizar")
    args = parser.parse_args()

    print("\n=======================================================")
    print(f"-> Tríade Studio: Decupagem COMPLETA em Atos Dramáticos")
    print(f"-> Capítulo: {args.chapter} | Provedor: {args.provider or 'Automático'}")
    print("=======================================================")

    try:
        out_path = generate_decoupage_for_chapter(args.chapter, provider=args.provider, model=args.model)
        print(f"\n-> Sucesso! A cena completa já está pronta para geração de áudio e visualização no Studio Web.")
    except Exception as e:
        print(f"\n[ERRO] Falha na decupagem: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()

