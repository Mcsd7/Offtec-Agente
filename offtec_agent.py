#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OFFTEC Agent v1.0
Agente de IA local para Android/Termux (Ollama, 100% offline).

Instalação:
    pkg install python ollama
    pip install rich
    ollama serve &                      # em outra sessão do Termux
    ollama pull llama3.2:1b-instruct-q4_K_M
    python offtec_agent.py
"""
import json
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text
    from rich.syntax import Syntax
    from rich.prompt import Confirm
    from rich import box
except ImportError:
    print("Falta a biblioteca rich. Rode: pip install rich")
    sys.exit(1)

VERSION = "1.0"
MODEL = os.environ.get("OFFTEC_MODEL", "llama3.2:1b-instruct-q4_K_M")
HOST = os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434")
if not HOST.startswith("http"):
    HOST = "http://" + HOST
WORKSPACE = Path(os.environ.get("OFFTEC_WORKSPACE", Path(__file__).resolve().parent / "workspace")).expanduser()
WORKSPACE.mkdir(parents=True, exist_ok=True)
MAX_ROUNDS = 4          # quantas voltas ação -> resultado -> modelo
MAX_HISTORY = 24        # mensagens mantidas no contexto
EXEC_TIMEOUT = 30       # segundos

# linguagens suportadas: realce de sintaxe, execução e detecção de programa interativo
LEXERS = {".py": "python", ".sh": "bash", ".c": "c", ".html": "html", ".txt": "text",
          ".css": "css", ".js": "javascript", ".md": "markdown"}
RUNNABLE = {".py", ".sh", ".c"}
RE_INTERACTIVE = {
    ".py": re.compile(r"input\("),
    ".sh": re.compile(r"(?m)(^\s*|[;&|]\s*)read\s"),
    ".c": re.compile(r"\b(scanf|getchar|fgets|gets|getline)\s*\("),
}

console = Console()

# ───────────────────────── Visual ─────────────────────────

BANNER_BIG = r"""
 ██████╗ ███████╗███████╗████████╗███████╗ ██████╗
██╔═══██╗██╔════╝██╔════╝╚══██╔══╝██╔════╝██╔════╝
██║   ██║█████╗  █████╗     ██║   █████╗  ██║
██║   ██║██╔══╝  ██╔══╝     ██║   ██╔══╝  ██║
╚██████╔╝██║     ██║        ██║   ███████╗╚██████╗
 ╚═════╝ ╚═╝     ╚═╝        ╚═╝   ╚══════╝ ╚═════╝
