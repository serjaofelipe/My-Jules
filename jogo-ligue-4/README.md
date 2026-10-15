# Jogo Ligue 4

Um jogo de Ligue 4 interativo construído com React e Vite, permitindo jogar com 2 jogadores locais ou 1 jogador contra a CPU. Apresenta uma interface imersiva com fundo animado de ondas do oceano e peças em design tridimensional.

## Como abrir
1. Instale a versão mais recente e recomendada (LTS) do [Node.js](https://nodejs.org/).
2. Se você estiver no **Windows**, dê um duplo clique no arquivo `iniciar.bat`.
3. Se você estiver no **macOS**, dê um duplo clique no arquivo `iniciar.command` (na primeira vez, talvez seja necessário clicar com o botão direito sobre o arquivo e escolher "Abrir").
4. A página do jogo será aberta no seu navegador, conectando-se a `http://localhost:5173`.

## Fontes de Dados
O jogo não necessita e não consome dados reais externos, portanto, informações coletadas da internet não se aplicam e dados externos podem ser considerados "dado indisponível".

## Decisões Tomadas
- O algoritmo Minimax com poda alfa-beta foi implementado para criar uma inteligência artificial moderadamente desafiadora, e uma profundidade de pesquisa igual a 5 foi selecionada para garantir jogadas instantâneas sem travar a interface e o navegador.
- Foi implementado um atraso ("timeout") na jogada da CPU, para proporcionar a sensação visual de que o "computador está pensando".
