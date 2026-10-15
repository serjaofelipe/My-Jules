import os
import platform
import subprocess
import psutil
import cpuinfo

def bytes_to_gb(bytes_value):
    return round(bytes_value / (1024 ** 3), 2)

def print_separator(title):
    print(f"\n{'=' * 50}")
    print(f" {title.upper()} ".center(50, "="))
    print(f"{'=' * 50}")

def get_os_info():
    print_separator("Sistema Operacional")
    print(f"Sistema: {platform.system()}")
    print(f"Versão: {platform.version()}")
    print(f"Release: {platform.release()}")
    print(f"Arquitetura: {platform.machine()}")

def get_cpu_info():
    print_separator("Processador (CPU)")
    try:
        info = cpuinfo.get_cpu_info()
        print(f"Modelo: {info.get('brand_raw', 'Desconhecido')}")
    except Exception as e:
        print(f"Modelo: Erro ao obter modelo ({e})")

    print(f"Núcleos Físicos: {psutil.cpu_count(logical=False)}")
    print(f"Núcleos Lógicos: {psutil.cpu_count(logical=True)}")
    print(f"Uso Atual da CPU: {psutil.cpu_percent(interval=1)}%")

def get_ram_info():
    print_separator("Memória RAM")
    ram = psutil.virtual_memory()
    print(f"Total: {bytes_to_gb(ram.total)} GB")
    print(f"Disponível: {bytes_to_gb(ram.available)} GB")
    print(f"Em Uso: {bytes_to_gb(ram.used)} GB")
    print(f"Porcentagem de Uso: {ram.percent}%")

def get_disk_info():
    print_separator("Discos / Armazenamento")
    partitions = psutil.disk_partitions()
    for partition in partitions:
        print(f"Disco: {partition.device}")
        print(f"  Ponto de Montagem: {partition.mountpoint}")
        print(f"  Sistema de Arquivos: {partition.fstype}")
        try:
            usage = psutil.disk_usage(partition.mountpoint)
            print(f"  Total: {bytes_to_gb(usage.total)} GB")
            print(f"  Usado: {bytes_to_gb(usage.used)} GB")
            print(f"  Livre: {bytes_to_gb(usage.free)} GB")
            print(f"  Uso (%): {usage.percent}%")
        except PermissionError:
            print("  Acesso negado para ler detalhes de uso deste disco.")
        print("-" * 30)

def get_gpu_info():
    print_separator("Placa de Vídeo (GPU)")
    sys_name = platform.system()
    gpus = []

    try:
        if sys_name == "Windows":
            output = subprocess.check_output(
                ["wmic", "path", "win32_VideoController", "get", "name"],
                text=True, stderr=subprocess.DEVNULL
            )
            lines = output.strip().split('\n')[1:]
            gpus = [line.strip() for line in lines if line.strip()]

        elif sys_name == "Darwin":
            output = subprocess.check_output(
                ["system_profiler", "SPDisplaysDataType"],
                text=True, stderr=subprocess.DEVNULL
            )
            for line in output.split('\n'):
                if "Chipset Model" in line or "Modelo do Chipset" in line:
                    gpus.append(line.split(":")[1].strip())

        elif sys_name == "Linux":
            output = subprocess.check_output(
                ["lspci"],
                text=True, stderr=subprocess.DEVNULL
            )
            for line in output.split('\n'):
                if "VGA" in line or "3D" in line or "Display" in line:
                    parts = line.split(":")
                    if len(parts) >= 3:
                        gpus.append(parts[-1].strip())
    except Exception as e:
        gpus.append(f"Erro ao detectar GPU: {e}")

    if gpus:
        for i, gpu in enumerate(gpus, 1):
            print(f"GPU {i}: {gpu}")
    else:
        print("Nenhuma GPU dedicada detectada ou não foi possível identificar o modelo.")

def main():
    if os.environ.get("MODO_TESTE") == "1":
        print("Executando em MODO_TESTE (modo de segurança ativado para validação sem intervenção manual).")

    get_os_info()
    get_cpu_info()
    get_ram_info()
    get_disk_info()
    get_gpu_info()

    print("\nAnálise concluída!")
    if os.environ.get("MODO_TESTE") != "1":
        # Evita travar para sempre, mas espera input de usuario se rodado direto num cmd
        print("Pressione ENTER para sair...")
        try:
            input()
        except:
            pass

if __name__ == "__main__":
    main()
