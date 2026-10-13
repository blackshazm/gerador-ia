"""
Orquestrador de Produção em Lote do Livro — Tríade Studio
Processa capítulos do livro em Markdown dividindo em Atos Dramáticos -> Cenas -> Planos de 6s,
sincroniza com a Bíblia Visual, sintetiza a locução neural PT-BR e gera cadernos e timelines.
"""
import os
import sys
import json
import re
import time
import argparse
import asyncio
from pathlib import Path

# Suporte UTF-8 no terminal Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Adiciona o diretório de scripts ao path
BASE_DIR = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = BASE_DIR / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from llm_client import LLMClient

# Importa módulos locais de suporte
try:
    import edge_tts
    import mutagen.mp3
    AUDIO_AVAILABLE = True
except ImportError:
    AUDIO_AVAILABLE = False

import project_context as pc
paths = pc.get_current_project_paths()
NORM_DIR = paths.normalized_dir
SCENES_DIR = paths.scenes_dir
SHOTS_DIR = paths.shots_dir
AUDIO_DIR = paths.audio_dir
TIMELINE_DIR = paths.timeline_dir
BIBLE_FILE = paths.manifest_path

DEFAULT_VOICE = "pt-BR-AntonioNeural"

def get_book_text() -> str:
    md_files = list(NORM_DIR.glob("*.md"))
    if not md_files:
        raise FileNotFoundError(f"Nenhum arquivo markdown encontrado em {NORM_DIR}")
    with open(md_files[0], "r", encoding="utf-8", errors="ignore") as f:
        return f.read()

def extract_chapter_content(full_text: str, chapter_num: int) -> tuple[str, str]:
    """
    Localiza e extrai o texto integral do capítulo específico ignorando sumários.
    Retorna (titulo_do_capitulo, texto_integral).
    """
    next_ch = chapter_num + 1
    # Padrão universal para Capítulo / Chapter com ou sem OCR g e pontuações
    pattern = rf"(?:^|\n)\s*(?:g\s+)?(?:#+\s*)?(?:Chapter|Capítulo|Capitulo|Cena|Scene)\s+{chapter_num}\b[:.\-—]?[ \t]*([^\n\r]*)\n([\s\S]*?)(?=(?:^|\n)\s*(?:g\s+)?(?:#+\s*)?(?:Chapter|Capítulo|Capitulo|Cena|Scene)\s+{next_ch}\b|\Z)"
    match = re.search(pattern, full_text, re.IGNORECASE)
    
    if not match:
        pattern_fallback = rf"(?:^|\n)\s*(?:g\s+)?(?:Chapter|Capítulo|Capitulo)\s+{chapter_num}\b[^\n]*\n([\s\S]*?)(?=(?:^|\n)\s*(?:g\s+)?(?:Chapter|Capítulo|Capitulo)\s+{next_ch}\b|\Z)"
        match = re.search(pattern_fallback, full_text, re.IGNORECASE)
        if match:
            return f"Capítulo {chapter_num}", match.group(1).strip()
        raise ValueError(f"Capítulo {chapter_num} não encontrado no livro.")
        
    raw_name = match.group(1).strip()
    clean_name = raw_name.splitlines()[0].strip() if raw_name else f"Parte {chapter_num}"
    clean_name = re.sub(r"\s+", " ", clean_name)
    title = f"Capítulo {chapter_num} — {clean_name}"
    content = match.group(2).strip()
    return title, content

