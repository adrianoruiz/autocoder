# Guia de Implementação: Configurações (YOLO Mode & Model Selection)

Este documento descreve como a funcionalidade de configurações globais foi implementada, permitindo que você a porte para o seu projeto fork.

---

## 1. Backend: Persistência e API

A funcionalidade utiliza **SQLite** com **SQLAlchemy** para persistência e **FastAPI** para os endpoints.

### 1.1 Modelo de Dados (`registry.py`)

As configurações são armazenadas como pares chave-valor em uma tabela dedicada para facilitar a expansão futura.

```python
# registry.py
from sqlalchemy import Column, DateTime, String
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class Settings(Base):
    """Modelo para configurações globais (key-value store)."""
    __tablename__ = "settings"
    key = Column(String(50), primary_key=True)
    value = Column(String(500), nullable=False)
    updated_at = Column(DateTime, nullable=False)

# Configuração Única de Modelos
AVAILABLE_MODELS = [
    {"id": "claude-opus-4-5-20251101", "name": "Claude Opus 4.5"},
    {"id": "claude-sonnet-4-5-20250929", "name": "Claude Sonnet 4.5"},
]
DEFAULT_MODEL = "claude-opus-4-5-20251101"
```

### 1.2 Endpoints da API (`server/routers/settings.py`)

A API expõe três ações principais:

- **Listar modelos:** `GET /api/settings/models`
- **Ler configurações:** `GET /api/settings`
- **Atualizar (Patch):** `PATCH /api/settings`

Ao atualizar o **YOLO Mode**, salvamos `"true"` ou `"false"` como string no banco e convertemos de volta para boolean na leitura.

---

## 2. Frontend: React + React Query

A interface é construída com **React** e gerencia o estado assíncrono usando o **React Query**.

### 2.1 Camada de Dados (`ui/src/hooks/useProjects.ts`)

Utilizamos `useQuery` para carregar os dados e `useMutation` para salvar as alterações de forma reativa.

```typescript
export function useSettings() {
  return useQuery({
    queryKey: ["settings"],
    queryFn: api.getSettings,
    placeholderData: { yolo_mode: false, model: "claude-opus-4-5-20251101" },
  });
}

export function useUpdateSettings() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (settings: SettingsUpdate) => api.updateSettings(settings),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["settings"] });
    },
  });
}
```

### 2.2 Componente Visual (`ui/src/components/SettingsModal.tsx`)

O modal implementa o design **Neo-brutalista**:

- **Bordas:** 4px sólidas pretas.
- **Sombra:** Off-set rígido (`box-shadow: 8px 8px 0px #000`).
- **Estados:** Feedback visual imediato ao clicar nos modelos (toggle switch e botões de rádio).

---

## 3. Design System (CSS)

Para replicar a estética da imagem, adicione os seguintes tokens ao seu `index.css` ou `globals.css`:

```css
:root {
  --color-neo-border: #000000;
  --color-neo-accent: #ff006e; /* Rosa vibrante para o modelo selecionado */
  --color-neo-pending: #ffbe0b; /* Amarelo para o toggle de YOLO mode */
  --color-neo-text: #1a1a1a;
}

/* Estilo Neo-brutalista para o Modal */
.neo-modal {
  background: #ffffff;
  border: 4px solid var(--color-neo-border);
  box-shadow: 8px 8px 0px var(--color-neo-border);
  padding: 1.5rem;
}

/* Botões de Seleção de Modelo */
.model-selector-btn {
  flex: 1;
  padding: 0.75rem;
  border: 3px solid var(--color-neo-border);
  font-weight: bold;
  transition: background 0.2s;
}

.model-selector-btn.selected {
  background-color: var(--color-neo-accent);
  color: white;
}
```

---

## Como Portar para o seu Fork

1.  **Crie a Tabela no Banco:** Execute a migration ou garanta que a tabela `settings` exista no SQLite.
2.  **Define a Lista de Modelos:** No backend, centralize os IDs dos modelos que seu fork suportará.
3.  **Adicione os Hooks:** Certifique-se de que o frontend tenha acesso às funções `api.getSettings` e `api.updateSettings`.
4.  **Aplique o CSS:** Copie os estilos Neo-brutalistas para manter a identidade visual.
