"""
Módulo de Serviço do Livro & Capítulos — Tríade Studio
Gerencia a extração, separação por capítulos e tradução sob demanda com cache persistente.
"""
import os
import re
import json
from pathlib import Path
from typing import List, Dict, Optional, Tuple

import sys
BASE_DIR = Path(__file__).resolve().parent.parent.parent
SCRIPTS_DIR = BASE_DIR / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import project_context as pc
from llm_client import LLMClient

# Cache em memória: (project_id, file_path_str) -> {"mtime": float, "text": str, "chapters": List[Dict]}
_BOOK_CACHE: Dict[Tuple[str, str], Dict] = {}

def invalidate_book_cache(project_id: Optional[str] = None):
    """Limpa o cache do livro para um projeto específico ou todos."""
    global _BOOK_CACHE
    if project_id:
        keys_to_remove = [k for k in _BOOK_CACHE if k[0] == project_id]
        for k in keys_to_remove:
            _BOOK_CACHE.pop(k, None)
    else:
        _BOOK_CACHE.clear()

def _get_paths(project_id: Optional[str] = None):
    return pc.get_current_project_paths(project_id)

def _get_book_md_file(paths) -> Optional[Path]:
    md_files = list(paths.normalized_dir.glob("*.md"))
    return md_files[0] if md_files else None

def get_book_full_text(project_id: Optional[str] = None) -> str:
    """Retorna o texto integral do livro em Markdown com cache baseado em mtime."""
    paths = _get_paths(project_id)
    p_id = paths.project_id
    md_file = _get_book_md_file(paths)
    if not md_file or not md_file.exists():
        return ""

    cache_key = (p_id, str(md_file.resolve()))
    mtime = md_file.stat().st_mtime
    cached = _BOOK_CACHE.get(cache_key)
    if cached and cached.get("mtime") == mtime:
        return cached.get("text", "")

    try:
        with open(md_file, "r", encoding="utf-8", errors="ignore") as f:
            text = f.read()
    except Exception:
        text = ""

    if cache_key not in _BOOK_CACHE or _BOOK_CACHE[cache_key].get("mtime") != mtime:
        _BOOK_CACHE[cache_key] = {
            "mtime": mtime,
            "text": text,
            "chapters": None
        }
    else:
        _BOOK_CACHE[cache_key]["text"] = text

    return text

def get_cached_chapters(project_id: Optional[str] = None) -> List[Dict]:
    """Retorna a lista de capítulos parseados aproveitando o cache baseado em mtime."""
    paths = _get_paths(project_id)
    p_id = paths.project_id
    md_file = _get_book_md_file(paths)
    if not md_file or not md_file.exists():
        return [{"number": 1, "title": "Capítulo 1", "full_title": "Capítulo 1", "start": 0, "end": 0}]

    cache_key = (p_id, str(md_file.resolve()))
    mtime = md_file.stat().st_mtime
    cached = _BOOK_CACHE.get(cache_key)

    if cached and cached.get("mtime") == mtime and cached.get("chapters") is not None:
        return cached["chapters"]

    text = get_book_full_text(project_id)
    chapters = parse_book_chapters(text)

    if cache_key in _BOOK_CACHE:
        _BOOK_CACHE[cache_key]["chapters"] = chapters

    return chapters

def parse_book_chapters(content: str) -> List[Dict]:
    """
    Analisa o texto do livro e detecta todos os capítulos com posições de início e fim.
    """
    if not content:
        return [{"number": 1, "title": "Capítulo 1", "full_title": "Capítulo 1 — Início", "start": 0, "end": 0}]

    pattern = re.compile(
        r"(?:^|\n)[ \t]*(?:g\s+)?(?:#+\s*)?(?:Chapter|Capítulo|Capitulo|Cena|Scene)\s*([0-9]+)[ \t]*[:.\-—]?[ \t]*([^\n\r]*)",
        re.IGNORECASE
    )
    matches = list(pattern.finditer(content))
    if not matches:
        return [{
            "number": 1,
            "title": "Cena Completa",
            "full_title": "Capítulo 1 — Texto Integral",
            "start": 0,
            "end": len(content)
        }]

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
        if len(title) > 40:
            first_sentence = title.split(".")[0].strip()
            words = first_sentence.split()
            if len(words) >= 4 and words[0].lower() == words[2].lower():
                title = " ".join(words[:2])
            elif len(words) <= 3 and len(first_sentence) > 0:
                title = first_sentence
            else:
                title = " ".join(words[:4])

        title = re.sub(r"\s+", " ", title).strip()
        if not title:
            title = f"Parte {num}"

        chapters.append({
            "number": num,
            "title": title,
            "full_title": f"Capítulo {num} — {title}",
            "start": c["start"],
            "end": c["end"]
        })

    chapters.sort(key=lambda x: x["number"])
    return chapters if chapters else [{"number": 1, "title": "Capítulo 1", "full_title": "Capítulo 1", "start": 0, "end": len(content)}]

def is_text_likely_portuguese(text: str) -> bool:
    """Verifica com heurística simples se o texto original já está em português."""
    sample = text[:1500].lower()
    pt_markers = [" e ", " de ", " do ", " da ", " não ", " para ", " com ", " um ", " uma ", " que "]
    en_markers = [" and ", " of ", " the ", " to ", " with ", " a ", " was ", " said ", " that "]
    
    pt_score = sum(1 for m in pt_markers if m in sample)
    en_score = sum(1 for m in en_markers if m in sample)
    return pt_score > en_score

