# PRD — Tríade: Pipeline de Pré-Produção e Geração de Vídeo Automatizado

**Versão:** 2.0 · **Status:** Rascunho para revisão · **Base:** pesquisa direta nos repositórios das três ferramentas (out/2026)

---

## 0. O que mudou da v1 e o que a pesquisa revelou

### 0.1 Fontes analisadas
| Papel | Repositório | Licença | Observação |
|---|---|---|---|
| Visual | `christopherjohnogden/CineGen` (README) | MIT | Existem outros projetos chamados "CineGen"; este é o único que bate com 7 painéis e @Tags. |
| Teoria | `smixs/visual-skills` (`video/SKILL.md`, `dramaturgy.md`, `veo.md`) | **CC-BY-4.0** | Atribuição obrigatória a Serge Shima. |
| Matemática | `wuwangzhang1216/DirectorSKILL` (README) | MIT | Identificado pelo nome/descrição; existem homônimos (ex.: `princeca4746/DirectorSkill`, focado em mangá). **Confirmar que é este.** |

### 0.2 Correções à v1 (premissas que não se confirmaram)
1. **A "cartela de 14 campos" é real e já tem definição** (seção 4.2). Os 14 campos que eu tinha inventado na v1 foram descartados.
2. **O smixs não coloca a regra dos 180° no topo.** Na Regra dos Seis de Murch adotada por ele, o eixo de tela pesa 5% e o rastro ocular 7%; emoção pesa 51%. Isso gera uma tensão com o seu requisito de "atores nunca trocam de lado" (seção 7.2).
3. **O DirectorSKILL é raciocínio de direção, não um motor matemático.** Ele trabalha com psicologia de lente/focal, geometria de continuidade (eixo, regra dos 30°, direção de tela, eyeline match), 13 passos, 10 modos de saída (A–J) e um catálogo de falhas F1–F19. Não encontrei cálculo formal de lente. Tratamos a "matemática" como **regras determinísticas que nós implementamos como validadores** sobre a saída dele (seção 7).
4. **O CineGen não é 100% local e hoje é só macOS.** O app é Electron com módulo nativo AVFoundation (macOS 10.15+). As gerações de imagem/vídeo passam por provedores em nuvem (fal.ai, kie.ai, RunPod); só o LLM via Ollama e alguns runners (Whisper, SAM3, LTX) rodam local.
5. **Os 7 painéis e as @Tags existem, mas a ingestão de `.md` não está documentada.** O README descreve Elements (personagens, locações, props, veículos) com 7 painéis gerados por IA, "consistency engine" (o primeiro painel vira referência dos demais) e `@` nos nós de prompt. O README que li não descreve importar um livro `.md`. Um trecho de busca de outro snapshot cita um "Breakdown" com cenas e @Tags, mas **não consegui confirmar** isso no código. **Assumo que a ingestão `.md` → @Tags é uma lacuna a construir** (seção 3.3).
6. **O Veo gera clipes de 4, 6 ou 8 s** e o CineGen chama o Veo 3.1 via kie.ai, não pelo Google Flow (web). Isso muda o Passo 5.
7. **O CineGen já tem editor NLE próprio** com export MP4. Premiere/CapCut vira opcional; EDL/XML **não** consta no README (lacuna).

---

## 1. Resumo Executivo e Visão do Produto

### 1.1 Problema
Vídeo generativo produz planos bonitos, mas **inconsistentes entre si**: o rosto muda (face-drift), o figurino e o cenário derivam, prompts literários ("ele está triste") viram ruído, atores trocam de lado na tela e a câmera se move sem motivo. O resultado é o "efeito slideshow": quadros bonitos que vagam entre os planos.

### 1.2 Solução
Um pipeline em camadas onde cada camada resolve uma classe de falha:

