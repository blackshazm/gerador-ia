"""
Cliente fal.ai — Black Forest Labs FLUX.3 / FLUX Text-to-Image
Pipeline Cinematográfico da Tríade Studio
Gera Model Sheets, Character Sheets, Location Sheets e Renders de Planos usando FLUX.
"""
import os
import sys
import json
import time
import urllib.request
import urllib.error
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = BASE_DIR / ".env"

def load_env() -> dict:
    env = {}
    if ENV_PATH.exists():
        try:
            with open(ENV_PATH, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        env[k.strip()] = v.strip().strip("\"'")
        except Exception:
            pass
    for k in ["FAL_KEY", "FAL_MODEL"]:
        if k in os.environ and os.environ[k]:
            env[k] = os.environ[k]
    return env

def get_fal_key() -> str:
    env = load_env()
    key = env.get("FAL_KEY", "")
    if not key:
        raise ValueError("FAL_KEY não encontrada no arquivo .env. Configure sua chave do fal.ai.")
    return key

def clean_flux_prompt(prompt: str) -> str:
    """Remove flags específicas do Midjourney (--ar, --v, --q, etc) que podem quebrar o validador do fal.ai."""
    import re
    # Remove --ar 16:9, --ar 1:1, etc
    p = re.sub(r'--ar\s+\d+:\d+', '', prompt, flags=re.IGNORECASE)
    # Remove outras flags comuns de Midjourney
    p = re.sub(r'--(v|version|style|stylize|chaos|weird|q|quality|seed|stop|tile)\s+\S+', '', p, flags=re.IGNORECASE)
    p = re.sub(r'--(v6|v5|v4|fast|relax|turbo|raw)', '', p, flags=re.IGNORECASE)
    # Remove espaços duplos
    p = re.sub(r'\s+', ' ', p).strip()
    return p

def generate_flux_image(prompt: str, output_path: Path, aspect_ratio: str = "16:9", model: str = None) -> tuple[bool, str]:
    """
    Envia requisição para a API fal.ai gerando imagem com Black Forest Labs FLUX.3.
    Salva diretamente no output_path.
    Retorna (sucesso: bool, mensagem_ou_url: str).
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        fal_key = get_fal_key()
    except Exception as e:
        return False, str(e)

    env = load_env()
    target_model = model or env.get("FAL_MODEL", "blackforestlabs/flux-3/text-to-image")
    clean_p = clean_flux_prompt(prompt)

    # Mapeamento de Proporção
    if "16:9" in aspect_ratio or aspect_ratio == "16_9":
        image_size = "landscape_16_9"
    elif "1:1" in aspect_ratio:
        image_size = "square_hd"
    elif "9:16" in aspect_ratio:
        image_size = "portrait_16_9"
    elif "4:3" in aspect_ratio:
        image_size = "landscape_4_3"
    else:
        image_size = "landscape_16_9"

    # Modelos candidatos em cascata
    candidate_models = [target_model]
    if target_model != "fal-ai/flux/dev":
        candidate_models.append("fal-ai/flux/dev")
    if target_model != "fal-ai/flux/schnell":
        candidate_models.append("fal-ai/flux/schnell")

    last_error = None
    for current_model in candidate_models:
        url = f"https://fal.run/{current_model}"
        headers = {
            "Authorization": f"Key {fal_key}",
            "Content-Type": "application/json",
            "User-Agent": "TriadeStudio/2.0"
        }
        
        payload = {
            "prompt": clean_p,
            "image_size": image_size,
            "num_inference_steps": 28 if "schnell" not in current_model else 4,
            "guidance_scale": 3.5,
            "enable_safety_checker": True
        }

        print(f"[FAL.AI] Enviando requisição para {current_model} (Aspect: {image_size})...")
        req_data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=req_data, headers=headers, method="POST")

        for attempt in range(1, 4):
            try:
                with urllib.request.urlopen(req, timeout=120) as resp:
                    resp_data = json.loads(resp.read().decode("utf-8"))
                    images = resp_data.get("images", [])
                    if not images or not images[0].get("url"):
                        raise ValueError(f"fal.ai não retornou imagens válidas: {resp_data}")

                    image_url = images[0]["url"]
                    print(f"[FAL.AI] Imagem gerada com sucesso! Baixando binário de: {image_url[:60]}...")

                    # Download do binário
                    img_req = urllib.request.Request(image_url, headers={"User-Agent": "TriadeStudio/2.0"})
                    with urllib.request.urlopen(img_req, timeout=60) as img_resp:
                        img_bytes = img_resp.read()
                        with open(output_path, "wb") as f:
                            f.write(img_bytes)

                    print(f"[FAL.AI] Arquivo salvo em: {output_path} ({len(img_bytes)} bytes)")
                    return True, image_url

            except urllib.error.HTTPError as e:
                err_body = e.read().decode("utf-8", errors="ignore")
                last_error = f"HTTP {e.code}: {err_body[:200]}"
                print(f"[FAL.AI] Erro {current_model} [Tentativa {attempt}/3]: {last_error}")
                if e.code in [404, 422]:
                    # Modelo incorreto ou parâmetros não suportados, tenta próximo modelo
                    break
                time.sleep(2 * attempt)
            except Exception as e:
                last_error = str(e)
                print(f"[FAL.AI] Exceção [Tentativa {attempt}/3]: {last_error}")
                time.sleep(2 * attempt)

    return False, f"Falha na geração fal.ai: {last_error}"

def generate_fal_video(
    image_path: Path,
    prompt: str,
    output_path: Path,
    duration_s: float = 5.0,
    model: str = None
) -> tuple[bool, str]:
    """
    Gera clipe de vídeo (MP4) usando a API fal.ai (Kling Standard / Minimax Video / Luma).
    Utiliza a imagem fornecida como First Frame (Image-to-Video).
    Salva diretamente em output_path.
    Retorna (sucesso: bool, url_ou_mensagem: str).
    """
    import base64
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    image_path = Path(image_path)

    if not image_path.exists():
        return False, f"Imagem de referência não encontrada: {image_path}"

    try:
        fal_key = get_fal_key()
    except Exception as e:
        return False, str(e)

    env = load_env()
    target_model = model or env.get("FAL_VIDEO_MODEL", "fal-ai/kling-video/v1/standard/image-to-video")
    clean_p = clean_flux_prompt(prompt)

    # Converte imagem local para data URI base64
    try:
        with open(image_path, "rb") as f:
            b64_content = base64.b64encode(f.read()).decode("utf-8")
        mime = "image/png" if image_path.suffix.lower() == ".png" else "image/jpeg"
        image_data_uri = f"data:{mime};base64,{b64_content}"
    except Exception as ex_b64:
        return False, f"Erro ao processar imagem de entrada: {ex_b64}"

    dur_str = "5" if duration_s <= 6.0 else "10"
    payload = {
        "prompt": clean_p,
        "image_url": image_data_uri,
        "duration": dur_str,
        "aspect_ratio": "16:9"
    }

    # Modelos candidatos em cascata para vídeo
    candidate_models = [target_model]
    if "kling" not in target_model:
        candidate_models.append("fal-ai/kling-video/v1/standard/image-to-video")
    if "minimax" not in target_model:
        candidate_models.append("fal-ai/minimax/video-01")

    headers = {
        "Authorization": f"Key {fal_key}",
        "Content-Type": "application/json",
        "User-Agent": "TriadeStudio/2.0"
    }

    last_error = None
    for current_model in candidate_models:
        print(f"[FAL.AI VIDEO] Enfileirando geração de vídeo em {current_model}...")
        queue_url = f"https://queue.fal.run/{current_model}"
        req_data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(queue_url, data=req_data, headers=headers, method="POST")

        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                q_data = json.loads(resp.read().decode("utf-8"))
            
            request_id = q_data.get("request_id")
            status_url = q_data.get("status_url")
            response_url = q_data.get("response_url")

            if not status_url or not response_url:
                # Se respondeu diretamente com o resultado
                video_info = q_data.get("video", {})
                v_url = video_info.get("url")
                if v_url:
                    return _download_video(v_url, output_path)

            print(f"[FAL.AI VIDEO] Tarefa {request_id} aceita na fila. Aguardando render (até 180s)...")
            # Polling da fila
            start_time = time.time()
            while time.time() - start_time < 180:
                time.sleep(5)
                s_req = urllib.request.Request(status_url, headers=headers)
                with urllib.request.urlopen(s_req, timeout=20) as s_resp:
                    s_data = json.loads(s_resp.read().decode("utf-8"))
                
                status = s_data.get("status")
                if status == "COMPLETED":
                    # Busca resultado final
                    r_req = urllib.request.Request(response_url, headers=headers)
                    with urllib.request.urlopen(r_req, timeout=20) as r_resp:
                        res_data = json.loads(r_resp.read().decode("utf-8"))
                    
                    video_info = res_data.get("video", {})
                    v_url = video_info.get("url")
                    if not v_url:
                        raise ValueError(f"fal.ai não retornou URL de vídeo válida: {res_data}")
                    return _download_video(v_url, output_path)

                elif status in ["FAILED", "CANCELLED"]:
                    raise ValueError(f"fal.ai falhou no processamento do vídeo: {s_data.get('error')}")

        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8", errors="ignore")
            last_error = f"HTTP {e.code}: {err_body[:200]}"
            print(f"[FAL.AI VIDEO] Erro no modelo {current_model}: {last_error}")
        except Exception as e:
            last_error = str(e)
            print(f"[FAL.AI VIDEO] Exceção no modelo {current_model}: {last_error}")

    return False, f"Falha na geração de vídeo fal.ai: {last_error}"

def _download_video(video_url: str, output_path: Path) -> tuple[bool, str]:
    """Baixa o arquivo binário do vídeo MP4 gerado."""
    try:
        print(f"[FAL.AI VIDEO] Baixando vídeo renderizado de: {video_url[:60]}...")
        req = urllib.request.Request(video_url, headers={"User-Agent": "TriadeStudio/2.0"})
        with urllib.request.urlopen(req, timeout=90) as resp:
            v_bytes = resp.read()
            with open(output_path, "wb") as f:
                f.write(v_bytes)
        print(f"[FAL.AI VIDEO] Vídeo salvo com sucesso em: {output_path} ({len(v_bytes)} bytes)")
        return True, video_url
    except Exception as ex:
        return False, f"Erro ao baixar vídeo: {ex}"

if __name__ == "__main__":
    if "--test" in sys.argv:
        test_out = BASE_DIR / "web" / "assets" / "fal_test_preview.jpg"
        print("[TEST] Iniciando teste de conexão fal.ai FLUX...")
        prompt_test = "Cinematic character model sheet turnaround of Mrs. Gorf, 4 views: front view, three-quarter view, profile view, back view, Victorian schoolteacher, neutral studio background, photorealistic 35mm film photograph, 8k --ar 16:9"
        ok, msg = generate_flux_image(prompt_test, test_out, aspect_ratio="16:9")
        if ok:
            print(f"[TEST] SUCESSO! Teste gravado em {test_out}")
        else:
            print(f"[TEST] ERRO: {msg}")
