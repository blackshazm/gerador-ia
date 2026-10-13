"""
Script de Enriquecimento da Bíblia Visual — Tríade Studio
Preenche prompts técnicos hiper-detalhados de Model Sheet (4 vistas), Expressões (4 emoções),
Cenários Arquiteturais e Props para o projeto ativo, com suporte a modo Realista (35mm) e Estilizado (Pixar 3D).
"""
import sys
import json
import re
import argparse
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = BASE_DIR / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

import project_context as pc

def clean_tag(t):
    return re.sub(r'[^a-zA-Z0-9_\-]', '', t).strip('_')

def enrich(force: bool = False):
    paths = pc.get_current_project_paths()
    manifest_path = paths.manifest_path

    if not manifest_path.exists():
        print(f"Manifesto não encontrado em {manifest_path}")
        return

    with open(manifest_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # 1. Enriquecer Personagens
    for char in data.get("characters", []):
        name = char.get("name", "Personagem")
        desc = char.get("physical_description", "")
        role = char.get("role", "")
        tag = char.get("tag", "")
        c_tag = clean_tag(tag)

        # Prompts Realistas Ultra-Detalhados (35mm Live-Action)
        if force or not char.get("modelsheet_prompt_realistic") or len(char.get("modelsheet_prompt_realistic", "")) < 120:
            char["modelsheet_prompt_realistic"] = (
                f"Full character turnaround model sheet of {name}, 4 exact orthographic angles arranged horizontally: "
                f"front view, three-quarter view, full side profile view, and clean back view. "
                f"Subject standing in balanced neutral A-pose on seamless pure white studio background with soft contact floor shadows. "
                f"Physical features: {desc}. "
                f"Costume details: realistic fabric weaving, aged texture, natural cloth wrinkles and folds. "
                f"Camera: 85mm portrait prime lens, f/8 aperture for deep focus sharpness across all views, "
                f"soft balanced three-point studio lighting, subsurface scattering on skin, visible facial pores, sharp eyelashes. "
                f"Ultra-sharp film production character turnaround sheet, photorealistic 35mm film photography, 8k resolution --ar 16:9"
            )

        if force or not char.get("expressions_prompt_realistic") or len(char.get("expressions_prompt_realistic", "")) < 120:
            char["expressions_prompt_realistic"] = (
                f"Facial expression study sheet of {name}, clean 2x2 grid of 4 distinct ultra-expressive close-up portraits: "
                f"1) Top-left: neutral analytical stare with subtle tension around the eyes; "
                f"2) Top-right: intense terrified scream with widened pupils, raised eyebrows and gasping open mouth; "
                f"3) Bottom-left: suspicious puzzled sideways glance with furrowed brow; "
                f"4) Bottom-right: wicked sinister smirk with narrowing eyelids and subtle cheek crease. "
                f"Character traits: {desc}. "
                f"Consistent facial anatomy across all 4 frames. 85mm macro portrait lens, f/2.8, shallow depth of field, "
                f"subtle directional key light revealing authentic skin micro-textures, individual hair strands. "
                f"Cinematographic character expression chart, photorealistic 35mm film, 8k --ar 16:9"
            )

        # Prompts Estilizados Ultra-Detalhados (Pixar / Disney 3D)
        if force or not char.get("modelsheet_prompt_stylized") or len(char.get("modelsheet_prompt_stylized", "")) < 120:
            char["modelsheet_prompt_stylized"] = (
                f"Full character turnaround reference model sheet of {name}, 4 orthographic views: "
                f"front, three-quarter, side profile, and back view in neutral A-pose. "
                f"Stylized 3D animated feature film character design, Disney and Pixar animation studio aesthetic. "
                f"Character design notes: {desc}. "
                f"Clean white cyclorama studio background, soft ambient occlusion, smooth stylized subsurface scattering skin shader, "
                f"vibrant appealing color palette, expressive proportions, RenderMan and Octane render quality, 8k --ar 16:9"
            )

        if force or not char.get("expressions_prompt_stylized") or len(char.get("expressions_prompt_stylized", "")) < 120:
            char["expressions_prompt_stylized"] = (
                f"Character emotional expression sheet of {name}, clean 2x2 grid showing 4 vibrant stylized facial expressions: "
                f"1) curious mischievous smile; 2) hilarious comically terrified open-mouthed scream; "
                f"3) skeptical squinting side-eye; 4) triumphant joyful wide grin. "
                f"Character: {desc}. "
                f"Disney Pixar style animation character concept art, rich specular eye highlights, appealing volumetric lighting, 8k --ar 16:9"
            )

        # Segregação e garantia de dicionários de imagem
        img_p1 = char.get("image_primary", f"assets/{c_tag}_p1.jpg")
        img_ms = char.get("image_modelsheet", img_p1)
        img_ex = char.get("image_expressions", img_p1)

        if "images_realistic" not in char:
            char["images_realistic"] = {"p1": img_p1, "modelsheet": img_ms, "expressions": img_ex}
        if "images_stylized" not in char:
            char["images_stylized"] = {"p1": img_p1, "modelsheet": img_ms, "expressions": img_ex}

    # 2. Enriquecer Locações
    for loc in data.get("locations", []):
        name = loc.get("name", "Cenário")
        desc = loc.get("description", "")
        tag = loc.get("tag", "")
        c_tag = clean_tag(tag)

        if force or not loc.get("matte_prompt_realistic") or len(loc.get("matte_prompt_realistic", "")) < 100:
            loc["matte_prompt_realistic"] = (
                f"Architectural set design concept and comprehensive environment turnaround of {name}. "
                f"Split view showing 3 wide cinematic angles: wide establishing perspective, reverse angle showing opposing wall, "
                f"and low-angle architectural details. {desc}. "
                f"Authentic aged wooden floorboards, textured plaster walls, volumetric window lighting with floating dust motes, "
                f"Arri Alexa 65 cinematography look, 24mm wide angle lens, f/4.0, ultra-realistic physical set, 8k --ar 16:9"
            )
        if force or not loc.get("matte_prompt_stylized") or len(loc.get("matte_prompt_stylized", "")) < 100:
            loc["matte_prompt_stylized"] = (
                f"Stylized 3D animated environment design turnaround of {name}, 3 colorful angles showing architectural geometry, "
                f"interior props, whimsical angles and playful scale. {desc}. "
                f"Pixar and DreamWorks movie set concept art, warm inviting lighting, soft shadows, RenderMan engine, 8k --ar 16:9"
            )
        if force or not loc.get("lighting_prompt_realistic") or len(loc.get("lighting_prompt_realistic", "")) < 100:
            loc["lighting_prompt_realistic"] = (
                f"Cinematic dual lighting study for movie set {name}: split comparison showing warm 3200K late-afternoon sunlight "
                f"with golden shafts versus dramatic stormy twilight with cool 6500K shadows and high-contrast chiaroscuro. "
                f"{desc}. 35mm film still, photorealistic, cinematic atmosphere, 8k --ar 16:9"
            )
        if force or not loc.get("lighting_prompt_stylized") or len(loc.get("lighting_prompt_stylized", "")) < 100:
            loc["lighting_prompt_stylized"] = (
                f"Stylized animation color key and lighting keyframe study for {name}: vibrant contrasting daylight palette "
                f"versus mysterious dramatic emerald and amber glow, Pixar animation feature color script, 8k --ar 16:9"
            )

        img_master = loc.get("image_primary", f"assets/{c_tag}.jpg")
        img_set = loc.get("image_matte_painting", img_master)
        img_light = loc.get("image_lighting", img_master)

        if "images_realistic" not in loc:
            loc["images_realistic"] = {"master": img_master, "set_design": img_set, "lighting": img_light}
        if "images_stylized" not in loc:
            loc["images_stylized"] = {"master": img_master, "set_design": img_set, "lighting": img_light}

    # 3. Enriquecer Props
    for prop in data.get("props", []):
        name = prop.get("name", "Objeto")
        desc = prop.get("description", "")
        tag = prop.get("tag", "")
        c_tag = clean_tag(tag)

        if force or not prop.get("propsheet_prompt_realistic") or len(prop.get("propsheet_prompt_realistic", "")) < 100:
            prop["propsheet_prompt_realistic"] = (
                f"Hero prop model sheet turnaround of {name}, 4 orthographic views: front, top-down, profile side, "
                f"and 45-degree isometric beauty shot. {desc}. "
                f"Seamless neutral studio backdrop, 85mm macro lens, f/5.6 for sharp depth of field, "
                f"tactile surface scratches, micro-imperfections, realistic reflections and specular highlights, "
                f"photorealistic 35mm film product photography, 8k --ar 16:9"
            )
        if force or not prop.get("propsheet_prompt_stylized") or len(prop.get("propsheet_prompt_stylized", "")) < 100:
            prop["propsheet_prompt_stylized"] = (
                f"Stylized 3D animated hero prop model sheet of {name}, 4 angles on clean studio pedestal. "
                f"{desc}. Pixar aesthetic, vibrant bold colors, subtle bevels, charming characterful proportions, "
                f"Octane render, 8k --ar 16:9"
            )

        img_hero = prop.get("image_primary", f"assets/{c_tag}.jpg")
        img_sheet = prop.get("image_propsheet", img_hero)

        if "images_realistic" not in prop:
            prop["images_realistic"] = {"hero": img_hero, "propsheet": img_sheet}
        if "images_stylized" not in prop:
            prop["images_stylized"] = {"hero": img_hero, "propsheet": img_sheet}

    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"[OK] Biblia Visual enriquecida com prompts hiper-detalhados para o projeto '{paths.project_id}'!")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true", help="Força a regravação de prompts mesmo se já existirem")
    args = parser.parse_args()
    enrich(force=args.force)