""".strip("\n").split("\n")

BANNER_SMALL = [
    "╔═╗╔═╗╔═╗╔╦╗╔═╗╔═╗",
    "║ ║╠╣ ╠╣  ║ ║╣ ║  ",
    "╚═╝╚  ╚   ╩ ╚═╝╚═╝",
]

GRADIENT = ["#00e5ff", "#00b8ff", "#5c8dff", "#9a6bff", "#c85bff", "#ff4fd8"]


def gradient_banner(lines):
    out = Text()
    for i, line in enumerate(lines):
        color = GRADIENT[min(i * len(GRADIENT) // max(len(lines), 1), len(GRADIENT) - 1)]
        out.append(line + "\n", style=f"bold {color}")
    return out


def ollama_status():
    """Retorna (online, modelo_instalado)."""
    try:
        with urllib.request.urlopen(HOST + "/api/tags", timeout=3) as r:
            data = json.load(r)
        names = [m.get("name", "") for m in data.get("models", [])]
        return True, any(n == MODEL or n.startswith(MODEL.split(":")[0] + ":" + MODEL.split(":")[-1]) for n in names) or MODEL in names
    except Exception:
        return False, False


def splash():
    console.clear()
    width = console.size.width
    banner = BANNER_BIG if width >= 56 else BANNER_SMALL
    console.print()
    console.print(gradient_banner(banner), justify="center")
    console.print(
        Text(f"A G E N T   v{VERSION}", style="bold white"), justify="center"
    )
    console.print(
        Text("IA local • offline • sem chave de API", style="italic #8a8fa3"),
        justify="center",
    )
    console.print()

    online, has_model = ollama_status()
    ok = "[bold green]●[/] online"
    bad = "[bold red]●[/] offline"
    status = ok if online else bad
    model_status = "[bold green]✔[/] pronto" if has_model else "[bold yellow]![/] não encontrado"

    info = Table.grid(padding=(0, 2))
    info.add_column(style="bold #5c8dff", no_wrap=True)
    info.add_column()
    info.add_row("Ollama", status)
    info.add_row("Modelo", f"{MODEL}")
    info.add_row("", model_status)
    info.add_row("Pasta", str(WORKSPACE))
    info.add_row("Segurança", "confirma antes de criar/executar")

    cmds = Table.grid(padding=(0, 2))
    cmds.add_column(style="bold #c85bff", no_wrap=True)
    cmds.add_column(style="#c9cdd8")
    cmds.add_row("/ajuda", "lista de comandos")
    cmds.add_row("/criar <arq> <desc>", "py sh c html txt")
    cmds.add_row("/app <nome> <desc>", "cria um app (pasta)")
    cmds.add_row("/editar <arq|pasta>", "abre no vim/nano")
    cmds.add_row("/ls", "arquivos da pasta")
    cmds.add_row("/ler <arq>", "mostra um arquivo")
    cmds.add_row("/rodar <arq>", "executa .py .sh .c")
    cmds.add_row("/limpar", "zera a conversa")
    cmds.add_row("/sair", "encerra")

    if width >= 90:
        grid = Table.grid(expand=True)
        grid.add_column(ratio=1)
        grid.add_column(ratio=1)
        grid.add_row(
            Panel(info, title="[bold]Sistema[/]", border_style="#5c8dff", box=box.ROUNDED),
            Panel(cmds, title="[bold]Comandos[/]", border_style="#c85bff", box=box.ROUNDED),
        )
        console.print(grid)
    else:
        console.print(Panel(info, title="[bold]Sistema[/]", border_style="#5c8dff", box=box.ROUNDED))
        console.print(Panel(cmds, title="[bold]Comandos[/]", border_style="#c85bff", box=box.ROUNDED))

    if not online:
        console.print(
            Panel(
                "O Ollama não respondeu. Em outra sessão do Termux rode:\n"
                "[bold]ollama serve[/]",
                border_style="red",
                title="Atenção",
            )
        )
    elif not has_model:
        console.print(
            Panel(
                f"Baixe o modelo com:\n[bold]ollama pull {MODEL}[/]",
                border_style="yellow",
                title="Atenção",
            )
        )
    console.print(
        Text("Peça algo, por exemplo: “crie um script que calcula fatorial e teste”", style="italic #8a8fa3"),
        justify="center",
    )
    console.print()


# ───────────────────────── Modelo ─────────────────────────

SYSTEM_PROMPT = f"""Você é o OFFTEC Agent, um assistente de programação que roda localmente no Android (Termux).
Responda sempre em português, de forma curta e direta.
Você trabalha dentro de uma pasta de trabalho. Para agir, use EXATAMENTE estas marcas, cada uma em sua própria linha:

[[CRIAR nome.py]]
(conteúdo completo do arquivo)
[[FIM]]

[[LER nome.py]]
[[EXEC nome.py]]
[[LISTAR]]

Exemplo correto (o nome vai DENTRO dos colchetes e o código fica entre CRIAR e FIM):
[[CRIAR soma.py]]
a = int(input("a: "))
b = int(input("b: "))
print(a + b)
[[FIM]]

