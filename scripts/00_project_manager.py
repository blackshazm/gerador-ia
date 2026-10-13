"""
Módulo Gerenciador de Projetos & Múltiplos Livros
Pipeline da Tríade Studio — Versão 1.3.0

Responsabilidades:
1. Gerenciamento do diretório 'projects/' com isolamento total por livro/história.
2. Migração automática do projeto padrão ('wayside_school') mantendo ativos existentes.
3. Criação de novos projetos a partir de arquivos PDF com limpeza para .md e inicialização de pastas.
4. Persistência de configuração de Estilo Visual (Realista vs. Animação 3D).
"""
import os
import sys
import shutil
import json
import re
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
PROJECTS_DIR = BASE_DIR / "projects"
CONFIG_FILE = BASE_DIR / "current_project.json"

DEFAULT_PROJECT_ID = "wayside_school"

def get_active_project_id() -> str:
    """Retorna o ID do projeto ativo atualmente."""
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("active_project", DEFAULT_PROJECT_ID)
        except Exception:
            pass
    return DEFAULT_PROJECT_ID

def set_active_project_id(project_id: str):
    """Define o projeto ativo e salva a preferência."""
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump({"active_project": project_id}, f, indent=2)

def get_project_dir(project_id: str = None) -> Path:
    """Retorna o diretório do projeto solicitado ou ativo."""
    p_id = project_id or get_active_project_id()
    return PROJECTS_DIR / p_id

def ensure_project_structure(project_dir: Path, title: str = "Sem Título", style: str = "realistic"):
    """Garante a existência de todas as subpastas cinematográficas de um projeto."""
    subfolders = [
        "00_raw_input",
        "01_normalized_text",
        "02_visual_bible/characters",
        "02_visual_bible/locations",
        "02_visual_bible/props",
        "03_scenes",
        "04_shots",
        "05_audio",
        "06_renders",
        "07_timeline_export"
    ]
    for sf in subfolders:
        (project_dir / sf).mkdir(parents=True, exist_ok=True)
        
    config_path = project_dir / "project_config.json"
    if not config_path.exists():
        cfg = {
            "project_id": project_dir.name,
            "title": title,
            "visual_style": style,  # 'realistic' | 'stylized'
            "created_at": "2026-10-06"
        }
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2, ensure_ascii=False)

class ProjectPaths:
    """Encapsula todos os caminhos cinematográficos do projeto ativo."""
    def __init__(self, project_id: str = None):
        self.project_id = project_id or get_active_project_id()
        self.project_dir = PROJECTS_DIR / self.project_id
        self.raw_dir = self.project_dir / "00_raw_input"
        self.normalized_dir = self.project_dir / "01_normalized_text"
        self.bible_dir = self.project_dir / "02_visual_bible"
        self.manifest_path = self.bible_dir / "manifest.json"
        self.scenes_dir = self.project_dir / "03_scenes"
        self.shots_dir = self.project_dir / "04_shots"
        self.audio_dir = self.project_dir / "05_audio"
        self.renders_dir = self.project_dir / "06_renders"
        self.timeline_dir = self.project_dir / "07_timeline_export"
        self.config_path = self.project_dir / "project_config.json"

    def ensure_dirs(self):
        for d in [self.raw_dir, self.normalized_dir, self.bible_dir, self.scenes_dir, 
                  self.shots_dir, self.audio_dir, self.renders_dir, self.timeline_dir]:
            d.mkdir(parents=True, exist_ok=True)

    def get_book_text(self) -> str:
        md_files = list(self.normalized_dir.glob("*.md"))
        if not md_files:
            return ""
        with open(md_files[0], "r", encoding="utf-8", errors="ignore") as f:
            return f.read()

def get_current_project_paths(project_id: str = None) -> ProjectPaths:
    """Helper global para obter os caminhos do projeto ativo."""
    return ProjectPaths(project_id)

def initialize_default_project():
    """Inicializa ou valida a existência do projeto padrão."""
    PROJECTS_DIR.mkdir(parents=True, exist_ok=True)
    paths = get_current_project_paths(DEFAULT_PROJECT_ID)
    paths.ensure_dirs()
    ensure_project_structure(paths.project_dir, title="Sideways Stories From Wayside School", style="realistic")

    if not CONFIG_FILE.exists():
        set_active_project_id(DEFAULT_PROJECT_ID)