def split_chapter_into_acts(chapter_text: str, num_acts: int = 3) -> list[dict]:
    """Divide o capítulo em atos dramáticos equilibrados por parágrafos."""
    paragraphs = [p.strip() for p in chapter_text.split("\n\n") if p.strip()]
    if len(paragraphs) < num_acts:
        paragraphs = [p.strip() for p in chapter_text.split("\n") if p.strip()]
    
    total = len(paragraphs)
    chunk_size = max(1, total // num_acts)
    acts = []
    
    act_names = [
        "Ato 1: Introdução & Situação Inicial",
        "Ato 2: Conflito Central & Complicações",
        "Ato 3: Clímax & Desfecho Cômico/Dramático",
        "Ato 4: Epílogo & Resolução"
    ]
    
    for i in range(num_acts):
        start = i * chunk_size
        end = (i + 1) * chunk_size if i < num_acts - 1 else total
        act_text = "\n\n".join(paragraphs[start:end])
        acts.append({
            "act_number": i + 1,
            "act_name": act_names[i] if i < len(act_names) else f"Ato {i+1}",
            "text": act_text
        })
    return acts

def decoupage_act_with_llm(llm: LLMClient, act: dict, scene_id: str, chapter_title: str, start_shot_idx: int) -> list[dict]:
    """Gera planos contínuos de 6 segundos com ação em PT-BR e prompts técnicos hiper-detalhados de imagem e vídeo."""
    system_prompt = (
        "Você é um Diretor de Cinema e Decupador Profissional da Tríade Studio.\n"
        "Sua missão é decupar o trecho da história em PLANOS CINEMATOGRÁFICOS CONTÍNUOS DE 6 SEGUNDOS (Live-Action Fotorrealista 35mm).\n"
        "REGRAS INEGOCIÁVEIS:\n"
        "1. NÃO RESUMA! Cada fala, reação, objeto e acontecimento do texto deve ser um plano específico.\n"
        "2. 'action_pt': Descreva em Português do Brasil com riqueza dramática: micro-expressões (olhar, tensão muscular, respiração), ação corporal precisa e iluminação.\n"
        "3. 'narration': Diálogo ou narração em Português do Brasil, pronto para locução contínua (L-Cut).\n"
        "4. 'image_prompt_en' (Start Frame para FLUX / Midjourney): Detalhe câmera de cinema (Arri Alexa LF / 35mm), lente física e abertura (ex: 50mm f/1.8), iluminação volumétrica com temperatura Kelvin (3200K tungstênio / 5600K daylight), texturas hiper-reais de pele (subsurface scattering, poros) e tecidos autênticos, grão 35mm, 8k.\n"
        "5. 'video_prompt_en' (Dinâmica de Movimento 6s para Kling / Runway / Veo): Descreva a física temporal segundo a segundo (0-2s: postura inicial; 2-4s: ação física; 4-6s: reação/desfecho), movimento suave de câmera e termos: 24fps film shutter look, fluid natural motion, stable coherence.\n"
        "6. 'start_frame_instruction': Instrução clara de continuidade visual entre planos.\n"
        "7. 'negative_prompt': Termos cirúrgicos anti-deformação e anti-flicker.\n"
        "8. Retorne APENAS um JSON válido contendo a chave 'shots' com a lista de planos."
    )
    
    user_prompt = f"""CENA: {scene_id} ({chapter_title})
PARTE DRAMÁTICA: {act['act_name']}
TEXTO DO TRECHO:
\"\"\"{act['text']}\"\"\"

Gere entre 4 a 7 planos para este trecho, numerados a partir de {start_shot_idx}.
Formato JSON obrigatório:
{{
  "shots": [
    {{
      "shot_id": "{scene_id}_SH{start_shot_idx:02d}",
      "role": "action_threat | reaction | establishing | climax",
      "target_duration_s": 6.0,
      "shot_type": "Wide Shot | Medium Shot | Close-up | Insert",
      "lens_mm": 50,
      "eyeline_match": "screen_left | screen_right",
      "camera_movement": "Slow 24fps push-in frontal | Static | Tracking shot",
      "action_pt": "Descrição detalhada em português da ação física, micro-expressões e atmosfera de luz.",
      "narration": "Texto da fala ou narração em português.",
      "start_frame_instruction": "Usar último frame do plano anterior ou referência de personagem.",
      "kling_camera_controls": {{ "zoom": 1.0, "horizontal": 0.0, "vertical": 0.0, "tilt": 0.0, "pan": 0.0, "roll": 0.0 }},
      "image_prompt_en": "Cinematic portrait shot, Arri Alexa 65, 50mm Master Prime f/1.8, warm 3200K side lighting, photorealistic skin pores, authentic period fabric textures, 35mm film grain, 8k...",
      "video_prompt_en": "Continuous 6-second shot. Subject begins breathing subtly, slowly shifts gaze with tension building over 6 seconds, smooth 24fps push-in camera movement, fluid organic motion...",
      "prompt_en": "Cinematic 50mm shot, photorealistic, 24fps movie look, film grain...",
      "negative_prompt": "cartoon, 3d render, CGI, plastic skin, deformed hands, extra limbs, temporal flicker, low bitrate, blurry, watermark"
    }}
  ]
}}"""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]
    
    try:
        response_text = llm.chat_completion(messages, temperature=0.4, json_mode=True, max_tokens=3500)
        parsed = llm.safe_parse_json(response_text)
        shots = parsed.get("shots", [])
        if not shots and isinstance(parsed, list):
            shots = parsed
        return shots
    except Exception as e:
        print(f"[Orquestrador] Erro ao decupar {act['act_name']}: {e}")
        return []

