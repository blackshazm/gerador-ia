"""
Módulo de Gerenciamento de Tarefas Assíncronas — Tríade Studio
Executa processos pesados de IA (decupagem longa, geração em lote de imagens)
em background com acompanhamento de progresso e sem risco de timeout HTTP.
"""
import time
import uuid
import threading
from typing import Optional, Dict, Any, Callable
from concurrent.futures import ThreadPoolExecutor

# Executor compartilhado para tarefas em segundo plano (máximo 2 concorrentes para poupar recursos)
_EXECUTOR = ThreadPoolExecutor(max_workers=2, thread_name_prefix="TriadeTaskWorker")
_TASKS_LOCK = threading.Lock()
_TASKS: Dict[str, Dict[str, Any]] = {}

def _cleanup_old_tasks_locked():
    """Remove tarefas concluídas/falhadas antigas para evitar vazamento de memória."""
    now = time.time()
    cutoff = now - 7200  # 2 horas
    to_delete = []
    finished_tasks = []

    for tid, tinfo in _TASKS.items():
        if tinfo["status"] in ["completed", "failed"]:
            finished_tasks.append((tid, tinfo.get("finished_at") or tinfo.get("created_at", 0)))
            if (tinfo.get("finished_at") or 0) < cutoff:
                to_delete.append(tid)

    if len(finished_tasks) - len(to_delete) > 50:
        finished_tasks.sort(key=lambda x: x[1])
        excess = (len(finished_tasks) - len(to_delete)) - 50
        for tid, _ in finished_tasks[:excess]:
            if tid not in to_delete:
                to_delete.append(tid)

    for tid in to_delete:
        _TASKS.pop(tid, None)

def submit_task(fn: Callable, *args, **kwargs) -> str:
    """
    Submete uma função para execução assíncrona na thread pool.
    Retorna o task_id único para acompanhamento.
    """
    task_id = f"task_{uuid.uuid4().hex[:8]}"
    now = time.time()

    with _TASKS_LOCK:
        _cleanup_old_tasks_locked()
        _TASKS[task_id] = {
            "task_id": task_id,
            "status": "pending",  # pending | running | completed | failed
            "progress": 0,        # 0 a 100
            "message": "Tarefa enfileirada para execução",
            "result": None,
            "error": None,
            "created_at": now,
            "started_at": None,
            "finished_at": None
        }

    def _runner():
        with _TASKS_LOCK:
            if task_id in _TASKS:
                _TASKS[task_id]["status"] = "running"
                _TASKS[task_id]["started_at"] = time.time()
                _TASKS[task_id]["message"] = "Processando..."

        try:
            # Executa a função passando callback de progresso se aceitar
            result = fn(*args, **kwargs)
            with _TASKS_LOCK:
                if task_id in _TASKS:
                    _TASKS[task_id]["status"] = "completed"
                    _TASKS[task_id]["progress"] = 100
                    _TASKS[task_id]["result"] = result
                    _TASKS[task_id]["message"] = "Tarefa concluída com sucesso!"
                    _TASKS[task_id]["finished_at"] = time.time()
        except Exception as ex:
            with _TASKS_LOCK:
                if task_id in _TASKS:
                    _TASKS[task_id]["status"] = "failed"
                    _TASKS[task_id]["error"] = str(ex)
                    _TASKS[task_id]["message"] = f"Falha na execução: {ex}"
                    _TASKS[task_id]["finished_at"] = time.time()

    _EXECUTOR.submit(_runner)
    return task_id

def get_task_status(task_id: str) -> Optional[Dict[str, Any]]:
    """Retorna cópia do estado atual da tarefa especificada."""
    with _TASKS_LOCK:
        task_info = _TASKS.get(task_id)
        if task_info:
            return dict(task_info)
    return None

def update_task_progress(task_id: str, progress: int, message: str = ""):
    """Atualiza o percentual de progresso de uma tarefa em execução."""
    with _TASKS_LOCK:
        if task_id in _TASKS:
            _TASKS[task_id]["progress"] = max(0, min(100, progress))
            if message:
                _TASKS[task_id]["message"] = message

def list_recent_tasks(limit: int = 10) -> list:
    """Lista as tarefas mais recentes registradas."""
    with _TASKS_LOCK:
        items = list(_TASKS.values())
    items.sort(key=lambda x: x.get("created_at", 0), reverse=True)
    return items[:limit]
