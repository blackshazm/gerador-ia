# Padrão: Caderno de Execução da Cena ("Copiar e Colar")
## Modelo Oficial de Ficha de Produção para Operação Manual em Sites

**Objetivo:** Permitir que qualquer pessoa pegue os dados gerados pelo pipeline e execute diretamente nas interfaces web de qualquer ferramenta (Kling AI, Runway, Luma, Veo, ElevenLabs, etc.) com simples ações de **Copiar e Colar (Ctrl+C / Ctrl+V)**, sem depender de linhas de comando ou APIs.

---

## Estrutura Obrigatória por Cena

Toda cena processada pela Tríade deve gerar automaticamente o arquivo consolidado:  
`04_shots/CADERNO_EXECUCAO_CENA_XX.md`

Dentro desse arquivo, cada micro-beat é apresentado em uma **caixa individual pronta para execução**:

---

# Exemplo Real de Ficha: Cena 01 — "O Encontro Diante da Porta"

### 📌 Resumo da Cena
* **ID:** `SC-01`
* **Locação:** Rua escura diante de portão de ferro enferrujado
* **Personagem Principal:** `@antonio`
* **Total de Planos:** 3 planos (Duração total estimada: 14 segundos)

---

## 🎬 PLANO 01 (Duração: 5 segundos) — Plano Geral de Atmosfera

### 1. No site de Voz / Narração (ElevenLabs / Edge-TTS):
> **Texto para Locução (Copie e cole):**  
> ```text
> A noite caía pesada sobre a rua deserta quando Antônio parou diante do velho portão de ferro.
> ```

### 2. No site de Vídeo (Kling AI / Runway / Veo):
* **Imagem de Entrada (Start Frame):** Carregar arquivo `Visual_Bible/@antonio/P1_front.png`
* **Controles de Câmera no Site:**
  * Zoom: `+2.0` (Aproximação suave)
  * Pan / Horizontal / Vertical: `0`
* **Prompt Positivo (Copie e cole):**
  ```text
  Cinematic wide establishing shot, 35mm lens, damp dark street at night, Antonio standing in front of a rusty iron gate, street lamp casting cold 5600K side light, fine mist on wet asphalt, slow camera push-in, 24fps movie look, photorealistic, film grain.
  ```
* **Prompt Negativo (Copie e cole):**
  ```text
  cartoon, 3d render, smiling, bright daylight, bad anatomy, deformed hands, face mutation, blurry, watermark, oversaturated.
  ```

---

## 🎬 PLANO 02 (Duração: 4 segundos) — Plano Médio / Tensão Física

### 1. No site de Voz / Narração:
> **Texto para Locução (Copie e cole):**  
> ```text
> Sua mão tocou o ferrolho gelado. Ele hesitou.
> ```

### 2. No site de Vídeo:
* **Imagem de Entrada (Start Frame):** ⚠️ **ATENÇÃO:** Carregar o **Último Frame extraído do Plano 01** (`SC01_SH01_last.png`) para manter 100% de continuidade sem quebra de roupa ou iluminação!
* **Controles de Câmera no Site:**
  * Horizontal / Pan: `0`
  * Zoom: `+1.5`
* **Prompt Positivo (Copie e cole):**
  ```text
  Eye-level medium shot, 50mm lens, Antonio's hand freezing on the cold iron latch, jaw clenching, eyes darting sideways, maintaining exact clothing and cold lighting from previous frame, tense atmosphere, photorealistic, cinematic lighting.
  ```
* **Prompt Negativo (Copie e cole):**
  ```text
  cartoon, 3d render, deformed fingers, extra limbs, smiling, bright light, low quality.
  ```

---

## 🎬 PLANO 03 (Duração: 5 segundos) — Close-Up / Reação nos Olhos

### 1. No site de Voz / Narração:
> **Texto para Locução (Copie e cole):**  
> ```text
> Do segundo andar da casa em frente, uma luz amarelada acendeu-se de repente.
> ```

### 2. No site de Vídeo:
* **Imagem de Entrada (Start Frame):** Carregar `Visual_Bible/@antonio/P2_3q_left.png` ou o último frame do Plano 02.
* **Controles de Câmera no Site:**
  * Tilt (Cima): `+2.5` (Câmera ergue levemente acompanhando o olhar)
  * Zoom: `0`
* **Prompt Positivo (Copie e cole):**
  ```text
  Intense close-up, 85mm lens at f/2.0 shallow depth of field, Antonio's eyes lifting diagonally toward a sudden warm amber 2800K light reflection, jaw muscles tight, cold rain drops on his cheek, cinematic drama, ultra-realistic 35mm film look.
  ```
* **Prompt Negativo (Copie e cole):**
  ```text
  cartoon, plastic skin, distorted eyes, blurry, text, watermark, bad lighting.
  ```

---

## ✂️ Na Ilha de Edição (CapCut / Premiere)
1. Arraste os 3 vídeos gerados na ordem: `Plano 01` ➔ `Plano 02` ➔ `Plano 03`.
2. Arraste os 3 áudios de locução abaixo de cada plano respectivo.
3. Coloque um efeito sonoro (SFX) de chuva leve contínua ao fundo.
4. **Pronto! A cena está montada.**
