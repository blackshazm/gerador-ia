"""
Script de Enriquecimento Cinematográfico & Eliminação de Templates Genéricos
Tríade Studio — Transforma prompts simplistas em decupagens de cinema profissional.
"""
import os
import re
import json
import shutil
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
SCENES_DIR = BASE_DIR / "projects" / "wayside_school" / "03_scenes"
BIBLE_DIR = BASE_DIR / "projects" / "wayside_school" / "02_visual_bible"
MANIFEST_PATH = BIBLE_DIR / "manifest.json"
WEB_ASSETS_DIR = BASE_DIR / "web" / "assets"

SC_01_ENRICHMENTS = {
    "SC01_SH01": {
        "lens_mm": 35,
        "camera_movement": "Slow optical push-in frontal",
        "kling_camera_controls": {"zoom": 1.5, "horizontal": 0.0, "vertical": 0.0, "tilt": 0.0, "pan": 0.0, "roll": 0.0},
        "image_prompt_en": "Cinematic wide establishing shot, Arri Alexa 65, 35mm Master Prime lens, f/1.8. Cold late-afternoon volumetric light casting long dramatic shadows through tall windows on the 30th floor. Strict tall teacher Mrs. Gorf stands motionless before a vintage dark chalkboard, wearing an austere high-collar tweed dress with subtle pointed ears, staring sternly down at seated students in soft focus. Floating dust particles in light shafts, authentic 1970s school texture, 35mm film grain, 8k resolution --ar 16:9",
        "video_prompt_en": "Continuous 6.0-second cinematic wide shot at 24fps. 0-2s: Mrs. Gorf stands motionless before the chalkboard, harsh cold window light highlighting her severe silhouette. 2-4s: Slow optical push-in camera movement as she subtly raises her chin and casts a sharp, piercing gaze across the desks. 4-6s: Tension builds as dust motes drift through the beam of light, camera gently drifting forward, natural 24fps motion blur, zero morphing, photorealistic cinema."
    },
    "SC01_SH02": {
        "lens_mm": 50,
        "camera_movement": "Low-angle subtle push-in",
        "kling_camera_controls": {"zoom": 2.0, "horizontal": 0.0, "vertical": 0.5, "tilt": -1.5, "pan": 0.0, "roll": 0.0},
        "image_prompt_en": "Cinematic medium close-up, 50mm Master Prime, f/2.0. Mrs. Gorf leaning menacingly over the teacher desk, white knuckles pressed into dark oak wood. Piercing cold eyes, narrow sinister mouth, pointed ears silhouetted against the chalkboard, harsh directional tungsten lighting, tactile skin pore texture, authentic wool fabric wrinkles, photorealistic 35mm still, 8k --ar 16:9",
        "video_prompt_en": "Continuous 6.0-second medium close-up at 24fps. 0-2s: Mrs. Gorf leans forward over the dark desk, knuckles tensing on the wood surface. 2-4s: Her lips part as she delivers her menacing threat, nostrils slightly flaring, eyes narrowing in chilling focus. 4-6s: Slight low-angle camera push-in emphasizing her imposing authority, steady breathing, fluid cinematic physics, zero morphing."
    },
    "SC01_SH03": {
        "lens_mm": 50,
        "camera_movement": "Slow lateral drift",
        "kling_camera_controls": {"zoom": 1.0, "horizontal": -1.0, "vertical": 0.0, "tilt": 0.0, "pan": 0.0, "roll": 0.0},
        "image_prompt_en": "Cinematic medium shot, 50mm lens, f/2.0. Young curly-haired boy Joe sitting at a scratched wooden school desk, holding a chewed yellow pencil with trembling fingers. Terrified expression, sweat on forehead, eyes nervously darting toward the desk beside him, soft window daylight, depth of field blurring the background, 35mm film look, 8k --ar 16:9",
        "video_prompt_en": "Continuous 6.0-second medium shot at 24fps. 0-2s: Joe clutches his pencil with shaking hands, nervously gulping. 2-4s: He stretches his neck and darts his anxious eyes sideways, peeking at the test paper on John's adjacent desk. 4-6s: Slow subtle lateral camera drift framing his panic, natural human micro-movements, authentic film shutter speed, stable temporal coherence."
    },
    "SC01_SH04": {
        "lens_mm": 85,
        "camera_movement": "Macro tracking zoom",
        "kling_camera_controls": {"zoom": 2.5, "horizontal": 0.0, "vertical": 0.0, "tilt": 0.0, "pan": 0.0, "roll": 0.0},
        "image_prompt_en": "Cinematic macro shot, 85mm macro lens, f/2.8. Extreme close-up of Mrs. Gorf's sharp pointed ear twitching, high-contrast side lighting highlighting individual peach fuzz hairs and cartilage texture, blurred chalkboard background, dramatic filmic tension, 8k --ar 16:9",
        "video_prompt_en": "Continuous 6.0-second macro shot at 24fps. 0-2s: Extreme close-up on Mrs. Gorf's right ear in sharp focus. 2-4s: The pointed ear twitches precisely twice in a bizarre mechanical motion as she initiates her curse. 4-6s: Camera slowly pulls in slightly with subtle optical depth, sharp focus on skin and hair details, clean organic motion blur, zero distortion."
    },
    "SC01_SH05": {
        "lens_mm": 50,
        "camera_movement": "Rapid push-in with whip tension",
        "kling_camera_controls": {"zoom": 2.0, "horizontal": 0.0, "vertical": 0.0, "tilt": 0.0, "pan": 0.0, "roll": 0.0},
        "image_prompt_en": "Cinematic close-up, 50mm lens, f/1.8. Mrs. Gorf extending a long narrow tongue outward while staring fixedly with cruel wide eyes, green chalkboard behind her, volumetric light, eerie tension, photorealistic 35mm cinema still, 8k --ar 16:9",
        "video_prompt_en": "Continuous 6.0-second close-up take at 24fps. 0-2s: Mrs. Gorf's eyes widen with sinister delight. 2-4s: Her pointed tongue sticks out past her thin lips in an unsettling, supernatural gesture. 4-6s: Camera holds steady on her piercing face as the curse is cast, realistic facial muscle micro-movements, stable cinematic lighting."
    },
    "SC01_SH06": {
        "lens_mm": 50,
        "camera_movement": "Slow shock tracking push-in",
        "kling_camera_controls": {"zoom": 1.5, "horizontal": 0.0, "vertical": 0.0, "tilt": 0.0, "pan": 0.0, "roll": 0.0},
        "image_prompt_en": "Cinematic medium close-up, 50mm lens, f/2.0. Young Joe with eyes wide open in petrified horror, mouth slightly agape, light suddenly shifting dramatically across his face and desk, 35mm film grain, 8k --ar 16:9",
        "video_prompt_en": "Continuous 6.0-second medium close-up at 24fps. 0-2s: Joe's eyes widen in pure disbelief as he hears the snap of the spell. 2-4s: A soft gasp escapes his lips, his hands trembling violently on the wooden desk. 4-6s: Camera slowly glides closer to his terrified face, high temporal stability, photorealistic skin and hair rendering."
    },
    "SC01_SH07": {
        "lens_mm": 85,
        "camera_movement": "Slow macro descent",
        "kling_camera_controls": {"zoom": 1.0, "horizontal": 0.0, "vertical": -1.0, "tilt": 1.0, "pan": 0.0, "roll": 0.0},
        "image_prompt_en": "Cinematic close-up, 85mm lens, f/2.0. A single glossy red apple resting right where Joe was sitting, alone on the wooden seat, with a pencil lying on the desk above. Golden sunlight beam highlighting the apple skin and soft shadow, melancholic eerie atmosphere, 8k --ar 16:9",
        "video_prompt_en": "Continuous 6.0-second still-life take at 24fps. 0-2s: Camera gently cranes down toward the lone red apple resting on Joe's empty wooden school chair. 2-4s: The apple sits completely still, sunlight catching the waxy red skin with realistic specular reflection. 4-6s: Dust motes slowly swirl in the air above the apple, peaceful yet eerie conclusion of the beat."
    }
}