Regras:
- Faça UMA ação por resposta e nunca repita marcas.
- Depois de [[EXEC]] ou [[LER]], PARE de escrever e espere o resultado. Nunca invente resultados.
- Use as marcas só quando for realmente criar, ler, executar ou listar.
- Nunca coloque o conteúdo do arquivo dentro de ``` ao usar [[CRIAR]].
- Só execute arquivos .py, .sh ou .c. Nomes de arquivo sem espaços e sem pastas.
- Depois de [[EXEC]] você receberá o resultado; analise-o e diga se passou ou o que corrigir.
- Para testar, crie um arquivo de teste simples (assert/print) e execute.
"""

RE_CRIAR = re.compile(r"\[\[CRIAR\s+([^\]\s]+)\]\]\s*\n(.*?)(?=\[\[FIM\]\]|\[\[(?:CRIAR|LER|EXEC|LISTAR)|\Z)", re.S)
# fim da ação: o modelo deve parar aqui e esperar o resultado (evita resultados inventados)
RE_STOP = re.compile(
    r"\[\[FIM\]\]|\[\[LISTAR\]\]|\[\[(?:EXEC|LER) [\w.\-]+\]\]|\[\[(?:EXEC|LER)\]\] *[\w.\-]+[ \t]*\n"
)
RE_LER = re.compile(r"\[\[LER\s+([^\]\s]+)\]\]")
RE_EXEC = re.compile(r"\[\[EXEC\s+([^\]\s]+)\]\]")
RE_LISTAR = re.compile(r"\[\[LISTAR\]\]")


def is_looping(text):
    """Detecta resposta repetitiva (modelo pequeno travado em loop)."""
    counts = {}
    for ln in text.splitlines():
        ln = ln.strip()
        if re.match(r"\[\[(CRIAR|LER|EXEC|LISTAR|FIM)", ln):
            limit = 4
        elif len(ln) > 12:
            limit = 8
        else:
            continue
        counts[ln] = counts.get(ln, 0) + 1
        if counts[ln] >= limit:
            return True
    return False


LAST = {"truncated": False}  # a última resposta foi cortada (limite ou loop)?


def chat_stream(messages, num_predict=700):
    """Faz streaming da resposta do Ollama e devolve o texto completo."""
    payload = json.dumps(
        {
            "model": MODEL,
            "messages": messages,
            "stream": True,
            "options": {"temperature": 0.2, "num_ctx": 4096, "num_predict": num_predict, "repeat_penalty": 1.2},
        }
    ).encode()
    req = urllib.request.Request(
        HOST + "/api/chat", data=payload, headers={"Content-Type": "application/json"}
    )
    full = []
    LAST["truncated"] = False
    try:
        with urllib.request.urlopen(req, timeout=300) as resp:
            for raw in resp:
                if not raw.strip():
                    continue
                chunk = json.loads(raw)
                piece = chunk.get("message", {}).get("content", "")
                if piece:
                    full.append(piece)
                    console.print(piece, end="", markup=False, highlight=False, style="#e6e9f2")
                    joined = "".join(full)
                    m_stop = RE_STOP.search(joined)
                    if m_stop:
                        full = [joined[: m_stop.end()]]
                        break
                    if "\n" in piece and is_looping(joined):
                        console.print("\n[yellow]⚠ Resposta repetitiva, interrompi.[/]")
                        LAST["truncated"] = True
                        break
                if chunk.get("done"):
                    if chunk.get("done_reason") == "length":
                        LAST["truncated"] = True
                    break
    except urllib.error.URLError:
        console.print("\n[red]Não consegui falar com o Ollama. Ele está rodando? (ollama serve)[/]")
        return None
    except Exception as e:  # noqa
        console.print(f"\n[red]Erro: {e}[/]")
        return None
    console.print()
    return "".join(full)


# ───────────────────────── Ferramentas ─────────────────────────

def safe_path(name):
    """Garante que o arquivo fica dentro da pasta de trabalho."""
    p = (WORKSPACE / name).resolve()
    if WORKSPACE.resolve() not in p.parents and p != WORKSPACE.resolve():
        raise ValueError("caminho fora da pasta de trabalho")
    return p


def strip_fences(code):
    code = code.strip("\n")
    m = re.match(r"^```[a-zA-Z0-9]*\n(.*?)\n?```\s*$", code, re.S)
    body = (m.group(1) if m else code).rstrip()
    body = re.sub(r"\n?```\s*$", "", body)
    return body.rstrip() + "\n"


def tool_listar():
    files = sorted(p.name + ("/" if p.is_dir() else "") for p in WORKSPACE.iterdir())
    return "Arquivos: " + (", ".join(files) if files else "(pasta vazia)")


def tool_ler(name):
    try:
        p = safe_path(name)
        text = p.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        return f"Erro ao ler {name}: {e}"
    console.print(Panel(Syntax(text, LEXERS.get(p.suffix.lower(), "text"), theme="monokai", word_wrap=True),
                        title=f"📄 {name}", border_style="#5c8dff"))
    return f"Conteúdo de {name}:\n{text[:3000]}"


def tool_criar(name, content):
    try:
        p = safe_path(name)
    except Exception as e:
        return f"Erro: {e}"
    code = strip_fences(content)
    if not code.strip():
        return f"Erro: o conteúdo de {name} veio vazio. Escreva o código completo entre [[CRIAR {name}]] e [[FIM]]."
    console.print(Panel(Syntax(code, LEXERS.get(p.suffix.lower(), "text"), theme="monokai", word_wrap=True),
                        title=f"✏️  Criar {name}", border_style="#c85bff"))
    if not Confirm.ask(f"Criar/sobrescrever [bold]{name}[/]?", default=True):
        return f"O usuário recusou criar {name}."
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(code, encoding="utf-8")
    console.print(f"[green]✔ {name} salvo.[/]")
    return f"Arquivo {name} criado com sucesso."


