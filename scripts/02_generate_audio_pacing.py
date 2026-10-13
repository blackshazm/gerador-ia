"""
Módulo de Áudio & Pacing: Síntese de Voz e Medição de Tempo dos Cortes
Pipeline da Tríade - Versão 1.0.0
"""
import os
import json
import asyncio
from pathlib import Path

try:
    import edge_tts
    import mutagen.mp3
    AUDIO_DEPS_AVAILABLE = True
except ImportError:
    AUDIO_DEPS_AVAILABLE = False

BASE_DIR = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = BASE_DIR / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import project_context as pc
paths = pc.get_current_project_paths()
SCENES_DIR = paths.scenes_dir
AUDIO_DIR = paths.audio_dir

DEFAULT_VOICE = "pt-BR-AntonioNeural"  # Voz madura e sóbria para narrativa

async def synthesize_beat(text: str, voice: str, output_path: Path) -> float:
    """
    Gera o áudio neural e retorna a duração exata em segundos.
    """
    communicate = edge_tts.Communicate(text, voice, rate="-4%", pitch="-2Hz")
    await communicate.save(str(output_path))
    
    audio = mutagen.mp3.MP3(str(output_path))
    duration_s = round(audio.info.length, 2)
    return duration_s

async def process_scene_audio(scene_json_path: Path):
    if not AUDIO_DEPS_AVAILABLE:
        print("ERRO: edge-tts ou mutagen não instalados. Execute: pip install edge-tts mutagen")
        return

    with open(scene_json_path, "r", encoding="utf-8") as f:
        scene_data = json.load(f)
        
    scene_id = scene_data.get("scene_id", "SC_01")
    beats = scene_data.get("beats", [])
    
    AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    
    print(f"\n=======================================================")
    print(f"-> Gerando Locução e Pacing para a Cena: {scene_id}")
    print(f"=======================================================")
    
    pacing_results = []
    
    for i, beat in enumerate(beats, start=1):
        shot_id = beat.get("shot_id", f"{scene_id}_SH{i:02d}")
        narration_text = beat.get("narration", "")
        
        if not narration_text:
            continue
            
        audio_filename = f"{shot_id}_voice.mp3"
        audio_path = AUDIO_DIR / audio_filename
        
        print(f"[{shot_id}] Gerando voz para: \"{narration_text[:45]}...\"")
        duration_s = await synthesize_beat(narration_text, DEFAULT_VOICE, audio_path)
        
        # Regra de Pacing: Duração do Áudio + 0.8s de respiro visual
        # Mínimo de 3.5s para estabilidade do modelo de vídeo
        video_duration_s = max(3.5, round(duration_s + 0.8, 1))
        
        beat_info = {
            "shot_id": shot_id,
            "narration": narration_text,
            "audio_file": audio_filename,
            "audio_duration_s": duration_s,
            "recommended_video_duration_s": video_duration_s
        }
        pacing_results.append(beat_info)
        print(f"      -> Áudio: {duration_s}s | Vídeo planejado: {video_duration_s}s")
        
    report_file = AUDIO_DIR / f"pacing_report_{scene_id}.json"
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(pacing_results, f, indent=2, ensure_ascii=False)
        
    print(f"\n-> Relatório de Pacing salvo em:\n   {report_file.relative_to(BASE_DIR)}")
    return pacing_results

def main():
    SCENES_DIR.mkdir(parents=True, exist_ok=True)
    scenes = list(SCENES_DIR.glob("*.json"))
    
    if not scenes:
        print(f"Nenhum arquivo de cena encontrado em: {SCENES_DIR}")
        return
        
    for scene_file in scenes:
        asyncio.run(process_scene_audio(scene_file))

if __name__ == "__main__":
    main()
