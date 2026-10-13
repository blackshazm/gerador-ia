# Especificação de Arquitetura & UX: Cockpit de Direção e Estúdio Focado
## Tríade Studio — Transformação da Interface para Máxima Intuitividade & Zero Perda de Contexto

**Versão:** 2.0.0  
**Status:** Aprovado para Implementação  
**Objetivo:** Eliminar a sobrecarga cognitiva (mais de 130 blocos de texto abertos), fornecer acompanhamento de progresso em tempo real e guiar o operador passo a passo sem deixar escapar nenhum detalhe da produção cinematográfica.

---

## 1. Diagnóstico do Problema & Princípios de Design

### 1.1 O Desafio Atual
Atualmente, cada plano da cena renderiza 6 blocos de texto simultâneos. Em uma cena com 22 planos, isso gera mais de **130 campos de texto concorrentes**. O operador perde a noção de:
1. *O que já foi feito e o que falta fazer.*
2. *Qual botão deve ser clicado em cada etapa.*
3. *Se a continuidade visual (roupa, iluminação e ator) entre o Plano $N-1$ e o Plano $N$ foi mantida.*

### 1.2 Os 4 Pilares da Nova Arquitetura
* **Pilar 1 — Cockpit Consolidado:** O topo da tela responde instantaneamente *"em quantos % esta cena está pronta?"*.
* **Pilar 2 — Botão da Próxima Ação (Next Action):** O sistema assume a inteligência de guiar o próximo passo lógico.
* **Pilar 3 — Gaveta Retrátil de Prompts ("Modo Limpo"):** O operador vê a história, o vídeo e a voz. Prompts técnicos em inglês ficam recolhidos em gavetas com cópia em 1 clique.
* **Pilar 4 — Mesa de Corte & Continuidade (Split-View):** Comparação direta entre o último quadro do plano anterior e o quadro atual para garantir *Tail-to-Head Chaining*.

---

## 2. Módulo 1: O Cockpit de Produção (Topo da Cena)

