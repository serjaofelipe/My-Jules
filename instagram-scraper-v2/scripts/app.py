"""A J A X G R A M: janela para escolher o que puxar de um perfil do Instagram.

A coleta em si é o coletar_dados.py, rodado como processo separado: a saída
dele aparece ao vivo no log da janela (e fica salva em dados/<perfil>/ultima_coleta.log),
e o botão "parar" encerra o processo e o navegador que ele abriu.
"""

import json
import os
import queue
import subprocess
import sys
import threading
import time
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk
from tkinter import font as tkfont

RAIZ = Path(__file__).resolve().parent.parent
SCRIPT_COLETA = RAIZ / "scripts" / "coletar_dados.py"
ASSETS = RAIZ / "scripts" / "assets"
PASTA_DADOS = RAIZ / "dados"
ARQUIVO_ESTADO = PASTA_DADOS / "estado_login.json"
PREFERENCIAS = PASTA_DADOS / "ajaxgram.json"

APP_NAME = "A J A X G R A M"

# (chave do coletar_dados.py, texto na janela, explicação)
OPCOES = [
    ("posts", "posts", "fotos e vídeos do feed"),
    ("reels", "reels", "vídeos da aba reels"),
    ("stories", "stories", "stories ativos agora"),
    ("destaques", "destaques", "todos os destaques"),
    ("seguidores", "seguidores", "lista de quem segue o perfil"),
    ("seguindo", "seguindo", "lista de quem o perfil segue"),
    ("depara", "de-para", "quem não segue de volta (usa as duas listas)"),
]

# ---------------------------------------------------------------- tema (cores do Instagram, modo escuro)

GRADIENTE = ["#FEDA75", "#FA7E1E", "#D62976", "#962FBF", "#4F5BD5"]
C = {
    "bg": "#000000",
    "panel": "#121212",
    "field": "#0a0a0a",
    "border": "#363636",
    "fg": "#f5f5f5",
    "dim": "#a8a8a8",
    "pink": "#E1306C",
    "pink_dark": "#4a1024",
    "orange": "#FA7E1E",
    "yellow": "#FEDA75",
    "purple": "#962FBF",
    "blue": "#0095F6",
    "red": "#ED4956",
    "green": "#58C322",
    "select": "#3a1426",
}
MONO_CANDIDATES = ("Cascadia Mono", "Cascadia Code", "JetBrains Mono", "Fira Code",
                   "Consolas", "Menlo", "Monaco", "Courier New")


def misturar(c1, c2, t):
    a = [int(c1[i:i + 2], 16) for i in (1, 3, 5)]
    b = [int(c2[i:i + 2], 16) for i in (1, 3, 5)]
    return "#" + "".join(f"{round(x + (y - x) * t):02x}" for x, y in zip(a, b))


def cor_no_gradiente(t):
    """Cor na posição t (0..1) do degradê do Instagram."""
    t = min(max(t, 0.0), 1.0) * (len(GRADIENTE) - 1)
    i = min(int(t), len(GRADIENTE) - 2)
    return misturar(GRADIENTE[i], GRADIENTE[i + 1], t - i)


def pick_mono(root):
    available = set(tkfont.families(root))
    return next((f for f in MONO_CANDIDATES if f in available), "Courier")


def dark_title_bar(win):
    """Barra de título escura no Windows 10/11 (ignora em outros sistemas)."""
    if sys.platform != "win32":
        return
    try:
        import ctypes
        win.update_idletasks()
        hwnd = ctypes.windll.user32.GetParent(win.winfo_id())
        on = ctypes.c_int(1)
        for attr in (20, 19):  # DWMWA_USE_IMMERSIVE_DARK_MODE (19 nas versões antigas do Win10)
            if ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, attr, ctypes.byref(on), ctypes.sizeof(on)) == 0:
                break
    except Exception:  # noqa: BLE001 - só estética
        pass


