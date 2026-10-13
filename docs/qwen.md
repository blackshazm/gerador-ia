# Documento de Requisitos do Produto (PRD)

## Pipeline de Pré-Produção e Geração de Vídeo Automatizado — "A Tríade"

| Campo | Detalhe |
|---|---|
| **Versão** | 1.1.0 (Multi-Engine: Veo + Kling AI) |
| **Classificação** | Confidencial / Engenharia de Produção |
| **Autor** | Gerência de Produto — Divisão de IA Cinematográfica |
| **Stakeholders** | Direção de Fotografia, Engenharia de Prompt, Pós-Produção, QA Visual |
| **Status** | Especificação Técnica Aprovada para Multi-Engine |
| **Data de Emissão** | Outubro 2026 |

---

## 1. Resumo Executivo e Visão do Produto

### 1.1 O Problema

A geração de vídeo por modelos de difusão (Veo, Sora, Runway, Kling) sofreu, até o presente ciclo de desenvolvimento, de três falhas sistêmicas que impedem sua adoção em produção cinematográfica seriada:

| # | Falha | Sintoma Observável |
|---|---|---|
| F-01 | **Face-Drift / Identity Collapse** | O rosto do personagem muda entre cortes consecutivos, quebrando a suspensão de descrença. |
| F-02 | **Alucinação Semântica** | O modelo interpreta adjetivos subjetivos ("melancólico", "tenso") com resultados visuais inconsistentes e não-dirigíveis. |
| F-03 | **Colapso Geométrico-Espacial** | A regra dos 180°, a continuidade de eixo e o rastro ocular (eye-trace) são ignorados, gerando desorientação espacial no espectador. |

Nenhuma ferramenta isolada resolve as três falhas simultaneamente. O mercado opera com prompts ad-hoc, sem pipeline determinístico.

### 1.2 A Solução — "A Tríade"

**A Tríade** é um pipeline integrado, sequencial e determinístico que transforma um texto literário bruto (Markdown) em pacotes de prompts técnicos renderizáveis por motores de difusão cinematográfica — com suporte primário ao **Google Flow (Veo)** e à **Kling AI** (modelo de difusão de vídeo chinês de alta fidelidade e custo acessível via nuvem), garantindo consistência facial, obediência à física óptica e continuidade espacial.

A arquitetura é composta por três módulos de especialização complementar:

- **CineGen** → Resolve F-01 (consistência de identidade visual e geração de 7 painéis).
- **smixs / visual-skills** → Resolve F-02 (eliminação de ambiguidade semântica e cartela de 14 campos).
- **DirectorSKILL** → Resolve F-03 (geometria, óptica, regra dos 180° e compilação de prompt multi-motor).

### 1.3 Visão do Produto

> *"Traduzir a intenção literária de um autor em fotogramas fisicamente corretos, sem intervenção manual de direção, com taxa de aprovação de primeiro render ≥ 85% tanto em ecossistemas Google Flow (Veo) quanto em Kling AI."*

### 1.4 Não-Escopo (Out of Scope — v1.1)

- Geração de áudio / trilha sonora final (apenas diretrizes de sound design e falas sincronizadas no prompt).
- Pós-processamento de cor (color grading) automatizado avançado.
- Suporte a formatos de entrada que não sejam Markdown (.md) puro.
- Renderização em tempo real / streaming.
- Modelos sem suporte a imagem de referência ou controle de câmera.

---

## 2. Arquitetura do Sistema

### 2.1 Diagrama Lógico de Fluxo (Data Flow)

