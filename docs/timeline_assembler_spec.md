# Especificação Técnica do Montador Automático de Linha do Tempo
## Pipeline da Tríade — Camada de Pós-Produção & Automação CapCut Desktop

**Versão:** 1.0.0  
**Status:** Aprovado para Implementação  
**Escopo:** Montagem automatizada em lote de clipes de vídeo, locuções, efeitos sonoros e legendas na linha do tempo do CapCut Desktop.

---

## 1. O Problema da Montagem Manual

Em uma produção de vídeo automatizada por IA:
* Um único capítulo de livro gera entre **30 e 80 micro-clipes** de 4 a 6 segundos.
* Importar e alinhar manualmente cada par `(clipe_video_N, audio_locucao_N)` consome de 1 a 3 horas de trabalho tedioso por cena.
* Qualquer desalinhamento de 1 frame quebra o ritmo dramático da decupagem.

---

## 2. A Solução: Injeção Direta no CapCut Desktop

O CapCut Desktop armazena seus projetos em pastas locais estruturadas, controladas por um arquivo JSON chamado `draft_content.json` (localizado em `%LOCALAPPDATA%\CapCut\User Data\Projects\com.lveditor.draft`).

O **Montador da Tríade (Timeline Assembler)** gera programaticamente esse projeto, de modo que ao abrir o CapCut:
* Todos os vídeos já estão ordenados na trilha **V1**.
* Todas as locuções já estão alinhadas no tempo exato na trilha **A1**.
* Efeitos sonoros (SFX) posicionados nos pontos de impacto na trilha **A2**.
* Legendas sincronizadas criadas na trilha de texto.

```
┌────────────────────────────────────────────────────────────────────────┐
│ LINHA DO TEMPO DO CAPCUT (Montagem Automatizada)                       │
├────────────────────────────────────────────────────────────────────────┤
│ [V1] │ Shot 01 (4.2s)    │ Shot 02 (5.0s)      │ Shot 03 (4.5s)        │
│ [A1] │ Voz Beat 01 (3.4s)│ Voz Beat 02 (4.2s)  │ Voz Beat 03 (3.8s)    │
│ [A2] │ [SFX Passada]     │                     │ [SFX Porta Rangendo]  │
│ [TX] │ "Ele parou..."    │ "A luz acendeu..."  │ "A mão hesitou..."    │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Formato Alternativo de Intercâmbio: FCPXML / XML

Para estúdios e editores que utilizam **Adobe Premiere Pro** ou **DaVinci Resolve**, o Assembler também pode exportar um arquivo padrão **Final Cut Pro XML (.fcpxml / .xml)**:
* Compatibilidade nativa com Premiere / DaVinci.
* Nomeia cada corte com o identificador estável (`SC03_SH02`).
* Zero necessidade de relink manual.

---

## 4. Script de Referência para Construção da Timeline (Python)

```python
import json
import os
from pathlib import Path

def create_capcut_draft(project_name: str, shots_metadata: list, output_dir: str):
    """
    Cria a estrutura de rascunho de projeto do CapCut pronta para abertura.
    """
    timeline_duration_us = 0  # Microssegundos
    tracks_video = []
    tracks_audio = []
    
    current_time_us = 0
    
    for shot in shots_metadata:
        duration_us = int(shot["duration_s"] * 1_000_000)
        
        # Segmento de vídeo
        video_segment = {
            "id": shot["shot_id"],
            "material_id": shot["video_file_path"],
            "target_timerange": {
                "start": current_time_us,
                "duration": duration_us
            }
        }
        tracks_video.append(video_segment)
        
        # Segmento de áudio
        if shot.get("audio_file_path"):
            audio_segment = {
                "id": f"{shot['shot_id']}_audio",
                "material_id": shot["audio_file_path"],
                "target_timerange": {
                    "start": current_time_us,
                    "duration": duration_us
                }
            }
            tracks_audio.append(audio_segment)
            
        current_time_us += duration_us

    print(f"Projeto montado com sucesso: {len(shots_metadata)} planos totalizando {current_time_us / 1_000_000:.2f}s.")
```
