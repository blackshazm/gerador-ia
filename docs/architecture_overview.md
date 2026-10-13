# Arquitetura do Sistema — Pipeline Cinematográfico "A Tríade"
## Visão Técnica Ponta a Ponta (Do PDF Bruto à Montagem Final)

**Versão:** 1.0.0  
**Classificação:** Engenharia de Produção & Arquitetura de Software  
**Status:** Baseline para Desenvolvimento

---

## 1. Visão Geral e Princípio de Funcionamento

O objetivo do sistema é converter um livro físico/digital em formato PDF em um filme fotorrealista completo, subdividido em micro-beats cinematográficos estáveis (3 a 6 segundos), sincronizados com locução e montados automaticamente no **CapCut Desktop** ou NLE similar.

### Princípio das Camadas Especializadas
> *O Ingestor limpa e traduz; o CineGen tranca o quem e onde; o smixs elimina o abstrato; o DirectorSKILL define a física da câmera; o Motor de Áudio dita o tempo de corte; o Motor de Vídeo (Kling/Veo) executa a difusão; e o Assembler une tudo na timeline.*

```
┌────────────────────────────────────────────────────────────────────────┐
│                        ESTÁGIO 0: INGESTÃO PDF                         │
│  PDF (EN ou PT) ─► Parser/Cleaner ─► Tradução ─► livro_limpo.md       │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                        ESTÁGIO 1: CASTING & BÍBLIA                     │
│  Identificação @Tags ─► Casting Inicial ─► 7 Painéis LOCKED por Ator   │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                        ESTÁGIO 2: DECUPAGEM EM MICRO-BEATS             │
│  smixs: Fórmula da Cena + 14 campos físicos (Sem adjetivos subjetivos) │
│  DirectorSKILL: Eixo 180° + Lente (mm) + Movimento + Encadeamento      │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                        ESTÁGIO 3: ÁUDIO-FIRST PACING                   │
│  Geração TTS (Edge-TTS / ElevenLabs) ─► Duração Exata do Shot (s)      │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                        ESTÁGIO 4: COMPILAÇÃO MULTI-MOTOR               │
│  Adaptador Kling AI (Sliders -10..+10, I2V) ou Veo 3.1 (Prosa Estrita) │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                        ESTÁGIO 5: RENDER & CHAINING                    │
│  Render Shot N ─► Extração Last Frame ─► Start Frame do Shot N+1       │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                        ESTÁGIO 6: MONTAGEM AUTOMATIZADA                │
│  Geração do draft_content.json do CapCut (Vídeo + Áudio + Legendas)    │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Portões de Qualidade (Quality Gates) Entre Estágios

Cada etapa só transmite dados para a etapa seguinte se passar por validação estrita (sem bypass):

| Portão | De ➔ Para | Condição Obrigatória de Aprovação | Se Reprovado |
|---|---|---|---|
| **Gate 0** | PDF ➔ Markdown | 100% dos cabeçalhos/rodapés e números de página removidos; nomes de entidades identificados. | Reexecuta regex de higienização. |
| **Gate 1** | Casting ➔ Bíblia | 7 painéis gerados com consistência facial (P1 a P7) e hash trancado (`LOCKED`). | Regenera painéis defeituosos. |
| **Gate 2** | Texto ➔ Micro-Beats | Zero termos da lista negra lexical smixs; 14 campos da cartela preenchidos; Eixo 180° checado. | Linter devolve ao LLM com linha destacada. |
| **Gate 3** | Roteiro ➔ Áudio | Áudio gerado sem cortes de dicção; duração medida em milissegundos. | Regenera áudio do micro-beat. |
| **Gate 4** | Prompt ➔ Motor | Payload compilado para schema específico do motor (Kling ou Veo) com Start Frame anexado. | Bloqueio pré-envio no compilador. |
| **Gate 5** | Render ➔ Timeline | Similaridade facial ≥ 92%; ausência de artefatos de IA; last frame extraído com sucesso. | Dispara re-render com variação de seed. |

---

## 3. Topologia de Pastas do Sistema

Todo projeto segue uma estrutura de árvore determinística para garantir isolamento e permitir automação de scripts:

```text
/PROJETO_LIVRO/
├── config/
│   ├── project_settings.json       # Configuração do motor (kling/veo), resolução, voz
│   └── forbidden_lexicon.json      # Dicionário smixs de termos banidos
│
├── 00_raw_input/
│   └── livro_original.pdf          # PDF de entrada
│
├── 01_normalized_text/
│   ├── livro_completo.md           # Markdown limpo higienizado
│   └── capitulos/
│       ├── cap_01.md
│       └── cap_02.md
│
├── 02_visual_bible/                # Imagens de referência trancadas (LOCKED)
│   ├── characters/
│   │   ├── @antonio/
│   │   │   ├── P1_front.png
│   │   │   ├── P2_3q_left.png
│   │   │   └── ... P7_macro.png
│   │   └── @helena/
│   └── environments/
│       └── @rua_noite/
│
├── 03_scenes/                      # Cenas dramáticas identificadas
│   ├── SC_01.json
│   └── SC_02.json
│
├── 04_shots/                       # Micro-beats decupados e Ficha Pronta de Copiar e Colar
│   ├── CADERNO_EXECUCAO_SC01.md    # Ficha Mastigada (Ctrl+C / Ctrl+V para sites web)
│   ├── SC01_SH01.json
│   ├── SC01_SH02.json
│   └── SC01_SH03.json
│
├── 05_audio/                       # Locuções e SFX gerados
│   ├── SC01_SH01_voice.mp3
│   ├── SC01_SH02_voice.mp3
│   └── sfx/
│
├── 06_renders/                     # Clipes e frames extraídos
│   ├── SC01_SH01.mp4
│   ├── SC01_SH01_last.png
│   ├── SC01_SH02.mp4
│   └── SC01_SH02_last.png
│
└── 07_timeline_export/             # Projeto gerado para edição
    ├── capcut_project/
    │   └── draft_content.json
    └── timeline.xml (opcional)
```
