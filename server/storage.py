"""
Módulo de Armazenamento e Operações de Arquivo Seguras — Tríade Studio
Garante atomicidade, rotação de backups e sincronização com locks em arquivos críticos.
"""
import os
import json
import shutil
import logging
import datetime
import threading
from pathlib import Path
from typing import Union

logger = logging.getLogger("StorageService")

MANIFEST_LOCK = threading.Lock()
SCENES_LOCK = threading.Lock()

def is_safe_subpath(base_dir: Path, target_path: Path) -> bool:
    """Valida se target_path está contido estritamente dentro de base_dir."""
    try:
        base = Path(base_dir).resolve()
        target = Path(target_path).resolve()
        return target.is_relative_to(base)
    except Exception:
        return False

def create_file_backup(file_path: Path, max_backups: int = 10):
    """Cria cópia histórica de segurança em .backups/ com rotação limitada."""
    try:
        file_path = Path(file_path)
        if not file_path.exists():
            return
        backup_dir = file_path.parent / ".backups"
        backup_dir.mkdir(parents=True, exist_ok=True)

        now_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"{file_path.stem}_{now_str}{file_path.suffix}"
        backup_path = backup_dir / backup_name
        shutil.copy2(file_path, backup_path)

        # Rotação: mantém apenas os últimos `max_backups` deste arquivo
        pattern = f"{file_path.stem}_*{file_path.suffix}"
        existing = sorted(backup_dir.glob(pattern), key=lambda p: p.stat().st_mtime)
        if len(existing) > max_backups:
            for old_p in existing[:-max_backups]:
                try:
                    old_p.unlink()
                except Exception:
                    pass
    except Exception as ex:
        logger.warning("Falha ao gerar backup de %s: %s", file_path, ex)

def atomic_write_json(file_path: Union[str, Path], data: Union[dict, list], make_backup: bool = True):
    """Grava dados JSON de forma atômica utilizando arquivo temporário e os.replace, gerando backup se solicitado."""
    file_path = Path(file_path)
    file_path.parent.mkdir(parents=True, exist_ok=True)

    if make_backup and file_path.exists():
        create_file_backup(file_path)

    tmp_path = file_path.with_suffix(file_path.suffix + ".tmp")
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    os.replace(tmp_path, file_path)
