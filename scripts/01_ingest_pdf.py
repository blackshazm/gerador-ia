"""
Módulo 0: Ingestão de PDF / Texto Literário e Higienização
Pipeline da Tríade - Versão 1.0.0
"""
import os
import re
import sys
from pathlib import Path

try:
    from pypdf import PdfReader
    PYPDF_AVAILABLE = True
except ImportError:
    PYPDF_AVAILABLE = False

BASE_DIR = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = BASE_DIR / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import project_context as pc
paths = pc.get_current_project_paths()
INPUT_DIR = paths.raw_dir
OUTPUT_DIR = paths.normalized_dir

def clean_text_content(text: str) -> str:
    """
    Remove números de página, corrige hifens silábicos e quebras duras de linha.
    """
    # Remove linhas que são apenas números isolados (números de página)
    text = re.sub(r'^\s*\d+\s*$', '', text, flags=re.MULTILINE)
    
    # Corrige hifenização silábica quebrada no fim de linha: ex. "co-\n nhecido" -> "conhecido"
    text = re.sub(r'(\b\w+)-\s*\n\s*(\w+\b)', r'\1\2', text)
    
    # Unifica quebras de linha duras no meio de parágrafos (mantém se terminar em pontuação)
    text = re.sub(r'(?<![.!?—:])\n(?!\n)', ' ', text)
    
    # Remove múltiplos espaços e linhas vazias redundantes
    text = re.sub(r'[ \t]+', ' ', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    return text.strip()

def process_file(file_path: Path) -> Path:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_file = OUTPUT_DIR / f"{file_path.stem}_limpo.md"
    
    raw_text = ""
    if file_path.suffix.lower() == ".pdf":
        if not PYPDF_AVAILABLE:
            print("ERRO: Biblioteca pypdf não instalada. Execute: pip install pypdf")
            sys.exit(1)
        print(f"-> Extraindo páginas de: {file_path.name}")
        reader = PdfReader(str(file_path))
        pages_text = []
        for i, page in enumerate(reader.pages):
            t = page.extract_text() or ""
            pages_text.append(t)
        raw_text = "\n\n".join(pages_text)
    else:
        # Suporta arquivos .txt ou .md brutos
        print(f"-> Lendo texto bruto de: {file_path.name}")
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            raw_text = f.read()
            
    cleaned = clean_text_content(raw_text)
    
    with open(out_file, "w", encoding="utf-8") as f:
        f.write(cleaned)
        
    print(f"-> Concluído! Texto normalizado salvo em:\n   {out_file.relative_to(BASE_DIR)}")
    return out_file

def main():
    INPUT_DIR.mkdir(parents=True, exist_ok=True)
    files = list(INPUT_DIR.glob("*.pdf")) + list(INPUT_DIR.glob("*.txt")) + list(INPUT_DIR.glob("*.md"))
    
    if not files:
        print(f"Nenhum arquivo encontrado em: {INPUT_DIR}")
        print("Por favor, coloque seu livro em PDF ou TXT nessa pasta.")
        return
        
    for f in files:
        process_file(f)

if __name__ == "__main__":
    main()