| Falha | Camada responsável |
|---|---|
| Identidade, figurino, cenário | **CineGen** (Elements + painéis + @Tags) |
| Texto subjetivo, cena sem drama | **smixs** (Fórmula da Cena, três detalhes, cartela de 14 campos) |
| Lente, eixo, motivo de câmera, continuidade | **DirectorSKILL** (+ validadores nossos) |
| Execução fiel | **Veo** (Flow ou API) com referências |

### 1.3 Princípio central
> O CineGen decide *quem e onde*; o smixs decide *o que acontece e por quê*; o DirectorSKILL decide *como a câmera registra*; o Veo apenas executa.

### 1.4 Fora de escopo (v1)
Color grading final, mixagem de som, legendagem, distribuição, treinamento de LoRA.

---

## 2. Personas e User Stories

| Persona | Papel |
|---|---|
| **Diretor(a)** | Aprova Bíblia Visual, eixo e seleção final. |
| **Roteirista/Adaptador(a)** | Corrige cenas reprovadas no linter. |
| **Operador(a) de pipeline** | Roda os passos, resolve planos `FLAGGED`. |
| **Editor(a)** | Recebe clipes nomeados por `shot_id` e monta o filme. |

| ID | Story | Critério de aceite |
|---|---|---|
| US-01 | Como diretor, quero que cada personagem tenha o mesmo rosto em todos os planos. | Similaridade facial ≥ limiar em 90% dos planos. |
| US-02 | Como roteirista, quero saber *por que* uma cena foi reprovada. | Relatório linha a linha com o campo/regra violada. |
| US-03 | Como operador, quero reprocessar só os planos afetados após mudar um personagem. | Re-render restrito ao grafo de dependência. |
| US-04 | Como editor, quero clipes já nomeados e ordenados. | Importação sem relink manual. |
| US-05 | Como diretor, quero vetar qualquer cruzamento de eixo. | Plano bloqueado até decisão registrada. |

---

## 3. Arquitetura do Sistema

### 3.1 Camadas e dados

```
livro.md ─► [Ingestão: parser + LLM] ─► cenas.json + @Tags (candidatas)
                                            │
                              revisão humana (aliases)
                                            ▼
                         CineGen Elements ─► 7 painéis/ator (LOCKED, hash)
                                            │
cenas.json ─► smixs (Claude) ─► cena.json (Fórmula) + shotcards (14 campos)
                                            │
                      DirectorSKILL (Claude) ─► shotlist.json + axis_state + lentes
                                            │
                  Validadores Tríade (eixo, eyeline, linter) ─► OK / FLAGGED
                                            ▼
             Prompt Compiler (veo) ─► Veo (4/6/8 s) ─► QC ─► NLE / Premiere / CapCut
```

### 3.2 Mapa de capacidades reais vs. necessárias
| Capacidade | Existe? | Onde |
|---|---|---|
| 7 painéis por Element, primeiro painel vira referência | Sim | CineGen |
| `@` para injetar imagens no prompt | Sim | CineGen (nós de prompt) |
| Storyboarder (3–12 planos por cena) | Sim | CineGen |
| Shot Board 9 células (a partir de 1 referência) | Sim | CineGen |
| Veo 3.1 como modelo de vídeo | Sim | CineGen via kie.ai |
| Export MP4 (FFmpeg) | Sim | CineGen |
| Ingestão de `.md` com extração de @Tags | **Não confirmado** | **A construir** |
| Linter de adjetivos/estados internos | **Não** (é instrução ao LLM) | **A construir** |
| Validador determinístico de eixo/180° | **Não** | **A construir** |
| Export EDL/XML para Premiere/CapCut | **Não** | **A construir** |
| QC facial automático | **Não** | **A construir** |
| Integração com Google Flow (web) | **Não verificada** | Investigar API |

### 3.3 Componentes novos (escopo de engenharia)
1. **Ingestor** (`.md` → `cenas.json`, candidatas a @Tags com âncora de linha).
2. **Orquestrador** (executa os skills do smixs e do DirectorSKILL via Claude, grava JSONs versionados).
3. **Validadores** (linter smixs, eixo/eyeline, completude da cartela).
4. **Prompt Compiler** (shot → prompt Veo prosa/JSON, anexando painéis).
5. **QC** (embedding facial, checagem de duração/áudio/artefatos).
6. **Exportador** (EDL/XML ou FCPXML).

