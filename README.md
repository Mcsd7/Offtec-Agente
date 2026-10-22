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

O **OFFTEC Agent** é um assistente de programação que roda inteiramente no seu celular. Ele conversa em português, cria e lê arquivos, escreve scripts Python, executa testes e analisa os resultados, tudo dentro de uma interface de terminal estilosa, com tela inicial em degradê.

Nada sai do aparelho: o modelo roda localmente via [Ollama](https://ollama.com).

## 🚀 Recursos

| | Recurso | Descrição |
|---|---|---|
| 💬 | **Chat em português** | Respostas em streaming, em tempo real |
| 📝 | **Cria arquivos** | Escreve scripts na pasta de trabalho |
| 📖 | **Lê arquivos** | Mostra o código com destaque de sintaxe |
| ▶️ | **Executa Python** | Roda scripts `.py` e captura a saída |
| 🧪 | **Testa e analisa** | O resultado volta para o modelo, que diz o que passou ou falhou |
| 🎨 | **TUI bonita** | Banner em degradê, painéis e cores, feito com [Rich](https://github.com/Textualize/rich) |
| 🔒 | **Seguro por padrão** | Pede confirmação antes de criar arquivos ou executar código |
| 📴 | **Offline** | Sem internet e sem chave de API |

## 📦 Requisitos

- 📱 Android com [Termux](https://termux.dev)
- 🐍 Python 3.10+
- 🦙 Ollama
- 🧠 Modelo `llama3.2:1b-instruct-q4_K_M` (~808 MB)

## ⚙️ Instalação

```bash
# 1. Dependências
pkg update
pkg install python git ollama
pip install rich

# 2. Baixar o projeto
git clone https://github.com/Mcsd7/Offtec-Agente.git
cd Offtec-Agente

# 3. Baixar o modelo (precisa de internet só nesta etapa)
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

Exemplo de pedido:

> crie um script que calcula fatorial e teste

### 🧰 Comand
