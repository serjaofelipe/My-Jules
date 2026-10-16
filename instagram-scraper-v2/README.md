# Instagram Scraper V2 (Avançado com Login)

Este script avança na extração de dados utilizando a própria conta do usuário. Na primeira vez, ele pede para você logar na página do Instagram. Nos acessos seguintes, usará a sessão salva para evitar relogamentos.
Ele busca coletar fotos, vídeos, stories (se visíveis) e também dados numéricos mais completos e reais sem bloqueio agressivo.

**AVISO**: O Instagram é muito agressivo na proteção de dados e automação logada pode causar advertências ou restrições no seu perfil. Use por sua conta e risco. Extrações em massa completas (milhares de seguidores ou mensagens de chat) são pesadamente bloqueadas por limitações de rede no front-end, mas o script fará um "best effort" para puxar o visível. Mensagens (Directs) necessitam acessar outra parte do sistema. Esse script foca no Perfil do usuário. O projeto baixa os arquivos originais de fotos (.jpg) e vídeos (.mp4) de posts, reels, stories e destaques em `dados/<perfil>/`; os arquivos .json guardam só dados de texto (histórico do perfil, seguidores, seguindo, legendas e datas).

## Como abrir
- Instale o **Python 3** (https://www.python.org/downloads/) certificando-se de marcar a opção "Add python.exe to PATH" durante a instalação.
- Dê um duplo clique no arquivo `iniciar.bat` (no Windows) ou `iniciar.command` (no macOS, lembre-se de clicar com botão direito e escolher "Abrir" na primeira vez).

Abre a janela do **AJAXGRAM**: digite o perfil, marque o que quer puxar (posts, reels, stories, destaques, seguidores, seguindo e o de-para) e clique em **▶ COLETAR**. O andamento aparece no log da janela; o botão **■ parar** encerra a coleta e **[ trocar conta ]** apaga a sessão salva para logar de novo.

Os dados coletados serão salvos de forma organizada na pasta `dados`, sendo gerada uma subpasta para cada perfil. O log da última coleta fica em `dados/<perfil>/ultima_coleta.log`.

Também dá para rodar sem a janela: `python scripts/coletar_dados.py <perfil> --so posts,destaques,depara`.
