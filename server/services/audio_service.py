"""
Módulo de Serviço de Áudio & Locução Neural — Tríade Studio
Sintetiza locuções com Edge-TTS / ElevenLabs e mede a duração milimétrica de cada beat.
"""
import os
import json
import asyncio
from pathlib import Path
from typing import Dict, List, Optional

import sys
BASE_DIR = Path(__file__).resolve().parent.parent.parent
SCRIPTS_DIR = BASE_DIR / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import project_context as pc
from server.storage import atomic_write_json, SCENES_LOCK

try:
    import edge_tts
    import mutagen.mp3
    AUDIO_DEPS_AVAILABLE = True
except ImportError:
    AUDIO_DEPS_AVAILABLE = False

DEFAULT_VOICE = "pt-BR-AntonioNeural"

async def _synthesize_file(text: str, voice: str, output_path: Path) -> float:
    """Gera o áudio neural MP3 e retorna a duração em segundos."""
    communicate = edge_tts.Communicate(text, voice, rate="-4%", pitch="-2Hz")
    await communicate.save(str(output_path))
    
    audio = mutagen.mp3.MP3(str(output_path))
    return round(audio.info.length, 2)

def generate_scene_audio(scene_id: str, voice: str = DEFAULT_VOICE, project_id: Optional[str] = None) -> Dict:
    """
    Gera todos os arquivos de áudio para os beats de uma cena e grava o relatório de pacing.
    """
    if not AUDIO_DEPS_AVAILABLE:
        raise RuntimeError("Dependências edge-tts ou mutagen não instaladas. Execute: pip install edge-tts mutagen")

    paths = pc.get_current_project_paths(project_id)
    scene_file = paths.scenes_dir / f"{scene_id}.json"
    if not scene_file.exists():
        matches = list(paths.scenes_dir.glob(f"*{scene_id}*.json"))
        if matches:
            scene_file = matches[0]
        else:
            raise FileNotFoundError(f"Cena {scene_id} não encontrada em {paths.scenes_dir}")

    with open(scene_file, "r", encoding="utf-8") as f:
        scene_data = json.load(f)

    beats = scene_data.get("beats", [])
    paths.audio_dir.mkdir(parents=True, exist_ok=True)

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    pacing_results = []
    updated_beats = False

    try:
        for i, beat in enumerate(beats, start=1):
            shot_id = beat.get("shot_id", f"{scene_id}_SH{i:02d}")
            narration = beat.get("narration", "").strip()
            
            if not narration:
                narration = beat.get("action_pt", "Cena em silêncio dramático.")

            audio_filename = f"{shot_id}.mp3"
            audio_out_path = paths.audio_dir / audio_filename

            # Sintetiza o áudio se não existir ou se solicitado
            try:
                duration_s = loop.run_until_complete(_synthesize_file(narration, voice, audio_out_path))
            except Exception as e:
                print(f"[AudioService] Erro ao sintetizar {shot_id}: {e}")
                duration_s = 6.0

            target_duration = beat.get("target_duration_s", 6.0)
            recommended_video_dur = max(target_duration, duration_s + 0.8)

            # Atualiza o próprio beat se a duração medida for maior que a padrão
            beat["duration_s"] = duration_s
            beat["audio_file"] = f"/api/audio/{audio_filename}"
            updated_beats = True

            pacing_results.append({
                "shot_id": shot_id,
                "narration_text": narration,
                "audio_file": audio_filename,
                "audio_duration_s": duration_s,
                "target_duration_s": target_duration,
                "recommended_video_duration_s": round(recommended_video_dur, 2)
            })

        # Salva o relatório de pacing
        report_file = paths.audio_dir / f"pacing_report_{scene_id}.json"
        atomic_write_json(report_file, pacing_results, make_backup=False)

        # Salva os beats atualizados com os caminhos de áudio na cena
        if updated_beats:
            with SCENES_LOCK:
                atomic_write_json(scene_file, scene_data, make_backup=True)

    finally:
        loop.close()

    total_time = sum(p["recommended_video_duration_s"] for p in pacing_results)
    return {
        "status": "ok",
        "scene_id": scene_id,
        "total_shots": len(pacing_results),
        "total_duration_s": round(total_time, 2),
        "pacing": pacing_results
    }