### 3.4 Contratos de dados
- JSON versionado (`schema_version`); IDs estáveis: `@ator_id`, `@loc_id`, `scene_id`, `shot_id` (`S03_SH07`).
- Bíblia trancada é imutável; mudança gera `bible_v2` e invalida só os planos que dependem dela.
- Cada clipe guarda `shot_id`, `bible_version`, `prompt_hash`, `seed`, `modelo`, `provedor`.

---

## 4. Fluxo de Trabalho de Produção

### Passo 1 — Ingestão e Trancamento Visual (CineGen)
1. Parse do `.md` em capítulo → cena → parágrafo (âncora de linha).
2. LLM propõe entidades; **humano resolve aliases** ("o velho", "Seu Antônio", "ele").
3. Criação dos Elements por categoria (personagem, locação, prop, veículo).
4. Geração dos **7 painéis** por Element. O primeiro painel gerado vira a referência dos demais (consistency engine do CineGen). Regeneração por painel, sem refazer o Element.
5. Diretor aprova → status `LOCKED` + hash por painel.

**Gate:** nenhuma cena avança sem todos os @ids `LOCKED`.

### Passo 2 — Conversão Literária e Cartela de Plano (smixs)

**2.1 Fórmula da Cena (obrigatória, nível de cena):**
`Cena = desejo do herói + obstáculo + geometria do espaço + olhar controlado + ritmo de edição`. Falta um elemento → a cena volta ao roteirista.

**2.2 Regra dos Detalhes (nível de plano):** todo plano tem 1 pressão ambiental + 1 microação física no corpo + 1 âncora de som ou motivo visual. Termos banidos: "cinematic", "epic", "stunning", "beautiful lighting", "dynamic camera" e emoção nomeada sem corpo ("ele está triste").

**2.3 Regra dos Três Trabalhos:** todo plano muda a emoção, avança a ação ou aumenta a pressão. Senão, é deletado.

**2.4 Cinco âncoras por peça curta:** emoção, motivo visual, objeto-âncora, quebra, imagem final.

**2.5 Cartela de 14 campos (definição do smixs):**

| # | Campo | # | Campo |
|---|---|---|---|
| 1 | Shot ID | 8 | Eye trace (onde o olho pousa nos primeiros 0,3 s) |
| 2 | Beat (o que muda na história) | 9 | Duração |
| 3 | Emoção | 10 | Tipo de corte (match, smash, cut on action, J/L-cut) |
| 4 | Frame (wide/medium/close/macro) | 11 | Som |
| 5 | Composição | 12 | Luz / cor |
| 6 | Câmera (estática, push-in, handheld, tracking, whip-pan) | 13 | Ação (evento físico exato) |
| 7 | Razão do movimento ("o que mudou?") | 14 | Nota de produção (prop, locação, direção de ator) |

**Extensão Tríade (campos adicionais fora dos 14, preenchidos pelas outras camadas):** `@tags`, `scene_id`, `source_anchor` (linha do livro), `lens_mm`, `axis_state`, `screen_position`, `shot_function` (Establish/Power/Pressure/Detail/Reaction/Shift/Impact/Aftermath/Exit).

### Passo 3 — Decupagem e Lógica Direcional (DirectorSKILL)
1. Roda os passos do skill sobre a cena: beat map → director's book (regras invariantes) → blocking → shot list com cobertura.
2. Escolhe lente/focal e justifica (`lens_rationale`) ligando ao desejo/obstáculo.
3. Define o **eixo de ação** da cena e grava `axis_state` (lado da câmera, @ator à esquerda/direita).
4. Gera o **Continuity Bible** (Modo G): strings de identidade, direção de luz, direção de tela, era — escritos uma vez e repetidos literalmente.
5. Nossos validadores checam as saídas (seção 7). Falha → `FLAGGED`.

