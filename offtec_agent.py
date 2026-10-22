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
    cmds.add_row("/criar <arq> <desc>", "cria um .py")
    cmds.add_row("/ls", "arquivos da pasta")
    cmds.add_row("/ler <arq>", "mostra um arquivo")
    cmds.add_row("/rodar <arq>", "executa um .py")
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
- Só execute arquivos .py. Nomes de arquivo sem espaços e sem pastas.
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
        if ln.startswith("[["):
            limit = 4
        elif len(ln) > 12:
            limit = 5
        else:
            continue
        counts[ln] = counts.get(ln, 0) + 1
        if counts[ln] >= limit:
            return True
    return False


def chat_stream(messages):
    """Faz streaming da resposta do Ollama e devolve o texto completo."""
    payload = json.dumps(
        {
            "model": MODEL,
            "messages": messages,
            "stream": True,
            "options": {"temperature": 0.2, "num_ctx": 4096, "num_predict": 700, "repeat_penalty": 1.2},
        }
    ).encode()
    req = urllib.request.Request(
        HOST + "/api/chat", data=payload, headers={"Content-Type": "application/json"}
    )
    full = []
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
                        break
                if chunk.get("done"):
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
    files = sorted(p.name for p in WORKSPACE.iterdir())
    return "Arquivos: " + (", ".join(files) if files else "(pasta vazia)")


def tool_ler(name):
    try:
        p = safe_path(name)
        text = p.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        return f"Erro ao ler {name}: {e}"
    console.print(Panel(Syntax(text, "python", theme="monokai", word_wrap=True),
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
    console.print(Panel(Syntax(code, "python", theme="monokai", word_wrap=True),
                        title=f"✏️  Criar {name}", border_style="#c85bff"))
    if not Confirm.ask(f"Criar/sobrescrever [bold]{name}[/]?", default=True):
        return f"O usuário recusou criar {name}."
    p.write_text(code, encoding="utf-8")
    console.print(f"[green]✔ {name} salvo.[/]")
    return f"Arquivo {name} criado com sucesso."


def tool_exec(name):
    try:
        p = safe_path(name)
    except Exception as e:
        return f"Erro: {e}"
    if p.suffix != ".py" or not p.exists():
        return f"Não posso executar {name} (precisa existir e ser .py)."
    if not Confirm.ask(f"Executar [bold]{name}[/]?", default=True):
        return f"O usuário recusou executar {name}."
    t0 = time.time()
    try:
        r = subprocess.run(
            [sys.executable, str(p)], cwd=WORKSPACE, capture_output=True,
            text=True, timeout=EXEC_TIMEOUT,
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
    """Se o modelo respondeu só com um bloco ```python, salva no arquivo citado pelo usuário."""
    fn = re.search(r"([\w\-]+\.py)", user)
    code = re.search(r"```(?:python|py)?\s*\n(.*?)```", reply, re.S)
    if fn and code and code.group(1).strip():
        return tool_criar(fn.group(1), code.group(1))
    return None


CREATE_PROMPT = (
    "Você escreve código Python. Responda SOMENTE com o código completo do arquivo, "
    "sem explicações, sem marcas e sem texto antes ou depois. "
    "Use apenas a biblioteca padrão do Python."
)


def cmd_criar(arg):
    """/criar nome.py descrição -> pede só o código ao modelo e salva (com confirmação)."""
    parts = arg.split(maxsplit=1)
    name = parts[0]
    desc = parts[1].strip() if len(parts) > 1 else ""
    if not re.fullmatch(r"[\w\-]+(\.py)?", name) or not desc:
        console.print("[yellow]Uso: /criar nome.py descrição do que o programa faz[/]")
        return
    if not name.endswith(".py"):
        name += ".py"
    msgs = [
        {"role": "system", "content": CREATE_PROMPT},
        {"role": "user", "content": f"Escreva o arquivo {name}: {desc}"},
    ]
    console.print("[bold #c85bff]◆ OFFTEC[/] [#8a8fa3]gerando código...[/]")
    reply = chat_stream(msgs)
    if not reply:
        return
    m = re.search(r"```(?:python|py)?\s*\n(.*?)```", reply, re.S)
    code = m.group(1) if m else reply
    code = re.sub(r"^\s*```[a-zA-Z0-9]*\n", "", code)
    result = tool_criar(name, code)
    if "criado com sucesso" in result and Confirm.ask(f"Executar [bold]{name}[/] agora?", default=False):
        tool_exec(name)


# ───────────────────────── Loop principal ─────────────────────────

def handle_command(cmd, history):
    parts = cmd.split(maxsplit=1)
    c, arg = parts[0], (parts[1].strip() if len(parts) > 1 else "")
    if c in ("/sair", "/exit", "/q"):
        console.print("[#8a8fa3]Até mais.[/]")
        sys.exit(0)
    elif c == "/ajuda":
        splash()
    elif c == "/criar":
        if arg:
            cmd_criar(arg)
        else:
            console.print("[yellow]Uso: /criar nome.py descrição[/]")
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