def setup_style(root, mono):
    root.configure(bg=C["bg"])
    st = ttk.Style(root)
    st.theme_use("clam")
    base = (mono, 10)
    st.configure(".", background=C["bg"], foreground=C["fg"], font=base,
                 bordercolor=C["border"], lightcolor=C["border"], darkcolor=C["border"],
                 troughcolor=C["bg"], focuscolor=C["pink"], selectbackground=C["select"],
                 selectforeground=C["fg"], insertcolor=C["pink"])
    st.configure("TFrame", background=C["bg"])
    st.configure("Panel.TFrame", background=C["panel"])
    st.configure("TLabel", background=C["bg"], foreground=C["fg"])
    st.configure("Dim.TLabel", foreground=C["dim"])
    st.configure("Prompt.TLabel", foreground=C["pink"])
    st.configure("Status.TLabel", background=C["panel"], foreground=C["dim"])
    st.configure("TButton", background=C["panel"], foreground=C["fg"], padding=(12, 6),
                 bordercolor=C["border"], focusthickness=0, font=base)
    st.map("TButton",
           background=[("disabled", C["bg"]), ("pressed", C["pink_dark"]), ("active", "#1f1f1f")],
           foreground=[("disabled", C["dim"])],
           bordercolor=[("active", C["pink"])])
    st.configure("Accent.TButton", background=C["pink"], foreground="#ffffff",
                 bordercolor=C["pink"], font=(mono, 10, "bold"))
    st.map("Accent.TButton",
           background=[("disabled", C["pink_dark"]), ("pressed", "#b0204f"), ("active", "#f0507f")],
           foreground=[("disabled", C["dim"])])
    st.configure("Stop.TButton", foreground=C["red"])
    st.map("Stop.TButton", bordercolor=[("active", C["red"])], foreground=[("disabled", C["dim"])])
    st.configure("TCheckbutton", background=C["bg"], foreground=C["fg"], indicatorbackground=C["field"],
                 indicatorforeground="#ffffff", indicatorcolor=C["field"], focusthickness=0,
                 font=(mono, 11, "bold"))
    st.map("TCheckbutton", background=[("active", C["bg"])],
           indicatorcolor=[("selected", C["pink"])], foreground=[("active", C["pink"]), ("disabled", C["dim"])])
    st.configure("TEntry", fieldbackground=C["field"], foreground=C["fg"], insertcolor=C["pink"],
                 bordercolor=C["border"], padding=6)
    st.map("TEntry", bordercolor=[("focus", C["pink"])], lightcolor=[("focus", C["pink"])])
    st.configure("Vertical.TScrollbar", background=C["panel"], troughcolor=C["field"],
                 bordercolor=C["field"], arrowcolor=C["dim"], gripcount=0, relief="flat")
    st.map("Vertical.TScrollbar", background=[("active", C["pink_dark"])])


def terminal_text(parent, mono, height=10, size=10):
    """Caixa de texto escura com barra de rolagem do tema."""
    box = tk.Frame(parent, bg=C["border"], padx=1, pady=1)
    inner = tk.Frame(box, bg=C["field"])
    inner.pack(fill="both", expand=True)
    text = tk.Text(inner, height=height, wrap="word", font=(mono, size), bg=C["field"], fg=C["fg"],
                   insertbackground=C["pink"], selectbackground=C["select"], selectforeground=C["fg"],
                   relief="flat", borderwidth=0, padx=10, pady=8, highlightthickness=0)
    bar = ttk.Scrollbar(inner, orient="vertical", command=text.yview)
    text.configure(yscrollcommand=bar.set)
    bar.pack(side="right", fill="y")
    text.pack(side="left", fill="both", expand=True)
    return box, text


def open_path(path):
    if sys.platform == "win32":
        os.startfile(path)  # noqa: S606 - abre no Explorer
    elif sys.platform == "darwin":
        subprocess.Popen(["open", str(path)])
    else:
        subprocess.Popen(["xdg-open", str(path)])