def build_command(p):
    """Devolve (comando, erro). Para C, compila antes."""
    ext = p.suffix.lower()
    if ext == ".py":
        return [sys.executable, str(p)], None
    if ext == ".sh":
        return ["bash", str(p)], None
    cc = shutil.which("clang") or shutil.which("gcc")
    if not cc:
        return None, "Compilador de C não encontrado. Instale com: pkg install clang"
    out = p.with_suffix(".out")
    try:
        r = subprocess.run(
            [cc, str(p), "-o", str(out), "-lm"], cwd=p.parent, capture_output=True,
            text=True, timeout=60, stdin=subprocess.DEVNULL,
        )
    except subprocess.TimeoutExpired:
        return None, "Tempo esgotado na compilação (60s)."
    if r.returncode != 0:
        return None, "Erro de compilação:\n" + (r.stderr or r.stdout).strip()[:1500]
    return [str(out)], None


def tool_exec(name, confirm=True):
    try:
        p = safe_path(name)
    except Exception as e:
        return f"Erro: {e}"
    ext = p.suffix.lower()
    if ext not in RUNNABLE or not p.exists():
        return f"Não posso executar {name} (precisa existir e ser .py, .sh ou .c)."
    if confirm and not Confirm.ask(f"Executar [bold]{name}[/]?", default=True):
        return f"O usuário recusou executar {name}."
    cmd, err = build_command(p)
    if err:
        console.print(Panel(err, title=f"✖ {name}", border_style="red"))
        return f"Não foi possível executar {name}: {err}"
    try:
        interactive = bool(RE_INTERACTIVE[ext].search(p.read_text(encoding="utf-8", errors="replace")))
    except Exception:
        interactive = False
    if interactive:
        # programa que pede dados: roda direto no terminal para você poder digitar
        console.print("[#8a8fa3]Programa interativo: rodando direto no terminal (Ctrl+C para parar).[/]")
        try:
            rc = subprocess.run(cmd, cwd=p.parent).returncode
        except KeyboardInterrupt:
            rc = -2
        console.print(f"[#8a8fa3]▶ {name} terminou (código {rc}).[/]")
        return f"{name} é interativo e foi executado direto no terminal (código {rc}); a saída não foi capturada."
    t0 = time.time()
    try:
        r = subprocess.run(
            cmd, cwd=p.parent, capture_output=True,
            text=True, timeout=EXEC_TIMEOUT, stdin=subprocess.DEVNULL,
        )
        out, err, code = r.stdout, r.stderr, r.returncode
    except subprocess.TimeoutExpired:
        out, err, code = "", f"Tempo esgotado ({EXEC_TIMEOUT}s).", -1
    dt = time.time() - t0
    color = "green" if code == 0 else "red"
    body = (out + ("\n" + err if err else "")).strip() or "(sem saída)"
    console.print(Panel(body[:2000], title=f"▶ {name}  •  código {code}  •  {dt:.1f}s",
                        border_style=color))
    return f"Resultado de {name} (código de saída {code}):\n{body[:2000]}"


def open_html(name):
    try:
        p = safe_path(name)
    except Exception as e:
        console.print(f"[red]{e}[/]")
        return
    console.print(f"[#8a8fa3]Arquivo: file://{p}[/]")
    opener = shutil.which("termux-open")
    if opener:
        subprocess.run([opener, str(p)])
    else:
        console.print("[#8a8fa3]Abra o caminho acima no navegador do celular.[/]")


def run_actions(text):
    """Executa as marcas encontradas e devolve os resultados (lista de str)."""
    # aceita também [[CRIAR]] nome.py (formato errado comum em modelos pequenos)
    text = re.sub(r"\[\[(CRIAR|LER|EXEC)\]\]\s*([\w.\-]+)", r"[[\1 \2]]", text)
    results = []
    done = set()
    for name, content in RE_CRIAR.findall(text):
        if name in done:
            continue
        done.add(name)
        results.append(tool_criar(name, content))
    for name in dict.fromkeys(RE_LER.findall(text)):
        results.append(tool_ler(name))
    if RE_LISTAR.search(text):
        r = tool_listar()
        console.print(Panel(r, border_style="#5c8dff", title="📁 pasta"))
        results.append(r)
    for name in dict.fromkeys(RE_EXEC.findall(text)):
        results.append(tool_exec(name))
    return results