### Passo 4 — Formatação de Prompt Estrito (Veo)
Regras do `veo.md` do smixs, adotadas no Prompt Compiler:
- **Ordem:** sujeito/ação → ambiente → câmera/lente → luz → estilo → áudio → duração. Para câmera ser respeitada, **abrir o prompt com ela**.
- Faixa de 50–200 palavras em prosa; para continuidade rígida, **JSON** (bloco `continuity` com personagens, props e luz constante; humor isolado em `global_style` para não "vazar" na cor dos objetos).
- Áudio com rótulos explícitos (`Audio:`, `SFX:`, `Says:`). Fala: aspas + verbo de abertura; **máx. 8 s de fala por clipe**.
- **Imagem → vídeo (Veo 3.1):** o primeiro frame é a imagem; descrever só movimento, câmera, luz e áudio; incluir "maintain the subject from the first frame".
- **Reference ingredients (3.1):** anexar personagem, locação e prop e citá-los no prompt.
- Prompt final em **inglês**; relatórios para o humano em português.
- **Seleção de painéis:** enviar só os painéis relevantes ao ângulo do plano (ex.: perfil, 3/4), pois o limite de referências por geração **não foi verificado**.

### Passo 5 — Renderização e Pós-Produção
1. Envio ao Veo (via CineGen/kie.ai ou Flow). Planos > 8 s são fatiados em clipes de 4/6/8 s com **último frame → primeiro frame** do clipe seguinte.
2. 3 variações por plano (seeds registradas).
3. QC automático → humano escolhe.
4. Reprovado → volta ao Passo 4 (máx. 3 ciclos; depois, replanejar o plano no Passo 3, não só reescrever o prompt).
5. Montagem no NLE do CineGen ou Premiere/CapCut (EDL/XML a construir).

---

## 5. Requisitos Funcionais e Não Funcionais

| ID | Requisito | Prioridade | Aceite |
|---|---|---|---|
| RF-01 | Ingerir `.md` e gerar `cenas.json` com âncoras de linha | P0 | 100% dos parágrafos mapeados |
| RF-02 | Propor @Tags e bloquear avanço com aliases não resolvidos | P0 | 0 ambiguidades pendentes |
| RF-03 | Gerar 7 painéis/Element e trancar com hash | P0 | Painéis `LOCKED` |
| RF-04 | Validar a Fórmula da Cena (5 elementos) | P0 | Cena incompleta é rejeitada com motivo |
| RF-05 | Validar os 14 campos e a regra dos três detalhes | P0 | Campo vazio bloqueia o plano |
| RF-06 | Linter de termos banidos/emoção sem corpo | P0 | Relatório linha a linha |
| RF-07 | Definir eixo por cena e `axis_state` por plano | P0 | Presente em 100% dos planos |
| RF-08 | Bloquear plano que cruza o eixo sem ponte autorizada | P0 | 0 cruzamentos silenciosos |
| RF-09 | Compilar prompt Veo (prosa/JSON) com referências | P0 | Template único, sem campos vazios |
| RF-10 | Fatiar planos longos com encadeamento de frames | P1 | Último/primeiro frame coincidem |
| RF-11 | QC facial e de lado/eixo por clipe | P1 | Relatório por clipe |
| RF-12 | Invalidar só planos afetados ao mudar a Bíblia | P1 | Grafo de dependência |
| RF-13 | Exportar EDL/XML com `shot_id` | P1 | Importa sem relink |
| RNF-01 | Reprodutibilidade (seed, versão do modelo, hash do prompt) | P0 | 100% dos clipes |
| RNF-02 | Rastreabilidade clipe → linha do livro | P0 | 100% |
| RNF-03 | Prompts agnósticos de motor (trocar Veo por Kling/Seedance) | P1 | Adapter por motor |
| RNF-04 | Segredos/API keys fora do repositório | P0 | Auditoria |
| RNF-05 | Atribuição CC-BY-4.0 ao smixs nos artefatos | P0 | Aviso incluído |