def extract_and_update_bible(llm: LLMClient, chapter_title: str, chapter_text: str):
    """Analisa o texto do capítulo e atualiza a Bíblia Visual com novos personagens e props."""
    if not BIBLE_FILE.exists():
        return
        
    try:
        with open(BIBLE_FILE, "r", encoding="utf-8") as f:
            bible = json.load(f)
    except Exception:
        bible = {"characters": [], "locations": [], "props": []}
        
    existing_tags = {c.get("tag") for c in bible.get("characters", [])}
    existing_props = {p.get("tag") for p in bible.get("props", [])}
    
    prompt = f"""Você é o Diretor de Arte da Tríade Studio.
Analise o capítulo \"{chapter_title}\" da Wayside School e identifique os PERSONAGENS e PROPS principais introduzidos.
Texto:
\"\"\"{chapter_text[:2500]}\"\"\"

Retorne APENAS um JSON no formato:
{{
  "new_characters": [
    {{
      "tag": "@nome_personagem",
      "name": "Nome Completo (em PT-BR)",
      "role": "Papel dramático",
      "physical_description": "Descrição física detalhada em português (idade, traços, roupas)",
      "casting_prompt_realistic": "Ultra-detailed studio portrait photograph of [character], front-facing eye level, 85mm lens, f/1.8, soft directional studio lighting, subsurface scattering on skin, visible skin pores, fine hair strands, authentic period wardrobe textures, neutral studio background, 35mm film still, 8k --ar 1:1",
      "casting_prompt_stylized": "Stylized 3D animated character design of [character], Disney Pixar animation studio aesthetic, subsurface scattering, vibrant lighting, expressive facial proportions, RenderMan quality, 8k --ar 1:1"
    }}
  ],
  "new_props": [
    {{
      "tag": "@nome_prop",
      "name": "Nome do Objeto",
      "description": "Descrição visual em português",
      "casting_prompt_realistic": "Cinematic close-up product photograph of [prop], 85mm macro lens, f/2.8, shallow depth of field, dramatic rim lighting, tactile aged surface texture, scratches and micro-details, 8k --ar 1:1",
      "casting_prompt_stylized": "Stylized 3D animated hero prop design of [prop], Pixar aesthetic, vibrant colors, soft volumetric lighting, Octane render, 8k --ar 1:1"
    }}
  ]
}}"""

    messages = [
        {"role": "system", "content": "Extraia personagens e adereços no formato JSON estruturado."},
        {"role": "user", "content": prompt}
    ]
    
    try:
        resp = llm.chat_completion(messages, temperature=0.3, json_mode=True, max_tokens=1500)
        data = llm.safe_parse_json(resp)
        
        updated = False
        for char in data.get("new_characters", []):
            tag = char.get("tag", "").lower().replace(" ", "_")
            if not tag.startswith("@"):
                tag = f"@{tag}"
            char["tag"] = tag
            if tag not in existing_tags:
                char["image_primary"] = "web/assets/dona_gorf_p1.jpg"
                bible.setdefault("characters", []).append(char)
                existing_tags.add(tag)
                updated = True
                print(f"[Bíblia Visual] + Novo Personagem: {char.get('name')} ({tag})")
                
        for prop in data.get("new_props", []):
            tag = prop.get("tag", "").lower().replace(" ", "_")
            if not tag.startswith("@"):
                tag = f"@{tag}"
            prop["tag"] = tag
            if tag not in existing_props:
                prop["image_primary"] = "web/assets/maca_vermelha.jpg"
                bible.setdefault("props", []).append(prop)
                existing_props.add(tag)
                updated = True
                print(f"[Bíblia Visual] + Novo Prop: {prop.get('name')} ({tag})")
                
        if updated:
            with open(BIBLE_FILE, "w", encoding="utf-8") as f:
                json.dump(bible, f, indent=2, ensure_ascii=False)
            print(f"[Bíblia Visual] Atualizada com sucesso em: {BIBLE_FILE.relative_to(BASE_DIR)}")
    except Exception as e:
        print(f"[Bíblia Visual] Aviso ao atualizar artefatos: {e}")

