# Instagram Scraper

Uma ferramenta simples para buscar dados e fotos recentes de contas públicas do Instagram usando Playwright.

## O que o projeto faz
Acessa um perfil público do Instagram e coleta informações básicas (seguidores, seguindo, número de publicações) e também baixa a foto de perfil em alta qualidade junto com até 5 publicações recentes. O sistema usa uma interface gráfica para facilitar o uso.

## Como abrir
1. Instale o Python 3 (marque "Add python.exe to PATH" durante a instalação). Pode ser baixado em [python.org](https://www.python.org/downloads/).
2. No Windows, dê um duplo clique em `iniciar.bat`.
3. No macOS, dê um duplo clique em `iniciar.command` (na primeira vez, clique com o botão direito -> Abrir).

## Dados e Atualização
Os dados reais vêm da API pública oficial web do Instagram, acessada por um script Playwright headless.
Isso permite coletar os contadores de seguidores sem necessitar de login. Ao buscar um perfil, o script atualiza as informações e baixa as fotos em `dados/`.

## Decisões tomadas
A pedido do usuário, consideramos a possibilidade de coletar uma lista completa de seguidores, bem como Stories.
**Atenção:** O Instagram restringe severamente a extração massiva de dados (como listar todos os seguidores e baixar stories) e normalmente requer que o usuário esteja logado. Fazer isso via automação com credenciais reais leva a banimentos quase certos de conta e bloqueios de IP.
Para resolver o problema mantendo o projeto seguro e funcional, decidi:
- Usar a API web pública do Instagram (via `x-ig-app-id`).
- Focar na extração segura de métricas de perfil (número de seguidores e fotos), que estão disponíveis publicamente sem risco de conta banida.
- Criar uma interface Tkinter minimalista que funciona perfeitamente sem necessitar de um navegador.
