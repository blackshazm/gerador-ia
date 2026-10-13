# Especificação Técnica do Módulo de Áudio e Ritmo Cinematográfico
## Pipeline da Tríade — Camada Audio-First Shot Pacing & Sound Design

**Versão:** 1.0.0  
**Status:** Aprovado para Implementação  
**Escopo:** Síntese de voz neural (TTS), medição determinística de duração de cortes visuais e desenho de som (SFX).

---

## 1. O Princípio "Audio-First" (O Áudio Dita o Corte)

No cinema clássico e na produção automatizada para YouTube/Dark Channels, **a imagem serve ao ritmo do som**.

> **Regra Fundamental de Pacing:** É impossível acertar a duração de um plano de vídeo sem saber com exatidão quantos segundos a locução ou o efeito sonoro vai durar. Gerar o vídeo antes do áudio gera cortes truncados, acelerações artificiais e perda de impacto dramático.

---

## 2. A Fórmula de Duração do Plano Cinematográfico

Para cada micro-beat da decupagem, o motor de áudio gera a locução e afere o tempo em milissegundos ($T_{audio}$). A duração do plano de vídeo ($T_{shot}$) é calculada deterministicamente:

$$T_{shot} = \text{clamp}(T_{audio} + T_{pad}, \ T_{min}, \ T_{max})$$

Onde:
* $T_{pad}$ = Margem de respiro/reação física do ator (**0.6s a 1.0s** após a fala).
* $T_{min}$ = Duração mínima permitida pelo motor de difusão (ex: **3.0 segundos**).
* $T_{max}$ = Duração máxima do clipe antes de exigir encadeamento (*split*) (ex: **5.0s a 8.0s** no Kling/Veo).

Se uma narração tiver 7.5 segundos, o DirectorSKILL fatia o beat em dois planos encadeados:
1. **Shot A (4.0s):** Plano médio do herói falando/ouvindo.
2. **Shot B (4.5s):** Close-up ou insert da reação corporal, encadeado via *Last Frame*.

---

## 3. Seleção de Motores de Síntese Vocal (TTS)

O pipeline suporta dois provedores:

### 3.1 Provedor A: Edge-TTS (Gratuito, Sem API Key, Qualidade Neural)
* **Biblioteca:** `edge-tts` (Python).
* **Vozes Recomendadas (PT-BR):**
  * `pt-BR-AntonioNeural` (Voz masculina madura, ideal para narrativa/suspense/cinema).
  * `pt-BR-FranciscaNeural` (Voz feminina sóbria e dramática).
* **Vozes Recomendadas (EN):**
  * `en-US-ChristopherNeural` ou `en-US-GuyNeural`.

### 3.2 Provedor B: ElevenLabs (Qualidade Ultra-Realista / Voice Cloning)
* **Modo:** API paga com ID de voz personalizado para projetos com orçamento dedicado.

---

## 4. Estrutura do Sound Design (Camada SFX e Ambience)

Cada shot card possui especificações para três trilhas de áudio:
1. **Voice Track (Voz/Locução):** Gerada pelo TTS e sincronizada no início do beat.
2. **SFX Track (Efeitos Sonoros Físicos):** Cliquet do ferrolho, vidro quebrando, passada na poça d'água.
3. **Ambience Track (Cama de Som):** Chuva fina constante, vento em janela, ruído ambiente da locação.

---

## 5. Exemplo de Script de Execução (Edge-TTS)

```python
import asyncio
import edge_tts
import mutagen.mp3

async def generate_beat_audio(text: str, voice: str, output_mp3: str) -> float:
    """
    Gera o áudio do beat e retorna a duração exata em segundos.
    """
    communicate = edge_tts.Communicate(text, voice, rate="-5%", pitch="-2Hz")
    await communicate.save(output_mp3)
    
    # Mede a duração exata do arquivo gerado
    audio = mutagen.mp3.MP3(output_mp3)
    duration_seconds = audio.info.length
    
    # Calcula duração de vídeo com respiro de 0.8s
    video_duration = round(duration_seconds + 0.8, 2)
    print(f"Áudio gerado: {output_mp3} | Duração: {duration_seconds:.2f}s | Vídeo planejado: {video_duration:.2f}s")
    return video_duration
```
