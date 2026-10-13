"""
Cliente Unificado de Modelos de Linguagem (LLM) — Tríade Studio
Suporta OpenRouter, NVIDIA NIM e Ollama Local com interface compatível OpenAI.
Sem dependências pesadas externas (usa biblioteca padrão urllib.request).
"""
import os
import sys
import json
import time
import re
import urllib.request
import urllib.error
from pathlib import Path

try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(line_buffering=True)
except Exception:
    pass

BASE_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = BASE_DIR / ".env"

def load_env() -> dict:
    """Carrega variáveis de ambiente do arquivo .env sem sobrescrever o sistema."""
    env = {}
    if ENV_PATH.exists():
        try:
            with open(ENV_PATH, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        env[k.strip()] = v.strip().strip("\"'")
        except Exception as e:
            print(f"[LLM] Aviso ao carregar .env: {e}")
    # Mescla com variáveis de ambiente do sistema (sistema tem precedência se definida)
    for k in ["GEMINI_API_KEY", "GOOGLE_API_KEY", "GEMINI_MODEL",
              "OPENROUTER_API_KEY", "NVIDIA_API_KEY", "DEFAULT_LLM_PROVIDER", 
              "OPENROUTER_MODEL", "NVIDIA_MODEL", "OLLAMA_MODEL", "OLLAMA_BASE_URL", "FAL_KEY"]:
        if k in os.environ and os.environ[k]:
            env[k] = os.environ[k]
    return env

def mask_api_key(key: str) -> str:
    """Retorna a chave mascarada para exibição segura na interface web."""
    if not key or len(key) < 8:
        return ""
    return f"{key[:4]}...{key[-4:]}"

def save_env_keys(keys_to_update: dict):
    """Atualiza chaves no arquivo .env preservando comentários e variáveis existentes com proteção contra CRLF Injection."""
    clean_updates = {}
    for k, v in keys_to_update.items():
        clean_k = re.sub(r'[^a-zA-Z0-9_]', '', str(k)).strip()
        clean_v = re.sub(r'[\r\n]', '', str(v)).strip()
        if clean_k:
            clean_updates[clean_k] = clean_v

    lines = []
    updated_keys = set()
    if ENV_PATH.exists():
        with open(ENV_PATH, "r", encoding="utf-8") as f:
            for line in f:
                stripped = line.strip()
                if stripped and not stripped.startswith("#") and "=" in stripped:
                    k, v = stripped.split("=", 1)
                    k = k.strip()
                    if k in clean_updates:
                        new_val = clean_updates[k]
                        lines.append(f"{k}={new_val}\n")
                        updated_keys.add(k)
                        continue
                lines.append(line)
    
    # Adiciona chaves novas que não existiam no arquivo
    for k, v in clean_updates.items():
        if k not in updated_keys and v:
            lines.append(f"{k}={v}\n")

    tmp_path = ENV_PATH.with_suffix(".env.tmp")
    with open(tmp_path, "w", encoding="utf-8") as f:
        f.writelines(lines)
    os.replace(tmp_path, ENV_PATH)

    # Atualiza variáveis em memória
    for k, v in clean_updates.items():
        if v:
            os.environ[k] = str(v)

def verify_api_key(provider: str, api_key: str = None) -> tuple:
    """Valida se a chave fornecida ou configurada está operando com sucesso."""
    env = load_env()
    prov = (provider or "gemini").lower()
    
    if prov in ["gemini", "google"]:
        key = api_key or env.get("GEMINI_API_KEY") or env.get("GOOGLE_API_KEY")
        if not key:
            return False, "Chave Gemini não informada."
        url = f"https://generativelanguage.googleapis.com/v1beta/models?key={key}"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "TriadeStudio/1.0"})
            with urllib.request.urlopen(req, timeout=5) as resp:
                if resp.status == 200:
                    return True, "Chave Google Gemini validada com sucesso!"
        except urllib.error.HTTPError as err:
            return False, f"Falha na validação do Gemini (HTTP {err.code}): {err.reason}"
        except Exception as ex:
            return False, f"Erro de conexão ao validar Gemini: {ex}"
            
    elif prov == "openrouter":
        key = api_key or env.get("OPENROUTER_API_KEY")
        if not key:
            return False, "Chave OpenRouter não informada."
        url = "https://openrouter.ai/api/v1/auth/key"
        try:
            req = urllib.request.Request(url, headers={"Authorization": f"Bearer {key}", "User-Agent": "TriadeStudio/1.0"})
            with urllib.request.urlopen(req, timeout=5) as resp:
                if resp.status == 200:
                    return True, "Chave OpenRouter validada com sucesso!"
        except Exception as ex:
            return False, f"Falha ao validar OpenRouter: {ex}"

    elif prov == "fal":
        key = api_key or env.get("FAL_KEY")
        if not key:
            return False, "Chave fal.ai não informada."
        if ":" in key or len(key) >= 20:
            return True, "Formato da chave fal.ai reconhecido."
        return False, "Formato de chave fal.ai inválido."

    return False, f"Provedor {provider} desconhecido."