def get_chapter_text(content: str, chapter_num: int, chapters: Optional[List[Dict]] = None) -> Tuple[str, str]:
    """Retorna (titulo, texto_completo) do capítulo especificado."""
    if chapters is None:
        chapters = parse_book_chapters(content)
    target = next((c for c in chapters if c["number"] == chapter_num), None)
    if not target:
        if chapters:
            target = chapters[0]
        else:
            return f"Capítulo {chapter_num}", content

    start = target.get("start", 0)
    end = target.get("end", len(content))
    chapter_content = content[start:end].strip()
    return target["full_title"], chapter_content

def get_chapter_detail(chapter_num: int, project_id: Optional[str] = None) -> Dict:
    """Retorna detalhes completos do capítulo: texto original e traduzido em cache."""
    paths = _get_paths(project_id)
    full_text = get_book_full_text(project_id)
    chapters = get_cached_chapters(project_id)
    title, orig_text = get_chapter_text(full_text, chapter_num, chapters=chapters)
    
    # Pasta de traduções em cache
    trans_dir = paths.normalized_dir / "translations"
    trans_dir.mkdir(parents=True, exist_ok=True)
    trans_file = trans_dir / f"chapter_{chapter_num:02d}_pt.md"

    translated_text = ""
    has_translation = False
    if trans_file.exists():
        try:
            with open(trans_file, "r", encoding="utf-8") as tf:
                translated_text = tf.read().strip()
                has_translation = bool(translated_text)
        except Exception:
            pass

    is_pt = is_text_likely_portuguese(orig_text)
    # Se já é em português e não tem tradução separada, o original é a versão em português
    if is_pt and not translated_text:
        translated_text = orig_text
        has_translation = True

    scene_id = f"SC_{chapter_num:02d}"
    scene_file = paths.scenes_dir / f"{scene_id}.json"
    is_decoupled = scene_file.exists()
    total_shots = 0
    if is_decoupled:
        try:
            with open(scene_file, "r", encoding="utf-8") as sf:
                s_data = json.load(sf)
                total_shots = len(s_data.get("beats", []))
        except Exception:
            pass

    return {
        "number": chapter_num,
        "title": title,
        "original_text": orig_text,
        "translated_text": translated_text,
        "has_translation": has_translation,
        "is_portuguese": is_pt,
        "word_count": len(orig_text.split()),
        "scene_id": scene_id,
        "is_decoupled": is_decoupled,
        "total_shots": total_shots
    }

def translate_chapter(chapter_num: int, provider: Optional[str] = None, model: Optional[str] = None, project_id: Optional[str] = None) -> Dict:
    """Traduz o capítulo literário para Português do Brasil com preservação estilística."""
    paths = _get_paths(project_id)
    full_text = get_book_full_text(project_id)
    chapters = get_cached_chapters(project_id)
    title, orig_text = get_chapter_text(full_text, chapter_num, chapters=chapters)

    if not orig_text.strip():
        raise ValueError(f"Capítulo {chapter_num} vazio ou não encontrado.")

    # Se já é português, apenas salva e confirma
    if is_text_likely_portuguese(orig_text):
        trans_dir = paths.normalized_dir / "translations"
        trans_dir.mkdir(parents=True, exist_ok=True)
        trans_file = trans_dir / f"chapter_{chapter_num:02d}_pt.md"
        with open(trans_file, "w", encoding="utf-8") as tf:
            tf.write(orig_text)
        return {
            "status": "ok",
            "message": "O texto original já está em Português.",
            "translated_text": orig_text,
            "is_portuguese": True
        }

    client = LLMClient(provider=provider, model=model)
    system_prompt = (
        "Você é um renomado tradutor literário e roteirista cinematográfico brasileiro. "
        "Traduza o capítulo fornecido do inglês para o Português do Brasil (PT-BR) com perfeição estilística, "
        "mantendo o tom, a vivacidade dos diálogos, o humor e as nuances dramáticas da história. "
        "Mantenha nomes próprios consistentes e adapte termos culturais para soarem naturais na leitura. "
        "Retorne APENAS o texto traduzido em formato Markdown limpo, sem introduções ou notas de rodapé."
    )
    user_prompt = f"Traduza o seguinte capítulo integralmente para Português (Brasil):\n\n---\n{orig_text}\n---"

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]

    translated_content = client.chat_completion(
        messages=messages,
        temperature=0.3,
        json_mode=False,
        max_tokens=8192
    )

    clean_translation = translated_content.strip()
    if clean_translation.startswith("```markdown"):
        clean_translation = clean_translation.replace("```markdown", "", 1)
    if clean_translation.startswith("```"):
        clean_translation = clean_translation.replace("```", "", 1)
    if clean_translation.endswith("```"):
        clean_translation = clean_translation[:-3]
    clean_translation = clean_translation.strip()

    # Salva no cache do projeto
    trans_dir = paths.normalized_dir / "translations"
    trans_dir.mkdir(parents=True, exist_ok=True)
    trans_file = trans_dir / f"chapter_{chapter_num:02d}_pt.md"
    with open(trans_file, "w", encoding="utf-8") as tf:
        tf.write(clean_translation)

    return {
        "status": "ok",
        "message": f"Capítulo {chapter_num} traduzido com sucesso para Português!",
        "translated_text": clean_translation,
        "is_portuguese": False
    }