def fallback_save(user, reply):
    """Se o modelo respondeu só com um bloco de código, salva no arquivo citado pelo usuário."""
    exts = "|".join(e.lstrip(".") for e in LEXERS)
    fn = re.search(rf"([\w\-]+\.(?:{exts}))\b", user, re.I)
    code = re.search(r"```[a-zA-Z0-9]*\s*\n(.*?)```", reply, re.S)
    if fn and code and code.group(1).strip():
        return tool_criar(fn.group(1), code.group(1))
    return None


_ONLY = "sem explicações, sem marcas e sem texto antes ou depois. Seja curto e simples, no máximo 50 linhas."
CREATE_PROMPTS = {
    ".py": "Você escreve código Python. Responda SOMENTE com o código completo do arquivo, "
           + _ONLY + " Use apenas a biblioteca padrão do Python.",
    ".sh": "Você escreve scripts Bash para o Termux (Android). Responda SOMENTE com o script "
           "completo, começando com #!/usr/bin/env bash, " + _ONLY,
    ".c": "Você escreve programas em C (padrão C99) para compilar com clang no Termux. "
          "Responda SOMENTE com o código completo, com os #include e a função main, " + _ONLY,
    ".html": "Você escreve páginas web. Responda SOMENTE com um arquivo HTML completo e "
             "autocontido (CSS e JavaScript dentro do próprio arquivo, sem bibliotecas externas), "
             + _ONLY,
    ".txt": "Você escreve textos em português. Responda SOMENTE com o conteúdo do arquivo, "
            "sem comentários extras e sem blocos de código.",
}


def check_code(code, ext):
    """Verifica a sintaxe de um texto de código (py/sh). Devolve o erro ou None."""
    try:
        if ext == ".sh":
            r = subprocess.run(["bash", "-n"], input=code, capture_output=True, text=True, timeout=10)
            return (r.stderr.strip() or "erro de sintaxe") if r.returncode else None
        if ext == ".py":
            compile(code, "<app>", "exec")
    except SyntaxError as e:
        return f"{e.msg} (linha {e.lineno})"
    except Exception:
        return None
    return None


def syntax_error(p):
    """Devolve a mensagem de erro de sintaxe (py/sh) ou None se estiver ok."""
    ext = p.suffix.lower()
    try:
        if ext == ".sh":
            r = subprocess.run(["bash", "-n", str(p)], capture_output=True, text=True, timeout=10)
            return (r.stderr.strip() or "erro de sintaxe") if r.returncode else None
        if ext == ".py":
            compile(p.read_text(encoding="utf-8", errors="replace"), str(p), "exec")
    except SyntaxError as e:
        return f"{e.msg} (linha {e.lineno})"
    except Exception:
        return None
    return None


def cmd_criar(arg):
    """/criar nome.ext descrição -> pede só o conteúdo ao modelo e salva (com confirmação)."""
    parts = arg.split(maxsplit=1)
    name = parts[0]
    desc = parts[1].strip() if len(parts) > 1 else ""
    if not re.fullmatch(r"[\w\-]+(\.\w+)?", name) or not desc:
        console.print("[yellow]Uso: /criar nome.ext descrição  (tipos: py, sh, c, html, txt)[/]")
        return
    if "." not in name:
        name += ".py"
    ext = Path(name).suffix.lower()
    if ext not in CREATE_PROMPTS:
        console.print("[yellow]Tipo não suportado. Use: .py, .sh, .c, .html ou .txt[/]")
        return
    name = Path(name).stem + ext
    msgs = [
        {"role": "system", "content": CREATE_PROMPTS[ext]},
        {"role": "user", "content": f"Escreva o arquivo {name}. Faça exatamente isto, nada além disso: {desc}"},
    ]
    console.print("[bold #c85bff]◆ OFFTEC[/] [#8a8fa3]gerando conteúdo...[/]")
    reply = chat_stream(msgs, num_predict=900)
    if not reply:
        return
    if ext == ".txt":
        code = reply
    else:
        m = re.search(r"```[a-zA-Z0-9]*\s*\n(.*?)```", reply, re.S)
        code = m.group(1) if m else reply
        code = re.sub(r"^\s*```[a-zA-Z0-9]*\n", "", code)
    result = tool_criar(name, code)
    if "criado com sucesso" not in result:
        return
    err = syntax_error(safe_path(name))
    if err:
        console.print(Panel(err[:600], title=f"⚠ {name} tem erro de sintaxe", border_style="yellow"))
        console.print("[yellow]O modelo gerou um código com problema. Tente de novo com uma descrição mais curta e direta, ou corrija à mão.[/]")
        offer_editor([name])
        return
    if LAST["truncated"]:
        console.print("[yellow]⚠ A resposta foi cortada pelo limite de tamanho; o arquivo pode estar incompleto.[/]")
    offer_editor([name])
    if ext in RUNNABLE:
        if Confirm.ask(f"Executar [bold]{name}[/] agora?", default=False):
            tool_exec(name, confirm=False)
    elif ext == ".html":
        if Confirm.ask(f"Abrir [bold]{name}[/] no navegador?", default=False):
            open_html(name)