class LLMClient:
    def __init__(self, provider: str = None, model: str = None):
        self.env = load_env()
        self.provider = provider or self.env.get("DEFAULT_LLM_PROVIDER", "gemini").lower()
        self.model = model

    def get_provider_config(self):
        """Retorna (endpoint, api_key, model, headers) para o provedor selecionado."""
        if self.provider in ["gemini", "google"]:
            api_key = self.env.get("GEMINI_API_KEY") or self.env.get("GOOGLE_API_KEY", "")
            if not api_key:
                raise ValueError(
                    "GEMINI_API_KEY não configurada no arquivo .env. "
                    "Obtenha sua chave gratuita em https://aistudio.google.com e insira no arquivo .env"
                )
            raw_model = self.model or self.env.get("GEMINI_MODEL", "gemini-2.5-flash")
            if "3.5-flash" in raw_model:
                raw_model = "gemini-2.5-flash"
            model = raw_model
            endpoint = "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions"
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            return endpoint, model, headers

        elif self.provider == "nvidia":
            api_key = self.env.get("NVIDIA_API_KEY", "")
            if not api_key:
                raise ValueError("NVIDIA_API_KEY não configurada no arquivo .env.")
            model = self.model or self.env.get("NVIDIA_MODEL", "meta/llama-3.1-70b-instruct")
            endpoint = "https://integrate.api.nvidia.com/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "User-Agent": "TriadeStudio/1.0"
            }
            return endpoint, model, headers

        elif self.provider == "ollama":
            base_url = self.env.get("OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/")
            endpoint = f"{base_url}/v1/chat/completions"
            model = self.model or self.env.get("OLLAMA_MODEL", "qwen2.5:7b-instruct")
            headers = {
                "Content-Type": "application/json"
            }
            return endpoint, model, headers

        else: # openrouter por padrão
            api_key = self.env.get("OPENROUTER_API_KEY", "")
            if not api_key:
                raise ValueError("OPENROUTER_API_KEY não configurada no arquivo .env.")
            model = self.model or self.env.get("OPENROUTER_MODEL", "qwen/qwen-2.5-72b-instruct")
            endpoint = "https://openrouter.ai/api/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "http://127.0.0.1:8080",
                "X-Title": "Triade Studio AI"
            }
            return endpoint, model, headers

    def chat_completion(self, messages: list, temperature: float = 0.5, json_mode: bool = True, max_tokens: int = 4096) -> str:
        """
        Executa chamada de chat completion e retorna o conteúdo textual da resposta.
        """
        if self.provider in ["gemini", "google"]:
            api_key = self.env.get("GEMINI_API_KEY") or self.env.get("GOOGLE_API_KEY", "")
            if not api_key:
                raise ValueError("GEMINI_API_KEY não configurada no arquivo .env.")
            raw_model = self.model or self.env.get("GEMINI_MODEL", "gemini-2.5-flash")
            if "3.5-flash" in raw_model:
                raw_model = "gemini-2.5-flash"
            model = raw_model
            clean_model = model.replace("models/", "")
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{clean_model}:generateContent?key={api_key}"
            
            system_text = ""
            contents = []
            for m in messages:
                role = m.get("role")
                c = m.get("content", "")
                if role == "system":
                    system_text += c + "\n"
                elif role == "user":
                    contents.append({"role": "user", "parts": [{"text": c}]})
                elif role == "assistant":
                    contents.append({"role": "model", "parts": [{"text": c}]})

            gem_payload = {
                "contents": contents,
                "generationConfig": {
                    "temperature": temperature,
                    "maxOutputTokens": max_tokens
                }
            }
            if system_text.strip():
                gem_payload["systemInstruction"] = {"parts": [{"text": system_text.strip()}]}
            if json_mode:
                gem_payload["generationConfig"]["response_mime_type"] = "application/json"

            data = json.dumps(gem_payload).encode("utf-8")
            req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")

            retries = 3
            for attempt in range(1, retries + 1):
                try:
                    print(f"[LLM] Enviando requisição para GOOGLE GEMINI ({clean_model})... [Tentativa {attempt}/{retries}]")
                    with urllib.request.urlopen(req, timeout=90) as resp:
                        resp_json = json.loads(resp.read().decode("utf-8"))
                        candidates = resp_json.get("candidates", [])
                        if not candidates:
                            raise ValueError("Gemini não retornou candidatos.")
                        return candidates[0]["content"]["parts"][0]["text"]
                except urllib.error.HTTPError as e:
                    err_msg = e.read().decode("utf-8", errors="ignore")
                    print(f"[LLM] Erro na Gemini API: HTTP {e.code}: {err_msg[:200]}")
                    if clean_model != "gemini-2.5-flash":
                        clean_model = "gemini-2.5-flash"
                        url = f"https://generativelanguage.googleapis.com/v1beta/models/{clean_model}:generateContent?key={api_key}"
                        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
                    time.sleep(2 * attempt)
                except Exception as e:
                    print(f"[LLM] Exceção na chamada Gemini: {e}")
                    time.sleep(2 * attempt)
            raise RuntimeError("Falha ao comunicar com Google Gemini.")

        endpoint, model, headers = self.get_provider_config()
        
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        
        # Modo JSON estruturado se solicitado
        if json_mode:
            payload["response_format"] = {"type": "json_object"}

        # Desativa tokens de raciocínio no OpenRouter para entrega direta e ultrarrápida do JSON
        if self.provider == "openrouter":
            payload["reasoning"] = {"max_tokens": 0}
            
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(endpoint, data=data, headers=headers, method="POST")

        retries = 3
        last_error = None
        for attempt in range(1, retries + 1):
            try:
                print(f"[LLM] Enviando requisição para {self.provider.upper()} (Modelo: {model})... [Tentativa {attempt}/{retries}]")
                with urllib.request.urlopen(req, timeout=90) as resp:
                    resp_body = resp.read().decode("utf-8")
                    resp_json = json.loads(resp_body)
                    
                    choices = resp_json.get("choices", [])
                    if not choices:
                        raise ValueError(f"Resposta sem escolhas retornadas: {resp_body}")
                        
                    content = choices[0].get("message", {}).get("content", "")
                    return content

            except urllib.error.HTTPError as e:
                err_content = e.read().decode("utf-8", errors="ignore")
                last_error = f"HTTP {e.code}: {err_content}"
                print(f"[LLM] Erro na API: {last_error}")
                # Se for erro 400 (ex: response_format não suportado pelo modelo), tenta sem ele
                if e.code == 400 and json_mode and "response_format" in str(err_content):
                    print("[LLM] Removendo response_format e tentando novamente...")
                    payload.pop("response_format", None)
                    data = json.dumps(payload).encode("utf-8")
                    req = urllib.request.Request(endpoint, data=data, headers=headers, method="POST")
                elif e.code in [429, 500, 502, 503, 504]:
                    time.sleep(2 * attempt)
                else:
                    break
            except Exception as e:
                last_error = str(e)
                print(f"[LLM] Exceção na requisição: {last_error}")
                if self.provider == "openrouter" and attempt >= 2:
                    fallback_model = "meta-llama/llama-3.3-70b-instruct:free"
                    if payload.get("model") != fallback_model:
                        print(f"[LLM] Ativando fallback automático para {fallback_model}...")
                        payload["model"] = fallback_model
                        data = json.dumps(payload).encode("utf-8")
                        req = urllib.request.Request(endpoint, data=data, headers=headers, method="POST")
                time.sleep(2 * attempt)

        raise RuntimeError(f"Falha ao comunicar com o provedor {self.provider}: {last_error}")

    def safe_parse_json(self, text: str) -> dict:
        return extract_json_from_text(text)

