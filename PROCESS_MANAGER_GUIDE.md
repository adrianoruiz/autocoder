# Process Manager - Guia de Uso

## 📋 O que foi implementado?

Um sistema completo para gerenciar processos do agente através da interface web.

### Backend (API)

**Novo arquivo:** `server/routers/processes.py`

Endpoints criados:
- `GET /api/processes` - Lista todos os processos do agente
- `POST /api/processes/kill` - Mata um processo específico por PID
- `POST /api/processes/kill-all` - Mata todos os processos do agente

### Frontend (UI)

**Novo arquivo:** `ui/src/components/ProcessManager.tsx`

Interface visual com:
- Botão flutuante no canto inferior direito (mostra contagem de processos)
- Modal com lista de processos ativos
- Auto-refresh a cada 2 segundos
- Informações detalhadas: PID, projeto, uso de CPU/memória, uptime
- Botões para matar processos individualmente ou todos de uma vez

## 🚀 Como usar

### 1. Iniciar o servidor (se não estiver rodando)

```bash
# Ativar ambiente virtual
source venv/bin/activate  # Mac/Linux
venv\Scripts\activate     # Windows

# Iniciar servidor
python -m uvicorn server.main:app --host 127.0.0.1 --port 8888 --reload
```

### 2. Acessar a UI

Abra http://127.0.0.1:8888/ no navegador

### 3. Usar o Process Manager

1. **Ver processos ativos:**
   - Clique no botão com ícone de CPU no canto inferior direito
   - O número no badge vermelho mostra quantos processos estão rodando

2. **Matar um processo específico:**
   - Abra o Process Manager
   - Clique no botão vermelho com ícone de lixeira ao lado do processo

3. **Matar todos os processos:**
   - Abra o Process Manager
   - Clique em "Kill All Processes" no topo da lista
   - Confirme a ação

## 🎯 Detecção de Processos

O sistema detecta automaticamente:
- `autonomous_agent_demo.py` - Agente principal
- `claude --output-format stream-json` - Processos do Claude SDK
- `python agent.py` - Processos do agente direto

## 📊 Informações Mostradas

Para cada processo:
- **PID** - ID do processo
- **Status** - running, sleeping, etc.
- **Uptime** - Tempo desde que iniciou
- **Projeto** - Nome do projeto (extraído do comando)
- **CPU** - Uso de CPU em %
- **Memória** - Uso de memória em MB
- **Linha de comando** - Comando completo (truncado)

## 🔧 Estrutura Técnica

### Backend

```python
# server/routers/processes.py
class ProcessInfo:
    pid: int
    name: str
    cmdline: str
    project_dir: Optional[str]
    cpu_percent: float
    memory_mb: float
    status: str
    create_time: float

# Funções principais
is_agent_process(proc) -> bool
extract_project_dir(cmdline) -> str
list_processes() -> ProcessListResponse
kill_process(pid) -> KillProcessResponse
kill_all_processes() -> dict
```

### Frontend

```typescript
// ui/src/components/ProcessManager.tsx
interface ProcessInfo {
  pid: number
  name: string
  cmdline: string
  project_dir: string | null
  cpu_percent: number
  memory_mb: number
  status: string
  create_time: number
}

// Funções principais
fetchProcesses() // Auto-refresh a cada 2s
killProcess(pid)
killAllProcesses()
```

## 🔒 Segurança

- **Validação de processos:** Só permite matar processos identificados como agentes
- **Localhost only:** Servidor aceita apenas conexões locais (127.0.0.1)
- **Confirmação:** Kill-all requer confirmação do usuário

## 🐛 Troubleshooting

### Botão não aparece
- Certifique-se de que o servidor está rodando
- Verifique o console do navegador (F12) para erros
- Tente recarregar a página (Ctrl+R)

### Processos não aparecem
- Execute algum agente para testar
- Verifique se os processos estão realmente rodando:
  ```bash
  ps aux | grep -E "(autonomous_agent|claude.*--output-format)"
  ```

### Erro ao matar processo
- Pode ser um problema de permissões no sistema
- Tente usar o comando manual como fallback:
  ```bash
  kill -9 [PID]
  ```

## 📝 Notas

- O Process Manager é **global** - sempre visível em todas as páginas
- Auto-refresh pode ser desabilitado fechando o modal
- Matar processos é **permanente** - o agente precisará ser reiniciado

## 🎨 Design

O componente segue o design system neobrutalism do projeto:
- Bordas pretas grossas
- Cores vibrantes (verde/amarelo/vermelho)
- Sombras neo-brutal
- Animações suaves
- Layout limpo e moderno
