# Instagram Scraper V2 (Avançado com Login)

Este script avança na extração de dados utilizando a própria conta do usuário. Na primeira vez, ele pede para você logar na página do Instagram. Nos acessos seguintes, usará a sessão salva para evitar relogamentos.
Ele busca coletar fotos, vídeos, stories (se visíveis) e também dados numéricos mais completos e reais sem bloqueio agressivo.

**AVISO**: O Instagram é muito agressivo na proteção de dados e automação logada pode causar advertências ou restrições no seu perfil. Use por sua conta e risco. Extrações em massa completas (milhares de seguidores ou mensagens de chat) são pesadamente bloqueadas por limitações de rede no front-end, mas o script fará um "best effort" para puxar o visível. Mensagens (Directs) necessitam acessar outra parte do sistema. Esse script foca no Perfil do usuário. O projeto salva imagens e thumbnails, visto que vídeos não são trivialmente capturados pela estrutura do DOM (blob url).

## Como abrir
- Instale o **Python 3** (https://www.python.org/downloads/) certificando-se de marcar a opção "Add python.exe to PATH" durante a instalação.
- Dê um duplo clique no arquivo `iniciar.bat` (no Windows) ou `iniciar.command` (no macOS, lembre-se de clicar com botão direito e escolher "Abrir" na primeira vez).

Os dados coletados serão salvos de forma organizada na pasta `dados`, sendo gerada uma subpasta para cada perfil.