---

## 6. Contratos de Dados (exemplos)

### 6.1 Cena
```json
{
  "schema_version": "1.0",
  "scene_id": "S03",
  "source_anchor": {"file": "livro.md", "lines": [412, 448]},
  "formula": {
    "desire": "Antônio quer entregar a carta antes que a vizinha o veja",
    "obstacle": "A porta rangente e a vizinha na janela em frente",
    "geometry": "Antônio de costas para a rua, porta à direita; vizinha ao fundo, esquerda",
    "gaze": "Do envelope para a janela iluminada",
    "rhythm": "longo - mais curto - mais curto - pausa - impacto"
  },
  "anchors": {"emotion": "culpa", "motif": "reflexos em vidro", "object": "envelope",
              "break": "ele hesita e empurra a carta", "final_image": "reflexo no vidro escuro da porta"},
  "axis": {"line": "Antônio→porta", "camera_side": "A"},
  "tags": ["@antonio", "@vizinha", "@rua_noite", "@envelope"]
}
```

### 6.2 Shot card (14 campos smixs + extensão)
```json
{
  "shot_id": "S03_SH02",
  "beat": "Ele nota a vizinha na janela",
  "emotion": "culpa",
  "frame": "medium close-up",
  "composition": "Antônio no terço esquerdo, janela iluminada ao fundo (desfocada)",
  "camera": "push-in lento",
  "movement_reason": "Nova informação entra no quadro: a luz na janela",
  "action": "Ele para com a mão no ferrolho; a mandíbula trava; o olhar sobe até a janela",
  "eye_trace": "Mão no ferrolho → janela",
  "duration_s": 4,
  "cut_type": "cut on action",
  "sound": "chuva fina, ferrolho, uma respiração curta",
  "light_color": "luz fria lateral da rua, rim quente da janela",
  "production_note": "Casaco marrom, sem chapéu (ver @antonio painel 3/4)",
  "ext": {
    "tags": ["@antonio", "@vizinha", "@rua_noite"],
    "lens_mm": 50,
    "lens_rationale": "Proporção natural; pressão sem distorção",
    "axis_state": {"camera_side": "A", "antonio": "screen_left", "vizinha": "screen_right"},
    "shot_function": "Pressure",
    "source_anchor": {"file": "livro.md", "lines": [420, 424]}
  }
}
```

### 6.3 Prompt Veo (imagem → vídeo, prosa)
```
Maintain the subject from the first frame. Slow push-in, 50mm, eye-level. He stops with his hand on the latch, jaw tightening, eyes rising to the lit window behind him. Cold side street light, warm window rim light. Rain on wet asphalt.

Audio: fine rain, a metal latch, one short breath.
Duration: 4 seconds.
References: @antonio (3/4 left panel), @rua_noite.
```

---

## 7. Requisitos de Continuidade e Geometria

### 7.1 Matriz de mitigação
| ID | Risco | Mitigação | Verificação |
|---|---|---|---|
| C1 | Face-drift | Painéis anexados em todo plano; Bíblia trancada; planos curtos | Similaridade facial |
| C2 | Figurino/props | Strings de identidade do Continuity Bible repetidas literalmente | Checklist visual + QC |
| C3 | Cruzar o eixo | `axis_state` por plano; bloquear sem ponte | Validador de lado |
| C4 | Rastro ocular | Campo 8 do shot card: onde o olho pousa em 0,3 s; o plano N+1 recebe esse olhar | Validador de pares |
| C5 | Direção de tela | Mesma direção de movimento entre planos | Validador de sequência |
| C6 | Luz | Campo 12 + direção/temperatura constantes por cena | Histograma entre vizinhos |
| C7 | O modelo não sabe onde a câmera estava | Reescrever geometria (posição, direção) em cada prompt | Revisão + QC |
| C8 | Cortes encadeados | Último frame → primeiro frame | Verificação de encadeamento |

