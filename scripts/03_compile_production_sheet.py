"""
Compilador da Ficha de Produção ("Copiar e Colar") & Payloads Multi-Motor
Pipeline da Tríade - Versão 1.0.0
"""
import os
import json
from pathlib import Path

import sys
BASE_DIR = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = BASE_DIR / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import project_context as pc
paths = pc.get_current_project_paths()
SCENES_DIR = paths.scenes_dir
AUDIO_DIR = paths.audio_dir
SHOTS_DIR = paths.shots_dir

def compile_scene_sheet(scene_path: Path):
    SHOTS_DIR.mkdir(parents=True, exist_ok=True)
    
    with open(scene_path, "r", encoding="utf-8") as f:
        scene = json.load(f)
        
    scene_id = scene.get("scene_id", "SC_01")
    title = scene.get("title", "Cena Sem Título")
    location = scene.get("location", "Ambiente não especificado")
    characters = scene.get("characters", [])
    props = scene.get("props", [])
    beats = scene.get("beats", [])
    
    # Carrega Bíblia Visual para enriquecer personagens, cenários e props
    bible_chars_map = {}
    bible_locs_map = {}
    bible_props_map = {}
    manifest_path = paths.manifest_path
    if manifest_path.exists():
        try:
            with open(manifest_path, "r", encoding="utf-8") as mf:
                b_data = json.load(mf)
            for c in b_data.get("characters", []):
                tag = c.get("tag") or f"@{c.get('name', '').lower().replace(' ', '_')}"
                bible_chars_map[tag.lower()] = c
            for l in b_data.get("locations", []):
                tag = l.get("tag") or f"@{l.get('name', '').lower().replace(' ', '_')}"
                bible_locs_map[tag.lower()] = l
            for p in b_data.get("props", []):
                tag = p.get("tag") or f"@{p.get('name', '').lower().replace(' ', '_')}"
                bible_props_map[tag.lower()] = p
        except Exception:
            pass

    # Carrega relatório de pacing se disponível
    pacing_file = AUDIO_DIR / f"pacing_report_{scene_id}.json"
    pacing_map = {}
    if pacing_file.exists():
        with open(pacing_file, "r", encoding="utf-8") as f:
            for item in json.load(f):
                pacing_map[item["shot_id"]] = item
                
    location_tag = scene.get("location_tag", "@sala_30_andar")
    md_output = []
    md_output.append(f"# CADERNO DE EXECUÇÃO — {scene_id}: \"{title}\"")
    md_output.append(f"> **Uso:** Copie e cole os textos e prompts diretamente nos sites da web (Kling AI, Runway, ElevenLabs, Midjourney, FLUX).\n")
    md_output.append(f"### 📍 Ficha Geral da Cena")
    md_output.append(f"* **ID:** `{scene_id}`")
    md_output.append(f"* **🏛️ Cenário Principal (@tag):** `{location_tag}` — {location}")
    md_output.append(f"* **👤 Personagens em Cena:** {', '.join(f'`{c}`' if not c.startswith('`') else c for c in characters)}")
    md_output.append(f"* **📦 Objetos / Props Centrais:** {', '.join(f'`{p}`' if not p.startswith('`') else p for p in props)}")
    md_output.append(f"* **Total de Planos:** {len(beats)} planos de 6.0s\n")
    md_output.append("---\n")
    
    kling_payloads = []
    veo_payloads = []
    
    for i, beat in enumerate(beats, start=1):
        shot_id = beat.get("shot_id", f"{scene_id}_SH{i:02d}")
        shot_type = beat.get("shot_type", "Medium Shot")
        lens_mm = beat.get("lens_mm", 50)
        camera_move = beat.get("camera_movement", "Slow optical push-in")
        eyeline = beat.get("eyeline_match", "screen_center")
        narration = beat.get("narration", "")
        action_pt = beat.get("action_pt", "")
        prompt_image = beat.get("image_prompt_en") or beat.get("prompt_en", "")
        prompt_video = beat.get("video_prompt_en") or beat.get("prompt_en", "")
        prompt_neg = beat.get("negative_prompt", "cartoon, 3d render, CGI, smooth plastic skin, deformed hands, extra fingers, morphing face, temporal flicker, low bitrate, modern technology, oversaturated, watermark, blurry background, distorted limbs")
        start_frame = beat.get("start_frame_instruction", "")
        kling_sliders = beat.get("kling_camera_controls", {"zoom": 0.0, "horizontal": 0.0, "vertical": 0.0, "tilt": 0.0, "pan": 0.0, "roll": 0.0})
        
        # Elementos específicos deste plano
        chars_present = beat.get("characters_present", [])
        if not chars_present:
            # Fallback buscando tags no texto
            import re
            found_tags = set(re.findall(r"@\w+", f"{action_pt} {prompt_image} {prompt_video}"))
            for t in found_tags:
                tl = t.lower()
                if tl in bible_chars_map:
                    c_info = bible_chars_map[tl]
                    chars_present.append({
                        "tag": t,
                        "name": c_info.get("name", t),
                        "physical_description": c_info.get("physical_description", "")
                    })
        
        loc_tag = beat.get("location_tag", location_tag)
        loc_name = beat.get("location_name", location)
        scene_env = beat.get("scene_environment") or location
        props_in_shot = beat.get("props_in_shot", [])
        props_present = beat.get("props_present", [])
        if not props_present and props_in_shot:
            for pt in props_in_shot:
                p_info = bible_props_map.get(pt.lower()) or {}
                props_present.append({
                    "tag": pt,
                    "name": p_info.get("name", pt.replace("@", "").title()),
                    "description": p_info.get("description", "Objeto em cena.")
                })
        
        # Pega duração ajustada pelo áudio
        pacing_info = pacing_map.get(shot_id)
        if pacing_info:
            dur_video = pacing_info.get("recommended_video_duration_s", 6.0)
            dur_audio = pacing_info.get("audio_duration_s", 6.0)
        else:
            dur_video = beat.get("duration_s", 6.0)
            dur_audio = "6.0"
            
        md_output.append(f"## 🎬 PLANO {i:02d} — `{shot_id}` ({dur_video}s) — {shot_type} ({lens_mm}mm)")
        md_output.append(f"**Ação & Subtexto Dramático (PT-BR):**\n{action_pt}\n")
        
        # Bloco de Elementos em Cena
        md_output.append("### 📋 ELEMENTOS PRESENTES NA CENA (O QUE EXISTE NO PLANO):")
        if chars_present:
            md_output.append("* **👤 Personagens em Cena:**")
            for cp in chars_present:
                c_tag = cp.get("tag", "@personagem")
                c_name = cp.get("name", "")
                c_desc = cp.get("physical_description", "Sem descrição física")
                md_output.append(f"  * `{c_tag}` ({c_name}): {c_desc}")
        else:
            md_output.append("* **👤 Personagens em Cena:** Ambiente / Objetos em destaque (sem personagens principais).")
            
        md_output.append(f"* **🏛️ Cenário & Iluminação (@tag):** `{loc_tag}` ({loc_name}) — {scene_env}")
        if props_present:
            md_output.append(f"* **📦 Objetos / Props em Jogo (@tags):**")
            for pp in props_present:
                md_output.append(f"  * `{pp.get('tag')}` ({pp.get('name')}): {pp.get('description')}")
        elif props_in_shot:
            md_output.append(f"* **📦 Objetos / Props em Jogo (@tags):** {', '.join(f'`{p}`' for p in props_in_shot)}")
        md_output.append(f"* **🎥 Câmera & Óptica:** Lente {lens_mm}mm Anamórfica | Movimento: {camera_move} | Eyeline: {eyeline}\n")
        
        # 1. Bloco de Voz
        md_output.append("### 🎙️ 1. NO SITE DE VOZ / NARRAÇÃO (ElevenLabs ou Edge-TTS):")
        md_output.append(f"> **Texto para Locução (Copie e cole):**")
        md_output.append(f"```text\n{narration}\n```")
        md_output.append(f"*(Duração prevista do áudio: {dur_audio}s)*\n")
        
        # 2. Bloco de Imagem (Start Frame)
        md_output.append("### 🖼️ 2. NO SITE DE IMAGEM / START FRAME (FLUX.1 / Midjourney / Imagen 3):")
        if start_frame:
            md_output.append(f"* **Instrução de Continuidade:** {start_frame}")
        md_output.append(f"> **Prompt de Imagem (Copie e cole):**")
        md_output.append(f"```text\n{prompt_image}\n```\n")
        
        # 3. Bloco de Vídeo
        md_output.append("### 🎬 3. NO SITE DE VÍDEO (Kling AI / Runway Gen-3 / Luma / Veo 2):")
        md_output.append(f"* **Duração no Site:** `6s` (ou `5s/10s` conforme motor)")
        md_output.append(f"> **Prompt de Vídeo com Dinâmica Temporal (Copie e cole):**")
        md_output.append(f"```text\n{prompt_video}\n```\n")
        
        # 4. Sliders de Câmera
        md_output.append("### 🎛️ 4. CONTROLES DE CÂMERA NO SITE (Sliders Kling AI):")
        has_slider = False
        for k, v in kling_sliders.items():
            if v != 0.0:
                has_slider = True
                md_output.append(f"* **{k.capitalize()}:** `{v:+0.1f}`")
        if not has_slider:
            md_output.append("* Câmera Estática / Padrão (Sem movimento)")
        md_output.append("")
            
        # 5. Negativo
        md_output.append("### 🚫 5. PROMPT NEGATIVO (Anti-Artefatos):")
        md_output.append(f"```text\n{prompt_neg}\n```\n")
        md_output.append("---\n")
        
        # Salva payloads individuais estruturados
        kling_payloads.append({
            "shot_id": shot_id,
            "target_engine": "kling_v2",
            "duration_s": dur_video,
            "characters_present": chars_present,
            "prompt_image": prompt_image,
            "prompt_video": prompt_video,
            "negative_prompt": prompt_neg,
            "camera_controls": kling_sliders,
            "start_frame": start_frame
        })
        
        veo_payloads.append({
            "shot_id": shot_id,
            "target_engine": "veo_3.1",
            "duration_s": dur_video,
            "prompt": f"Maintain subject. {shot_type}, {lens_mm}mm, {camera_move}. {prompt_video}",
            "negative_prompt": prompt_neg,
            "reference_image": start_frame
        })
        
    # Instruções de montagem no final da ficha
    md_output.append("## ✂️ Ordem de Montagem no CapCut Desktop / Premiere")
    md_output.append("1. Baixe os vídeos gerados e arraste para a linha do tempo na ordem dos planos:")
    order_str = " ➔ ".join([f"`{b.get('shot_id', f'SH{idx:02d}')}`" for idx, b in enumerate(beats, start=1)])
    md_output.append(f"   {order_str}")
    md_output.append("2. Arraste os arquivos `.mp3` correspondentes da pasta `05_audio/` para a trilha de áudio logo abaixo de cada vídeo.")
    md_output.append("3. Adicione a música de ambiência com volume baixo (-20dB) e ative a legenda automática.")
    
    # Grava o arquivo de Caderno
    sheet_path = SHOTS_DIR / f"CADERNO_EXECUCAO_{scene_id}.md"
    with open(sheet_path, "w", encoding="utf-8") as f:
        f.write("\n".join(md_output))
        
    # Grava os payloads de API
    with open(SHOTS_DIR / f"payload_kling_{scene_id}.json", "w", encoding="utf-8") as f:
        json.dump(kling_payloads, f, indent=2, ensure_ascii=False)
        
    with open(SHOTS_DIR / f"payload_veo_{scene_id}.json", "w", encoding="utf-8") as f:
        json.dump(veo_payloads, f, indent=2, ensure_ascii=False)
        
    print(f"\n-> Sucesso! Caderno de Execução gerado em:\n   {sheet_path.relative_to(BASE_DIR)}")
    return sheet_path

def main():
    SCENES_DIR.mkdir(parents=True, exist_ok=True)
    scenes = list(SCENES_DIR.glob("*.json"))
    
    if not scenes:
        print(f"Nenhum arquivo de cena encontrado em: {SCENES_DIR}")
        return
        
    for scene_file in scenes:
        compile_scene_sheet(scene_file)

if __name__ == "__main__":
    main()