# ───────────────────────── Editor (vim / nano) ─────────────────────────

EDITORS = ["vim", "nvim", "nano"]  # ordem de preferência (ou defina OFFTEC_EDITOR)
EDITOR_HINTS = {"vim": ":wq salva e sai", "nvim": ":wq salva e sai", "vi": ":wq salva e sai",
                "nano": "Ctrl+O salva, Ctrl+X sai"}


def pick_editor(name=None):
    if name:
        cands = [name]
    elif os.environ.get("OFFTEC_EDITOR"):
        cands = [os.environ["OFFTEC_EDITOR"]]
    else:
        cands = EDITORS
    for c in cands:
        if shutil.which(c):
            return c
    return None


def open_editor(rels, editor):
    files = []
    for r in rels:
        try:
            files.append(str(safe_path(r)))
        except Exception as e:
            console.print(f"[red]{e}[/]")
    if not files:
        return
    cmd = [editor]
    if len(files) > 1 and Path(editor).name in ("vim", "nvim", "vi"):
        cmd.append("-p")  # abre cada arquivo em uma aba
    cmd += files
    try:
        subprocess.run(cmd, cwd=WORKSPACE)
    except (KeyboardInterrupt, FileNotFoundError):
        pass
    console.print("[#8a8fa3]Editor fechado.[/]")


def offer_editor(rels):
    ed = pick_editor()
    if not ed:
        return
    hint = EDITOR_HINTS.get(Path(ed).name, "")
    if Confirm.ask(f"Abrir o código no [bold]{ed}[/]? [#8a8fa3]({hint})[/]", default=False):
        open_editor(rels, ed)


def cmd_editar(arg):
    """/editar arquivo|pasta [editor] -> abre no vim/nano."""
    parts = arg.split()
    ed = pick_editor(parts[1] if len(parts) > 1 else None)
    if not ed:
        console.print("[yellow]Editor não encontrado. Instale com: pkg install vim nano[/]")
        return
    try:
        target = safe_path(parts[0])
    except Exception as e:
        console.print(f"[red]{e}[/]")
        return
    if target.is_dir():
        root = WORKSPACE.resolve()
        rels = [str(f.relative_to(root)) for f in sorted(target.iterdir())
                if f.is_file() and f.suffix.lower() != ".out"]
        if not rels:
            console.print("[yellow]Pasta vazia.[/]")
            return
    else:
        rels = [parts[0]]
    open_editor(rels, ed)


# ───────────────────────── Apps (vários arquivos) ─────────────────────────