async def synthesize_scene_audio(scene_data: dict) -> list[dict]:
    """Gera a locução em português via Edge-TTS para todos os planos da cena."""
    if not AUDIO_AVAILABLE:
        print("[Áudio] Edge-TTS ou mutagen não disponíveis. Pulando síntese.")
        return []
        
    scene_id = scene_data.get("scene_id", "SC_01")
    beats = scene_data.get("beats", [])
    AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    
    pacing_results = []
    print(f"\n-> Sintetizando Locução Neural (Edge-TTS) para {scene_id} ({len(beats)} planos)...")
    
    for beat in beats:
        shot_id = beat.get("shot_id")
        narration = beat.get("narration", "")
        if not narration:
            continue
            
        audio_filename = f"{shot_id}_voice.mp3"
        audio_path = AUDIO_DIR / audio_filename
        
        try:
            communicate = edge_tts.Communicate(narration, DEFAULT_VOICE, rate="-3%", pitch="-2Hz")
            await communicate.save(str(audio_path))
            
            audio = mutagen.mp3.MP3(str(audio_path))
            duration_s = round(audio.info.length, 2)
            video_duration_s = max(3.5, round(duration_s + 0.8, 1))
            
            pacing_results.append({
                "shot_id": shot_id,
                "narration": narration,
                "audio_file": audio_filename,
                "audio_duration_s": duration_s,
                "recommended_video_duration_s": video_duration_s
            })
            beat["duration_s"] = video_duration_s
            beat["audio_duration_s"] = duration_s
            beat["audio_file"] = audio_filename
        except Exception as e:
            print(f"   [!] Erro no áudio de {shot_id}: {e}")
            
    report_file = AUDIO_DIR / f"pacing_report_{scene_id}.json"
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(pacing_results, f, indent=2, ensure_ascii=False)
        
    return pacing_results

def compile_caderno_and_timeline(scene_data: dict):
    """Compila o Caderno de Execução Markdown e a Timeline do CapCut."""
    scene_id = scene_data.get("scene_id", "SC_01")
    beats = scene_data.get("beats", [])
    
    # 1. Caderno de Produção
    SHOTS_DIR.mkdir(parents=True, exist_ok=True)
    caderno_path = SHOTS_DIR / f"CADERNO_EXECUCAO_{scene_id}.md"
    
    lines = [
        f"# Caderno de Produção — {scene_id}",
        f"**Título:** {scene_data.get('title', '')}",
        f"**Ambiente:** {scene_data.get('location', '')}",
        f"**Total de Planos:** {len(beats)} planos contínuos (~6s)",
        "",
        "---",
        ""
    ]
    
    for i, beat in enumerate(beats, start=1):
        lines.extend([
            f"## Plano {i:02d} — {beat.get('shot_id')}",
            f"- **Enquadramento:** {beat.get('shot_type')} | Lente: {beat.get('lens_mm', 50)}mm",
            f"- **Movimento de Câmera:** {beat.get('camera_movement', 'Estática')}",
            f"- **Ação em Cena (PT-BR):** {beat.get('action_pt', '')}",
            f"- **Locução / Diálogo:** \"{beat.get('narration', '')}\"",
            f"- **Continuidade / Start Frame:** {beat.get('start_frame_instruction', '')}",
            f"- **Prompt de Vídeo (Kling/Veo):**",
            f"```text\n{beat.get('prompt_en', '')}\n```",
            f"- **Prompt Negativo:** `{beat.get('negative_prompt', '')}`",
            "",
            "---",
            ""
        ])
        
    with open(caderno_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"[Caderno] Gerado em: {caderno_path.relative_to(BASE_DIR)}")
    
    # 2. Manifesto de Timeline
    TIMELINE_DIR.mkdir(parents=True, exist_ok=True)
    timeline_path = TIMELINE_DIR / f"timeline_manifest_{scene_id}.json"
    
    total_time = 0.0
    timeline_tracks = []
    for beat in beats:
        dur = beat.get("duration_s", 6.0)
        timeline_tracks.append({
            "shot_id": beat.get("shot_id"),
            "start_time_s": round(total_time, 2),
            "end_time_s": round(total_time + dur, 2),
            "duration_s": dur,
            "narration": beat.get("narration"),
            "audio_file": beat.get("audio_file")
        })
        total_time += dur
        
    timeline_manifest = {
        "scene_id": scene_id,
        "title": scene_data.get("title"),
        "total_duration_s": round(total_time, 2),
        "total_shots": len(beats),
        "cuts": timeline_tracks
    }
    with open(timeline_path, "w", encoding="utf-8") as f:
        json.dump(timeline_manifest, f, indent=2, ensure_ascii=False)
    print(f"[Timeline] Salva em: {timeline_path.relative_to(BASE_DIR)} ({round(total_time, 1)}s)")

