# Instagram Scraper V2 (Avançado com Login)

Este script avança na extração de dados utilizando a própria conta do usuário. Na primeira vez, ele pede para você logar na página do Instagram. Nos acessos seguintes, usará a sessão salva para evitar relogamentos.
Ele busca coletar fotos, vídeos, stories (se visíveis) e também dados numéricos mais completos e reais sem bloqueio agressivo.

**AVISO**: O Instagram é muito agressivo na proteção de dados e automação logada pode causar advertências ou restrições no seu perfil. Use por sua conta e risco. Extrações em massa completas (milhares de seguidores ou mensagens de chat) são pesadamente bloqueadas por limitações de rede no front-end, mas o script fará um "best effort" para puxar o visível. Mensagens (Directs) necessitam acessar outra parte do sistema. Esse script foca no Perfil do usuário. O projeto baixa os arquivos originais de fotos (.jpg) e vídeos (.mp4) de posts, reels, stories e destaques em `dados/<perfil>/`; os arquivos .json guardam só dados de texto (histórico do perfil, seguidores, seguindo, legendas e datas).

## Como abrir
- Instale o **Python 3** (https://www.python.org/downloads/) certificando-se de marcar a opção "Add python.exe to PATH" durante a instalação.
- Dê um duplo clique no arquivo `iniciar.bat` (no Windows) ou `iniciar.command` (no macOS, lembre-se de clicar com botão direito e escolher "Abrir" na primeira vez).

Abre a janela do **AJAXGRAM**: digite o perfil, marque o que quer puxar (posts, reels, stories, destaques, seguidores, seguindo e o de-para) e clique em **▶ COLETAR**. Posts e reels vêm todos por padrão. O andamento aparece no log da janela e o botão **■ parar** encerra a coleta.

**Gerenciar contas** (botão no canto): adicione, renomeie, remova e escolha a conta ativa. Com mais de uma conta, ao puxar seguidores/seguindo o AJAXGRAM começa pela ativa e, se não fechar o total, junta as outras contas somando só os usuários novos (ajuda em perfis de terceiros, que o Instagram limita por conta). Usar várias contas aumenta o risco de bloqueio — é por sua conta e risco.

**de-para: +contas**: compara perfis **já coletados**. Marque 2 ou mais e ele gera `dados/Merge-<perfis>/comparativo.xlsx` com o que têm em comum, o que é exclusivo de cada um e quem um segue e o outro não.

Os dados são salvos em `dados/<perfil>/`: as mídias em subpastas e os .json de texto em `Logs_json`; a planilha estilizada em `Followers_Docs`. O log da última coleta fica em `dados/<perfil>/ultima_coleta.log`.

Também dá para rodar sem a janela: `python scripts/coletar_dados.py <perfil> --so posts,destaques,depara`, comparar com `python scripts/gerar_comparativo.py <perfil1> <perfil2>` e adicionar uma conta com `python scripts/coletar_dados.py --login-conta "Nome"`.