```
┌─────────────────────────────────────────────────────────────────────┐
│                        ENTRADA ÚNICA                                │
│              Livro Literário (.md) — Texto Bruto                    │
└──────────────────────────┬──────────────────────────────────────────┘
                           │  Ingestão
                           ▼
┌──────────────────────────────────────────────────────────────────────┐
│  MÓDULO 1 — CineGen (Local / On-Premise)                            │
│  ┌────────────────────────────────────────────────────────────────┐  │
│  │ • Parser Markdown → Segmentação por cena/capítulo              │  │
│  │ • Extração de @Tags: @PERSONAGEM, @CENÁRIO, @OBJETO           │  │
│  │ • Construção da BÍBLIA VISUAL                                  │  │
│  │   → 7 painéis de referência por personagem                    │  │
│  │   → (Frente, ¾ Esq., Perfil Esq., Costas, ¾ Dir.,            │  │
│  │      Perfil Dir., Detalhe/Macro)                               │  │
│  │ • Geração de seed facial + embedding de identidade             │  │
│  │ • Output: Visual_Bible.json + character_embeddings/            │  │
│  └────────────────────────────────────────────────────────────────┘  │
└──────────────────────────┬───────────────────────────────────────────┘
                           │  Cena bruta + referências visuais
                           ▼
┌──────────────────────────────────────────────────────────────────────┐
│  MÓDULO 2 — smixs / visual-skills (Filtro Semântico)               │
│  ┌────────────────────────────────────────────────────────────────┐  │
│  │ • Regra de Entrada: PROIBIÇÃO de adjetivos subjetivos          │  │
│  │   ✗ "Ele está triste"                                         │  │
│  │   ✓ "Luz fria 5600K lateral, mandíbula travada,               │  │
│  │      pálpebras a 70% de abertura, respiração torácica curta"  │  │
│  │ • Aplicação da FÓRMULA DA CENA:                                │  │
│  │   Desejo + Obstáculo + Geometria + Rastro Ocular + Ritmo      │  │
│  │ • Preenchimento da CARTELA RESTRITIVA (14 campos)              │  │
│  │ • Output: Scene_Card.json (validado, sem ambiguidade)          │  │
│  └────────────────────────────────────────────────────────────────┘  │
└──────────────────────────┬───────────────────────────────────────────┘
                           │  Cartela de 14 campos preenchida
                           ▼
┌──────────────────────────────────────────────────────────────────────┐
│  MÓDULO 3 — DirectorSKILL (Claude / LLM — Cérebro Matemático)      │
│  ┌────────────────────────────────────────────────────────────────┐  │
│  │ • Seleção de Lente Física (24mm / 35mm / 50mm / 85mm / 135mm)│  │
│  │ • Aplicação da REGRA DOS 180° e eixo de ação                  │  │
│  │ • Motivação de movimento de câmera (dolly, pan, tilt, steadicam)│ │
│  │ • Cálculo de profundidade de campo (f-stop, distância focal)   │  │
│  │ • Definição de iluminação (key, fill, back, temperatura Kelvin)│  │
│  │ • Formatação do PACOTE DE PROMPT ESTRITO (Veo ou Kling AI)     │  │
│  │ • Output: Render_Prompt.json + Camera_Setup.json               │  │
│  └────────────────────────────────────────────────────────────────┘  │
└──────────────────────────┬───────────────────────────────────────────┘
                           │  Prompt técnico + embeddings faciais / referências
                           ▼
┌──────────────────────────────────────────────────────────────────────┐
│  MÓDULO 4 — Motores de Difusão Multi-Engine (Veo 3.1 / Kling AI)     │
│  ┌────────────────────────────────────────────────────────────────┐  │
│  │ • Provedor A: Google Flow (Veo 3.1)                            │  │
│  │   - Referências: Injeção de P1/P3 + Prompt Prosa/JSON          │  │
│  │ • Provedor B: Kling AI (1.5 / 2.0 - Nuvem / Acessível)         │  │
│  │   - Referências: Start Frame (P1-P7) + Controle Numérico Câmera│  │
│  │   - Modo: Standard ou Professional (1080p nativo)              │  │
│  │ • Encadeamento de Planos: Last Frame → First Frame (Long Video)│  │
│  │ • Output: .mp4 (H.264/H.265) por plano numerado                │  │
│  └────────────────────────────────────────────────────────────────┘  │
└──────────────────────────┬───────────────────────────────────────────┘
                           │  Arquivos de vídeo renderizados
                           ▼
┌──────────────────────────────────────────────────────────────────────┐
│  MÓDULO 5 — Ilha de Edição (Premiere Pro / DaVinci / CapCut Desktop)│
│  ┌────────────────────────────────────────────────────────────────┐  │
│  │ • Montagem sequencial conforme decupagem                       │  │
│  │ • Sincronia de áudio/voz e transições de continuidade          │  │
│  │ • Exportação final em lote (Batch Assembly)                    │  │
│  └────────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────────┘
```

### 2.2 Contrato de Dados entre Módulos (Interface Contracts)

| Interface | Formato | Schema Principal | Validação |
|---|---|---|---|
| CineGen → smixs | JSON | `{scene_id, characters[], locations[], objects[], narrative_block}` | JSON Schema v7 |
| smixs → DirectorSKILL | JSON | `{scene_id, formula{}, cartela_14{}, forbidden_terms_flag: false}` | Cartela 14/14 preenchida, zero subjetividade |
| DirectorSKILL → Render Engine | JSON | `{target_engine: "veo"\|"kling", prompt_payload{}, camera_params{}, reference_images[], seed}` | Prompt conforme schema do motor de destino |
| Render Engine → Editor | Arquivo | `.mp4 (H.264 / H.265) / .mov (ProRes)` | Resolução, fps e duração conformes com decupagem |

### 2.3 Modelo de Execução e Infraestrutura

| Módulo | Runtime | Dependência | Requisito de Hardware |
|---|---|---|---|
| CineGen | Local ou Nuvem (ComfyUI/API) | Flux / SDXL / InstantID para painéis de referência | GPU local ≥ 16GB VRAM ou API remota |
| smixs / visual-skills | API / Local | Claude 3.5 Sonnet / GPT-4o com system prompt de linter | Acesso a API |
| DirectorSKILL | API Claude | Contexto: Scene_Card.json + regras de câmera | Acesso a API |
| **Google Flow (Veo)** | Cloud (Google) | API Veo 3.1 / Web Flow | Navegador / API Key Google |
| **Kling AI** | Cloud (Kuaishou) | Kling AI Web / API (v1.5 / v2.0) | Navegador / Token API (zero GPU local) |
| Editor | Desktop | CapCut Desktop / Adobe Premiere Pro | Computador comum / Estação de edição |

### 2.4 Matriz Técnica Comparativa: Google Flow (Veo 3.1) vs. Kling AI

