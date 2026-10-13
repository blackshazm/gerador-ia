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
    beats = scene.get("beats", [])
    
    # Carrega relatório de pacing se disponível
    pacing_file = AUDIO_DIR / f"pacing_report_{scene_id}.json"
    pacing_map = {}
    if pacing_file.exists():
        with open(pacing_file, "r", encoding="utf-8") as f:
            for item in json.load(f):
                pacing_map[item["shot_id"]] = item
                
    md_output = []
    md_output.append(f"# CADERNO DE EXECUÇÃO — {scene_id}: \"{title}\"")
    md_output.append(f"> **Uso:** Copie e cole os textos e prompts diretamente nos sites da web (Kling AI, Runway, ElevenLabs, etc.).\n")
    md_output.append(f"### 📍 Ficha da Cena")
    md_output.append(f"* **ID:** `{scene_id}`")
    md_output.append(f"* **Locação:** {location}")
    md_output.append(f"* **Personagens:** {', '.join(characters)}")
    md_output.append(f"* **Total de Planos:** {len(beats)} planos\n")
    md_output.append("---\n")
    
    kling_payloads = []
    veo_payloads = []
    
    for i, beat in enumerate(beats, start=1):
        shot_id = beat.get("shot_id", f"{scene_id}_SH{i:02d}")
        shot_type = beat.get("shot_type", "Medium Shot")
        lens_mm = beat.get("lens_mm", 50)
        camera_move = beat.get("camera_movement", "Slow push-in")
        narration = beat.get("narration", "")
        prompt_pos = beat.get("prompt_en", "")
        prompt_neg = beat.get("negative_prompt", "cartoon, 3d render, smiling, bad anatomy, deformed hands, face mutation, blurry, watermark")
        start_frame = beat.get("start_frame_instruction", "")
        kling_sliders = beat.get("kling_camera_controls", {"zoom": 0.0, "horizontal": 0.0, "vertical": 0.0, "tilt": 0.0, "pan": 0.0, "roll": 0.0})
        
        # Pega duração ajustada pelo áudio
        pacing_info = pacing_map.get(shot_id)
        if pacing_info:
            dur_video = pacing_info["recommended_video_duration_s"]
            dur_audio = pacing_info["audio_duration_s"]
        else:
            dur_video = beat.get("duration_s", 5.0)
            dur_audio = "A calcular"
            
        md_output.append(f"## 🎬 PLANO {i:02d} — `{shot_id}` ({dur_video}s) — {shot_type} ({lens_mm}mm)")
        md_output.append(f"**Ação do Plano:** {beat.get('action_pt', '')}\n")
        
        # Bloco de Voz
        md_output.append("### 1. No site de Voz / Narração (ElevenLabs ou Edge-TTS):")
        md_output.append(f"> **Texto para Locução (Copie e cole):**")
        md_output.append(f"```text\n{narration}\n```")
        md_output.append(f"*(Duração prevista do áudio: {dur_audio}s)*\n")
        
        # Bloco de Vídeo
        md_output.append("### 2. No site de Vídeo (Kling AI / Runway / Veo):")
        md_output.append(f"* **🖼️ Imagem de Entrada (Start Frame):** {start_frame}")
        md_output.append("* **🎛️ Controles de Câmera no Site:**")
        for k, v in kling_sliders.items():
            if v != 0.0:
                md_output.append(f"  * **{k.capitalize()}:** `{v:+0.1f}`")
        if all(v == 0.0 for v in kling_sliders.values()):
            md_output.append(f"  * Câmera Estática / Padrão (Sem movimento)")
            
        md_output.append(f"* **📝 Prompt Positivo (Copie e cole no site):**")
        md_output.append(f"```text\n{prompt_pos}\n```")
        
        md_output.append(f"* **🚫 Prompt Negativo (Copie e cole no site):**")
        md_output.append(f"```text\n{prompt_neg}\n```\n")
        md_output.append("---\n")
        
        # Salva payloads individuais estruturados
        kling_payloads.append({
            "shot_id": shot_id,
            "target_engine": "kling_v2",
            "duration_s": dur_video,
            "prompt": prompt_pos,
            "negative_prompt": prompt_neg,
            "camera_controls": kling_sliders,
            "start_frame": start_frame
        })
        
        veo_payloads.append({
            "shot_id": shot_id,
            "target_engine": "veo_3.1",
            "duration_s": dur_video,
            "prompt": f"Maintain subject. {shot_type}, {lens_mm}mm, {camera_move}. {prompt_pos}",
            "negative_prompt": prompt_neg,
            "reference_image": start_frame
        })
        
    # Instruções de montagem no final da ficha
    md_output.append("## ✂️ Ordem de Montagem no CapCut Desktop")
    md_output.append("1. Arraste os vídeos baixados para a linha do tempo na ordem dos planos:")
    order_str = " ➔ ".join([f"`{b.get('shot_id', f'SH{idx:02d}')}`" for idx, b in enumerate(beats, start=1)])
    md_output.append(f"   {order_str}")
    md_output.append("2. Arraste os arquivos `.mp3` correspondentes da pasta `05_audio/` para a trilha de áudio logo abaixo de cada vídeo.")
    md_output.append("3. Adicione a música de fundo com volume baixo (-20dB) e ative a legenda automática.")
    
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
