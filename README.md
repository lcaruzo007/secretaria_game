# ☕ Muzambinho Coffee Run — Operação Café Quente

Jogo 2D feito em Python com Pygame, ambientado no IF Muzambinho. A proposta mistura exploração curta, corrida contra o tempo e interação com personagens do ambiente administrativo da escola.

## Sobre o projeto

Este projeto foi pensado como um pequeno jogo de coleta e entrega, com clima de speedrun e estética de corredor escolar. O jogador começa no menu inicial, entra na partida e percorre a área do jogo enquanto encontra NPCs com falas temáticas dos setores administrativos.

O jogo já possui uma base organizada em classes, separando a lógica principal da janela, do jogador e dos NPCs. Isso facilita evoluir o projeto depois para incluir objetivos, tempo, colisões, itens e outras telas.

## História e objetivo

Você controla um estagiário da Secretaria Acadêmica. A missão é buscar o café na **Copa do Administrativo** e entregar na **Secretaria** o mais rápido possível, tentando não ser interrompido pelos colegas dos setores ao longo do caminho.

O tom é leve e humorístico, usando frases inspiradas no dia a dia administrativo do campus.

## O que já existe no jogo

- Menu inicial com visual próprio e botão de entrada.
- Tela principal com navegação por teclado.
- Jogador com sprite animado e direção de movimento.
- NPCs posicionados no cenário com falas diferentes.
- Detecção de proximidade entre jogador e NPC.
- Estrutura pronta para ampliar a interação e o fluxo do jogo.

## Mecânicas atuais

| Mecânica | Descrição |
|---|---|
| **Menu inicial** | Tela de abertura com o título do jogo e instruções básicas |
| **Movimento** | Controle por WASD ou setas direcionais |
| **NPCs** | Personagens posicionados em pontos fixos do mapa |
| **Interação** | Quando o jogador se aproxima de um NPC, o sistema reconhece a proximidade |
| **Diálogos** | Cada setor tem uma lista de frases próprias |
| **Loop do jogo** | Estrutura clássica de eventos, atualização e desenho na tela |

## Controles

```text
W / ↑       -> Mover para cima
S / ↓       -> Mover para baixo
A / ←       -> Mover para esquerda
D / →       -> Mover para direita
ENTER       -> Iniciar o jogo a partir do menu
ESC         -> Sair do jogo
```

## Fluxo da aplicação

1. O programa inicia em `src/main.py`.
2. A classe `Game` é criada e configura a janela do Pygame.
3. O jogo abre no menu inicial.
4. Ao iniciar a partida, o loop desenha a cena principal.
5. O jogador se move, os NPCs aparecem e a lógica de proximidade pode ser usada para interação.

## Estrutura do projeto

```text
secretaria_game/
|
|-- src/
|   |-- main.py          # Ponto de entrada da aplicação
|   |-- game.py          # Loop principal, telas, eventos e renderização
|   |-- player.py        # Lógica do personagem controlado pelo jogador
|   |-- npc.py           # Lógica dos personagens não jogáveis
|   |-- settings.py      # Constantes globais do jogo
|   `-- __init__.py
|
|-- assets/
|   |-- data/
|   |   `-- banco.sql    # Base de dados/estrutura futura do projeto
|   |-- fonts/
|   `-- images/          # Sprites, logos e imagens do jogo
|
|-- requirements.txt
`-- README.md
```

## Como executar

### 1. Pré-requisitos

- Python 3.10 ou superior
- Ambiente virtual recomendado

### 2. Instalar dependências

```bash
pip install -r requirements.txt
```

### 3. Rodar o jogo

```bash
python src/main.py
```

## Arquitetura do código

O projeto usa uma divisão simples por responsabilidade:

- `Game` centraliza a janela, os estados da interface e o game loop.
- `Player` concentra a movimentação, animação e sprite do personagem controlado.
- `NPC` concentra posição, imagem e falas de cada personagem do cenário.
- `settings.py` guarda constantes de resolução, cores, caminhos e título da aplicação.

Essa separação deixa o código mais fácil de manter e ajuda a crescer o projeto sem misturar tudo em um único arquivo.

## Conceitos de programação aplicados

- **Orientação a Objetos (POO):** cada entidade do jogo tem sua própria classe.
- **Game Loop:** o jogo segue o ciclo eventos -> atualização -> desenho.
- **Sprites e animação:** o jogador usa sprite sheet e troca de frames.
- **Colisão por distância:** NPCs usam distância euclidiana para detectar proximidade.
- **Organização por módulos:** a lógica está separada em arquivos pequenos e reutilizáveis.

## Recursos gráficos e assets

O projeto usa imagens armazenadas em `assets/images`. Se algum arquivo não estiver disponível, o código tenta continuar com superfícies simples para evitar quebra imediata da execução.

Os principais recursos esperados hoje são:

- `logo.png` para o menu.
- `player.png` para o personagem principal.
- Sprites dos setores, como `rh.png`, `gabinete.png`, `nti.png` e `ascom.png`.

## Estado atual e próximos passos

Hoje o projeto já serve como base jogável e visual para o início da experiência. Ainda há espaço para evoluir para a proposta completa de speedrun, adicionando:

- objetivo de buscar e entregar o café;
- cronômetro de tempo;
- sistema de pontuação e recorde local;
- colisão com paredes e obstáculos;
- feedback visual e sonoro de interação;
- telas de vitória e derrota.

## Requisitos técnicos

- Resolução: 1280 x 720 pixels
- FPS alvo: 60
- Biblioteca gráfica: Pygame

## Público-alvo

O projeto é ideal para estudo de:

- Pygame e renderização 2D;
- organização de código em camadas;
- controle de personagem e animação;
- prototipagem de jogo casual com humor local.


preciso de um cenário