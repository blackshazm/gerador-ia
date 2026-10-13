# Especificação Técnica do Compilador de Prompts (Prompt Compiler)
## Pipeline da Tríade — Camada Multi-Engine (Veo 3.1 & Kling AI)

**Versão:** 1.0.0  
**Status:** Aprovado para Implementação  
**Escopo:** Mapeamento determinístico de parâmetros cinematográficos para Google Flow (Veo 3.1) e Kling AI (1.5 / 2.0).

---

## 1. Visão Geral da Arquitetura

O **Compilador de Prompts (Prompt Compiler)** é a camada de software responsável por traduzir as decisões de direção cinematográfica (geradas pela Tríade: CineGen + smixs + DirectorSKILL) em payloads executáveis pelos motores de difusão de vídeo.

```
┌────────────────────────────────────────────────────────┐
│             Entrada Unificada (ShotCard + Ext)         │
│  • smixs: Fatos físicos, fórmula da cena, rastro ocular│
│  • DirectorSKILL: Lente, eixo 180°, blocking, câmera   │
│  • CineGen: IDs de atores (@tags) e painéis P1–P7      │
└───────────────────────────┬────────────────────────────┘
                            │
              ┌─────────────▼─────────────┐
              │      PROMPT COMPILER      │
              │  Validação & Normalização │
              └──────┬─────────────┬──────┘
                     │             │
        ┌────────────┘             └────────────┐
        ▼                                       ▼
┌─────────────────────────┐   ┌─────────────────────────────────┐
│     ADAPTER GOOGLE      │   │          ADAPTER KLING          │
│       (Veo 3.1)         │   │         (Kling AI 1.5/2.0)      │
│ • Prosa estruturada     │   │ • Image-to-Video (Start Frame)  │
│ • Câmera no topo        │   │ • Sliders numéricos (-10 a +10) │
│ • Tags de áudio e fala  │   │ • Payload JSON estrito          │
│ • Reference Ingredients │   │ • Parâmetro de Criatividade     │
└─────────────────────────┘   └─────────────────────────────────┘
```

---

## 2. Contrato de Entrada Unificado (`UnifiedShotSpec`)

Todo plano gerado pelo DirectorSKILL é entregue ao compilador neste formato canônico:

```json
{
  "project_id": "PRJ-CINEMA-001",
  "scene_id": "SC-03",
  "shot_id": "SC-03_SH02",
  "sequence_index": 2,
  "characters": [
    {
      "tag": "@antonio",
      "panel_front": "Visual_Bible/Antonio/P1_front.png",
      "panel_active": "Visual_Bible/Antonio/P2_3q_left.png",
      "screen_position": "screen_left",
      "physical_action": "Mão congelada no ferrolho, mandíbula travada, olhar sobe em diagonal para a janela."
    }
  ],
  "environment": {
    "location": "Rua úmida e escura diante de portão de ferro enferrujado",
    "practical_lights": "Janela iluminada ao fundo com luz âmbar 2800K",
    "key_light": "Luz fria lateral da rua 5600K",
    "contrast_ratio": "5:1"
  },
  "camera": {
    "lens_mm": 50,
    "f_stop": "f/2.2",
    "angle": "eye-level",
    "shot_type": "medium-close-up",
    "movement_type": "push-in",
    "speed_mps": 0.25,
    "axis_side": "Side_A",
    "rule_180_verified": true
  },
  "sound": {
    "ambient": "Chuva fina e vento suave",
    "sfx": "Cliquet metálico do ferrolho",
    "dialogue": null
  },
  "duration_s": 5.0,
  "chaining": {
    "is_chained": true,
    "parent_shot_id": "SC-03_SH01",
    "use_parent_last_frame": true
  }
}
```

---

## 3. Especificação do Adaptador: Google Flow (Veo 3.1)

### 3.1 Diretrizes de Engenharia de Prompt (Veo)
1. **Abertura obrigatória com Câmera e Lente:** O Veo respeita a geometria espacial quando a instrução de câmera abre o prompt.
2. **Linguagem Físico-Comportamental:** Sem adjetivos subjetivos; apenas ações corporais e iluminação.
3. **Tags Explícitas de Áudio:** Sintaxe `Audio:` e `SFX:`.
4. **Ancoragem de Primeiro Frame:** Declaração explícita `Maintain the subject and lighting from the first frame.`

### 3.2 Template Gerado (Prosa Estruturada)

```text
Maintain the subject and lighting from the first frame. Eye-level medium close-up, 50mm lens at f/2.2, slow push-in at 0.25 m/s. Antonio is positioned screen-left facing right. His hand freezes on the iron door latch, jaw clenching, eyes lifting diagonally toward the lit second-story window behind him. Cold 5600K street light on the side of his face, warm 2800K amber rim light from the window. Damp asphalt, fine misty rain.

Audio: fine rain on pavement.
SFX: metallic click of the iron latch, quiet breath.
Duration: 5 seconds.
References: @antonio (Visual_Bible/Antonio/P1_front.png).
```

### 3.3 Payload JSON para API Veo

