<div align="center">

# 🤖 OFFTEC Agent

**Agente de IA local para Android/Termux — 100% offline, sem chave de API.**

![Versão](https://img.shields.io/badge/versão-1.0-00e5ff?style=for-the-badge)
![Status](https://img.shields.io/badge/status-beta-ff4fd8?style=for-the-badge)
![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Termux](https://img.shields.io/badge/Termux-Android-000000?style=for-the-badge&logo=android&logoColor=3DDC84)
![Ollama](https://img.shields.io/badge/Ollama-local-5c8dff?style=for-the-badge)
![Offline](https://img.shields.io/badge/100%25-offline-success?style=for-the-badge)

</div>

---

## ✨ Sobre

O **OFFTEC Agent** é um assistente de programação que roda inteiramente no seu celular. Ele conversa em português, cria e lê arquivos, escreve código em várias linguagens, executa os programas e analisa os resultados, tudo dentro de uma interface de terminal estilosa, com tela inicial em degradê.

Nada sai do aparelho: o modelo roda localmente via [Ollama](https://ollama.com).

## 🚀 Recursos

| | Recurso | Descrição |
|---|---|---|
| 💬 | **Chat em português** | Respostas em streaming, em tempo real |
| ⚡ | **Comando `/criar`** | Gera um arquivo completo a partir de uma descrição curta |
| 🌐 | **Várias linguagens** | Python, Bash, C, HTML e texto |
| 📖 | **Lê arquivos** | Mostra o código com destaque de sintaxe |
| ▶️ | **Executa programas** | Roda `.py`, `.sh` e `.c` (compila o C automaticamente) |
| ⌨️ | **Programas interativos** | Se o programa pede dados (`input`, `read`, `scanf`), roda direto no terminal para você digitar |
| 🧪 | **Testa e analisa** | O resultado volta para o modelo, que diz o que passou ou falhou |
| 🛟 | **Proteções para modelos pequenos** | Detecta loops, valida a sintaxe e avisa quando a resposta é cortada |
| 🎨 | **TUI bonita** | Banner em degradê, painéis e cores, feito com [Rich](https://github.com/Textualize/rich) |
| 🔒 | **Seguro por padrão** | Pede confirmação antes de criar arquivos ou executar código |
| 📴 | **Offline** | Sem internet e sem chave de API |

## 📦 Requisitos

- 📱 Android com [Termux](https://termux.dev)
- 🐍 Python 3.10+
- 🦙 Ollama
- 🧠 Um modelo do Ollama. O padrão é `llama3.2:1b-instruct-q4_K_M` (~808 MB)
- 🔧 *(opcional)* `clang`, para criar e executar programas em C

## ⚙️ Instalação

```bash
# 1. Dependências
pkg update
pkg install python git ollama
pip install rich

# 2. (opcional) compilador, só para programas em C
pkg install clang

# 3. Baixar o projeto
git clone https://github.com/Mcsd7/Offtec-Agente.git
cd Offtec-Agente

# 4. Baixar o modelo (precisa de internet só nesta etapa)
ollama serve &
ollama pull llama3.2:1b-instruct-q4_K_M
```

## ▶️ Como usar

Em uma aba do Termux, deixe o servidor rodando:

```bash
ollama serve
```

Em outra aba, abra o agente:

```bash
python offtec_agent.py
```

Para sair, digite `/sair` ou use `Ctrl+C`.

### ⚡ Criando arquivos com `/criar`

O jeito mais confiável de gerar código, principalmente com modelos pequenos:

```
/criar calc.py calculadora de adição que pede dois números
/criar ola.sh pergunta meu nome e diz oi
/criar soma.c programa em C que lê dois números e mostra a soma
/criar pagina.html página simples com título e um botão que muda a cor do fundo
/criar notas.txt lista de 5 ideias de projetos para Termux
```

O agente gera o conteúdo, mostra uma prévia, pede confirmação para salvar e, para `.py`, `.sh` e `.c`, pergunta se você quer executar. Em `.html`, pergunta se quer abrir no navegador. Sem extensão, o arquivo é criado como `.py`.

Dica: peça uma coisa por vez, com frases curtas e diretas.

### 💬 Conversando com o agente

Você também pode pedir em linguagem natural:

> crie um script que calcula fatorial e teste

Nesse modo o modelo decide sozinho quando criar, ler e executar arquivos. Funciona melhor com modelos maiores.

### 🧰 Comandos

| Comando | O que faz |
|---|---|
| `/criar <arquivo> <descrição>` | Cria um arquivo `.py`, `.sh`, `.c`, `.html` ou `.txt` |
| `/ls` | Lista os arquivos da pasta de trabalho |
| `/ler <arquivo>` | Mostra o conteúdo de um arquivo |
| `/rodar <arquivo>` | Executa um `.py`, `.sh` ou `.c` |
| `/limpar` | Zera a conversa |
| `/ajuda` | Mostra a tela inicial e a lista de comandos |
| `/sair` | Encerra o agente |

## 🗂️ Onde ficam os arquivos

Os arquivos criados pelo agente ficam na pasta **`workspace/`**, ao lado do `offtec_agent.py`. Ela é criada automaticamente na primeira execução e fica fora do Git (veja o `.gitignore`).

```
Offtec-Agente/
├── offtec_agent.py
├── README.md
├── LICENSE
├── .gitignore
└── workspace/        ← criada pelo agente
```

## 🔧 Configuração

Variáveis de ambiente opcionais:

| Variável | Padrão | Função |
|---|---|---|
| `OFFTEC_MODEL` | `llama3.2:1b-instruct-q4_K_M` | Modelo do Ollama |
| `OLLAMA_HOST` | `http://127.0.0.1:11434` | Endereço do servidor Ollama |
| `OFFTEC_WORKSPACE` | `./workspace` (ao lado do script) | Pasta onde o agente cria os arquivos |

```bash
OFFTEC_MODEL=qwen2.5-coder:1.5b python offtec_agent.py
```

## 🧠 Escolhendo o modelo

O agente funciona com qualquer modelo do Ollama. Em geral, quanto maior o modelo, melhor ele segue as instruções e mais correto sai o código.

| Modelo | Quando usar |
|---|---|
| `llama3.2:1b-instruct-q4_K_M` | Padrão. Leve, para aparelhos mais modestos. Use o `/criar` com pedidos curtos |
| `qwen2.5-coder:1.5b` | Opção um pouco maior, voltada para código |
| `llama3.2:3b` ou `qwen2.5-coder:3b` | Para aparelhos com mais memória; seguem melhor a conversa livre |

Baixe com `ollama pull <modelo>` e rode com `OFFTEC_MODEL=<modelo>`.

## 🛡️ Segurança

- O agente só lê e escreve dentro da pasta de trabalho.
- Só executa `.py`, `.sh` e `.c`.
- Programas que não pedem dados têm limite de 30 segundos. A compilação de C tem limite de 60 segundos.
- Toda criação de arquivo e toda execução pedem a sua confirmação.
- O código gerado roda com as mesmas permissões do Termux, sem isolamento. **Leia a prévia antes de confirmar.**

## 🛟 Proteções contra erros do modelo

Modelos pequenos erram, repetem texto e inventam resultados. O agente se defende assim:

- Interrompe respostas repetitivas (loops).
- Para a resposta na primeira ação (criar, ler ou executar) e usa o resultado real, para o modelo não inventar saídas.
- Verifica a sintaxe de `.py` e `.sh` antes de oferecer a execução.
- Avisa quando a resposta foi cortada pelo limite de tamanho.
- Recusa arquivos vazios e ações repetidas.

## 🩺 Solução de problemas

| Problema | O que fazer |
|---|---|
| Ollama aparece **offline** na tela inicial | Rode `ollama serve` em outra aba do Termux |
| Modelo **não encontrado** | Rode `ollama pull llama3.2:1b-instruct-q4_K_M` |
| `Compilador de C não encontrado` | Rode `pkg install clang` |
| O código gerado vem errado ou fora do assunto | Use `/limpar`, peça de novo com uma frase mais curta e direta, ou teste um modelo maior |
| Termux fecha em segundo plano | Rode `termux-wake-lock` ou toque em *Acquire wakelock* na notificação |

## ⚠️ Limitações

O modelo padrão tem 1B de parâmetros. É pequeno e pode gerar código com falhas, sair do assunto ou errar o formato das ações. O `/criar` é mais confiável que a conversa livre, e modelos maiores funcionam melhor, se o seu aparelho aguentar.

## 🗺️ Roadmap

**Já feito**

- [x] 💬 Chat em português com streaming
- [x] ⚡ Comando `/criar`
- [x] 🌐 Suporte a Python, Bash, C, HTML e texto
- [x] ⌨️ Execução de programas interativos no terminal
- [x] 🛟 Detecção de loops, validação de sintaxe e aviso de resposta cortada
- [x] 🗂️ Pasta `workspace/` dentro do projeto

**Ideias para as próximas versões**

- [ ] 🖥️ Interface em painéis com [Textual](https://github.com/Textualize/textual), no estilo Hermes
- [ ] 🧠 Troca de modelo dentro do app (`/modelo`)
- [ ] 💾 Histórico de conversas salvo entre sessões
- [ ] 🔌 Integração com OpenCode e Neovim
- [ ] 🧩 Sistema de plugins e novas ferramentas (git, pip, busca em arquivos)
- [ ] 🔁 Ciclo automático de corrigir e testar até o teste passar
- [ ] 🌍 Mais linguagens (JavaScript, Go, Lua)
- [ ] 📋 Log das ações executadas
- [ ] 🌐 Interface em outros idiomas (en, ar, hi)
- [ ] 🧱 Modo somente leitura para análise de código
- [ ] 📦 Instalador automático (`install.sh`)

## 🤝 Contribuindo

Sugestões e correções são bem-vindas. Abra uma *issue* ou envie um *pull request*.

## 📄 Licença

Veja o arquivo [LICENSE](LICENSE).

## 👤 Autor

Feito por [**Mcsd7**](https://github.com/Mcsd7) 💙

---

<div align="center">

⭐ Se o projeto te ajudou, deixe uma estrela no repositório!

</div>