APP_ALIASES = {"python": "py", "bash": "sh", "html": "web", "site": "web"}
_APP = "Responda SOMENTE com o conteúdo completo do arquivo, sem explicações, sem marcas e sem texto antes ou depois."
APP_TYPES = {
    "py": {
        "label": "Python (terminal)",
        "files": [("main.py",
                   "Você escreve o arquivo principal main.py de um aplicativo de terminal em Python. "
                   "Use só a biblioteca padrão, organize em funções e termine com "
                   "if __name__ == \"__main__\": main(). Seja curto, no máximo 90 linhas. " + _APP)],
        "run": "python main.py",
    },
    "sh": {
        "label": "Bash (terminal)",
        "files": [("main.sh",
                   "Você escreve o script principal main.sh de um aplicativo de terminal em Bash para o Termux. "
                   "Comece com #!/usr/bin/env bash e use funções. Seja curto, no máximo 70 linhas. " + _APP)],
        "run": "bash main.sh",
    },
    "c": {
        "label": "C (terminal)",
        "files": [("main.c",
                   "Você escreve o arquivo principal main.c de um aplicativo de terminal em C (padrão C99) "
                   "para clang. Inclua os #include e a função main. Seja curto, no máximo 90 linhas. " + _APP)],
        "run": "clang main.c -o app -lm && ./app",
    },
    "web": {
        "label": "Web (HTML + CSS + JS)",
        "files": [
            ("index.html",
             "Você escreve o index.html de um app web. Ligue o CSS com <link rel=\"stylesheet\" href=\"style.css\"> "
             "e o JavaScript com <script src=\"script.js\"></script> antes de </body>. "
             "Use ids e classes simples. No máximo 60 linhas. " + _APP),
            ("style.css",
             "Você escreve o style.css para o HTML fornecido. Use os ids e classes que existem no HTML. "
             "Visual limpo, centralizado e bom em tela de celular. No máximo 60 linhas. " + _APP),
            ("script.js",
             "Você escreve o script.js para o HTML fornecido. Use exatamente os ids e classes do HTML, "
             "JavaScript puro e sem bibliotecas. No máximo 60 linhas. " + _APP),
        ],
        "run": "abra index.html no navegador",
    },
}


def extract_code(reply, ext):
    if ext in (".txt", ".md"):
        return reply
    m = re.search(r"```[a-zA-Z0-9]*\s*\n(.*?)```", reply, re.S)
    code = m.group(1) if m else reply
    return re.sub(r"^\s*```[a-zA-Z0-9]*\n", "", code)


def app_readme(name, desc, kind):
    if kind == "web":
        how = "Abra o arquivo `index.html` no navegador."
    else:
        how = "```\n" + APP_TYPES[kind]["run"] + "\n```"
    return f"# {name}\n\n{desc}\n\nCriado com o OFFTEC Agent.\n\n## Como executar\n\n{how}\n"


def cmd_app(arg):
    """/app nome [tipo] descrição -> gera um app com vários arquivos em apps/nome/."""
    usage = "[yellow]Uso: /app nome [tipo] descrição  (tipos: py, web, sh, c; padrão py)[/]"
    parts = arg.split(maxsplit=2)
    if len(parts) < 2:
        console.print(usage)
        return
    name = parts[0]
    kind = APP_ALIASES.get(parts[1].lower(), parts[1].lower())
    if kind in APP_TYPES:
        desc = parts[2].strip() if len(parts) > 2 else ""
    else:
        kind = "py"
        desc = arg.split(maxsplit=1)[1].strip()
    if not re.fullmatch(r"[\w\-]+", name) or not desc:
        console.print(usage)
        return
    folder = f"apps/{name}"
    try:
        root = safe_path(folder)
    except Exception as e:
        console.print(f"[red]{e}[/]")
        return
    if root.exists() and any(root.iterdir()):
        if not Confirm.ask(f"A pasta [bold]{folder}[/] já tem arquivos. Sobrescrever os de mesmo nome?", default=False):
            return
    spec = APP_TYPES[kind]
    names = ", ".join([fn for fn, _ in spec["files"]] + ["README.md"])
    console.print(Panel(f"Tipo: {spec['label']}\nPasta: {folder}/\nArquivos: {names}",
                        title=f"📦 App {name}", border_style="#c85bff"))

    made, truncated = [], []
    for fn, system in spec["files"]:
        ext = Path(fn).suffix.lower()
        ctx = "".join(f"\n--- {f} ---\n{c[:1500]}\n" for f, c in made)
        user_msg = (f"Aplicativo: {name}\nO que o app faz: {desc}\n"
                    + (f"Arquivos já criados:{ctx}\n" if made else "")
                    + f"Escreva agora o arquivo {fn}.")
        console.print(f"[bold #c85bff]◆ OFFTEC[/] [#8a8fa3]gerando {fn}...[/]")
        reply = chat_stream(
            [{"role": "system", "content": system}, {"role": "user", "content": user_msg}],
            num_predict=1100,
        )
        if not reply:
            console.print("[yellow]Interrompido. Nada foi salvo.[/]")
            return
        code = strip_fences(extract_code(reply, ext))
        if not code.strip():
            console.print(f"[yellow]O modelo não gerou conteúdo para {fn}. Nada foi salvo.[/]")
            return
        made.append((fn, code))
        if LAST["truncated"]:
            truncated.append(fn)

    problems, syntax_bad = [], False
    for fn, code in made:
        err = check_code(code, Path(fn).suffix.lower())
        if err:
            syntax_bad = True
            problems.append(f"{fn}: erro de sintaxe — {err[:200]}")
    for fn in truncated:
        problems.append(f"{fn}: resposta cortada pelo limite de tamanho")

    lines = "\n".join(f"• {fn}  ({code.count(chr(10))} linhas)" for fn, code in made)
    console.print(Panel(lines, title="Arquivos gerados", border_style="#5c8dff"))
    if problems:
        console.print(Panel("\n".join(problems), title="⚠ Atenção", border_style="yellow"))
    if not Confirm.ask(f"Salvar o app em [bold]{folder}/[/]?", default=not problems):
        console.print("[#8a8fa3]Cancelado. Nada foi salvo.[/]")
        return
    root.mkdir(parents=True, exist_ok=True)
    for fn, code in made:
        (root / fn).write_text(code, encoding="utf-8")
    (root / "README.md").write_text(app_readme(name, desc, kind), encoding="utf-8")
    console.print(f"[green]✔ App salvo em {root}[/]")
    offer_editor([f"{folder}/{fn}" for fn, _ in made])

    main_file = spec["files"][0][0]
    if kind == "web":
        if Confirm.ask("Abrir [bold]index.html[/] no navegador?", default=False):
            open_html(f"{folder}/index.html")
    elif not syntax_bad:
        if Confirm.ask(f"Executar [bold]{main_file}[/] agora?", default=False):
            tool_exec(f"{folder}/{main_file}", confirm=False)