| Parâmetro Técnico | Google Flow (Veo 3.1) | Kling AI (1.5 / 2.0) | Impacto no Pipeline Tríade |
|---|---|---|---|
| **Duração por Clipes** | 4s, 6s ou 8s | 5s ou 10s (extensível via *Extend*) | O DirectorSKILL divide os planos respeitando os múltiplos do motor escolhido. |
| **Resoluções Nativas** | 1080p / 4K | 720p (Std) e 1080p (Pro) | 1080p é o padrão de entrega para ambos. |
| **Método de Entrada** | Text-to-Video & Image-to-Video | Text-to-Video & Image-to-Video (Start & End Frame) | Kling permite trancar o primeiro e o último frame, ideal para encadeamento. |
| **Controle de Câmera** | Descritivo no prompt (prosa/ordem estrita) | Parâmetros numéricos dedicados (Horizontal, Vertical, Zoom, Roll, Pan, Tilt) | Kling aceita inputs de slider (-10 a +10), facilitando cálculo matemático determinístico. |
| **Injeção de Identidade** | Reference Ingredients / Painéis anexados | Imagem de referência primária (P1) + Prompt de apoio | No Kling, o P1 da Bíblia Visual alimenta o Start Frame obrigatoriamente. |
| **Custo e Acessibilidade** | Créditos corporativos Google / Whitelist | Nível gratuito / Créditos diários e planos acessíveis na nuvem | Kling viabiliza produção sem barreira de hardware ou aprovação de acesso enterprise. |
| **Sincronia Labial / Fala** | Máx. 8s com tags `Says:` | Integrado via Lip-Sync nativo ou áudio separado | Áudio final pós-sincronizado no CapCut. |

---

## 3. Fluxo de Trabalho de Produção — Passo a Passo

### Passo 1: Ingestão e Trancamento Visual (CineGen)

**Objetivo:** Converter texto literário em entidades visuais fixas e invariáveis.

#### 3.1.1 — Ingestão do Markdown

- O operador importa o arquivo `.md` completo (livro, capítulo ou sequência).
- O parser CineGen segmenta o texto por:
  - `## Capítulo` → agrupamento narrativo macro.
  - `### Cena` ou quebras de linha duplas com mudança de cenário → unidade de plano.
- Cada cena recebe um identificador único: `SC-{capítulo:02d}-{cena:03d}` (ex: `SC-03-017`).

#### 3.1.2 — Extração de @Tags

O sistema reconhece e isola as seguintes marcações no texto:

| Tag | Função | Exemplo |
|---|---|---|
| `@PERSONAGEM[Nome]` | Registra ator recorrente | `@PERSONAGEM[Helena]` |
| `@CENÁRIO[Descrição]` | Registra ambiente | `@CENÁRIO[Cozinha industrial abandonada]` |
| `@OBJETO[Item]` | Registra prop relevante | `@OBJETO[Revólver .38 cromado]` |
| `@TEMPORAL[Momento]` | Registra período/luz | `@TEMPORAL[Amanhecer, inverno]` |

#### 3.1.3 — Construção da Bíblia Visual (Visual Bible)

Para **cada** `@PERSONAGEM` extraído, o CineGen gera automaticamente **7 painéis de referência**:

| Painel | Ângulo | Uso no Pipeline |
|---|---|---|
| P1 | Frente (0°) | Referência primária de identidade |
| P2 | Três-quartos Esquerda (45°) | Planos médios e OTS |
| P3 | Perfil Esquerda (90°) | Planos laterais |
| P4 | Costas (180°) | Planos de fuga / saída de quadro |
| P5 | Três-quartos Direita (315°) | Contra-planos |
| P6 | Perfil Direito (270°) | Contra-planos laterais |
| P7 | Detalhe / Macro (olhos, mãos, cicatriz) | Close-ups e inserts |

**Especificações de geração:**
- Resolução mínima por painel: 1024 × 1024 px.
- Estilo: fotorrealista, iluminação neutra (flat light 5500K), fundo cinza 18%.
- O rosto é renderizado com **seed fixa** e **embedding de identidade** (IP-Adapter / InstantID) armazenado em `character_embeddings/{Nome}.safetensors`.
- Qualquer prompt futuro que mencione `@PERSONAGEM[Nome]` injeta automaticamente o embedding correspondente no pipeline de difusão.

**Trava Anti-Drift:** O embedding facial é anexado como **condicionante obrigatória** em toda chamada ao Google Flow para aquele personagem. Sem embedding, o prompt é rejeitado pelo validador.

#### 3.1.4 — Output do Passo 1

```json
{
  "visual_bible_version": "1.0",
  "project_id": "PRJ-2025-TRIAD-001",
  "characters": [
    {
      "name": "Helena",
      "tag": "@PERSONAGEM[Helena]",
      "panels": ["P1_front.png", "P2_3q_left.png", "...", "P7_detail.png"],
      "embedding_path": "embeddings/helena_v1.safetensors",
      "seed": 48291736,
      "physical_description": "Mulher, 34 anos, cabelo castanho curto, cicatriz no supercílio esquerdo"
    }
  ],
  "locations": [...],
  "objects": [...]
}
```

---

### Passo 2: Conversão Literária e Cartela de Plano (smixs / visual-skills)

**Objetivo:** Eliminar toda subjetividade textual e converter a narrativa em dados físicos graváveis.

#### 3.2.1 — Regra de Entrada (Gatekeeper Semântico)

O módulo smixs opera como **filtro de roteirização**. Sua diretriz primária é:

