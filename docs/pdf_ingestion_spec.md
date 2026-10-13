# Especificação Técnica do Módulo 0: Ingestão de PDF, Limpeza e Tradução
## Pipeline da Tríade — Camada de Processamento Literário

**Versão:** 1.0.0  
**Status:** Aprovado para Implementação  
**Escopo:** Transformar arquivos PDF (em Português ou Inglês) em Markdown (.md) estruturado, limpo de artefatos gráficos e segmentado em cenas dramáticas.

---

## 1. O Problema da Ingestão de Livros em PDF

Livros em PDF contêm três classes de ruído que corrompem a interpretação de LLMs e pipelines generativos:
1. **Artefatos de Paginação:** Cabeçalhos recorrentes (nome do autor/título no topo), números de páginas no rodapé e notas de rodapé intercaladas no meio do texto.
2. **Quebras de Linha Duras (Hard Line Breaks):** Textos justificados em PDF contêm quebras `\n` ao final de cada linha visual, partindo frases no meio.
3. **Hifens de Separação Silábica:** Palavras quebradas ao final da linha (ex: `co- / nhecido`) que se tornam palavras inexistentes se não forem reconstituídas.

---

## 2. Pipeline de Processamento em 4 Etapas

```
[PDF Bruto]
    │
    ▼ 1. Extração Estruturada (pdfplumber)
[Blocos de Texto com Coordenadas Bounding Box]
    │
    ▼ 2. Filtragem de Ruído (Remoção de Header/Footer & Hifens)
[Texto Bruto Contínuo]
    │
    ▼ 3. Detecção de Idioma & Tradução Contextual
[Markdown Normalizado em Português Literário]
    │
    ▼ 4. Detector de Quebras de Cena (Scene Splitter)
[Capítulos e Cenas Numeradas (SC_01.json, SC_02.json...)]
```

---

## 3. Algoritmo de Limpeza e Higienização

### 3.1 Remoção Geométrica de Cabeçalho e Rodapé
Utilizando extração com coordenadas de caixa delimitadora:
- **Margem Superior (Header Cutoff):** Qualquer linha localizada nos primeiros 8% do topo da página é descartada (exceto início de capítulo).
- **Margem Inferior (Footer Cutoff):** Qualquer linha nos últimos 7% do rodapé da página (típico de número de página) é descartada.

### 3.2 Reconstituição de Parágrafos e Hifens
- Expressão regular para união de hifens silábicos:  
  `r'(\b\w+)-\s*\n\s*(\w+\b)' ➔ r'\1\2'`
- Unificação de quebras duras: linhas que não terminam com pontuação final (`.`, `!`, `?`, `:"`, `—`) têm o `\n` substituído por um espaço simples.

---

## 4. Normalização de Idioma e Tradução Literária

Se o livro estiver em **Inglês**:
1. **Mapeamento de Entidades Pré-Tradução:**
   - Nomes de personagens, famílias e locações são extraídos para uma tabela de invariantes (ex: `John Doe` não vira `João Ninguém`).
2. **Tom e Estilo Literário:**
   - A tradução deve manter o tom literário da narrativa, sem adaptações modernas ou gírias.
3. **Dicionário de Tags (@Tags):**
   - Criação de tags automáticas: `@antonio`, `@helena`, `@mansao_abandonada`.

---

## 5. Algoritmo de Detecção de Quebra de Cena (Scene Splitter)

Uma cena é formalmente definida por:
$$\text{Cena} = \text{Mesma Locação} \times \text{Mesmo Período de Tempo} \times \text{Ação Contínua}$$

O parser de cena monitora marcadores no texto:
* **Marcadores Explícitos:** Quebras de asteriscos (`***`), números de cena ou subtítulos.
* **Marcadores Semânticos de Tempo:** *"Na manhã seguinte"*, *"Horas depois"*, *"Ao anoitecer"*.
* **Marcadores Semânticos de Espaço:** *"Ele entrou na carruagem"*, *"Ao cruzar o portão"*, *"Chegando à biblioteca"*.

Ao detectar um marcador, fecha-se a `Cena N` e abre-se a `Cena N+1`.

---

## 6. Exemplo de Script de Referência (Python)

```python
import re
import pdfplumber

def sanitize_pdf_to_markdown(pdf_path: str, output_md_path: str):
    full_text = []
    
    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages):
            width = page.width
            height = page.height
            
            # Corta cabeçalho (top 8%) e rodapé (bottom 7%)
            crop_box = (0, height * 0.08, width, height * 0.93)
            cropped_page = page.crop(crop_box)
            text = cropped_page.extract_text(layout=False)
            
            if not text:
                continue
                
            # Corrige quebras de hifenização
            text = re.sub(r'(\b\w+)-\s*\n\s*(\w+\b)', r'\1\2', text)
            
            # Unifica quebras de linha no meio de frases
            text = re.sub(r'(?<![.!?—:])\n(?!\n)', ' ', text)
            
            full_text.append(text)
            
    normalized_content = "\n\n".join(full_text)
    
    with open(output_md_path, "w", encoding="utf-8") as f:
        f.write(normalized_content)
        
    print(f"Livro processado com sucesso: {output_md_path}")
```
