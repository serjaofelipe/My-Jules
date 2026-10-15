# Analisador de Hardware

Este projeto é um script em Python que analisa e exibe informações sobre o hardware e o sistema operacional da sua máquina, incluindo uso de CPU, memória RAM, discos e detalhes da GPU.

## Como abrir

1. Certifique-se de ter o Python 3 instalado. Você pode baixar em [python.org](https://www.python.org/downloads/). Durante a instalação no Windows, marque a opção "Add python.exe to PATH".
2. Dê um duplo clique no arquivo `iniciar.bat` (se estiver no Windows) ou `iniciar.command` (se estiver no macOS). No Mac, na primeira vez que for abrir, pode ser necessário clicar com o botão direito e selecionar "Abrir" caso o sistema bloqueie o script.
3. O script irá instalar as dependências necessárias automaticamente na primeira execução e exibir as informações do seu computador no terminal.

## Decisões tomadas

- Optei por utilizar as bibliotecas `psutil` e `py-cpuinfo` para garantir compatibilidade multiplataforma ao coletar dados de CPU, RAM e Discos.
- Para obter informações da GPU, utilizo comandos nativos do sistema operacional (`wmic` no Windows, `system_profiler` no macOS e `lspci`/`lshw` no Linux) no lugar de bibliotecas extras, garantindo que o programa funcione sem requerer compilação de pacotes nativos (C/C++) ou drivers complexos (como o do pynvml que seria focado só em NVIDIA).
