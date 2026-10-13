"""
Inicializador em 1 Clique: Tríade Studio Web
Inicia o servidor backend e abre a interface cinematográfica no navegador.
"""
import sys
import webbrowser
import threading
import time
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

from server.app import run_server

def open_browser():
    time.sleep(1.2)
    url = "http://127.0.0.1:8080"
    print(f"Abrindo interface no navegador: {url}")
    webbrowser.open(url)

if __name__ == "__main__":
    # Dispara a abertura do navegador em uma thread paralela
    threading.Thread(target=open_browser, daemon=True).start()
    
    # Inicia o servidor HTTP
    try:
        run_server(port=8080)
    except KeyboardInterrupt:
        print("\nStudio finalizado pelo usuário.")