def process_single_chapter(chapter_num: int, llm: LLMClient = None) -> dict:
    """Executa a esteira completa para 1 capítulo específico."""
    if llm is None:
        llm = LLMClient()
        
    scene_id = f"SC_{chapter_num:02d}"
    print(f"\n=======================================================")
    print(f"🎬 Processando Capítulo {chapter_num} -> Cena: {scene_id}")
    print(f"=======================================================")
    
    full_text = get_book_text()
    title, chapter_text = extract_chapter_content(full_text, chapter_num)
    print(f"-> Título: {title}")
    print(f"-> Tamanho do texto: {len(chapter_text)} caracteres")
    
    # 1. Atualiza a Bíblia Visual com entidades do capítulo
    print("\n[Passo 1/4] Extraindo personagens e adereços para a Bíblia Visual...")
    extract_and_update_bible(llm, title, chapter_text)
    
    # 2. Divide em Atos e Decupa Planos de 6s
    print("\n[Passo 2/4] Fatiando em Atos Dramáticos e Decupando Planos de 6s com IA...")
    acts = split_chapter_into_acts(chapter_text, num_acts=3)
    all_beats = []
    current_shot_idx = 1
    
    for act in acts:
        print(f"   -> Decupando {act['act_name']}...")
        shots = decoupage_act_with_llm(llm, act, scene_id, title, current_shot_idx)
        if shots:
            for s in shots:
                if "shot_id" not in s or not s["shot_id"]:
                    s["shot_id"] = f"{scene_id}_SH{current_shot_idx:02d}"
                all_beats.append(s)
                current_shot_idx += 1
        time.sleep(1.0) # Proteção de rate-limit
        
    print(f"-> Total de planos contínuos gerados: {len(all_beats)}")
    
    scene_data = {
        "scene_id": scene_id,
        "title": title,
        "location": "Sala de aula do 30º andar da Escola Wayside",
        "chapter_number": chapter_num,
        "scene_rhythm": "Dynamic Character Comedy & Cinematic Tension",
        "audio_continuous_block": True,
        "beats": all_beats
    }
    
    # 3. Síntese de Áudio Neural PT-BR
    print("\n[Passo 3/4] Sintetizando Locução Neural (Edge-TTS) e Pacing...")
    if AUDIO_AVAILABLE and all_beats:
        asyncio.run(synthesize_scene_audio(scene_data))
        
    # Salva o arquivo de cena JSON final com durações atualizadas
    SCENES_DIR.mkdir(parents=True, exist_ok=True)
    scene_json_file = SCENES_DIR / f"{scene_id}.json"
    with open(scene_json_file, "w", encoding="utf-8") as f:
        json.dump(scene_data, f, indent=2, ensure_ascii=False)
    print(f"-> Cena JSON salva em: {scene_json_file.relative_to(BASE_DIR)}")
    
    # 4. Compila Caderno e Timeline CapCut
    print("\n[Passo 4/4] Compilando Caderno de Produção e Linha do Tempo...")
    compile_caderno_and_timeline(scene_data)
    
    print(f"\n✅ Capítulo {chapter_num} concluído com sucesso!")
    return scene_data

def main():
    parser = argparse.ArgumentParser(description="Orquestrador em Lote do Tríade Studio")
    parser.add_argument("--chapter", type=int, help="Número do capítulo a processar (1 a 30)")
    parser.add_argument("--chapters", nargs="+", type=int, help="Lista de capítulos (ex: --chapters 2 3 4)")
    parser.add_argument("--all", action="store_true", help="Processar todos os 30 capítulos do livro")
    parser.add_argument("--provider", default="openrouter", help="Provedor LLM (openrouter, nvidia, ollama)")
    args = parser.parse_args()
    
    llm = LLMClient(provider=args.provider)
    
    if args.chapter:
        process_single_chapter(args.chapter, llm)
    elif args.chapters:
        for c in args.chapters:
            process_single_chapter(c, llm)
            time.sleep(2.0)
    elif args.all:
        print("🚀 Iniciando esteira de produção para todos os 30 capítulos!")
        for c in range(1, 31):
            try:
                process_single_chapter(c, llm)
                time.sleep(2.0)
            except Exception as e:
                print(f"[!] Erro no capítulo {c}: {e}")
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