def list_all_projects() -> list:
    """Lista todos os projetos cadastrados."""
    initialize_default_project()
    active_id = get_active_project_id()
    projects = []
    
    for p_dir in sorted(PROJECTS_DIR.iterdir()):
        if p_dir.is_dir():
            cfg_file = p_dir / "project_config.json"
            title = p_dir.name
            style = "realistic"
            if cfg_file.exists():
                try:
                    with open(cfg_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        title = data.get("title", p_dir.name)
                        style = data.get("visual_style", "realistic")
                except Exception:
                    pass
            
            # Conta PDFs e Cenas
            pdf_count = len(list((p_dir / "00_raw_input").glob("*.pdf")))
            scene_count = len(list((p_dir / "03_scenes").glob("*.json")))
            
            projects.append({
                "id": p_dir.name,
                "title": title,
                "visual_style": style,
                "is_active": (p_dir.name == active_id),
                "pdf_count": pdf_count,
                "scene_count": scene_count
            })
    return projects

def create_new_project(name: str, pdf_file_path: Path = None, pdf_bytes: bytes = None, pdf_filename: str = "livro.pdf", style: str = "realistic") -> str:
    """Cria um novo projeto a partir de um nome e opcionalmente ingere o PDF."""
    clean_slug = re.sub(r"[^a-zA-Z0-9_-]", "_", name.lower()).strip("_")
    if not clean_slug:
        clean_slug = "novo_livro"
        
    target_dir = PROJECTS_DIR / clean_slug
    counter = 1
    original_slug = clean_slug
    while target_dir.exists():
        clean_slug = f"{original_slug}_{counter}"
        target_dir = PROJECTS_DIR / clean_slug
        counter += 1

    ensure_project_structure(target_dir, title=name, style=style)

    # Se bytes foram fornecidos diretamente via web
    raw_dest = None
    if pdf_bytes:
        raw_dest = target_dir / "00_raw_input" / pdf_filename
        with open(raw_dest, "wb") as pf:
            pf.write(pdf_bytes)
    elif pdf_file_path and pdf_file_path.exists():
        raw_dest = target_dir / "00_raw_input" / pdf_file_path.name
        shutil.copy2(pdf_file_path, raw_dest)

    if raw_dest and raw_dest.exists():
        clean_md_path = target_dir / "01_normalized_text" / f"{clean_slug}_limpo.md"
        try:
            from pypdf import PdfReader
            reader = PdfReader(str(raw_dest))
            extracted_text = []
            for i, page in enumerate(reader.pages):
                txt = page.extract_text() or ""
                extracted_text.append(f"<!-- Página {i+1} -->\n" + txt)
            full_text = "\n\n".join(extracted_text)
            
            with open(clean_md_path, "w", encoding="utf-8") as f:
                f.write(f"# {name}\n\n" + full_text)
        except Exception as e:
            print(f"Erro na extração do PDF: {e}")
            with open(clean_md_path, "w", encoding="utf-8") as f:
                f.write(f"# {name}\n\nTexto extraído em processamento.")

    # Inicializa manifesto de arte vazio
    manifest_target = target_dir / "02_visual_bible" / "manifest.json"
    if not manifest_target.exists():
        with open(manifest_target, "w", encoding="utf-8") as f:
            json.dump({"characters": [], "locations": [], "props": []}, f, indent=2, ensure_ascii=False)

    set_active_project_id(clean_slug)
    return clean_slug

def parse_book_chapters(content: str) -> list:
    """
    Analisa o texto do livro e detecta dinamicamente todos os capítulos.
    Retorna uma lista de objetos: [{'number': 1, 'title': '...', 'full_title': '...'}]
    """
    if not content:
        return [{"number": 1, "title": "Capítulo 1", "full_title": "Capítulo 1"}]

    pattern = re.compile(
        r"(?:^|\n)[ \t]*(?:g\s+)?(?:#+\s*)?(?:Chapter|Capítulo|Capitulo|Cena|Scene)\s*([0-9]+)[ \t]*[:.\-—]?[ \t]*([^\n\r]*)",
        re.IGNORECASE
    )
    matches = list(pattern.finditer(content))
    if not matches:
        return [{"number": 1, "title": "Cena Completa", "full_title": "Capítulo 1 — Cena Completa"}]

    valid_candidates = []
    for i, m in enumerate(matches):
        start_idx = m.start()
        end_idx = matches[i + 1].start() if i + 1 < len(matches) else len(content)
        chunk_len = end_idx - start_idx
        if chunk_len > 40:
            valid_candidates.append({
                "num": int(m.group(1)),
                "raw_title": m.group(2).strip(),
                "start": start_idx,
                "end": end_idx,
                "chunk_len": chunk_len
            })

    first_ch1_idx = next((i for i, c in enumerate(valid_candidates) if c["num"] == 1), 0)
    filtered = valid_candidates[first_ch1_idx:]

    chapters = []
    seen = set()
    for c in filtered:
        num = c["num"]
        if num in seen:
            continue
        seen.add(num)
        
        raw_title = c["raw_title"]
        title = raw_title
        if len(title) > 35:
            first_sentence = title.split(".")[0].strip()
            words = first_sentence.split()
            if len(words) >= 4 and words[0].lower() == words[2].lower():
                title = " ".join(words[:2])
            elif len(words) <= 3 and len(first_sentence) > 0:
                title = first_sentence
            else:
                title = " ".join(words[:3])
        
        title = re.sub(r"\s+", " ", title).strip()
        if not title:
            title = f"Parte {num}"
            
        chapters.append({
            "number": num,
            "title": title,
            "full_title": f"Capítulo {num} — {title}"
        })

    chapters.sort(key=lambda x: x["number"])
    return chapters if chapters else [{"number": 1, "title": "Capítulo 1", "full_title": "Capítulo 1"}]

def set_project_visual_style(project_id: str, style: str):
    """Atualiza o estilo visual (realistic ou stylized) do projeto."""
    p_dir = get_project_dir(project_id)
    cfg_file = p_dir / "project_config.json"
    cfg = {}
    if cfg_file.exists():
        try:
            with open(cfg_file, "r", encoding="utf-8") as f:
                cfg = json.load(f)
        except Exception:
            pass
    cfg["visual_style"] = style
    with open(cfg_file, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)

if __name__ == "__main__":
    initialize_default_project()
    print("Projetos disponíveis:")
    for p in list_all_projects():
        status = "[ATIVO]" if p["is_active"] else "       "
        print(f"  {status} {p['id']} - {p['title']} (Estilo: {p['visual_style']})")
