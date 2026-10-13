# Manual de Operação e Execução — Pipeline "A Tríade"
## Guia do Operador: Como Produzir a Primeira Cena (Piloto M0)

**Versão:** 1.0.0  
**Status:** Operacional  
**Público-alvo:** Diretores, Operadores de Pipeline e Produtores de Conteúdo

---

## 1. Pré-Requisitos e Setup Rápido

Antes de iniciar a primeira execução, certifique-se de ter:
1. **Python 3.10+** instalado com as dependências básicas:
   ```bash
   pip install pdfplumber edge-tts mutagen
   ```
2. **FFmpeg** instalado e adicionado ao PATH do sistema (para corte de frames de vídeo).
3. **Acesso à Nuvem:** Conta ativa no **Kling AI** (Web ou API) ou **Google Flow (Veo)**.
4. **CapCut Desktop** instalado para visualização e montagem.

---

## 2. Passo a Passo da Produção

### Passo 1 — Ingestão do Livro em PDF
1. Coloque o PDF do livro na pasta `00_raw_input/livro.pdf`.
2. Execute o script de higienização do Módulo 0.
3. Verifique o arquivo gerado em `01_normalized_text/livro_completo.md`.
4. *Ponto de Controle:* Certifique-se de que não restaram números de página ou cabeçalhos repetidos no meio dos parágrafos.

---

### Passo 2 — Casting e Criação da Bíblia Visual
1. Para cada personagem identificado (ex: `@antonio`, `@helena`):
   * Gere 3 opções de retrato frontal usando sua ferramenta de imagem (Midjourney, Flux ou Kling Image).
   * Escolha o rosto definitivo do personagem.
2. A partir do rosto escolhido, gere os **7 painéis canônicos de referência**:
   * `P1_front.png` (Rosto de frente)
   * `P2_3q_left.png` (Três-quartos esquerda)
   * `P3_profile_left.png` (Perfil esquerdo)
   * `P4_back.png` (Costas / Nuca)
   * `P5_3q_right.png` (Três-quartos direita)
   * `P6_profile_right.png` (Perfil direito)
   * `P7_detail.png` (Insert/Detalhe: olhos, mãos ou cicatriz)
3. Salve na pasta `02_visual_bible/characters/@antonio/`. **Marque como LOCKED.**

---

### Passo 3 — Decupagem da Cena e Geração da Ficha "Copiar e Colar"
1. Selecione o trecho da cena (ex: Cena 01).
2. O smixs processa o texto e preenche a **Cartela de 14 campos** (sem adjetivos subjetivos, apenas ações físicas e luz).
3. O DirectorSKILL calcula o **Eixo de Ação (180°)**, a lente em mm (ex: 50mm) e fatia o trecho em **micro-beats de 3 a 6 segundos**.
4. **Geração Automática do Caderno:** O sistema gera o arquivo `04_shots/CADERNO_EXECUCAO_SC01.md`.
   * Esse documento contém cada plano mastigado com caixas de texto prontas: qual imagem carregar, o prompt exato para colar no site de vídeo (Kling/Runway/Veo) e o texto para colar no site de voz (ElevenLabs/Edge-TTS).

---

### Passo 4 — Geração da Locução e Pacing (Áudio-First)
1. Dispare a geração da voz neural para os micro-beats (ou copie o texto da ficha e cole no site de sua preferência).
2. O sistema mede a duração exata da fala e ajusta o plano de vídeo:
   * *Exemplo:* Fala durou 3.4s ➔ Plano de vídeo configurado para 4.2s (com respiro).
3. Salve os áudios em `05_audio/SC01_SH01_voice.mp3`.

---

### Passo 5 — Execução no Motor (Kling / Runway / Veo)
* **Se você for usar a Web (navegador):**
  1. Abra o arquivo `04_shots/CADERNO_EXECUCAO_SC01.md`.
  2. Para o **Plano 01**:
     * Suba a imagem indicada (ex: `P1_front.png`).
     * Copie o prompt positivo da ficha e cole no campo de prompt do site.
     * Copie o prompt negativo e cole no site.
     * Ajuste os controles de câmera (ex: Zoom `+2.0`).
     * Clique em Gerar.
  3. Baixe o vídeo gerado (`SC01_SH01.mp4`).
  4. Extraia o último frame (ou tire print do último segundo) e use como imagem inicial do **Plano 02**!

---

### Passo 6 — Montagem no CapCut Desktop
1. O script montador organiza todos os clipes de vídeo e arquivos de locução sincronizados.
2. Abra o projeto no CapCut Desktop.
3. Adicione a trilha musical de fundo e ative as legendas automáticas.
4. Exporte o vídeo final em 1080p ou 4K!