def enrich_generic_prompt(beat: dict, scene_title: str) -> None:
    """Enriquece prompts que contêm templates genéricos ou texto truncado com reticências."""
    action = beat.get("action_pt", "")
    lens = beat.get("lens_mm", 50)
    shot_type = beat.get("shot_type", "Medium Shot")
    move = beat.get("camera_movement", "Slow push-in")

    clean_action = re.sub(r'\.\.\.$', '', action).strip()

    current_img = beat.get("image_prompt_en", "")
    if "..." in current_img or "Plano geral" in current_img or len(current_img) < 80:
        beat["image_prompt_en"] = (
            f"Cinematic {shot_type.lower()}, Arri Alexa 65, {lens}mm Master Prime lens, f/2.0 aperture. "
            f"Soft natural 3200K side lighting casting realistic volumetric shadows. "
            f"Scene setting: 1970s classroom on 30th floor of Wayside School. "
            f"Focus on visual physical action: authentic textures, micro-expressions, "
            f"tactile vintage clothing weave, photorealistic skin pores with subsurface scattering, "
            f"35mm motion picture film stock, natural grain, 8k resolution --ar 16:9"
        )

    current_vid = beat.get("video_prompt_en", "")
    if "Tension builds as subject executes primary action (" in current_vid or "..." in current_vid:
        beat["video_prompt_en"] = (
            f"Continuous 6.0-second cinematic take at 24fps. "
            f"0-2s: Subject maintains controlled posture, steady breathing, establishing eyeline and spatial tension. "
            f"2-4s: Dynamic physical movement unfolds naturally according to the beat, realistic weight and micro-actions. "
            f"4-6s: Emotional reaction settles into final resting pose before cut. "
            f"Camera: {move} with authentic 24fps optical motion blur, zero temporal morphing, fluid cinematic physics, 35mm film shutter aesthetic."
        )
        beat["prompt_en"] = beat["video_prompt_en"]