> **PROIBIDO:** qualquer adjetivo, advérbio ou construção que descreva estado emocional interno sem correspondência física observável pela câmera.
>
> **OBRIGATÓRIO:** toda descrição deve ser um **fato físico registrável** por um sensor óptico.

**Tabela de Conversão Obrigatória:**

| ✗ Proibido (Subjetivo) | ✓ Obrigatório (Físico/Gravável) |
|---|---|
| "Ele está triste" | "Pálpebras inferiores a 80% de abertura, cantos da boca 2mm abaixo da linha neutra, respiração torácica curta (ciclo 3s)" |
| "Ela corre desesperada" | "Passada de 1,4m, tronco inclinado 12° à frente, braços em ângulo de 90°, tecido do casaco em turbulência" |
| "O ambiente é assustador" | "Luz key única, 3200K, vinda de baixo (ângulo -30°), sombras duras com razão de contraste 8:1, névoa com densidade 40%" |
| "Ele olha com raiva" | "Sobrancelhas convergindo 15°, mandíbula travada (masseter visível), pupila contraída, rastro ocular fixo em ponto X do quadro" |

**Validação:** O smixs executa um parser de **lista negra lexical** (≈ 400 termos proibidos). Se qualquer termo for detectado, a cena é devolvida com erro `ERR_SUBJ_001` e o campo infrator é destacado. A cena só avança com `forbidden_terms_flag: false`.

#### 3.2.2 — Fórmula da Cena

Toda cena deve conter, obrigatoriamente, os cinco vetores:

| Vetor | Definição | Exemplo |
|---|---|---|
| **Desejo** | O que o personagem quer naquele plano (físico, não abstrato) | "Helena quer alcançar a maçaneta da porta" |
| **Obstáculo** | O que impede fisicamente | "A distância de 4 metros e o piso coberto de vidro quebrado" |
| **Geometria** | Posição espacial dos corpos no cenário (coordenadas relativas) | "Helena em quadro-esquerdo, porta em quadro-direito, profundidade 3m" |
| **Rastro Ocular (Eye-Trace)** | Ponto de entrada do olhar do espectador → trajetória → ponto de saída | "Entra pela mão em destaque → sobe pelo braço → ancora no rosto" |
| **Ritmo** | Duração do plano, velocidade de movimento, frequência de corte | "Plano de 6s, câmera em dolly lento (0,3 m/s), corte seco no frame 144" |

#### 3.2.3 — Cartela Restritiva de 14 Campos

Cada cena gera um objeto JSON com **exatamente 14 campos**. Nenhum pode estar nulo.

| # | Campo | Tipo | Exemplo |
|---|---|---|---|
| 1 | `scene_id` | string | `"SC-03-017"` |
| 2 | `location_tag` | string | `"@CENÁRIO[Cozinha industrial abandonada]"` |
| 3 | `characters_present` | array | `["@PERSONAGEM[Helena]", "@PERSONAGEM[Rui]"]` |
| 4 | `time_of_day_light` | string | `"Golden hour, sol a 12° do horizonte, luz lateral direita"` |
| 5 | `desire` | string | "Helena quer alcançar a faca sobre a bancada" |
| 6 | `obstacle` | string | "Rui bloqueia o corredor, corpo a 1,2m da bancada" |
| 7 | `geometry_blocking` | string | "Helena: quadro-esq, Z=4m. Rui: quadro-dir, Z=2,5m. Bancada: centro, Z=1m" |
| 8 | `eye_trace_path` | string | "Entra: mão de Helena (inferior-esq) → trajetória diagonal → ancora: olhos de Rui (superior-dir)" |
| 9 | `rhythm_duration_s` | float | `7.5` |
| 10 | `rhythm_camera_speed` | string | "Dolly-in, 0,2 m/s, aceleração 0" |
| 11 | `physical_emotion_markers` | array | `["mandíbula travada", "respiração 4s/ciclo", "punho fechado"]` |
| 12 | `sound_design_hint` | string | "Silêncio, apenas gotejamento metálico, 2 gotas/s" |
| 13 | `forbidden_terms_flag` | boolean | `false` |
| 14 | `continuity_notes` | string | "Helena usa o mesmo casaco de SC-03-014. Cicatriz visível no perfil esquerdo." |

**Gate de saída:** Se qualquer campo estiver vazio ou `forbidden_terms_flag === true`, o pipeline **trava** e retorna erro ao operador. Não há bypass.

#### 3.2.4 — Output do Passo 2

Arquivo `Scene_Card_SC-03-017.json` validado e assinado digitalmente pelo módulo smixs.

---

### Passo 3: Decupagem e Lógica Direcional (DirectorSKILL)

**Objetivo:** Transformar a cartela validada em instruções fotográficas e ópticas matematicamente precisas.

#### 3.3.1 — Seleção de Lente Física

O DirectorSKILL (rodando via modelo Claude com system prompt de direção de fotografia) seleciona a lente com base em regras determinísticas:

| Distância Focal | Uso Direcional | Efeito Psicológico |
|---|---|---|
| **18–24 mm** | Planos gerais, cenários opressivos, distorção de proximidade | Isolamento, vastidão, tensão espacial |
| **35 mm** | Plano americano, contextualização de personagem no espaço | Naturalismo, jornalismo |
| **50 mm** | Plano médio, visão "olho humano" | Neutralidade, intimidade controlada |
| **85 mm** | Close-up, retrato, compressão de fundo | Intimidade, vulnerabilidade, foco emocional |
| **135–200 mm** | Detalhe extremo, voyeurismo, compressão máxima | Observação à distância, tensão de vigilância |