def extract_json_from_text(text: str) -> dict:
    """Extrai e faz parse seguro de JSON contido em texto ou blocos markdown."""
    text = text.strip()
    candidates = []

    if "```json" in text:
        for p in text.split("```json")[1:]:
            candidates.append(p.split("```")[0].strip())

    if "```" in text:
        parts = text.split("```")
        for p in parts[1::2]:
            candidates.append(p.strip())

    first_brace = text.find("{")
    last_brace = text.rfind("}")
    if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
        candidates.append(text[first_brace:last_brace + 1].strip())

    candidates.append(text)

    for cand in candidates:
        fb = cand.find("{")
        lb = cand.rfind("}")
        if fb != -1 and lb != -1 and lb > fb:
            cand = cand[fb:lb+1]
        else:
            continue

        # Normaliza escapes acidentais em fim de linha: ex 'texto\",' -> 'texto",'
        import re
        cand = re.sub(r'\\"(?=\s*,?\s*$)', '"', cand, flags=re.MULTILINE)

        # 1. Tentativa padrão direta
        try:
            return json.loads(cand, strict=False)
        except Exception:
            pass

        # 2. Remoção de trailing commas comuns em saídas de LLM (ex: [1, 2,] ou {"a": 1,})
        try:
            cand_no_trailing = re.sub(r',\s*([}\]])', r'\1', cand)
            return json.loads(cand_no_trailing, strict=False)
        except Exception:
            pass

        # 3. Fallback via ast.literal_eval para sintaxe de dicionário Python
        try:
            import ast
            res = ast.literal_eval(cand)
            if isinstance(res, dict):
                return res
        except Exception:
            pass

        # 4. Normalização de aspas simples e literais booleanos
        try:
            fixed = re.sub(r"'([^'\\]*(?:\\.[^'\\]*)*)'", r'"\1"', cand)
            fixed = re.sub(r':\s*True\b', ': true', fixed)
            fixed = re.sub(r':\s*False\b', ': false', fixed)
            fixed = re.sub(r':\s*None\b', ': null', fixed)
            fixed = re.sub(r',\s*([}\]])', r'\1', fixed)
            return json.loads(fixed, strict=False)
        except Exception:
            pass

    # Tentativa 4: Reparar JSON truncado por limite de max_tokens
    first_b = text.find("{")
    if first_b != -1:
        s = text[first_b:].strip()
        last_item = s.rfind("}")
        if last_item != -1:
            cand = s[:last_item + 1]
            open_curlies = cand.count("{") - cand.count("}")
            open_brackets = cand.count("[") - cand.count("]")
            cand += ("]" * max(0, open_brackets)) + ("}" * max(0, open_curlies))
            try:
                return json.loads(cand)
            except Exception:
                pass

    raise ValueError(f"Não foi possível decodificar JSON da resposta (primeiros 300 caracteres): {text[:300]}")

