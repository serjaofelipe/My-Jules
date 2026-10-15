// Instala as dependências se preciso, inicia o servidor e abre o navegador.
import { spawn, spawnSync } from "node:child_process";
import { existsSync, realpathSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const PORTA = 5173;
const COMANDO_DEV = `npm run dev -- --port ${PORTA} --strictPort`;
const URL_APP = `http://localhost:${PORTA}`;

// realpath troca caminhos curtos do Windows (ex.: SERGIO~1) pelo real; o Vite bloqueia os curtos.
const raiz = realpathSync.native(join(dirname(fileURLToPath(import.meta.url)), ".."));
const win = process.platform === "win32";

// Checa um executável, não só a pasta: um install que falhou no meio deixa node_modules incompleto.
const binario = join(raiz, "node_modules", ".bin", win ? "vite.cmd" : "vite");
if (!existsSync(binario)) {
  console.log("Instalando dependencias (so na primeira vez, pode demorar)...");
  const r = spawnSync("npm install", { cwd: raiz, stdio: "inherit", shell: true });
  if (r.status !== 0) {
    console.error("[ERRO] Falha ao instalar dependencias. Apague a pasta node_modules e tente de novo.");
    process.exit(1);
  }
}

console.log(`Iniciando em ${URL_APP} (feche esta janela para parar)`);
const servidor = spawn(COMANDO_DEV, { cwd: raiz, stdio: "inherit", shell: true });
servidor.on("exit", (codigo) => process.exit(codigo ?? 1));

if (!process.env.SEM_NAVEGADOR) {
  const inicio = Date.now();
  const tentar = async () => {
    try {
      await fetch(URL_APP);
      abrirNavegador(URL_APP);
    } catch {
      if (Date.now() - inicio < 60000) setTimeout(tentar, 500);
    }
  };
  tentar();
}

function abrirNavegador(url) {
  const [cmd, args] = win
    ? ["cmd", ["/c", "start", "", url]]
    : process.platform === "darwin" ? ["open", [url]] : ["xdg-open", [url]];
  spawn(cmd, args, { stdio: "ignore", detached: true }).on("error", () => {});
}