def python_de_console():
    """python.exe ao lado do pythonw.exe (a janela pode ter sido aberta com pythonw)."""
    exe = Path(sys.executable)
    if exe.stem.lower() == "pythonw":
        alt = exe.with_name("python.exe" if sys.platform == "win32" else "python")
        if alt.exists():
            return str(alt)
    return str(exe)


# ---------------------------------------------------------------- UI


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.mono = pick_mono(self)
        setup_style(self, self.mono)
        self.title(APP_NAME)
        self.geometry("820x780")
        self.minsize(640, 620)
        self._icone()
        dark_title_bar(self)

        self.proc = None
        self.log_file = None
        self.perfil_atual = None
        self.inicio = 0.0
        self._linhas = queue.Queue()
        self._spin = 0

        prefs = self._ler_prefs()
        self.perfil_var = tk.StringVar(value=prefs.get("perfil", ""))
        marcadas = set(prefs.get("opcoes", [k for k, *_ in OPCOES]))
        self.vars = {k: tk.BooleanVar(value=k in marcadas) for k, *_ in OPCOES}

        self._build_header()
        self._build_form()
        self._build_log()
        self._build_statusbar()
        self._atualizar_login()
        self.protocol("WM_DELETE_WINDOW", self.fechar)
        self.after(100, self._drenar)
        self.after(150, self._animar)
        self.entry.focus_set()

    # ------------------------------------------------ moldura

    def _icone(self):
        self.logo = None
        try:
            if sys.platform == "win32" and (ASSETS / "instagram.ico").exists():
                self.iconbitmap(default=str(ASSETS / "instagram.ico"))
            png = tk.PhotoImage(file=str(ASSETS / "instagram.png"))
            self.logo = png.subsample(2, 2)  # 96px -> 48px
            if sys.platform != "win32":
                self.iconphoto(True, png)
        except (tk.TclError, OSError):
            pass

    def _build_header(self):
        head = tk.Frame(self, bg=C["bg"])
        head.pack(fill="x", padx=18, pady=(16, 0))
        if self.logo:
            tk.Label(head, image=self.logo, bg=C["bg"]).pack(side="left", padx=(0, 12))
        titulo = tk.Frame(head, bg=C["bg"])
        titulo.pack(side="left")
        letras = tk.Frame(titulo, bg=C["bg"])
        letras.pack(anchor="w")
        # Cada letra numa cor do degradê do Instagram.
        visiveis = [ch for ch in APP_NAME if ch != " "]
        n = 0
        for ch in APP_NAME:
            if ch == " ":
                tk.Label(letras, text=" ", font=(self.mono, 22, "bold"), bg=C["bg"]).pack(side="left")
                continue
            tk.Label(letras, text=ch, font=(self.mono, 24, "bold"), bg=C["bg"],
                     fg=cor_no_gradiente(n / max(len(visiveis) - 1, 1))).pack(side="left")
            n += 1
        tk.Label(titulo, text="// coletor de perfis do instagram", font=(self.mono, 9),
                 fg=C["dim"], bg=C["bg"]).pack(anchor="w")

        info = tk.Frame(head, bg=C["bg"])
        info.pack(side="right", anchor="e")
        self.login_label = tk.Label(info, text="", font=(self.mono, 9), bg=C["bg"])
        self.login_label.pack(anchor="e")
        self.trocar_btn = tk.Label(info, text="[ trocar conta ]", font=(self.mono, 9), fg=C["dim"],
                                   bg=C["bg"], cursor="hand2")
        self.trocar_btn.pack(anchor="e")
        self.trocar_btn.bind("<Button-1>", lambda e: self.trocar_conta())
        chrome_btn = tk.Label(info, text="[ login do chrome ]", font=(self.mono, 9), fg=C["dim"],
                              bg=C["bg"], cursor="hand2")
        chrome_btn.pack(anchor="e")
        chrome_btn.bind("<Button-1>", lambda e: self.login_do_chrome())

        # Linha em degradê embaixo do título.
        self.faixa = tk.Canvas(self, height=3, bg=C["bg"], highlightthickness=0)
        self.faixa.pack(fill="x", padx=18, pady=(10, 0))
        self.faixa.bind("<Configure>", self._pintar_faixa)

    def _pintar_faixa(self, event):
        self.faixa.delete("all")
        w = max(event.width, 1)
        passo = 4
        for x in range(0, w, passo):
            self.faixa.create_rectangle(x, 0, x + passo, 3, width=0, fill=cor_no_gradiente(x / w))

    def _build_form(self):
        frm = ttk.Frame(self, padding=(18, 14, 18, 0))
        frm.pack(fill="x")

        ttk.Label(frm, text="> perfil alvo_", style="Prompt.TLabel").pack(anchor="w")
        linha = ttk.Frame(frm)
        linha.pack(fill="x", pady=(4, 14))
        tk.Label(linha, text="@", font=(self.mono, 14, "bold"), fg=C["pink"], bg=C["bg"]).pack(side="left",
                                                                                            padx=(0, 6))
        self.entry = ttk.Entry(linha, textvariable=self.perfil_var, font=(self.mono, 12))
        self.entry.pack(side="left", fill="x", expand=True)
        self.entry.bind("<Return>", lambda e: self.coletar())

        topo = ttk.Frame(frm)
        topo.pack(fill="x")
        ttk.Label(topo, text="> o que puxar_", style="Prompt.TLabel").pack(side="left")
        for texto, valor in (("[ nenhum ]", False), ("[ todos ]", True)):
            b = tk.Label(topo, text=texto, font=(self.mono, 9), fg=C["dim"], bg=C["bg"], cursor="hand2")
            b.pack(side="right", padx=(8, 0))
            b.bind("<Button-1>", lambda e, v=valor: self.marcar_todos(v))

        grade = tk.Frame(frm, bg=C["border"], padx=1, pady=1)
        grade.pack(fill="x", pady=(6, 0))
        dentro = tk.Frame(grade, bg=C["bg"], padx=12, pady=8)
        dentro.pack(fill="both", expand=True)
        dentro.columnconfigure(0, weight=1)
        dentro.columnconfigure(1, weight=1)
        self.checks = {}
        for i, (chave, texto, ajuda) in enumerate(OPCOES):
            cel = tk.Frame(dentro, bg=C["bg"])
            # de-para ocupa a linha inteira no fim.
            if chave == "depara":
                cel.grid(row=i // 2 + 1, column=0, columnspan=2, sticky="w", pady=(6, 2))
            else:
                cel.grid(row=i // 2, column=i % 2, sticky="w", pady=2)
            cb = ttk.Checkbutton(cel, text=texto, variable=self.vars[chave],
                                 command=lambda k=chave: self._ao_marcar(k))
            cb.pack(anchor="w")
            tk.Label(cel, text=ajuda, font=(self.mono, 8), fg=C["dim"], bg=C["bg"]).pack(anchor="w", padx=(22, 0))
            self.checks[chave] = cb

        btns = ttk.Frame(frm)
        btns.pack(fill="x", pady=(14, 0))
        self.coletar_btn = ttk.Button(btns, text="▶ COLETAR", style="Accent.TButton", command=self.coletar)
        self.coletar_btn.pack(side="left")
        self.parar_btn = ttk.Button(btns, text="■ parar", style="Stop.TButton", command=self.parar,
                                    state="disabled")
        self.parar_btn.pack(side="left", padx=8)
        ttk.Button(btns, text="[ abrir pasta ]", command=self.abrir_pasta).pack(side="right")

    def _build_log(self):
        frm = ttk.Frame(self, padding=(18, 12, 18, 10))
        frm.pack(fill="both", expand=True)
        ttk.Label(frm, text="> log_", style="Prompt.TLabel").pack(anchor="w")
        box, self.log = terminal_text(frm, self.mono, size=9)
        box.pack(fill="both", expand=True, pady=(4, 0))
        self.log.configure(state="disabled", cursor="arrow")
        m = self.mono
        self.log.tag_configure("etapa", foreground=C["pink"], font=(m, 9, "bold"))
        self.log.tag_configure("aviso", foreground=C["orange"])
        self.log.tag_configure("erro", foreground=C["red"], font=(m, 9, "bold"))
        self.log.tag_configure("ok", foreground=C["green"], font=(m, 9, "bold"))
        self.log.tag_configure("info", foreground=C["purple"])
        self.log.tag_configure("dim", foreground=C["dim"])
        self.escrever("pronto. digite o perfil, marque o que quer puxar e clique em ▶ COLETAR.", "dim")

    def _build_statusbar(self):
        bar = ttk.Frame(self, style="Panel.TFrame", padding=(14, 4))
        bar.pack(side="bottom", fill="x")
        self.statusbar = ttk.Label(bar, text="pronto", style="Status.TLabel")
        self.statusbar.pack(side="left")
        ttk.Label(bar, text="enter » coletar", style="Status.TLabel").pack(side="right")

    # ------------------------------------------------ opções

    def _ao_marcar(self, chave):
        # O de-para precisa das duas listas: marcar um marca as outras, desmarcar uma lista desmarca o de-para.
        if chave == "depara" and self.vars["depara"].get():
            self.vars["seguidores"].set(True)
            self.vars["seguindo"].set(True)
        elif chave in ("seguidores", "seguindo") and not self.vars[chave].get():
            self.vars["depara"].set(False)

    def marcar_todos(self, valor):
        if self.proc:
            return
        for v in self.vars.values():
            v.set(valor)

    def escolhidas(self):
        return [k for k, *_ in OPCOES if self.vars[k].get()]

    def _ler_prefs(self):
        try:
            return json.loads(PREFERENCIAS.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}

    def _salvar_prefs(self):
        try:
            PASTA_DADOS.mkdir(exist_ok=True)
            PREFERENCIAS.write_text(json.dumps({"perfil": self.perfil_var.get().strip(),
                                                "opcoes": self.escolhidas()}, indent=2), encoding="utf-8")
        except OSError:
            pass

    def _atualizar_login(self):
        if ARQUIVO_ESTADO.exists():
            self.login_label.configure(text="● sessão salva", fg=C["green"])
        else:
            self.login_label.configure(text="○ sem login (vai abrir o navegador)", fg=C["orange"])

    def trocar_conta(self):
        if self.proc:
            return
        if not ARQUIVO_ESTADO.exists():
            messagebox.showinfo(APP_NAME, "Nenhuma sessão salva. Na próxima coleta o navegador abre para você logar.")
            return
        if messagebox.askyesno(APP_NAME, "Apagar a sessão salva?\nNa próxima coleta o navegador abre para "
                                         "você logar de novo (pode ser outra conta)."):
            ARQUIVO_ESTADO.unlink(missing_ok=True)
            self._atualizar_login()
            self.escrever("sessão apagada: na próxima coleta você loga de novo.", "aviso")

    def login_do_chrome(self):
        """Escolhe um perfil do Chrome e importa o login do Instagram dele."""
        if self.proc:
            return
        sys.path.insert(0, str(SCRIPT_COLETA.parent))
        from coletar_dados import perfis_do_chrome
        perfis = perfis_do_chrome()
        if not perfis:
            messagebox.showerror(APP_NAME, "Não achei o Google Chrome instalado neste computador.")
            return

        win = tk.Toplevel(self, bg=C["bg"])
        win.title(f"{APP_NAME} · login do chrome")
        win.geometry("560x360")
        win.transient(self)
        dark_title_bar(win)
        ttk.Label(win, text="> de qual perfil do Chrome puxar o login do Instagram?_",
                  style="Prompt.TLabel").pack(anchor="w", padx=14, pady=(12, 2))
        ttk.Label(win, text="feche o Chrome antes: aberto, ele trava os cookies.",
                  style="Dim.TLabel").pack(anchor="w", padx=14, pady=(0, 6))
        moldura = tk.Frame(win, bg=C["border"], padx=1, pady=1)
        moldura.pack(fill="both", expand=True, padx=14)
        lb = tk.Listbox(moldura, font=(self.mono, 10), bg=C["field"], fg=C["fg"], borderwidth=0,
                        highlightthickness=0, selectbackground=C["select"], selectforeground=C["pink"],
                        activestyle="none")
        lb.pack(fill="both", expand=True)
        for pasta, nome, email in perfis:
            lb.insert("end", f" {nome:<18} {email or '(sem conta Google)':<32} {pasta}")

        def importar(_=None):
            sel = lb.curselection()
            if not sel:
                return
            pasta, nome, _email = perfis[sel[0]]
            win.destroy()
            self.log.configure(state="normal")
            self.log.delete("1.0", "end")
            self.log.configure(state="disabled")
            self.escrever(f"» importando o login do Instagram do perfil '{nome}' do Chrome...", "etapa")
            self._rodar(["--importar-chrome", pasta], f"login do chrome ({nome})")

        lb.bind("<Double-Button-1>", importar)
        lb.bind("<Return>", importar)
        ttk.Button(win, text="▶ IMPORTAR", style="Accent.TButton", command=importar).pack(pady=12)
        lb.focus_set()

    # ------------------------------------------------ log

    def escrever(self, texto, tag=None):
        no_fim = self.log.yview()[1] > 0.98
        self.log.configure(state="normal")
        self.log.insert("end", texto + "\n", tag)
        self.log.configure(state="disabled")
        if no_fim:
            self.log.see("end")

    @staticmethod
    def _tag_da_linha(linha):
        baixa = linha.lower()
        if "erro" in baixa or "traceback" in baixa or "falha" in baixa or "exception" in baixa:
            return "erro"
        if "[aviso]" in baixa or "429" in baixa or "incompleta" in baixa or "bloqueou" in baixa:
            return "aviso"
        if "sucesso" in baixa or "salvos em" in baixa or "salva!" in baixa:
            return "ok"
        if linha.startswith(("Baixando", "Extraindo", "Acessando")):
            return "etapa"
        if linha.startswith("  "):
            return "dim"
        return "info" if linha.startswith(("Sessao", "Autenticacao", "Login", "Aguardando")) else None

    # ------------------------------------------------ coleta

    def coletar(self):
        if self.proc:
            return
        perfil = self.perfil_var.get().strip().lstrip("@").strip()
        if "instagram.com/" in perfil:  # aceita o link do perfil também
            perfil = perfil.split("instagram.com/", 1)[1].split("/")[0].split("?")[0]
            self.perfil_var.set(perfil)
        if not perfil:
            messagebox.showwarning(APP_NAME, "Digite o perfil (sem @).")
            self.entry.focus_set()
            return
        opcoes = self.escolhidas()
        self._salvar_prefs()

        pasta = PASTA_DADOS / perfil
        pasta.mkdir(parents=True, exist_ok=True)
        try:
            self.log_file = open(pasta / "ultima_coleta.log", "w", encoding="utf-8")
        except OSError:
            self.log_file = None

        self.log.configure(state="normal")
        self.log.delete("1.0", "end")
        self.log.configure(state="disabled")
        nomes = ", ".join(t for k, t, _ in OPCOES if k in opcoes) or "só os dados do perfil"
        self.escrever(f"» coletando @{perfil}: {nomes}", "etapa")
        if not ARQUIVO_ESTADO.exists():
            self.escrever("» o navegador vai abrir para você logar. Faça o login até o fim.", "aviso")

        self._rodar([perfil, "--so", ",".join(opcoes)], f"@{perfil}")

    def _rodar(self, argumentos, rotulo):
        """Roda o coletar_dados.py com estes argumentos, mostrando a saída no log."""
        env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUNBUFFERED="1")
        cmd = [python_de_console(), "-u", str(SCRIPT_COLETA), *argumentos]
        try:
            self.proc = subprocess.Popen(
                cmd, cwd=RAIZ, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL, text=True, encoding="utf-8", errors="replace",
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        except OSError as e:
            self.proc = None
            self.escrever(f"não consegui iniciar a coleta: {e}", "erro")
            return

        self.perfil_atual = rotulo
        self.inicio = time.time()
        self._travar(True)
        threading.Thread(target=self._ler_saida, args=(self.proc,), daemon=True).start()

    def _ler_saida(self, proc):
        for linha in proc.stdout:
            self._linhas.put(("linha", linha.rstrip("\r\n")))
        self._linhas.put(("fim", proc.wait()))

    def _drenar(self):
        try:
            while True:
                tipo, valor = self._linhas.get_nowait()
                if tipo == "linha":
                    if self.log_file:
                        self.log_file.write(valor + "\n")
                        self.log_file.flush()
                    self.escrever(valor, self._tag_da_linha(valor))
                else:
                    self._terminou(valor)
        except queue.Empty:
            pass
        self.after(100, self._drenar)

    def _terminou(self, codigo):
        duracao = int(time.time() - self.inicio)
        tempo = f"{duracao // 60}min {duracao % 60:02d}s"
        if self.proc is None:  # parado pelo botão
            pass
        elif codigo == 0:
            self.escrever(f"\n✓ concluído em {tempo}.", "ok")
            self.statusbar.configure(text=f"concluído » {self.perfil_atual} em {tempo}")
        else:
            self.escrever(f"\n! terminou com avisos (código {codigo}) em {tempo}. "
                          "Veja as linhas em laranja/vermelho acima.", "aviso")
            self.statusbar.configure(text=f"terminou com avisos » {self.perfil_atual}")
        if self.log_file:
            self.log_file.close()
            self.log_file = None
        self.proc = None
        self._travar(False)
        self._atualizar_login()
        self.bell()

    def parar(self):
        proc = self.proc
        if not proc:
            return
        if not messagebox.askyesno(APP_NAME, "Parar a coleta agora?\nO que já foi baixado fica salvo."):
            return
        self.proc = None
        self._encerrar(proc)
        self.escrever("\n■ coleta parada por você.", "aviso")
        self.statusbar.configure(text="parado")

    @staticmethod
    def _encerrar(proc):
        # /T leva junto o navegador que o Playwright abriu.
        if sys.platform == "win32":
            subprocess.run(["taskkill", "/PID", str(proc.pid), "/T", "/F"], capture_output=True,
                           creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        else:
            proc.terminate()

    def _travar(self, rodando):
        estado = "disabled" if rodando else "normal"
        self.coletar_btn.configure(state=estado)
        self.parar_btn.configure(state="normal" if rodando else "disabled")
        self.entry.configure(state=estado)
        for cb in self.checks.values():
            cb.configure(state=estado)

    def _animar(self):
        if self.proc:
            frames = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
            self._spin = (self._spin + 1) % len(frames)
            dur = int(time.time() - self.inicio)
            self.statusbar.configure(text=f"{frames[self._spin]} rodando » {self.perfil_atual} » "
                                          f"{dur // 60:02d}:{dur % 60:02d}")
        self.after(120, self._animar)

    def abrir_pasta(self):
        perfil = self.perfil_var.get().strip().lstrip("@")
        pasta = PASTA_DADOS / perfil if perfil and (PASTA_DADOS / perfil).exists() else PASTA_DADOS
        pasta.mkdir(exist_ok=True)
        open_path(pasta)

    def fechar(self):
        if self.proc:
            if not messagebox.askyesno(APP_NAME, "Uma coleta está rodando. Parar e fechar?"):
                return
            proc, self.proc = self.proc, None
            self._encerrar(proc)
        self._salvar_prefs()
        self.destroy()


if __name__ == "__main__":
    App().mainloop()