### 7.2 Decisão de produto: hierarquia entre Murch e o seu requisito
O smixs prioriza **emoção (51%) > história (23%) > ritmo (10%) > rastro ocular (7%) > plano 2D/eixo (5%) > espaço 3D (4%)**. O seu pedido trata o eixo como inegociável. Proposta:
- O **bloqueio de eixo continua obrigatório** como regra de produto (evita erro de AI, que não "sabe" onde a câmera estava).
- Violações deliberadas por motivo dramático são permitidas **só com ponte** (plano de corte, movimento visível sobre o eixo) ou **decisão registrada** do diretor, em linha com o princípio do smixs de que a emoção prevalece.

### 7.3 Pausa antes do impacto
Sempre inserir ao menos uma pausa antes do corte mais forte (escada de ritmo do smixs: longo → mais curto → mais curto → pausa → impacto).

---

## 8. Tratamento de Erros e Códigos de Falha

| Código | Origem | Situação | Ação |
|---|---|---|---|
| E-ING-01 | Ingestão | Alias ambíguo | Bloqueia; pede decisão humana |
| E-BIB-01 | CineGen | Painel de baixa qualidade/inconsistente | Regenera só aquele painel |
| E-SMX-01 | smixs | Cena sem elemento da Fórmula | Devolve ao roteirista |
| E-SMX-02 | smixs | Campo da cartela vazio | Bloqueia o plano |
| E-SMX-03 | smixs | Termo banido/emoção sem corpo | Relatório + sugestão físico-gravável |
| E-DIR-01 | Director | Cruzamento de eixo | `FLAGGED`; exige ponte ou decisão |
| E-DIR-02 | Director | Movimento sem motivo | Rebaixa para câmera estática |
| E-REN-01 | Render | Face-drift | Troca painéis, encurta plano, 3 ciclos |
| E-REN-02 | Render | Fala acelerada (>8 s de texto) | Cortar a fala |
| E-REN-03 | Render | Áudio ausente | Reforçar rótulos `Audio:`/`Says:` |
| E-REN-04 | Render | Câmera ignorada | Abrir prompt pela câmera |
| E-REN-05 | Render | Humor muda cor de objetos | Migrar para JSON |
| E-REN-06 | Render | Falha de API/limite | Retentar com backoff; fila |

**Regra de três tentativas:** após 3 falhas no mesmo plano, **replanejar o plano** (Passo 3) em vez de reescrever o prompt de novo. O DirectorSKILL mantém um catálogo de falhas F1–F19; o mapeamento detalhado fica para a engenharia.

---

## 9. Critérios de Sucesso e KPIs

### 9.1 Qualidade
| KPI | Meta v1 |
|---|---|
| Planos sem face-drift visível | ≥ 90% |
| Similaridade facial média | ≥ 0,85 (calibrar no piloto) |
| Cruzamentos de eixo chegando à edição | 0 |
| Cenas aprovadas no linter em ≤ 2 iterações | ≥ 85% |
| Planos que passam na checagem dos 3 detalhes + 3 trabalhos | ≥ 95% |

### 9.2 Eficiência
| KPI | Meta v1 |
|---|---|
| Aproveitamento (usados/gerados) | Baseline no piloto |
| Ciclos de re-render por plano | ≤ 2 |
| Custo por segundo aprovado | Teto definido após o piloto |
| Tempo de pré-produção por minuto de filme | −60% vs. manual |

### 9.3 Processo
| KPI | Meta v1 |
|---|---|
| Rastreabilidade clipe → linha do livro | 100% |
| `FLAGGED` resolvidos sem escalar ao diretor | ≥ 70% |
| Importação EDL/XML sem relink | ≥ 95% |

---

## 10. Exemplo Ponta a Ponta (trecho fictício)

> *"Antônio parou diante da porta. Do outro lado da rua, a luz da vizinha acendeu."*

