Repare que incluí as diretrizes técnicas exatas que extraímos das plataformas para que a IA entenda perfeitamente o rigor do seu projeto.   

Atue como um Gerente de Produto Sênior e Especialista em Fluxos de Trabalho de IA para Cinema.
Preciso que você escreva um Documento de Requisitos do Produto (PRD) completo, técnico e profissional para um pipeline de pré-produção e geração de vídeo automatizado.

Objetivo do Projeto:
Criar um fluxo de trabalho integrado (a "Tríade") que receba um livro literário em formato Markdown (.md), processe a narrativa aplicando regras matemáticas e físicas de direção cinematográfica, e gere prompts técnicos estruturados para renderizar vídeos fotorrealistas no Google Flow, finalizando na ilha de edição.

O Stack de Ferramentas (Lógica e Papéis):

CineGen (A Mesa de Trabalho e o Cofre Visual): Operando localmente, ele fará a ingestão do .md e isolará personagens e cenários usando marcações (@Tags). Ele brilha ao criar a "Bíblia Visual", gerando automaticamente 7 painéis de ângulos de referência (frente, perfil, costas, detalhe) para cada ator. Isso garantirá que o rosto do personagem nunca sofra "face-drift" durante os cortes.   

smixs/visual-skills (A Filosofia e o Filtro de Roteiro): Será a regra de entrada. Ele proíbe a IA de usar adjetivos subjetivos (ex: "ele está triste") e a obriga a escrever fatos físicos graváveis (ex: "luz fria, mandíbula travada"). Ele brilha garantindo que toda cena obedeça à "Fórmula da Cena" (desejo + obstáculo + geometria + rastro ocular + ritmo) e preencha uma cartela restritiva de 14 campos.   

DirectorSKILL (O Cérebro Matemático): Rodando via modelo Claude, ele pega a cena filtrada pelo smixs e assume a direção de fotografia. Ele brilha selecionando a lente física exata (ex: 24mm, 50mm, 85mm), aplicando a Regra dos 180 graus (para os atores não mudarem de lado na tela), avaliando o motivo do movimento de câmera e formatando pacotes de prompts exatos para a máquina de difusão de vídeo.   

Google Flow (O Motor) & Editor: O Google Flow (modelo Veo) receberá a direção fotográfica perfeita do DirectorSKILL e os rostos trancados do CineGen para renderizar o vídeo. O resultado vai para a linha do tempo do Premiere/CapCut.

Estrutura Exigida para o PRD:
Escreva o documento de forma técnica, voltada à engenharia de produção. Inclua:

Resumo Executivo e Visão do Produto: Qual problema de consistência de IA estamos resolvendo.

Arquitetura do Sistema: Como a informação viaja entre o CineGen (Visual), smixs (Teoria) e DirectorSKILL (Matemática).

Fluxo de Trabalho de Produção (Passo a Passo):

Passo 1: Ingestão e Trancamento Visual (CineGen).

Passo 2: Conversão Literária e Cartela de Plano (smixs).

Passo 3: Decupagem e Lógica Direcional (DirectorSKILL).

Passo 4: Formatação de Prompt Estrito de Movimento.

Passo 5: Renderização e Pós-Produção.

Requisitos de Continuidade e Geometria: Como mitigaremos falhas espaciais e de rastro ocular (eye-trace).

Critérios de Sucesso e KPIs: Como mediremos o sucesso da automação da pré-produção até a edição final.

Basta copiar o texto acima e enviar para o modelo da sua escolha. Ele já contém a arquitetura lógica e os jargões necessários para gerar um PRD de altíssimo nível. Se precisar de mais algum ajuste na estrutura, é só avisar!

Coloque aqui links dos repositórios para acessar todos e a logica ideograma

Aqui estão os links diretos para os repositórios oficiais no GitHub que estruturam esse projeto:

CineGen: https://github.com/christopherjohnogden/CineGen

[cite: 1]

smixs/visual-skills: https://github.com/smixs/visual-skills

[cite: 2]

DirectorSKILL: https://github.com/wuwangzhang1216/DirectorSKILL

[cite: 3]

ShotBench / ShotVL (A IA de 7B para análise fotográfica): https://github.com/Vchitect/ShotBench

[cite: 4]

Sobre a "lógica de ideograma" (ou fluxograma/diagrama visual) para você anexar ao seu documento PRD ou desenhar em ferramentas de arquitetura (como Miro, Draw.io ou Whimsical), a estrutura de como a informação viaja no sistema funciona exatamente assim:

(Início) Livro em formato Markdown (.md)
↓
CineGen (Estágio de Ingestão Visual)
↳ Processo: A IA lê o texto e mapeia quem é quem.
↳ Saída Lateral: Cria o Banco de Referências (7 ângulos do rosto de cada ator).
↓
smixs/visual-skills (Estágio de Filtro Literário)
↳ Processo: Pega os blocos do livro e remove qualquer adjetivo invisível (ex: pensamentos do personagem).
↳ Saída: Transforma o trecho em uma Cartela de Plano focada estritamente na física, geometria espacial e cenário.
↓
DirectorSKILL (Estágio de Matemática de Câmera)
↳ Processo: Recebe o texto físico e atua como o Diretor de Fotografia. Calcula a lógica espacial, não quebra o eixo (Regra dos 180 graus) e define a lente (ex: 50mm, 85mm).
↳ Saída: Pacote de Prompts formatados com códigos de movimento de máquina.
↓
Google Flow / Modelo Veo (Estágio de Renderização)
↳ Inputs Recebidos: Rosto trancado do CineGen + Prompt Matemático do DirectorSKILL.
↳ Saída: Clipes curtos de vídeo perfeitamente direcionados e fotorrealistas.
↓
(Fim) Linha do Tempo do Editor de Vídeo (Montagem e Áudio)