```json
{
  "engine": "veo_3.1",
  "aspect_ratio": "16:9",
  "duration_seconds": 6,
  "prompt": "Maintain the subject and lighting from the first frame. Eye-level medium close-up, 50mm lens at f/2.2, slow push-in at 0.25 m/s. Antonio positioned screen-left. Hand freezes on iron latch, jaw clenching, eyes lifting diagonally toward lit window. Cold 5600K side light, warm 2800K amber rim. Fine mist.",
  "negative_prompt": "cartoon, distorted faces, fast camera shaking, bright daylight, oversaturated, CGI artifact, extra fingers, text watermark",
  "input_image": "renders/SC-03/SC-03_SH01_last_frame.png",
  "reference_ingredients": [
    {
      "type": "character",
      "path": "Visual_Bible/Antonio/P1_front.png"
    }
  ]
}
```

---

## 4. Especificação do Adaptador: Kling AI (1.5 / 2.0)

### 4.1 Mapeamento Numérico de Controles de Câmera (Sliders)
Diferente do Veo, o Kling AI possui controles de câmera explícitos com sliders numéricos variando entre `-10.0` e `+10.0`. O compilador executa a seguinte conversão:

| Movimento DirectorSKILL | Kling Parameter | Fórmula de Conversão | Exemplo (0.25 m/s) |
|---|---|---|---|
| **Push-in / Zoom-in** | `zoom` | `+ (speed_mps * 10)` | `+2.5` |
| **Pull-out / Zoom-out** | `zoom` | `- (speed_mps * 10)` | `-2.5` |
| **Pan Esquerda** | `pan` | `- (ang_speed * 5)` | `-3.0` |
| **Pan Direita** | `pan` | `+ (ang_speed * 5)` | `+3.0` |
| **Tilt Cima** | `tilt` | `+ (ang_speed * 5)` | `+2.0` |
| **Tilt Baixo** | `tilt` | `- (ang_speed * 5)` | `-2.0` |
| **Tracking Lateral Esq.** | `horizontal` | `- (speed_mps * 8)` | `-2.0` |
| **Tracking Lateral Dir.** | `horizontal` | `+ (speed_mps * 8)` | `+2.0` |
| **Guindaste/Pedestal Cima**| `vertical` | `+ (speed_mps * 8)` | `+1.5` |
| **Roll Horário/Anti-hor.** | `roll` | `± (degrees / 10)` | `0.0` (raro/bloqueado) |

### 4.2 Estratégia de Injeção de Identidade no Kling
No Kling AI, o modo **Image-to-Video (I2V)** é o padrão absoluto da Tríade:
- Se for o **primeiro plano da cena**, utiliza-se o painel **P1_front** ou **P2_3q** da Bíblia Visual do personagem.
- Se for um **plano contínuo encadeado**, utiliza-se o **último frame do plano anterior** (`last_frame.png`), garantindo taxa de coerência de 98%.

### 4.3 Payload JSON Oficial (Kling AI)

```json
{
  "target_engine": "kling_v2",
  "mode": "professional",
  "duration_s": 5,
  "aspect_ratio": "16:9",
  "start_frame_path": "renders/SC-03/SC-03_SH01_last_frame.png",
  "end_frame_path": null,
  "prompt": "Cinematic 50mm portrait shot. Antonio frozen with hand on rusty iron latch, jaw clenching, eyes moving up toward second-story window. Cold 5600K side light, warm 2800K rim light from window. Rainy atmosphere, wet asphalt, 24fps movie look, film grain.",
  "negative_prompt": "cartoon, 3d render, smiling, bright daylight, bad anatomy, deformed hands, face mutation, extra limbs, low resolution, motion blur artifact",
  "camera_controls": {
    "type": "custom",
    "horizontal": 0.0,
    "vertical": 0.0,
    "zoom": 2.5,
    "tilt": 0.0,
    "pan": 0.0,
    "roll": 0.0
  },
  "creativity_relevance_ratio": 0.85
}
```

---

## 5. Algoritmo de Encadeamento para Vídeos Longos (Long Video Chaining)

Para transformar micro-clipes (5s a 10s) em cenas longas contínuas sem saltos de pose ou face-drift:

```
[Shot 01 (5s)]
   │
   ├─► Render Kling/Veo ──► `SC-03_SH01.mp4`
   │
   └─► Extração automática:
       `ffmpeg -sseof -0.04 -i SC-03_SH01.mp4 -update 1 SC-03_SH01_last.png`
         │
         ▼
[Shot 02 (5s)]
   │
   ├─► Start Frame: `SC-03_SH01_last.png`
   ├─► Novo prompt físico de continuação
   └─► Render Kling/Veo ──► `SC-03_SH02.mp4`
         │
         ▼
[Linha do Tempo CapCut Desktop / Premiere]
   └─► Clipes alinhados em ordem sequencial com corte seco (cut on action)
```

---

## 6. Validação e Matriz de Erros do Compilador

| Código | Condição | Ação de Bloqueio |
|---|---|---|
| `COMP_ERR_01` | Termo subjetivo detectado no prompt (ex: "nervoso", "triste") | Rejeita payload; devolve ao módulo smixs com linha destacada |
| `COMP_ERR_02` | Eixo 180° violado entre planos contínuos sem corte de transição | Bloqueia compilação; exige plano neutro ou justificativa |
| `COMP_ERR_03` | Start Frame inexistente no modo encadeado | Pausa pipeline até extração do último frame do clipe anterior |
| `COMP_ERR_04` | Slider numérico fora da faixa [-10, +10] no Kling | Clampa valor automaticamente para o limite máximo e registra log |