**Regra:** A escolha é justificada no campo `lens_justification` e vinculada ao vetor **Desejo** e **Ritmo** da cartela.

#### 3.3.2 — Regra dos 180° e Eixo de Ação

O DirectorSKILL calcula o **eixo de ação** (linha imaginária entre os dois personagens ou entre personagem e objeto de interesse) e determina:

- **Lado da câmera:** Lado A ou Lado B. Uma vez definido para a cena, **todos os planos subsequentes devem permanecer no mesmo lado**, salvo corte de transição justificado (ex: plano de corte neutro, insert, ou movimento de câmera que cruze o eixo em tempo real).
- **Posições de tela:** Se Helena está em quadro-esquerdo no plano master, ela **deve** permanecer em quadro-esquerdo em todos os contra-planos. O campo `screen_position_lock` é preenchido.
- **Validação:** Se um prompt solicitar posição invertida sem transição, o DirectorSKILL emite `ERR_180_CROSS` e bloqueia.

#### 3.3.3 — Motivação de Movimento de Câmera

Nenhum movimento de câmera é autorizado sem motivação narrativa vinculada à Fórmula da Cena:

| Movimento | Motivação Válida | Motivação Inválida |
|---|---|---|
| Dolly-in | Aproximar o espectador do desejo/obstáculo | "Porque fica bonito" |
| Pan horizontal | Acompanhar rastro ocular entre dois pontos de interesse | Movimento arbitrário |
| Tilt vertical | Revelar obstáculo oculto ou mudar de plano de foco | Sem vínculo com cartela |
| Steadicam / Tracking | Acompanhar deslocamento físico do personagem | "Para dar dinamismo" |
| Static (tripé) | Observação, tensão, ritmo contemplativo | Falta de ideia |

O campo `camera_move_justification` é obrigatório e referenciado ao campo `desire` ou `obstacle` da cartela.

#### 3.3.4 — Iluminação e Exposição

Para cada plano, o DirectorSKILL define:

```json
{
  "lighting": {
    "key": {
      "type": "Fresnel 2K",
      "position": "45° superior direita",
      "color_temp_K": 3200,
      "intensity_ratio": "1.0 (base)"
    },
    "fill": {
      "type": "Refletor prata",
      "position": "30° inferior esquerda",
      "ratio_to_key": "1:4"
    },
    "back": {
      "type": "Dedo 1K",
      "position": "160° atrás do personagem",
      "color_temp_K": 5600,
      "purpose": "Recorte de silhueta contra fundo escuro"
    },
    "contrast_ratio": "6:1",
    "practical_sources": ["Lâmpada fluorescente piscando, 4000K, no teto do cenário"]
  }
}
```

#### 3.3.5 — Output do Passo 3

```json
{
  "scene_id": "SC-03-017",
  "shot_id": "SC-03-017_SH01",
  "lens_mm": 85,
  "lens_justification": "Close-up de Helena: compressão de fundo isola o rosto e vincula intimidade ao desejo de alcançar a faca.",
  "f_stop": "f/2.0",
  "focus_distance_m": 1.8,
  "aspect_ratio": "2.39:1",
  "camera_position": "Lado A do eixo de ação",
  "screen_position_lock": {
    "Helena": "quadro-esquerdo",
    "Rui": "quadro-direito"
  },
  "camera_move": "Dolly-in",
  "camera_speed_ms": 0.2,
  "camera_move_justification": "Aproximação ao desejo (faca) e redução da distância ao obstáculo (Rui).",
  "lighting": { "...": "conforme 3.3.4" },
  "duration_s": 7.5,
  "fps": 24,
  "rule_180_status": "VERIFIED_SAME_SIDE",
  "eye_trace_confirmed": true,
  "continuity_check": "PASS"
}
```

---

### Passo 4: Formatação de Prompt Estrito de Movimento (Compilador Multi-Motor)

**Objetivo:** Empacotar toda a informação dos Passos 1–3 em um prompt técnico otimizado para o motor selecionado (**Google Flow / Veo** ou **Kling AI**), eliminando ambiguidade e garantindo reprodutibilidade.

#### 3.4.1 — Template A: Google Flow (Veo 3.1) — Estrutura de Prosa Estruturada

O DirectorSKILL gera o prompt Veo seguindo a ordem estrita de 8 blocos:

