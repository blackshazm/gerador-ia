"""
Módulo Unificado de Contexto do Projeto — Tríade Studio
Permite a qualquer script acessar de forma determinística os diretórios e arquivos do projeto ativo.
"""
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import importlib.util
_spec = importlib.util.spec_from_file_location("pm_mod", str(SCRIPTS_DIR / "00_project_manager.py"))
_pm = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_pm)

ProjectPaths = _pm.ProjectPaths
get_current_project_paths = _pm.get_current_project_paths
get_active_project_id = _pm.get_active_project_id
set_active_project_id = _pm.set_active_project_id
get_project_dir = _pm.get_project_dir
list_all_projects = _pm.list_all_projects
create_new_project = _pm.create_new_project
set_project_visual_style = _pm.set_project_visual_style
initialize_default_project = _pm.initialize_default_project
parse_book_chapters = _pm.parse_book_chapters