O cabeçalho da cena passa a abrigar um painel de instrumentação em tempo real:

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ 🎬 SC_01: Dona Gorf — O Feitiço das Maçãs                 [▶ Assistir Prévia da Cena] │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ 🎙️ Locuções: 22/22 (100%) │ 🖼️ Imagens: 4/22 (18%) │ 🎬 Vídeos: 0/22 (0%)              │
│ Barra de Progresso Geral: [████████████████░░░░░░░░░░░░░░░░░░░░░░░░] 39% Produzido     │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ FILTROS RÁPIDOS DE FOCO:                                                              │
│ [🔘 Todos (22)]  [⚠️ Pendentes de Imagem (18)]  [🎬 Prontos p/ Vídeo (4)]  [✓ Prontos (0)]│
└────────────────────────────────────────────────────────────────────────────────────────┘
```

### Funcionalidades do Cockpit:
1. **Contadores Reais de Mídia:** Varre em tempo real os diretórios `05_audio/`, `06_renders/` e metadados de `SC_01.json`.
2. **Filtros Rápidos de Exibição:** 
   * Ao clicar em `Pendentes de Imagem`, a tela oculta todos os planos prontos e isola somente os cartões que necessitam de geração de imagem.
   * Ao clicar em `Prontos p/ Vídeo`, exibe apenas os planos com Start Frame pronto aguardando renderização temporal.

---

## 3. Módulo 2: O Card Inteligente & Botão de Próxima Ação

O layout do cartão de plano é simplificado em 60%, destacando apenas o que é essencial para o diretor:

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ PLANO 02 — SC01_SH02   │   Medium Close-up (50mm)   │   ⏱️ 6.0s         [✏️ Editar Plano]│
├────────────────────────────────────────────────────────────────────────────────────────┤
│ [✓ Áudio Pronto] ➔ [⚠️ Falta Imagem Base] ➔ [⏳ Vídeo Pendente] ➔ [✓ Linha do Tempo]     │
├────────────────────────────────────────────────────────────────────────────────────────┤
│                       [ BANNER CINEMATOGRÁFICO 16:9 ]                                  │
│                 (Foto de alta resolução ou Player MP4 em loop)                         │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ 🎬 Ação Física: Dona Gorf inclina o tronco sobre a mesa, nós dos dedos brancos na madeira. │
│ 🎙️ Narração: "Se errarem uma única conta, vou transformar vocês em maçãs!"    [▶ Ouvir]│
├────────────────────────────────────────────────────────────────────────────────────────┤
│ 👉 PRÓXIMA AÇÃO RECOMENDADA:                                                           │
│ ┌────────────────────────────────────────────────────────────────────────────────────┐ │
│ │  🎨 GERAR QUADRO BASE COM FLUX (START FRAME)                                       │ │
│ └────────────────────────────────────────────────────────────────────────────────────┘ │
│                                                                                        │
│ ▶ [Expandir Prompts Técnicos de Cinema (FLUX / Kling / Negativo)]                      │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

### Lógica da Máquina de Estados do Botão Inteligente:
* **Estado 1 (Sem Áudio):** Exibe botão azul `[🎙️ Sintetizar Voz Neural PT-BR]`.
* **Estado 2 (Com Áudio, Sem Imagem):** Exibe botão verde vibrante `[🎨 Gerar Start Frame com FLUX]`.
* **Estado 3 (Com Imagem, Sem Vídeo):** Exibe botão roxo de destaque `[🎬 Animar Vídeo de 6s com Kling AI]`.
* **Estado 4 (Vídeo Renderizado):** Exibe badge de sucesso `[✓ Concluído - Reproduzindo Clipes]`.

---

## 4. Módulo 3: Gaveta Retrátil de Prompts Técnicos ("Modo Clean")

Para evitar poluição visual, os prompts técnicos em inglês ficam recolhidos sob uma barra expansível sanfonada (*Accordion*):
* **Ao clicar em "Expandir Prompts Técnicos":**
  * Abre com transição suave os 4 blocos de engenharia de prompt:
    1. *Sliders Numéricos do Kling* (Zoom, Pan, Tilt).
    2. *Prompt de Imagem Estática* (Arri Alexa 35mm f/1.8 com iluminação Kelvin).
    3. *Prompt de Vídeo Temporal* (Física de 0-2s, 2-4s, 4-6s).
    4. *Prompt Negativo Cirúrgico* (Anti-deformação).
  * Inclui botões de cópia rápida `📋 Copiar Prompt` para quem usa o site do Kling AI ou Runway na Web.

---

## 5. Módulo 4: Modo "Mesa de Direção" (Split-View de Continuidade)

Alternador no topo da tela permitindo trocar entre:
* **Modo Grade (Grid Overview):** Visão geral de todos os planos.
* **Modo Mesa de Direção (Foco Plano a Plano):**
  * Divide a tela em duas metades horizontais:
    * **Lado Esquerdo:** O plano anterior com o **Tail Frame (último segundo)** congelado.
    * **Lado Direito:** O plano atual que está sendo produzido.
  * O operador valida visualmente:
    * A iluminação permaneceu no mesmo lado?
    * O ator está na mesma posição corporal?
    * O figurino é idêntico?
  * Permite aprovar a continuidade com certeza cirúrgica antes de gastar tempo ou créditos de vídeo.

---

## 6. Módulo 5: Player de Pré-Visualização Integrada da Cena

Um botão fixo no cabeçalho: `[▶ Assistir Prévia da Cena]`:
* Abre um visualizador modal cinematográfico.
* Concatena e reproduz automaticamente todos os vídeos e áudios que já foram gerados na sequência cronológica da cena.
* Se um plano ainda não tem vídeo, exibe sua imagem estática pelo tempo da locução.
* Permite ao diretor assistir o corte do filme diretamente no navegador antes de abrir o CapCut Desktop.

---

## 7. Roteiro de Implementação e Arquivos Impactados

1. **`web/index.html`:**
   * Adição do container `#scene-cockpit-bar` no topo de `#tab-content-shots`.
   * Adição dos botões de filtro rápido e do botão de pré-visualização contínua.
   * Adição do modal de pré-visualização de cena completa `#scene-preview-modal`.
2. **`web/styles.css`:**
   * Estilização da barra de progresso em gradiente e dos filtros ativos.
   * Estilização do Botão Inteligente de Próxima Ação (`.btn-next-action`).
   * Estilização das gavetas retráteis de prompts (`.prompt-drawer`).
3. **`web/app.js`:**
   * Cálculo das métricas de progresso no carregamento da cena.
   * Implementação da lógica de estados do botão dinâmico por plano.
   * Implementação dos filtros de visualização (`filterShotsByStatus(status)`).
   * Implementação do player contínuo de cena (`playFullScenePreview()`).
4. **`server/app.py`:**
   * Adição do endpoint `/api/scene-stats` consolidando status de áudios, imagens e renders.