def generate_image_asset(prompt: str, output_path: Path, style: str = "realistic", seed: int = None) -> bool:
    """
    Gera imagem utilizando o Google AI Studio (Imagen 3) com fallback automático para Pollinations FLUX.
    Garante que a imagem seja sempre gerada com sucesso e salva em output_path.
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Enriquece o prompt com base no estilo visual cinematográfico selecionado
    if style == "stylized":
        styled_prompt = f"3D animation render, Pixar style, Disney character concept, vibrant lighting, smooth textures, expressive character, 8k: {prompt}"
    else:
        styled_prompt = f"35mm film still, cinematic photography, hyper-realistic, volumetric lighting, photorealistic skin texture, 8k, award-winning cinematography: {prompt}"

    env = load_env()
    fal_key = env.get("FAL_KEY", "")
    gemini_key = env.get("GEMINI_API_KEY") or env.get("GOOGLE_API_KEY", "")
    
    # 1. Tentativa via fal.ai (Black Forest Labs FLUX.3 / FLUX dev)
    if fal_key:
        try:
            import fal_client
            print(f"[IMAGE-AI] Solicitando geração via fal.ai FLUX...")
            ok, msg = fal_client.generate_flux_image(styled_prompt, output_path, aspect_ratio=aspect_ratio)
            if ok:
                print(f"[IMAGE-AI] Imagem gerada com sucesso via fal.ai FLUX: {output_path.name}")
                return True
        except Exception as e:
            print(f"[IMAGE-AI] Aviso fal.ai ({e}). Tentando provedores alternativos...")

    # 2. Tentativa via Google Imagen 3 (se a chave do Google AI Studio estiver disponível)
    if gemini_key:
        try:
            print(f"[IMAGEN] Solicitando geração de imagem ao Google AI Studio (Imagen 3)...")
            imagen_url = f"https://generativelanguage.googleapis.com/v1beta/models/imagen-3.0-generate-002:predict?key={gemini_key}"
            payload = {
                "instances": [{"prompt": styled_prompt}],
                "parameters": {
                    "sampleCount": 1,
                    "aspectRatio": "16:9",
                    "outputMimeType": "image/jpeg"
                }
            }
            req_data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                imagen_url, 
                data=req_data, 
                headers={"Content-Type": "application/json"}, 
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=35) as resp:
                resp_json = json.loads(resp.read().decode("utf-8"))
                preds = resp_json.get("predictions", [])
                if preds and "bytesBase64Encoded" in preds[0]:
                    import base64
                    img_bytes = base64.b64decode(preds[0]["bytesBase64Encoded"])
                    with open(output_path, "wb") as f:
                        f.write(img_bytes)
                    print(f"[IMAGEN] Imagem gerada com sucesso via Google Imagen 3: {output_path.name}")
                    return True
        except Exception as e:
            print(f"[IMAGEN] Aviso Imagen 3 ({e}). Comutando para fallback FLUX...")

    # 2. Tentativa via Pollinations
    try:
        import urllib.parse
        import random
        rnd_seed = seed if seed is not None else random.randint(1000, 999999)
        safe_prompt = urllib.parse.quote(prompt[:250])
        poll_url = f"https://image.pollinations.ai/prompt/{safe_prompt}?width=768&height=432&nologo=true&seed={rnd_seed}"
        print(f"[IMAGE-AI] Tentando serviço neural gratuito...")
        req = urllib.request.Request(poll_url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            img_data = resp.read()
            if len(img_data) > 1000:
                with open(output_path, "wb") as f:
                    f.write(img_data)
                print(f"[IMAGE-AI] Imagem gerada com sucesso: {output_path.name}")
                return True
    except Exception as e:
        print(f"[IMAGE-AI] Informação: {e}")

    # 3. Fallback Cinematográfico Local (Storyboard Slate Frame 16:9)
    try:
        from PIL import Image, ImageDraw, ImageFont
        w, h = 1280, 720
        img = Image.new("RGB", (w, h), color=(10, 14, 23))
        draw = ImageDraw.Draw(img)

        # Gradiente e moldura
        border_color = (245, 158, 11) if style == "realistic" else (6, 182, 212)
        draw.rectangle([(20, 20), (w - 20, h - 20)], outline=border_color, width=3)
        draw.rectangle([(28, 28), (w - 28, h - 28)], outline=(30, 40, 60), width=1)

        # Marca d'água / Claquete
        title_text = "TRÍADE STUDIO DIRECTOR — STORYBOARD SLATE"
        badge_text = "ESTILO: 35mm REALISTA" if style == "realistic" else "ESTILO: ANIMAÇÃO 3D"
        draw.text((60, 60), title_text, fill=(245, 158, 11))
        draw.text((60, 95), badge_text, fill=(148, 163, 184))

        # Prompt do plano formatado
        lines = []
        words = prompt.split()
        curr_line = []
        for word in words:
            curr_line.append(word)
            if len(" ".join(curr_line)) > 70:
                lines.append(" ".join(curr_line))
                curr_line = []
        if curr_line:
            lines.append(" ".join(curr_line))

        y_offset = 180
        draw.text((60, 150), "PROMPT CINEMATOGRÁFICO DE VÍDEO / START FRAME:", fill=(6, 182, 212))
        for line in lines[:8]:
            draw.text((60, y_offset), line, fill=(240, 240, 250))
            y_offset += 32

        # Orientação do Google AI Studio
        draw.line([(60, h - 120), (w - 60, h - 120)], fill=(40, 50, 75), width=2)
        info = "Para renderização fotorrealista com Google Imagen 3, configure sua GEMINI_API_KEY no arquivo .env"
        draw.text((60, h - 90), info, fill=(100, 116, 139))
        draw.text((60, h - 60), "Obtenha sua chave gratuita em: https://aistudio.google.com", fill=(245, 158, 11))

        img.save(output_path, "JPEG", quality=90)
        print(f"[IMAGE-AI] Storyboard Slate gerado localmente em: {output_path.name}")
        return True
    except Exception as ex:
        print(f"[IMAGE-AI] Erro ao gerar slate local: {ex}")

    return False

if __name__ == "__main__":
    # Teste rápido de conectividade
    client = LLMClient()
    print(f"Testando conexão com {client.provider}...")
    try:
        reply = client.chat_completion([
            {"role": "system", "content": "Responda apenas em formato JSON com uma chave 'status'."},
            {"role": "user", "content": "Diga 'online'"}
        ], json_mode=True)
        print("Resposta bruta:", reply)
        data = extract_json_from_text(reply)
        print("JSON parseado com sucesso:", data)
    except Exception as err:
        print("Erro no teste:", err)
