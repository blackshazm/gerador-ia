"""
Servidor Backend REST e Servidor de Arquivos Estáticos para o Studio Web da Tríade
Tríade Studio — Arquitetura de Produção Audiovisual & Direção com IA
"""
import os
import sys
import re
import json
import base64
import shutil
import urllib.parse
from pathlib import Path
import threading
import logging
import datetime
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("StudioServer")

# Garante suporte UTF-8 no terminal Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

BASE_DIR = Path(__file__).resolve().parent.parent
WEB_DIR = BASE_DIR / "web"
SCRIPTS_DIR = BASE_DIR / "scripts"

if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

import project_context as pc
pc.initialize_default_project()
import llm_client

# Importa os serviços modulares da Tríade
from server.services import book_service
from server.services import decoupage_service
from server.services import audio_service
from server.services import export_service
from server.services import task_service
from server.services import video_service

def get_current_dirs(project_id: str = None):
    """Retorna os caminhos correspondentes ao projeto ativo ou especificado."""
    paths = pc.get_current_project_paths(project_id)
    return {
        "active_id": paths.project_id,
        "project_dir": paths.project_dir,
        "scenes_dir": paths.scenes_dir,
        "audio_dir": paths.audio_dir,
        "normalized_dir": paths.normalized_dir,
        "bible_dir": paths.bible_dir,
        "manifest_path": paths.manifest_path,
        "shots_dir": paths.shots_dir,
        "renders_dir": paths.renders_dir,
        "timeline_dir": paths.timeline_dir
    }

from server.storage import (
    is_safe_subpath,
    create_file_backup,
    atomic_write_json,
    MANIFEST_LOCK,
    SCENES_LOCK
)

class StudioRequestHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(WEB_DIR), **kwargs)

    def _extract_project_id(self, query=None, payload=None) -> str:
        """Extrai o project_id de headers HTTP, query string ou payload JSON."""
        # 1. Header X-Project-Id
        pid = self.headers.get("X-Project-Id")
        if pid and re.match(r'^[a-zA-Z0-9_\-]+$', pid):
            return pid
        # 2. Query param ?project_id=...
        if query and "project_id" in query:
            q_pid = query["project_id"][0]
            if q_pid and re.match(r'^[a-zA-Z0-9_\-]+$', q_pid):
                return q_pid
        # 3. Payload JSON {"project_id": ...}
        if payload and isinstance(payload, dict) and "project_id" in payload:
            p_pid = payload.get("project_id")
            if p_pid and isinstance(p_pid, str) and re.match(r'^[a-zA-Z0-9_\-]+$', p_pid):
                return p_pid
        return None

    def translate_path(self, path):
        # Mapeia caminhos da raiz para a pasta /web/ protegendo contra Path Traversal
        url_path = urllib.parse.unquote(urllib.parse.urlparse(path).path)
        if url_path == "/" or url_path == "":
            return str(WEB_DIR / "index.html")
            
        clean_rel = url_path.lstrip("/\\")
        file_in_web = (WEB_DIR / clean_rel).resolve()
        if is_safe_subpath(WEB_DIR, file_in_web) and file_in_web.exists():
            return str(file_in_web)
            
        if url_path.startswith("/assets/"):
            asset_subpath = url_path.replace("/assets/", "", 1).lstrip("/\\")
            # Tenta localizar diretamente nos diretórios do projeto ativo antes do placeholder
            cd = get_current_dirs()
            proj_candidates = [
                cd["project_dir"] / "06_renders" / asset_subpath,
                cd["bible_dir"] / "characters" / asset_subpath,
                cd["bible_dir"] / "locations" / asset_subpath,
                cd["bible_dir"] / "props" / asset_subpath,
                cd["shots_dir"] / "renders" / asset_subpath,
                cd["project_dir"] / asset_subpath
            ]
            for cand in proj_candidates:
                try:
                    cand_res = cand.resolve()
                    if is_safe_subpath(cd["project_dir"], cand_res) and cand_res.exists() and cand_res.is_file():
                        return str(cand_res)
                except Exception:
                    pass

            placeholder = WEB_DIR / "assets" / "placeholder.svg"
            if placeholder.exists():
                return str(placeholder)
            
        # Fallback protegido para o manipulador padrão
        super_path = Path(super().translate_path(path)).resolve()
        if is_safe_subpath(WEB_DIR, super_path):
            return str(super_path)
        return str(WEB_DIR / "index.html")

    def _send_cors_headers(self):
        origin = self.headers.get("Origin", "")
        # Permite apenas origens locais autorizadas (localhost / 127.0.0.1)
        if origin and (
            origin.startswith("http://localhost:") or
            origin.startswith("http://127.0.0.1:") or
            origin.startswith("https://localhost:") or
            origin.startswith("https://127.0.0.1:")
        ):
            self.send_header("Access-Control-Allow-Origin", origin)
        else:
            self.send_header("Access-Control-Allow-Origin", "http://127.0.0.1:8080")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, X-Project-Id")

    def do_OPTIONS(self):
        self.send_response(204)
        self._send_cors_headers()
        self.end_headers()

    def _send_json(self, data, status=200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self._send_cors_headers()
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))

    def _send_error(self, message, status=500):
        self._send_json({"status": "error", "message": str(message)}, status=status)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        query = urllib.parse.parse_qs(parsed.query)
        req_project_id = self._extract_project_id(query=query)
        cd = get_current_dirs(req_project_id)

        # API: Lista de Projetos e Ativo
        if path == "/api/projects":
            projects = pc.list_all_projects()
            self._send_json({
                "projects": projects,
                "active_project": cd["active_id"]
            })
            return

        # API: Listar backups históricos (.backups/)
        if path == "/api/backups":
            target = query.get("target", ["manifest"])[0]
            if target == "manifest":
                backup_dir = cd["manifest_path"].parent / ".backups"
                prefix = cd["manifest_path"].stem
            elif target == "scene":
                raw_id = query.get("scene_id", ["SC_01"])[0]
                scene_id = re.sub(r'[^a-zA-Z0-9_\-]', '', raw_id)
                backup_dir = cd["scenes_dir"] / ".backups"
                prefix = scene_id
            else:
                self.send_error(400, "Alvo de backup desconhecido")
                return

            backups = []
            if backup_dir.exists():
                for p in sorted(backup_dir.glob(f"{prefix}_*.json"), key=lambda x: x.stat().st_mtime, reverse=True):
                    backups.append({
                        "filename": p.name,
                        "created_at": datetime.datetime.fromtimestamp(p.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
                        "size_bytes": p.stat().st_size
                    })
            self._send_json({"backups": backups, "target": target})
            return

        # API: Obter configurações mascaradas e status dos provedores de IA
        if path == "/api/settings":
            env = llm_client.load_env()
            gem_key = env.get("GEMINI_API_KEY") or env.get("GOOGLE_API_KEY", "")
            or_key = env.get("OPENROUTER_API_KEY", "")
            fal_key = env.get("FAL_KEY", "")

            self._send_json({
                "providers": {
                    "gemini": {
                        "configured": bool(gem_key),
                        "masked_key": llm_client.mask_api_key(gem_key),
                        "model": env.get("GEMINI_MODEL", "gemini-2.5-flash")
                    },
                    "openrouter": {
                        "configured": bool(or_key),
                        "masked_key": llm_client.mask_api_key(or_key),
                        "model": env.get("OPENROUTER_MODEL", "meta-llama/llama-3.3-70b-instruct")
                    },
                    "fal": {
                        "configured": bool(fal_key),
                        "masked_key": llm_client.mask_api_key(fal_key)
                    }
                },
                "default_provider": env.get("DEFAULT_LLM_PROVIDER", "gemini")
            })
            return

        # API: Consultar status de tarefa assíncrona
        if path.startswith("/api/tasks/"):
            raw_tid = path.replace("/api/tasks/", "").strip()
            task_id = re.sub(r'[^a-zA-Z0-9_\-]', '', raw_tid)
            status_info = task_service.get_task_status(task_id)
            if status_info:
                self._send_json(status_info)
            else:
                self.send_error(404, "Tarefa não encontrada")
            return

        # API: Configuração do Projeto Ativo
        if path == "/api/project/config":
            cfg_file = cd["project_dir"] / "project_config.json"
            cfg = {"project_id": cd["active_id"], "title": cd["active_id"], "visual_style": "realistic"}
            if cfg_file.exists():
                try:
                    with open(cfg_file, "r", encoding="utf-8") as f:
                        cfg.update(json.load(f))
                except Exception:
                    pass
            self._send_json(cfg)
            return

        # API: Lista de Cenas do Projeto Ativo
        if path == "/api/scenes":
            scenes = []
            s_dir = cd["scenes_dir"]
            if s_dir.exists():
                for f in sorted(s_dir.glob("*.json")):
                    try:
                        with open(f, "r", encoding="utf-8") as sf:
                            data = json.load(sf)
                            scenes.append({
                                "id": data.get("scene_id", f.stem),
                                "title": data.get("title", ""),
                                "total_shots": len(data.get("beats", []))
                            })
                    except Exception:
                        pass
            self._send_json({"scenes": scenes})
            return

        # API: Bíblia Visual & Assets
        if path == "/api/bible":
            manifest_file = cd["manifest_path"]
            if manifest_file.exists():
                try:
                    with open(manifest_file, "r", encoding="utf-8") as mf:
                        self._send_json(json.load(mf))
                        return
                except Exception:
                    pass
            self._send_json({"characters": [], "locations": [], "props": []})
            return

        # API: Capítulos do Livro (Detectados Dinamicamente com Cache por mtime)
        if path == "/api/book-chapters":
            chapters = book_service.get_cached_chapters(cd["active_id"])
            self._send_json({"chapters": chapters})
            return

        # API: Detalhes Completos de um Capítulo Específico (Original + Tradução)
        if path == "/api/book-chapter":
            try:
                chapter_num = int(query.get("num", ["1"])[0])
            except (ValueError, TypeError):
                self._send_error("Número de capítulo inválido.", status=400)
                return
            try:
                detail = book_service.get_chapter_detail(chapter_num, project_id=cd["active_id"])
                self._send_json(detail)
            except Exception as e:
                self._send_error(e)
            return

        # API: Texto Integral do Livro (Sem corte de tamanho, com cache)
        if path == "/api/book-text":
            content = book_service.get_book_full_text(cd["active_id"])
            self._send_json({"content": content})
            return

        # API: Status de Produção dos Capítulos
        if path == "/api/book-status":
            chapters = book_service.get_cached_chapters(cd["active_id"])
            
            chapters_status = []
            for ch in chapters:
                c_num = ch["number"]
                scene_id = f"SC_{c_num:02d}"
                scene_file = cd["scenes_dir"] / f"{scene_id}.json"
                    
                is_done = False
                total_shots = 0
                duration_s = 0.0
                if scene_file.exists():
                    try:
                        with open(scene_file, "r", encoding="utf-8") as sf:
                            s_data = json.load(sf)
                            beats = s_data.get("beats", [])
                            total_shots = len(beats)
                            duration_s = round(sum(b.get("duration_s", 6.0) for b in beats), 1)
                            is_done = total_shots > 0
                    except Exception as ex:
                        logger.warning("Falha ao ler status da cena %s: %s", scene_id, ex)
                        
                chapters_status.append({
                    "number": c_num,
                    "title": ch["full_title"],
                    "scene_id": scene_id,
                    "status": "completed" if is_done else "pending",
                    "total_shots": total_shots,
                    "duration_s": duration_s
                })
            self._send_json({"chapters": chapters_status})
            return

        # API: Detalhes da Cena
        if path.startswith("/api/scene/"):
            raw_id = path.replace("/api/scene/", "").strip()
            scene_id = re.sub(r'[^a-zA-Z0-9_\-]', '', raw_id)
            if not scene_id:
                self.send_error(400, "Identificador de cena inválido")
                return

            scenes_dir = cd["scenes_dir"]
            scene_file = scenes_dir / f"{scene_id}.json"
            if not (scene_file.exists() and is_safe_subpath(scenes_dir, scene_file)):
                matches = [p for p in scenes_dir.glob(f"*{scene_id}*.json") if is_safe_subpath(scenes_dir, p)]
                if matches:
                    scene_file = matches[0]

            if scene_file.exists() and is_safe_subpath(scenes_dir, scene_file):
                try:
                    with open(scene_file, "r", encoding="utf-8") as sf:
                        scene_data = json.load(sf)

                    # Mescla dados de pacing de áudio se disponíveis
                    actual_id = scene_data.get("scene_id", scene_id)
                    pacing_file = cd["audio_dir"] / f"pacing_report_{actual_id}.json"
                    if pacing_file.exists() and is_safe_subpath(cd["audio_dir"], pacing_file):
                        try:
                            with open(pacing_file, "r", encoding="utf-8") as pf:
                                pacing_map = {item["shot_id"]: item for item in json.load(pf)}
                                for b in scene_data.get("beats", []):
                                    sid = b.get("shot_id")
                                    if sid in pacing_map:
                                        p_info = pacing_map[sid]
                                        b["audio_duration_s"] = p_info.get("audio_duration_s")
                                        b["recommended_duration_s"] = p_info.get("recommended_video_duration_s")
                                        b["audio_file"] = f"/api/audio/{p_info.get('audio_file')}"
                        except Exception as ex:
                            logger.warning("Falha ao carregar pacing de áudio para %s: %s", actual_id, ex)

                    self._send_json(scene_data)
                    return
                except Exception as e:
                    self._send_error(f"Erro ao ler cena: {e}")
                    return
            else:
                self.send_error(404, f"Cena {scene_id} não encontrada")
                return

        # API: Servir Áudios Gerados (com suporte a Range HTTP 206 para seek de áudio)
        if path.startswith("/api/audio/"):
            raw_name = path.replace("/api/audio/", "").strip()
            audio_name = Path(raw_name).name
            audio_dir = cd["audio_dir"]
            audio_path = audio_dir / audio_name
            if audio_path.exists() and audio_path.is_file() and is_safe_subpath(audio_dir, audio_path):
                file_size = audio_path.stat().st_size
                range_header = self.headers.get("Range")

                # Suporte a Range requests (HTTP 206 Partial Content) para permitir seek no player de áudio
                if range_header and range_header.startswith("bytes="):
                    try:
                        range_spec = range_header.replace("bytes=", "").split("-")
                        start = int(range_spec[0]) if range_spec[0] else 0
                        end = int(range_spec[1]) if len(range_spec) > 1 and range_spec[1] else file_size - 1

                        if start >= file_size or end >= file_size or start > end:
                            self.send_response(416)
                            self.send_header("Content-Range", f"bytes */{file_size}")
                            self._send_cors_headers()
                            self.end_headers()
                            return

                        chunk_len = end - start + 1
                        self.send_response(206)
                        self.send_header("Content-Type", "audio/mpeg")
                        self.send_header("Content-Range", f"bytes {start}-{end}/{file_size}")
                        self.send_header("Content-Length", str(chunk_len))
                        self.send_header("Accept-Ranges", "bytes")
                        self._send_cors_headers()
                        self.end_headers()

                        with open(audio_path, "rb") as f:
                            f.seek(start)
                            remaining = chunk_len
                            while remaining > 0:
                                chunk = f.read(min(remaining, 64 * 1024))
                                if not chunk:
                                    break
                                self.wfile.write(chunk)
                                remaining -= len(chunk)
                        return
                    except Exception as ex:
                        logger.warning("Falha ao processar Range request para %s: %s", audio_name, ex)

                # Resposta padrão HTTP 200 completa com streaming por blocos de 64KB
                self.send_response(200)
                self.send_header("Content-Type", "audio/mpeg")
                self.send_header("Content-Length", str(file_size))
                self.send_header("Accept-Ranges", "bytes")
                self._send_cors_headers()
                self.end_headers()
                with open(audio_path, "rb") as f:
                    shutil.copyfileobj(f, self.wfile, length=64 * 1024)
                return
            else:
                self.send_error(404, "Áudio não encontrado")
                return

        # API: Servir Imagens do Projeto Ativo
        if path.startswith("/api/image/"):
            subpath = path.replace("/api/image/", "").strip().lstrip("/\\")
            candidates = [
                (cd["project_dir"], cd["project_dir"] / subpath),
                (cd["bible_dir"], cd["bible_dir"] / subpath),
                (cd["project_dir"], cd["project_dir"] / "06_renders" / subpath),
                (cd["shots_dir"], cd["shots_dir"] / "renders" / subpath),
                (WEB_DIR, WEB_DIR / subpath)
            ]

            target = None
            for base_dir, cand_path in candidates:
                if is_safe_subpath(base_dir, cand_path) and cand_path.exists() and cand_path.is_file():
                    target = cand_path
                    break

            if target:
                stat = target.stat()
                mtime_epoch = int(stat.st_mtime)
                ims_header = self.headers.get("If-Modified-Since")

                if ims_header:
                    try:
                        import email.utils
                        ims_epoch = email.utils.parsedate_to_datetime(ims_header).timestamp()
                        if int(ims_epoch) >= mtime_epoch:
                            self.send_response(304)
                            self._send_cors_headers()
                            self.end_headers()
                            return
                    except Exception:
                        pass

                import email.utils
                last_modified_str = email.utils.formatdate(mtime_epoch, usegmt=True)
                content_type = "image/png" if target.suffix.lower() == ".png" else "image/jpeg"
                self.send_response(200)
                self.send_header("Content-Type", content_type)
                self.send_header("Content-Length", str(stat.st_size))
                self.send_header("Accept-Ranges", "bytes")
                self.send_header("Cache-Control", "public, max-age=3600")
                self.send_header("Last-Modified", last_modified_str)
                self._send_cors_headers()
                self.end_headers()
                with open(target, "rb") as f:
                    shutil.copyfileobj(f, self.wfile, length=64 * 1024)
                return
            else:
                self.send_error(404, "Imagem não encontrada")
                return

        return super().do_GET()

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        content_length = int(self.headers.get("Content-Length", 0))
        max_body_bytes = 50 * 1024 * 1024
        if content_length > max_body_bytes:
            self.send_error(413, "Carga útil excede o limite permitido (50 MB).")
            return
        raw_post = self.rfile.read(content_length) if content_length > 0 else b"{}"
        try:
            post_data = raw_post.decode("utf-8")
        except UnicodeDecodeError:
            post_data = raw_post.decode("latin-1", errors="replace")
        try:
            payload = json.loads(post_data)
        except Exception:
            payload = {}

        req_project_id = self._extract_project_id(payload=payload)
        cd = get_current_dirs(req_project_id)

        # API: Restaurar backup anterior
        if path == "/api/backups/restore":
            target = payload.get("target", "manifest")
            backup_filename = payload.get("filename", "")
            clean_name = Path(backup_filename).name

            if not clean_name or ".." in clean_name or not clean_name.endswith(".json"):
                self._send_error("Nome de backup inválido", status=400)
                return

            if target == "manifest":
                backup_dir = cd["manifest_path"].parent / ".backups"
                target_path = cd["manifest_path"]
            elif target == "scene":
                backup_dir = cd["scenes_dir"] / ".backups"
                scene_id = re.sub(r'[^a-zA-Z0-9_\-]', '', payload.get("scene_id", ""))
                if not scene_id:
                    self._send_error("Identificador de cena ausente", status=400)
                    return
                target_path = cd["scenes_dir"] / f"{scene_id}.json"
            else:
                self._send_error("Alvo de restauração inválido", status=400)
                return

            src_file = backup_dir / clean_name
            if src_file.exists() and is_safe_subpath(backup_dir, src_file):
                try:
                    with MANIFEST_LOCK:
                        with open(src_file, "r", encoding="utf-8") as rf:
                            backup_data = json.load(rf)
                        atomic_write_json(target_path, backup_data, make_backup=True)
                    self._send_json({
                        "status": "ok",
                        "message": f"Backup {clean_name} restaurado com sucesso!"
                    })
                except Exception as ex:
                    self._send_error(f"Erro ao restaurar backup: {ex}")
            else:
                self._send_error("Arquivo de backup não encontrado", status=404)
            return

        # API: Salvar chaves de API e configurações no .env
        if path == "/api/settings":
            keys_to_save = {}
            if "gemini_key" in payload and payload["gemini_key"]:
                keys_to_save["GEMINI_API_KEY"] = payload["gemini_key"].strip()
            if "openrouter_key" in payload and payload["openrouter_key"]:
                keys_to_save["OPENROUTER_API_KEY"] = payload["openrouter_key"].strip()
            if "fal_key" in payload and payload["fal_key"]:
                keys_to_save["FAL_KEY"] = payload["fal_key"].strip()
            if "default_provider" in payload and payload["default_provider"]:
                keys_to_save["DEFAULT_LLM_PROVIDER"] = payload["default_provider"].strip().lower()

            if keys_to_save:
                llm_client.save_env_keys(keys_to_save)
            self._send_json({"status": "ok", "message": "Configurações atualizadas com sucesso!"})
            return

        # API: Testar conectividade de uma chave de API
        if path == "/api/settings/test-key":
            prov = payload.get("provider", "gemini")
            key = payload.get("key")
            ok, msg = llm_client.verify_api_key(prov, api_key=key)
            if ok:
                self._send_json({"status": "ok", "message": msg})
            else:
                self._send_error(msg, status=400)
            return

        # API: Alternar Projeto Ativo
        if path == "/api/projects/switch":
            p_id = payload.get("project_id", "wayside_school")
            if not p_id or not isinstance(p_id, str) or not re.match(r'^[a-zA-Z0-9_\-]+$', p_id):
                self._send_error("Identificador de projeto inválido.", status=400)
                return
            pc.set_active_project_id(p_id)
            book_service.invalidate_book_cache()
            self._send_json({"status": "ok", "active_project": p_id})
            return

        # API: Criar Novo Projeto / Livro
        if path == "/api/projects/create":
            name = payload.get("title", "Novo Livro")
            style = payload.get("visual_style", "realistic")
            pdf_base64 = payload.get("pdf_base64")
            pdf_name = payload.get("pdf_name", "livro.pdf")
            
            pdf_bytes = None
            if pdf_base64:
                try:
                    pdf_bytes = base64.b64decode(pdf_base64)
                except Exception as ex:
                    logger.warning("Erro ao decodificar base64 do PDF: %s", ex)

            try:
                new_id = pc.create_new_project(name=name, pdf_bytes=pdf_bytes, pdf_filename=pdf_name, style=style)
                book_service.invalidate_book_cache(new_id)
                self._send_json({
                    "status": "ok", 
                    "project_id": new_id, 
                    "message": f"História '{name}' criada com sucesso com o PDF processado!"
                })
            except Exception as e:
                self._send_error(f"Erro ao criar projeto: {e}")
            return

        # API: Alterar Estilo Visual do Projeto (Realista vs. Animação 3D)
        if path == "/api/project/style":
            new_style = payload.get("visual_style", "realistic")
            pc.set_project_visual_style(cd["active_id"], new_style)
            self._send_json({"status": "ok", "visual_style": new_style, "message": f"Estilo visual alterado para: {new_style}"})
            return

        # API: Traduzir Capítulo Específico via LLM
        if path == "/api/book-chapter/translate":
            chapter_num = payload.get("chapter", 1)
            provider = payload.get("provider", "gemini")
            model = payload.get("model")
            try:
                res = book_service.translate_chapter(chapter_num, provider=provider, model=model, project_id=cd["active_id"])
                self._send_json(res)
            except Exception as e:
                self._send_error(f"Erro na tradução do capítulo: {e}")
            return

        # API: Decupagem Cinematográfica com IA
        if path == "/api/decoupage":
            chapter_num = payload.get("chapter", 1)
            provider = payload.get("provider", "gemini")
            model = payload.get("model")

            # Modo assíncrono opcional para evitar timeout HTTP
            if payload.get("async"):
                task_id = task_service.submit_task(
                    decoupage_service.decoupage_chapter,
                    chapter_num=chapter_num,
                    provider=provider,
                    model=model,
                    project_id=cd["active_id"]
                )
                self._send_json({
                    "status": "ok",
                    "async": True,
                    "task_id": task_id,
                    "message": f"Decupagem do Capítulo {chapter_num} iniciada em segundo plano."
                })
                return

            try:
                res = decoupage_service.decoupage_chapter(
                    chapter_num=chapter_num,
                    provider=provider,
                    model=model,
                    project_id=cd["active_id"]
                )
                self._send_json(res)
            except Exception as e:
                self._send_error(f"Erro na decupagem: {e}")
            return

        # API: Regenerar Áudios TTS
        if path == "/api/generate-audio":
            scene_id = payload.get("scene_id", "SC_01")
            if payload.get("async"):
                task_id = task_service.submit_task(
                    audio_service.generate_scene_audio,
                    scene_id=scene_id,
                    project_id=cd["active_id"]
                )
                self._send_json({
                    "status": "ok",
                    "async": True,
                    "task_id": task_id,
                    "message": f"Síntese de áudio da cena {scene_id} iniciada em segundo plano."
                })
                return

            try:
                res = audio_service.generate_scene_audio(scene_id, project_id=cd["active_id"])
                self._send_json(res)
            except Exception as e:
                self._send_error(f"Erro ao sintetizar áudio: {e}")
            return

        # API: Exportar Linha do Tempo para CapCut Desktop
        if path == "/api/export-timeline":
            scene_id = payload.get("scene_id")
            try:
                res = export_service.export_timeline_manifest(scene_id, project_id=cd["active_id"])
                self._send_json(res)
            except Exception as e:
                self._send_error(f"Erro ao exportar timeline: {e}")
        # API: Atualizar Plano de Cena Manualmente (Edição Rápida da Web)
        if path == "/api/shot/update":
            scene_id = re.sub(r'[^a-zA-Z0-9_\-]', '', payload.get("scene_id", "SC_01"))
            shot_id = re.sub(r'[^a-zA-Z0-9_\-]', '', payload.get("shot_id", ""))
            if not scene_id or not shot_id:
                self._send_error("scene_id e shot_id são obrigatórios", status=400)
                return

            scene_file = cd["scenes_dir"] / f"{scene_id}.json"
            if not scene_file.exists():
                self._send_error(f"Cena {scene_id} não encontrada", status=404)
                return

            try:
                with SCENES_LOCK:
                    with open(scene_file, "r", encoding="utf-8") as sf:
                        scene_data = json.load(sf)
                    
                    target_beat = next((b for b in scene_data.get("beats", []) if b.get("shot_id") == shot_id), None)
                    if not target_beat:
                        self._send_error(f"Plano {shot_id} não encontrado na cena {scene_id}", status=404)
                        return

                    # Atualiza os campos editáveis
                    if "action_pt" in payload:
                        target_beat["action_pt"] = payload["action_pt"].strip()
                    if "narration" in payload:
                        target_beat["narration"] = payload["narration"].strip()
                    if "image_prompt_en" in payload:
                        target_beat["image_prompt_en"] = payload["image_prompt_en"].strip()
                    if "video_prompt_en" in payload:
                        target_beat["video_prompt_en"] = payload["video_prompt_en"].strip()
                        target_beat["prompt_en"] = payload["video_prompt_en"].strip()
                    if "kling_camera_controls" in payload and isinstance(payload["kling_camera_controls"], dict):
                        target_beat["kling_camera_controls"] = payload["kling_camera_controls"]

                    atomic_write_json(scene_file, scene_data, make_backup=True)

                # Recompila ficha de produção do plano
                try:
                    import importlib
                    compiler = importlib.import_module("03_compile_production_sheet")
                    compiler.compile_scene_sheet(scene_file)
                except Exception as ex_comp:
                    logger.warning("Aviso ao recompilar ficha após edição: %s", ex_comp)

                self._send_json({
                    "status": "ok",
                    "shot_id": shot_id,
                    "scene_id": scene_id,
                    "message": f"Plano {shot_id} atualizado com sucesso!"
                })
            except Exception as e:
                self._send_error(f"Erro ao salvar alterações do plano: {e}")
            return

        # API: Gerar Vídeo IA (Image-to-Video com Chaining)
        if path == "/api/generate-video":
            scene_id = payload.get("scene_id", "SC_01")
            shot_id = payload.get("shot_id")
            prompt = payload.get("prompt")
            use_chaining = payload.get("use_chaining", True)

            if not shot_id:
                self._send_error("Identificador do plano (shot_id) é obrigatório", status=400)
                return

            try:
                res = video_service.generate_shot_video(
                    scene_id=scene_id,
                    shot_id=shot_id,
                    project_id=cd["active_id"],
                    prompt_override=prompt,
                    use_chaining=use_chaining
                )
                if res.get("status") == "ok":
                    self._send_json(res)
                else:
                    self._send_error(res.get("message", "Falha ao gerar vídeo"))
            except Exception as e:
                self._send_error(f"Erro ao renderizar vídeo: {e}")
            return

        # API: Gerar Todos os Vídeos da Cena em Lote (Background Task)
        if path == "/api/generate-scene-videos":
            scene_id = payload.get("scene_id", "SC_01")
            try:
                task_id = video_service.generate_scene_videos_batch(
                    scene_id=scene_id,
                    project_id=cd["active_id"]
                )
                self._send_json({
                    "status": "ok",
                    "task_id": task_id,
                    "message": f"Renderização em lote iniciada para cena {scene_id}!"
                })
            except Exception as e:
                self._send_error(f"Erro ao iniciar render em lote: {e}")
            return

        # API: Gerar Imagem com IA (Google Imagen 3 / FLUX)
        if path == "/api/generate-image":
            prompt = payload.get("prompt", "")
            asset_type = payload.get("asset_type", "shot")
            identifier = payload.get("identifier", "shot_preview")
            scene_id = payload.get("scene_id", "SC_01")
            style = payload.get("style", "realistic")

            if not prompt:
                self._send_error("Prompt não informado", status=400)
                return

            try:
                import llm_client
                clean_id = re.sub(r'[^a-zA-Z0-9_\-]', '', identifier)
                
                if asset_type == "shot":
                    renders_dir = cd["project_dir"] / "06_renders"
                    renders_dir.mkdir(parents=True, exist_ok=True)
                    out_file = renders_dir / f"{clean_id}.jpg"
                    web_asset_file = WEB_DIR / "assets" / f"{clean_id}.jpg"
                    rel_url = f"assets/{clean_id}.jpg"

                    success = llm_client.generate_image_asset(prompt, out_file, style=style, aspect_ratio="16:9")
                    if success:
                        try:
                            shutil.copy2(out_file, web_asset_file)
                        except Exception as ex:
                            logger.warning("Falha ao sincronizar web_asset_file para shot %s: %s", clean_id, ex)
                        # Atualiza a cena para persistir a imagem gerada
                        s_file = cd["scenes_dir"] / f"{scene_id}.json"
                        if s_file.exists():
                            try:
                                with SCENES_LOCK:
                                    with open(s_file, "r", encoding="utf-8") as sf:
                                        s_data = json.load(sf)
                                    for beat in s_data.get("beats", []):
                                        if beat.get("shot_id") == identifier:
                                            beat["generated_image"] = rel_url
                                            beat["actor_image"] = rel_url
                                    atomic_write_json(s_file, s_data, make_backup=False)
                            except Exception as ex:
                                logger.warning("Aviso ao atualizar cena com imagem: %s", ex)
                else:
                    target_dir = cd["bible_dir"] / f"{asset_type}s"
                    target_dir.mkdir(parents=True, exist_ok=True)
                    out_file = target_dir / f"{clean_id}.jpg"
                    web_asset_file = WEB_DIR / "assets" / f"{clean_id}.jpg"
                    rel_url = f"assets/{clean_id}.jpg"

                    success = llm_client.generate_image_asset(prompt, out_file, style=style)
                    if success:
                        try:
                            shutil.copy2(out_file, web_asset_file)
                        except Exception as ex:
                            logger.warning("Falha ao sincronizar web_asset_file para bible %s: %s", clean_id, ex)

                if success:
                    self._send_json({
                        "status": "ok",
                        "image_url": rel_url,
                        "message": "Imagem gerada com sucesso via IA!"
                    })
                else:
                    self._send_error("Falha na geração da imagem pelos motores de IA.")
            except Exception as e:
                self._send_error(str(e))
            return

        # API: Upload de Imagem Externa (Midjourney, Leonardo, ComfyUI, etc.)
        if path == "/api/upload-image":
            image_base64 = payload.get("image_base64")
            filename = payload.get("filename", "upload.jpg")
            target_type = payload.get("target_type", "shot")
            
            if not image_base64:
                self._send_error("Nenhum arquivo enviado.", status=400)
                return

            try:
                if "," in image_base64:
                    image_base64 = image_base64.split(",", 1)[1]
                image_bytes = base64.b64decode(image_base64)
                
                ext = ".jpg"
                if filename.lower().endswith(".png"):
                    ext = ".png"
                elif filename.lower().endswith(".webp"):
                    ext = ".webp"
                
                if target_type == "shot":
                    shot_id = payload.get("identifier", "shot")
                    scene_id = re.sub(r'[^a-zA-Z0-9_\-]', '', payload.get("scene_id", "SC_01"))
                    clean_id = re.sub(r'[^a-zA-Z0-9_\-]', '', shot_id)
                    
                    renders_dir = cd["project_dir"] / "06_renders"
                    renders_dir.mkdir(parents=True, exist_ok=True)
                    out_file = renders_dir / f"{clean_id}{ext}"
                    web_asset_file = WEB_DIR / "assets" / f"{clean_id}{ext}"
                    rel_url = f"assets/{clean_id}{ext}"
                    
                    with open(out_file, "wb") as f_out:
                        f_out.write(image_bytes)
                    try:
                        shutil.copy2(out_file, web_asset_file)
                    except Exception as ex:
                        logger.warning("Falha ao sincronizar web_asset_file (%s): %s", clean_id, ex)
                        
                    s_file = cd["scenes_dir"] / f"{scene_id}.json"
                    if s_file.exists():
                        try:
                            with SCENES_LOCK:
                                with open(s_file, "r", encoding="utf-8") as sf:
                                    s_data = json.load(sf)
                                for beat in s_data.get("beats", []):
                                    if beat.get("shot_id") == shot_id:
                                        beat["generated_image"] = rel_url
                                        beat["actor_image"] = rel_url
                                atomic_write_json(s_file, s_data, make_backup=False)
                        except Exception as ex:
                            logger.warning("Erro ao atualizar cena com upload: %s", ex)
                            
                    self._send_json({
                        "status": "ok",
                        "image_url": rel_url,
                        "message": f"Imagem externa vinculada ao plano {shot_id} com sucesso!"
                    })
                    return

                elif target_type == "bible":
                    entity_type = re.sub(r'[^a-zA-Z0-9_\-]', '', payload.get("entity_type", "character"))
                    tag = payload.get("tag", "")
                    view_type = re.sub(r'[^a-zA-Z0-9_\-]', '', payload.get("view_type", "p1"))
                    style = re.sub(r'[^a-zA-Z0-9_\-]', '', payload.get("style", "realistic"))
                    
                    clean_tag = re.sub(r'[^a-zA-Z0-9_\-]', '', tag).strip("_")
                    target_folder = cd["bible_dir"] / f"{entity_type}s" / f"@{clean_tag}"
                    target_folder.mkdir(parents=True, exist_ok=True)
                    
                    out_file = target_folder / f"{view_type}_{style}{ext}"
                    web_filename = f"{clean_tag}_{view_type}_{style}{ext}"
                    web_asset_file = WEB_DIR / "assets" / web_filename
                    rel_url = f"assets/{web_filename}"
                    
                    with open(out_file, "wb") as f_out:
                        f_out.write(image_bytes)
                    try:
                        shutil.copy2(out_file, web_asset_file)
                    except Exception as ex:
                        logger.warning("Falha ao sincronizar web_asset_file (%s): %s", web_filename, ex)
                        
                    legacy_file = WEB_DIR / "assets" / f"{clean_tag}_{view_type}{ext}"
                    try:
                        shutil.copy2(out_file, legacy_file)
                    except Exception as ex:
                        logger.warning("Falha ao sincronizar legacy_file (%s): %s", clean_tag, ex)

                    manifest_file = cd["manifest_path"]
                    if manifest_file.exists():
                        try:
                            with MANIFEST_LOCK:
                                with open(manifest_file, "r", encoding="utf-8") as mf:
                                    b_data = json.load(mf)
                                
                                category_key = f"{entity_type}s"
                                if category_key in b_data:
                                    for item in b_data[category_key]:
                                        if item.get("tag") == tag:
                                            style_key = f"images_{style}"
                                            if style_key not in item:
                                                item[style_key] = {}
                                            item[style_key][view_type] = rel_url
                                            
                                            if entity_type == "character":
                                                if view_type == "p1":
                                                    item["image_primary"] = rel_url
                                                    item[f"image_primary_{style}"] = rel_url
                                                elif view_type == "modelsheet":
                                                    item["image_modelsheet"] = rel_url
                                                    item[f"image_modelsheet_{style}"] = rel_url
                                                elif view_type == "expressions":
                                                    item["image_expressions"] = rel_url
                                                    item[f"image_expressions_{style}"] = rel_url
                                            elif entity_type == "location":
                                                if view_type == "master":
                                                    item["image_primary"] = rel_url
                                                    item[f"image_primary_{style}"] = rel_url
                                                elif view_type == "set_design":
                                                    item["image_matte_painting"] = rel_url
                                                    item[f"image_matte_{style}"] = rel_url
                                                elif view_type == "lighting":
                                                    item["image_lighting"] = rel_url
                                                    item[f"image_lighting_{style}"] = rel_url
                                            elif entity_type == "prop":
                                                if view_type == "hero":
                                                    item["image_primary"] = rel_url
                                                    item[f"image_primary_{style}"] = rel_url
                                                elif view_type == "propsheet":
                                                    item["image_propsheet"] = rel_url
                                                    item[f"image_propsheet_{style}"] = rel_url

                                atomic_write_json(manifest_file, b_data)
                        except Exception as ex_m:
                            print(f"[SERVER] Erro ao atualizar manifest com upload: {ex_m}")

                    self._send_json({
                        "status": "ok",
                        "image_url": rel_url,
                        "view_type": view_type,
                        "style": style,
                        "message": f"Imagem externa de {tag} ({view_type}) importada com sucesso!"
                    })
                    return

            except Exception as e:
                self._send_error(f"Erro no processamento da imagem: {e}")
                return

        # API: Gerar Model Sheet / Character Sheet com fal.ai FLUX
        if path == "/api/generate-sheet":
            entity_type = payload.get("entity_type", "character")
            tag = payload.get("tag", "")
            view_type = payload.get("view_type", "p1")
            prompt = payload.get("prompt", "")
            style = payload.get("style", "realistic")

            if not prompt or not tag:
                self._send_error("Tag e Prompt são obrigatórios", status=400)
                return

            try:
                import fal_client
                clean_tag = re.sub(r'[^a-zA-Z0-9_\-]', '', tag).strip("_")

                target_folder = cd["bible_dir"] / f"{entity_type}s" / f"@{clean_tag}"
                target_folder.mkdir(parents=True, exist_ok=True)
                
                out_file = target_folder / f"{view_type}_{style}.jpg"
                web_filename = f"{clean_tag}_{view_type}_{style}.jpg"
                web_asset_file = WEB_DIR / "assets" / web_filename
                rel_url = f"assets/{web_filename}"

                aspect = "16:9" if any(k in view_type for k in ["modelsheet", "master", "set_design", "propsheet", "expressions", "lighting"]) else "1:1"
                ok, msg = fal_client.generate_flux_image(prompt, out_file, aspect_ratio=aspect)

                if ok:
                    shutil.copy2(out_file, web_asset_file)
                    legacy_file = WEB_DIR / "assets" / f"{clean_tag}_{view_type}.jpg"
                    try:
                        shutil.copy2(out_file, legacy_file)
                    except Exception as ex:
                        logger.warning("Falha ao sincronizar legacy_file em generate-sheet (%s): %s", clean_tag, ex)

                    manifest_file = cd["manifest_path"]
                    if manifest_file.exists():
                        try:
                            with MANIFEST_LOCK:
                                with open(manifest_file, "r", encoding="utf-8") as mf:
                                    b_data = json.load(mf)
                                
                                category_key = f"{entity_type}s"
                                if category_key in b_data:
                                    for item in b_data[category_key]:
                                        if item.get("tag") == tag:
                                            style_key = f"images_{style}"
                                            if style_key not in item:
                                                item[style_key] = {}
                                            item[style_key][view_type] = rel_url

                                            if entity_type == "character":
                                                if view_type == "p1":
                                                    item["image_primary"] = rel_url
                                                    item[f"image_primary_{style}"] = rel_url
                                                elif view_type == "modelsheet":
                                                    item["image_modelsheet"] = rel_url
                                                    item[f"image_modelsheet_{style}"] = rel_url
                                                elif view_type == "expressions":
                                                    item["image_expressions"] = rel_url
                                                    item[f"image_expressions_{style}"] = rel_url
                                            elif entity_type == "location":
                                                if view_type == "master":
                                                    item["image_primary"] = rel_url
                                                    item[f"image_primary_{style}"] = rel_url
                                                elif view_type == "set_design":
                                                    item["image_matte_painting"] = rel_url
                                                    item[f"image_matte_{style}"] = rel_url
                                                elif view_type == "lighting":
                                                    item["image_lighting"] = rel_url
                                                    item[f"image_lighting_{style}"] = rel_url
                                            elif entity_type == "prop":
                                                if view_type == "hero":
                                                    item["image_primary"] = rel_url
                                                    item[f"image_primary_{style}"] = rel_url
                                                elif view_type == "propsheet":
                                                    item["image_propsheet"] = rel_url
                                                    item[f"image_propsheet_{style}"] = rel_url

                                atomic_write_json(manifest_file, b_data)
                        except Exception as ex_m:
                            print(f"[SERVER] Aviso ao atualizar manifest.json: {ex_m}")

                    self._send_json({
                        "status": "ok",
                        "image_url": rel_url,
                        "view_type": view_type,
                        "style": style,
                        "message": f"Asset {view_type} gerado com sucesso via FLUX!"
                    })
                else:
                    self._send_error(f"Erro ao gerar com fal.ai: {msg}")
            except Exception as e:
                self._send_error(f"Exceção ao gerar com fal.ai: {e}")
            return

        # API: Gerar Pacote Completo com fal.ai FLUX
        if path == "/api/generate-pack":
            entity_type = payload.get("entity_type", "character")
            if entity_type not in ["character", "location", "prop"]:
                self._send_error("Tipo de entidade inválido.", status=400)
                return
            tag = payload.get("tag", "")
            style = payload.get("style", "realistic")

            try:
                import fal_client
                clean_tag = re.sub(r'[^a-zA-Z0-9_\-]', '', tag).strip("_")

                manifest_file = cd["manifest_path"]
                if not manifest_file.exists():
                    self._send_error("Manifesto da Bíblia não encontrado.", status=404)
                    return

                with open(manifest_file, "r", encoding="utf-8") as mf:
                    b_data = json.load(mf)

                category_key = f"{entity_type}s"
                item = next((i for i in b_data.get(category_key, []) if i.get("tag") == tag), None)
                if not item:
                    self._send_error(f"Item {tag} não encontrado no manifesto.", status=404)
                    return

                views_to_gen = []
                if entity_type == "character":
                    views_to_gen = [
                        ("p1", item.get("prompt_p1") or item.get("prompt_primary"), "1:1"),
                        ("modelsheet", item.get("prompt_modelsheet"), "16:9"),
                        ("expressions", item.get("prompt_expressions"), "16:9")
                    ]
                elif entity_type == "location":
                    views_to_gen = [
                        ("master", item.get("prompt_master") or item.get("prompt_primary"), "16:9"),
                        ("set_design", item.get("prompt_matte_painting"), "16:9"),
                        ("lighting", item.get("prompt_lighting"), "16:9")
                    ]
                elif entity_type == "prop":
                    views_to_gen = [
                        ("hero", item.get("prompt_hero") or item.get("prompt_primary"), "1:1"),
                        ("propsheet", item.get("prompt_propsheet"), "16:9")
                    ]

                target_folder = cd["bible_dir"] / category_key / f"@{clean_tag}"
                target_folder.mkdir(parents=True, exist_ok=True)
                results = {}

                for v_type, p_text, aspect in views_to_gen:
                    if not p_text:
                        continue
                    out_file = target_folder / f"{v_type}_{style}.jpg"
                    web_filename = f"{clean_tag}_{v_type}_{style}.jpg"
                    web_asset_file = WEB_DIR / "assets" / web_filename
                    rel_url = f"assets/{web_filename}"

                    ok, _ = fal_client.generate_flux_image(p_text, out_file, aspect_ratio=aspect)
                    if ok:
                        shutil.copy2(out_file, web_asset_file)
                        results[v_type] = rel_url

                self._send_json({
                    "status": "ok",
                    "results": results,
                    "message": f"Pacote de {tag} gerado com sucesso via FLUX!"
                })
            except Exception as e:
                self._send_error(f"Erro ao gerar pacote: {e}")
            return

        # API: Atualizar Prompt Customizado no Manifesto
        if path == "/api/bible/update-prompt":
            entity_type = payload.get("entity_type", "character")
            tag = payload.get("tag", "")
            view_type = payload.get("view_type", "p1")
            new_prompt = payload.get("prompt", "")

            manifest_file = cd["manifest_path"]
            if not manifest_file.exists():
                self._send_error("Manifesto não encontrado", status=404)
                return

            try:
                with MANIFEST_LOCK:
                    with open(manifest_file, "r", encoding="utf-8") as mf:
                        b_data = json.load(mf)

                    category_key = f"{entity_type}s"
                    for item in b_data.get(category_key, []):
                        if item.get("tag") == tag:
                            if view_type in ["p1", "master", "hero"]:
                                item["prompt_primary"] = new_prompt
                            if f"prompt_{view_type}" in item:
                                item[f"prompt_{view_type}"] = new_prompt

                    atomic_write_json(manifest_file, b_data)

                self._send_json({"status": "ok", "message": f"Prompt de {tag} ({view_type}) salvo!"})
            except Exception as e:
                self._send_error(f"Erro ao salvar prompt: {e}")
            return

        self.send_error(404, "Endpoint não encontrado")

def run_server(port=8080, host="127.0.0.1"):
    server_address = (host, port)
    httpd = ThreadingHTTPServer(server_address, StudioRequestHandler)
    print(f"\n=======================================================")
    print(f"🎬 Tríade Studio Web rodando em: http://{host}:{port}")
    print(f"=======================================================\n")
    httpd.serve_forever()

if __name__ == "__main__":
    run_server()