1. **CineGen:** `@antonio`, `@vizinha`, `@rua_noite`, `@envelope` → 7 painéis cada → `LOCKED`.
2. **smixs:** desejo (entregar a carta sem ser visto), obstáculo (a vizinha), geometria, olhar, ritmo → "ele está nervoso" é rejeitado e vira "mandíbula travada, mão parada no ferrolho".
3. **DirectorSKILL:** `S03_SH02`, 50 mm, push-in motivado pela luz na janela, eixo lado A.
4. **Compiler:** prompt de 4 s (6.3) com painéis do `@antonio`.
5. **Render + QC:** 3 variações, similaridade facial e lado verificados → exportado como `S03_SH02.mp4`.

---

## 11. Riscos, Licenças e Questões em Aberto

### 11.1 Riscos
| Risco | Prob. | Impacto | Mitigação |
|---|---|---|---|
| CineGen só em macOS | Alta | Médio | Confirmar plataforma da equipe ou portar |
| Ingestão `.md` não existe | Alta | Alto | Construir Ingestor (RF-01) |
| Veo ignora referências e deriva o rosto | Alta | Alto | Planos curtos, QC, regeneração |
| Skills mudam (repos pequenos e ativos) | Média | Médio | Fixar versão/commit; testes de regressão |
| Dependência de provedores (kie.ai/fal.ai) | Média | Médio | Adapters, fila, alternativas |
| DirectorSKILL errado (homônimos) | Média | Médio | Confirmar repositório com o time |

### 11.2 Licenças e conformidade
- **smixs/visual-skills: CC-BY-4.0.** Todo derivado que use o método precisa creditar Serge Shima e linkar o repositório.
- **DirectorSKILL e CineGen: MIT.** Os módulos de estilo do DirectorSKILL descrevem métodos de diretores e **não licenciam cópia** de planos/diálogos de filmes reais.
- Direitos do **livro** (domínio público ou autorizado) antes da ingestão.
- Conteúdo sintético: seguir política de marca d'água/metadados dos provedores.

### 11.3 Plano de entrega
| Fase | Escopo | Saída |
|---|---|---|
| M0 Piloto | 1 cena, 2 atores, 1 locação | Bíblia + ~10 planos contínuos |
| M1 Capítulo | Ingestor + linter + validador de eixo | KPIs de qualidade atingidos |
| M2 Automação | QC facial, fila de render, EDL/XML | −60% de tempo |
| M3 Livro | Obra completa | Montagem final |

### 11.4 Questões em aberto
1. O Google Flow tem API ou o envio será manual? (**não pesquisado**)
2. Qual o limite de imagens de referência por geração no Veo/Flow?
3. O repositório do DirectorSKILL é mesmo `wuwangzhang1216/DirectorSKILL`?
4. Plataforma da equipe (CineGen exige macOS)?
5. Idioma do livro e dos diálogos (Veo gera fala sincronizada)?
6. Orçamento do piloto M0?

---

## 12. Glossário
- **Face-drift:** o rosto muda entre planos.
- **Eye-trace / rastro ocular:** onde o olhar do espectador pousa no momento do corte.
- **Eixo de ação / regra dos 180°:** linha imaginária entre os atores; a câmera não a cruza sem ponte.
- **Ponte (buffer shot):** plano sobre o eixo que suaviza o cruzamento.
- **Blocking:** coreografia de atores e câmera no espaço.
- **Murch, Regra dos Seis:** hierarquia de critérios de corte.
- **Bíblia Visual / Elements:** referências trancadas de personagens, locações, props.
- **Continuity Bible:** strings de identidade, luz e direção de tela repetidas literalmente.
- **@Tag:** identificador estável de entidade usado nos prompts.
- **FLAGGED:** plano bloqueado aguardando decisão.

---

## Fontes
- CineGen: github.com/christopherjohnogden/CineGen
- smixs/visual-skills: github.com/smixs/visual-skills (`video/SKILL.md`, `video/references/dramaturgy.md`, `video/references/veo.md`)
- DirectorSKILL: github.com/wuwangzhang1216/DirectorSKILL
- Regra dos 180°: en.wikipedia.org/wiki/180-degree_rule