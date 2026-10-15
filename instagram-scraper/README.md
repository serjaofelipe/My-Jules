# Instagram Scraper

Um script que abre uma interface gráfica para você digitar o perfil do Instagram, coleta os dados usando o Playwright e tira screenshots.

Como o Instagram bloqueia bots constantemente e exige login em boa parte das vezes, os dados (seguidores, publicações, etc) tentamos coletar do Picuki (ou via Playwright direto no Instagram, que na maioria das vezes redireciona para login e impede a coleta de números). Se não for possível acessar sem login, será salvo como "dado indisponível", conforme a regra do repositório (não inventar dados). A screenshot será salva de qualquer forma se conseguirmos abrir o navegador.

## Como abrir
- Instale o **Python 3** (https://www.python.org/downloads/) certificando-se de marcar a opção "Add python.exe to PATH" durante a instalação.
- Dê um duplo clique no arquivo `iniciar.bat` (no Windows) ou `iniciar.command` (no macOS, lembre-se de clicar com botão direito e escolher "Abrir" na primeira vez).

Os resultados e as screenshots ficarão armazenados na pasta `dados`.
