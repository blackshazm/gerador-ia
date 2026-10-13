"""
Montador de Linha do Tempo para CapCut Desktop e Premiere Pro
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
SHOTS_DIR = paths.shots_dir
AUDIO_DIR = paths.audio_dir
RENDERS_DIR = paths.renders_dir
OUTPUT_DIR = paths.timeline_dir

def create_timeline_project(scene_id: str):
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    pacing_file = AUDIO_DIR / f"pacing_report_{scene_id}.json"
    if not pacing_file.exists():
        print(f"Relatório de pacing não encontrado em: {pacing_file}")
        return
        
    with open(pacing_file, "r", encoding="utf-8") as f:
        pacing_data = json.load(f)
        
    manifest = {
        "project_name": f"Tríade_{scene_id}",
        "target_editor": "CapCut Desktop",
        "fps": 24,
        "tracks": {
            "video_v1": [],
            "audio_a1_voice": []
        }
    }
    
    current_time_ms = 0
    
    for item in pacing_data:
        shot_id = item["shot_id"]
        dur_s = item["recommended_video_duration_s"]
        dur_ms = int(dur_s * 1000)
        
        # Vídeo esperado
        video_filename = f"{shot_id}.mp4"
        video_path = RENDERS_DIR / video_filename
        
        manifest["tracks"]["video_v1"].append({
            "shot_id": shot_id,
            "filename": video_filename,
            "expected_path": str(video_path),
            "start_time_ms": current_time_ms,
            "duration_ms": dur_ms,
            "exists_on_disk": video_path.exists()
        })
        
        # Áudio existente
        audio_filename = item["audio_file"]
        audio_path = AUDIO_DIR / audio_filename
        
        manifest["tracks"]["audio_a1_voice"].append({
            "shot_id": shot_id,
            "filename": audio_filename,
            "path": str(audio_path),
            "start_time_ms": current_time_ms,
            "duration_ms": int(item["audio_duration_s"] * 1000)
        })
        
        current_time_ms += dur_ms
        
    manifest_file = OUTPUT_DIR / f"timeline_manifest_{scene_id}.json"
    with open(manifest_file, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

    try:
        from server.services.export_service import generate_capcut_draft_files
        capcut_draft_dir = OUTPUT_DIR / f"capcut_draft_{scene_id}"
        generate_capcut_draft_files(scene_id, pacing_data, paths, capcut_draft_dir)
        print(f"   Rascunho CapCut Desktop criado em: {capcut_draft_dir.relative_to(BASE_DIR)}")
    except Exception as ex_draft:
        print(f"   Aviso ao gerar rascunho CapCut: {ex_draft}")
        
    print(f"\n=======================================================")
    print(f"-> Manifesto de Linha do Tempo gerado com sucesso!")
    print(f"   Duração total da cena: {current_time_ms / 1000:.2f}s")
    print(f"   Arquivo: {manifest_file.relative_to(BASE_DIR)}")
    print(f"=======================================================")

def main():
    AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    reports = list(AUDIO_DIR.glob("pacing_report_*.json"))
    for r in reports:
        scene_id = r.stem.replace("pacing_report_", "")
        create_timeline_project(scene_id)

if __name__ == "__main__":
    main()