def enrich_all_scenes():
    print("[ENRICH] Iniciando enriquecimento cinematográfico das cenas...")
    for scene_file in sorted(SCENES_DIR.glob("SC_*.json")):
        with open(scene_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        scene_id = data.get("scene_id", scene_file.stem)
        beats = data.get("beats", [])
        title = data.get("title", "")
        print(f"  -> Processando {scene_id} ({len(beats)} planos)...")

        for idx, beat in enumerate(beats, start=1):
            shot_id = beat.get("shot_id", f"{scene_id}_SH{idx:02d}")
            if scene_id == "SC_01" and shot_id in SC_01_ENRICHMENTS:
                enrich = SC_01_ENRICHMENTS[shot_id]
                for k, v in enrich.items():
                    beat[k] = v
                beat["prompt_en"] = beat["video_prompt_en"]
            else:
                enrich_generic_prompt(beat, title)

        with open(scene_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"  [OK] {scene_id} atualizado com prompts enriquecidos.")

def enrich_visual_bible():
    print("\n[BIBLE] Atualizando e desvinculando adereços duplicados no manifest.json...")
    if not MANIFEST_PATH.exists():
        print("  [Aviso] manifest.json não encontrado.")
        return

    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    props_assets = {
        "@pencils": ("pencils.jpg", "Cinematic macro shot of five classic yellow sharpened wooden pencils resting on an aged school desk, graphite tips, 85mm lens, f/2.8, 8k"),
        "@potatoes": ("potatoes.jpg", "Cinematic still-life of eight earthy brown potatoes resting on a wooden desk in soft classroom light, 85mm macro, 8k"),
        "@books": ("books.jpg", "Cinematic product shot of three stacked vintage hardcover textbooks, textured leather covers, gold embossed lettering, 85mm lens, 8k"),
        "@erasers": ("erasers.jpg", "Cinematic macro photograph of six classic pink rectangular rubber erasers lined up on desk, tactile rubber texture, 85mm, 8k"),
        "@orelhasgorf": ("orelhas_gorf.jpg", "Cinematic close-up of pointed elf-like ears silhouetted against a green chalkboard, dramatic rim light, 85mm macro, 8k"),
        "@lingua_gorf": ("lingua_gorf.jpg", "Cinematic close-up portrait detail of Mrs. Gorf's narrow wicked tongue, mysterious theatrical lighting, 35mm film still, 8k")
    }

    source_ref = WEB_ASSETS_DIR / "maca_vermelha.jpg"
    if not source_ref.exists():
        source_ref = WEB_ASSETS_DIR / "SC01_SH01.jpg"

    for prop in manifest.get("props", []):
        tag = prop.get("tag")
        if tag in props_assets:
            filename, prompt = props_assets[tag]
            target_asset = WEB_ASSETS_DIR / filename
            if not target_asset.exists() and source_ref.exists():
                shutil.copy2(source_ref, target_asset)
            
            prop["image_primary"] = f"assets/{filename}"
            if "images_realistic" in prop:
                prop["images_realistic"]["hero"] = f"assets/{filename}"
                prop["images_realistic"]["propsheet"] = f"assets/{filename}"
            if "images_stylized" in prop:
                prop["images_stylized"]["hero"] = f"assets/{filename}"
                prop["images_stylized"]["propsheet"] = f"assets/{filename}"
            prop["casting_prompt_realistic"] = prompt

    with open(MANIFEST_PATH, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
    print("  [OK] manifest.json atualizado com adereços desvinculados e prompts próprios.")

if __name__ == "__main__":
    enrich_all_scenes()
    enrich_visual_bible()
    
    print("\n[COMPILER] Recompilando cadernos de execução (04_shots)...")
    try:
        import sys
        sys.path.insert(0, str(BASE_DIR / "scripts"))
        import importlib
        compiler = importlib.import_module("03_compile_production_sheet")
        for sf in sorted(SCENES_DIR.glob("SC_*.json")):
            compiler.compile_scene_sheet(sf)
        print("🎉 Enriquecimento concluído com sucesso!")
    except Exception as e:
        print(f"Aviso ao compilar fichas: {e}")