# ───────────────────────── Loop principal ─────────────────────────

def handle_command(cmd, history):
    parts = cmd.split(maxsplit=1)
    c, arg = parts[0], (parts[1].strip() if len(parts) > 1 else "")
    if c in ("/sair", "/exit", "/q"):
        console.print("[#8a8fa3]Até mais.[/]")
        sys.exit(0)
    elif c == "/ajuda":
        splash()
    elif c == "/editar":
        if arg:
            cmd_editar(arg)
        else:
            console.print("[yellow]Uso: /editar arquivo ou pasta [vim|nano][/]")
    elif c == "/app":
        if arg:
            cmd_app(arg)
        else:
            console.print("[yellow]Uso: /app nome [tipo] descrição  (tipos: py, web, sh, c)[/]")
    elif c == "/criar":
        if arg:
            cmd_criar(arg)
        else:
            console.print("[yellow]Uso: /criar nome.ext descrição  (py, sh, c, html, txt)[/]")
    elif c == "/ls":
        console.print(Panel(tool_listar(), border_style="#5c8dff"))
    elif c == "/ler" and arg:
        tool_ler(arg)
    elif c == "/rodar" and arg:
        tool_exec(arg)
    elif c == "/limpar":
        history.clear()
        splash()
    else:
        console.print("[yellow]Comando desconhecido. Use /ajuda.[/]")


def main():
    splash()
    history = []
    while True:
        try:
            console.print("[bold #00e5ff]❯[/] ", end="")
            user = input().strip()
        except (EOFError, KeyboardInterrupt):
            console.print("\n[#8a8fa3]Até mais.[/]")
            break
        if not user:
            continue
        if user.startswith("/"):
            handle_command(user, history)
            continue

        history.append({"role": "user", "content": user})
        last = None
        for _ in range(MAX_ROUNDS):
            msgs = [{"role": "system", "content": SYSTEM_PROMPT}] + history[-MAX_HISTORY:]
            console.print("[bold #c85bff]◆ OFFTEC[/]")
            reply = chat_stream(msgs)
            if reply is None:
                history.pop()
                break
            history.append({"role": "assistant", "content": reply})
            results = run_actions(reply)
            if not results:
                if fallback_save(user, reply):
                    console.print("[#8a8fa3]Salvei o código do bloco da resposta.[/]")
                break
            if results == last:
                break
            last = results
            history.append({
                "role": "user",
                "content": "[RESULTADO DAS AÇÕES]\n" + "\n\n".join(results)
                           + "\n\nAnalise o resultado e responda ao usuário.",
            })
        console.print()


if __name__ == "__main__":
    main()