```
[IDENTITY LOCK]
Character: Helena. Embedding: helena_v1.safetensors. Seed: 48291736.
Face reference: P1_front.png, P3_profile_left.png.

[SCENE DESCRIPTION]
Interior. Abandoned industrial kitchen. Rusted metal surfaces. Broken tiles on floor.
Time: golden hour. Single warm light entering from a dirty window, frame-right, 12° elevation.
Practical: fluorescent tube flickering overhead, 4000K.

[COMPOSITION & LENS]
85mm lens, f/2.0, shallow depth of field.
Aspect ratio: 2.39:1 anamorphic.
Helena positioned frame-left, facing frame-right.
Rui positioned frame-right, blocking the corridor, 1.2m from counter.
Rule of thirds: Helena's eyes on upper-left intersection.

[ACTION & PHYSICAL PERFORMANCE]
Helena's jaw is clenched, masseter muscle visible.
Her right fist is closed at her side. Breathing cycle: 4 seconds, thoracic.
She takes one slow step forward onto broken glass.
Rui does not move. His weight is on his back foot.

[CAMERA MOVEMENT]
Slow dolly-in at 0.2 m/s on a straight axis toward Helena's face.
No pan. No tilt. No roll. Duration: 7.5 seconds at 24fps.

[LIGHTING]
Key: warm 3200K from frame-right, 45° elevation, hard shadow.
Fill: minimal, 1:4 ratio.
Backlight: cool 5600K rim on Helena's hair and shoulder.
Contrast ratio: 6:1. Visible dust particles in the light beam.

[EYE-TRACE GUIDANCE]
Viewer's eye enters frame at Helena's clenched fist (lower-left),
travels diagonally up along her arm, locks on her eyes (upper-left third).

[NEGATIVE PROMPT]
No smile. No bright colors. No clean surfaces. No modern appliances.
No cartoon. No illustration. No CGI look. No extra limbs. No face distortion.
No text. No watermark. No lens flare unless motivated by window.
```

#### 3.4.2 — Template B: Kling AI (1.5 / 2.0) — Formato Numérico e de Parâmetros

Para a Kling AI, a diretriz física do smixs/DirectorSKILL é mapeada para a sintaxe nativa com inputs numéricos e Start Frame:

```json
{
  "target_engine": "kling_v2",
  "mode": "professional",
  "duration_s": 5,
  "aspect_ratio": "16:9",
  "start_frame_path": "Visual_Bible/Helena/P1_front.png",
  "end_frame_path": null,
  "prompt": "Cinematic shot of Helena in an abandoned industrial kitchen, 85mm lens f/2.0 portrait compression. Helena's jaw is clenched, masseter muscle visible, right fist closed. Cold 5600K rim light on hair, warm 3200K key light from right. She takes one deliberate step on broken glass. Ultra-realistic, 35mm film grain, 24fps cinema look.",
  "negative_prompt": "cartoon, 3d render, plastic skin, blur, deformed hands, face mutation, extra limbs, oversaturated, text, watermark, bad anatomy",
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

#### 3.4.3 — Regras de Formatação e Validação Pré-Envio

| Regra | Google Flow (Veo) | Kling AI (1.5 / 2.0) |
|---|---|---|
| **Câmera** | Priorizada na abertura ou bloco dedicado `[CAMERA MOVEMENT]` | Mapeada diretamente para o objeto numérico `camera_controls` (-10 a +10) |
| **Referência Facial** | Injetada via Reference Ingredients / Embedding | Injetada no **Start Frame** (Image-to-Video) com P1 ou P3 |
| **Limite de Texto** | 800 tokens max | 500 caracteres max no prompt descritivo |
| **Negative Prompt** | Bloco textual fixo (mínimo 10 termos) | Campo negativo separado |

O validador rejeita qualquer payload com termos da lista negra smixs ou com quebra de eixo não justificada.

#### 3.4.4 — Output do Passo 4

Arquivo `Render_Payload_SC-03-017_SH01.json` validado, pronto para envio direto via API ou execução assistida pelo operador na interface do motor.

---

### Passo 5: Renderização, Encadeamento de Vídeos Longos e Pós-Produção

**Objetivo:** Renderizar os clipes nos motores de difusão, aplicar o encadeamento contínuo para sequências longas e montar a linha do tempo final no CapCut ou Premiere.

#### 3.5.1 — Estratégia de Vídeos Longos (Long Video Chaining & Micro-Beats)

Como os motores de vídeo geram clipes de 4s a 10s, a produção de cenas longas segue a estratégia demonstrada na metodologia Dark Cinema / Vídeos Longos:

1. **Divisão em Micro-Beats (2–6s):** Cada parágrafo de ação do livro é decupado em planos curtos com propósito narrativo e rastro ocular controlado.
2. **Encadeamento Last-Frame → First-Frame:** 
   - Ao concluir a renderização do clipe *Shot N*, o **último frame** é extraído automaticamente em alta resolução (`shot_N_last_frame.png`).
   - Este frame é injetado como **Start Frame** do *Shot N+1*, garantindo que a pose, figurino e iluminação do ator comecem no ponto exato onde o plano anterior terminou.
3. **Cortes de Cobertura e Transição:** Para mudanças de ângulo dramáticas (ex: corte de Helena para Rui), utiliza-se o Start Frame correspondente da Bíblia Visual (ex: P1 de Rui) com respeito rigoroso à Regra dos 180° e direção de olhar.

#### 3.5.2 — Submissão e Controle de Qualidade (QC)

- Cada plano gera de 1 a 3 variações de seed.
- Checklist de aprovação:
  - Similaridade facial ≥ 92% contra P1.
  - Alinhamento de eixo e olhar (eyeline match).
  - Ausência de artefatos de IA (mãos deformadas, derretimento de textura).
  - Duração precisa do clipe.

Clipes reprovados são re-renderizados com ajuste de prompt (máximo 2 re-renders antes de escalar ao Diretor de Fotografia humano).

#### 3.5.3 — Entrega à Ilha de Edição

- Arquivos exportados: `.mp4 H.265` (proxy) e `.mov ProRes 422 HQ` (master) quando disponível.
- Nomenclatura: `PRJ-001_SC-03-017_SH01_TK02_APPROVED.mov`.
- Estrutura de pastas:

```
/PRJ-001/
  /01_Visual_Bible/
  /02_Scene_Cards/
  /03_Render_Prompts/
  /04_Renders/
    /SC-03/
      SC-03-017_SH01_TK01.mp4
      SC-03-017_SH01_TK02_APPROVED.mov
      SC-03-017_SH01_TK03.mp4
  /05_Edit_Timeline/
  /06_Final_Export/
```

#### 3.5.4 — Montagem

- O editor importa os clipes aprovados na ordem da decupagem (gerada pelo DirectorSKILL como EDL ou XML de timeline).
- Ajuste fino de timing, transições, desenho de som e mixagem.
- Exportação final conforme deliverable (DCP, ProRes master, H.264 web).

---

## 4. Requisitos de Continuidade e Geometria

### 4.1 Mitigação de Face-Drift

| Estratégia | Implementação |
|---|---|
| Embedding facial fixo | Cada personagem possui um `.safetensors` de identidade gerado na Bíblia Visual. O embedding é injetado como condicionante em **100%** dos prompts que incluem o personagem. |
| Painéis de referência | P1 (frente) e P3 (perfil) são anexados como **reference images** em cada render. |
| Seed por personagem | A seed de geração do rosto é fixa. A seed do plano (composição) é variável. Isso ancora a identidade e permite diversidade de enquadramento. |
| QC facial | Comparação automática (ou assistida) de similaridade facial entre o render e P1. Threshold: ≥ 92%. |
| Lock de atributos | Cor do cabelo, cicatrizes, vestuário são descritos no prompt com linguagem física idêntica em todos os planos. O campo `continuity_notes` da cartela (campo 14) é propagado. |

### 4.2 Regra dos 180° e Eixo de Ação

- O DirectorSKILL calcula o eixo de ação na primeira cena de cada sequência.
- O campo `camera_position` (Lado A / Lado B) é **travado** para toda a sequência.
- Qualquer solicitação de mudança de lado exige:
  - Um plano de corte neutro (insert, detalhe, plano aéreo vertical), **ou**
  - Um movimento de câmera contínuo que cruze o eixo em tempo real (dolly/tracking que passe pelo eixo).
- O validador pré-render verifica `rule_180_status`. Status `CROSS_DETECTED` sem plano de transição → bloqueio.

### 4.3 Rastro Ocular (Eye-Trace)

- O campo `eye_trace_path` (cartela, campo 8) define ponto de entrada, trajetória e ponto de ancoragem do olhar.
- O DirectorSKILL traduz isso em composição: posição dos elementos no quadro, uso de profundidade de campo (foco seletivo), e direção de movimento.
- No prompt, o bloco `[EYE-TRACE GUIDANCE]` instrui o modelo de difusão sobre a hierarquia visual do quadro.
- No QC, o operador verifica se o ponto de ancoragem está na interseção de terço correta.

### 4.4 Continuidade Espacial entre Planos

- O campo `geometry_blocking` (cartela, campo 7) define coordenadas relativas dos corpos.
- Entre planos consecutivos da mesma cena, a posição relativa dos personagens **não pode mudar** (a menos que a ação justifique).
- O DirectorSKILL compara `geometry_blocking` de planos adjacentes e emite `ERR_GEOM_SHIFT` se houver inconsistência não motivada.

### 4.5 Continuidade Temporal e de Figurino

- O campo `continuity_notes` (cartela, campo 14) registra: vestuário, adereços, estado físico (ferimentos, sujidade), posição de objetos.
- Este campo é **copiado literalmente** para o prompt de todos os planos subsequentes da sequência.
- Alterações de figurino ou estado físico só ocorrem quando a narrativa justifica, e devem ser registradas como novo `continuity_notes`.

---

## 5. Critérios de Sucesso e KPIs

### 5.1 KPIs de Pipeline (Eficiência de Produção)

| KPI | Meta v1.0 | Método de Medição |
|---|---|---|
| **Taxa de aprovação de primeiro render** (First-Pass Approval Rate) | ≥ 85% dos planos aprovados no primeiro render sem re-prompt | Contagem de planos aprovados / total renderizado, por projeto |
| **Taxa de re-render** | ≤ 10% dos planos necessitam de segundo render | Logs de submissão ao Google Flow |
| **Taxa de escalonamento humano** | ≤ 5% dos planos exigem intervenção do Diretor de Fotografia | Registro de escalonamentos |
| **Tempo de ingestão a prompt final** (Livro → Prompt pronto) | ≤ 4 horas para um capítulo de ~20 cenas | Timestamps de início/fim de pipeline |
| **Tempo de render por plano** | ≤ 3 minutos (dependente do Veo) | API response time |
| **Throughput diário** | ≥ 50 planos renderizados e aprovados por estação de trabalho | Contagem de arquivos na pasta `/04_Renders/` |

### 5.2 KPIs de Qualidade Visual (Fidelidade)

| KPI | Meta | Método |
|---|---|---|
| **Similaridade facial (Face Similarity Score)** | ≥ 92% entre render e P1 da Bíblia Visual | Ferramenta de comparação facial (ArcFace / InsightFace) ou avaliação estruturada por operador |
| **Conformidade com a Regra dos 180°** | 100% dos planos sem violação não justificada | Auditoria por amostragem + validador automático |
| **Conformidade de iluminação** | ≥ 90% dos planos com temperatura de cor e razão de contraste dentro de ± 200K e ± 0.5 stop | Análise de histograma / avaliação visual |
| **Ausência de termos subjetivos no prompt final** | 0 termos da lista negra em qualquer prompt enviado | Parser automático pós-geração |
| **Cartela de 14 campos completa** | 100% dos campos preenchidos em 100% das cenas | Validação de schema JSON |

### 5.3 KPIs de Narrativa e Direção

| KPI | Meta | Método |
|---|---|---|
| **Fórmula da Cena presente** | 100% das cenas com os 5 vetores preenchidos | Validação de schema |
| **Motivação de câmera documentada** | 100% dos movimentos com `camera_move_justification` vinculada a desejo/obstáculo | Auditoria de campo |
| **Eye-trace definido e verificável** | 100% dos planos com `eye_trace_path` | Validação de campo + QC visual |

### 5.4 KPIs de Pós-Produção

| KPI | Meta | Método |
|---|---|---|
| **Tempo de montagem por cena** | ≤ 30% do tempo de montagem manual equivalente | Comparativo com baseline de produção anterior |
| **Taxa de clipes utilizáveis na timeline** | ≥ 90% dos clipes aprovados no QC são usados na edição final | Contagem na timeline vs. renders aprovados |
| **Retrabalho na ilha de edição** | ≤ 15% dos clipes exigem correção de cor, reframing ou estabilização | Registro do editor |

### 5.5 Critério Global de Sucesso (Go/No-Go)

O pipeline é considerado **operacional para produção** quando, em um projeto-piloto de 3 capítulos (≈ 60 cenas, ≈ 180 planos):

1. Taxa de aprovação de primeiro render ≥ 85%.
2. Zero violações de Regra dos 180° não justificadas.
3. Zero instâncias de face-drift perceptível (similaridade ≥ 92% em todos os planos).
4. Cartela de 14 campos com 100% de preenchimento.
5. Tempo total de pipeline (ingestão → renders aprovados) ≤ 2 dias úteis.

---

## 6. Riscos e Mitigações

| Risco | Probabilidade | Impacto | Mitigação |
|---|---|---|---|
| O Veo não respeita instruções de lente (ex: ignora "85mm") | Alta | Médio | Incluir referência visual de compressão de fundo. Testar com A/B de prompts. Escalar para suporte Google. |
| Face-drift em ângulos extremos (P4 – costas, P7 – detalhe) | Média | Alto | Reforçar embedding com múltiplos painéis de referência. Limitar ângulos extremos a inserts curtos. |
| Lista negra smixs não cobre todos os termos subjetivos | Média | Médio | Revisão trimestral da lista. Feedback loop: termos novos identificados no QC são adicionados. |
| DirectorSKILL gera prompts > 800 tokens | Baixa | Baixo | Compressão automática com prioridade de blocos. Validação pré-envio. |
| Inconsistência de figurino entre cenas de capítulos diferentes | Média | Alto | Campo `continuity_notes` propagado obrigatoriamente. QC visual dedicado a figurino. |
| Dependência de API externa (Google Flow / Claude) | Baixa | Crítico | Cache de prompts. Fallback para render local (Wan2.1 / Kling) em contingência. SLA de uptime monitorado. |

---

## 7. Glossário

| Termo | Definição |
|---|---|
| **Face-Drift** | Alteração não intencional das características faciais de um personagem entre gerações de imagem/vídeo. |
| **Bíblia Visual** | Documento de referência contendo todos os painéis de ângulo de cada personagem e cenário do projeto. |
| **Cartela de Plano** | Estrutura de 14 campos que descreve uma cena em termos físicos e geométricos, sem subjetividade. |
| **Eye-Trace (Rastro Ocular)** | Trajetória planejada do olhar do espectador dentro do quadro, do ponto de entrada ao ponto de ancoragem. |
| **Regra dos 180°** | Convenção cinematográfica que mantém a câmera em um único lado do eixo de ação para preservar a orientação espacial. |
| **Embedding de Identidade** | Vetor numérico que codifica as características faciais de um personagem, usado como condicionante na geração. |
| **Decupagem** | Processo de dividir a cena em planos (shots) com especificações técnicas de câmera, lente e composição. |
| **Prompt Estrito** | Instrução de geração formatada em blocos fixos, com linguagem exclusivamente física e valores numéricos. |

---

## 8. Aprovação e Controle de Versão

| Versão | Data | Autor | Alteração |
|---|---|---|---|
| 1.0.0 | Jul 2025 | Gerência de Produto — IA Cinematográfica | Emissão inicial do PRD |
| | | | |

| Papel | Nome | Assinatura | Data |
|---|---|---|---|
| Product Owner | _________________________ | _________ | ___/___/___ |
| Lead de Engenharia de Prompt | _________________________ | _________ | ___/___/___ |
| Diretor(a) de Fotografia | _________________________ | _________ | ___/___/___ |
| Lead de Pós-Produção | _________________________ | _________ | ___/___/___ |

---

*Fim do Documento.*

*Este PRD é um artefato vivo. Alterações de escopo, novos módulos ou mudanças na API do Google Flow exigem atualização de versão e re-aprovação pelos stakeholders listados.*