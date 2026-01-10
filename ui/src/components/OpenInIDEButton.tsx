import { useState } from 'react'
import { Code, ChevronDown, Loader2 } from 'lucide-react'
import { openProjectInIDE, type IDEType } from '../lib/api'

interface OpenInIDEButtonProps {
  projectName: string
}

const IDE_OPTIONS: { id: IDEType; label: string; icon: string }[] = [
  { id: 'vscode', label: 'VS Code', icon: '💙' },
  { id: 'windsurf', label: 'Windsurf', icon: '🏄' },
  { id: 'antigravity', label: 'Antigravity', icon: '🚀' },
]

export function OpenInIDEButton({ projectName }: OpenInIDEButtonProps) {
  const [isOpen, setIsOpen] = useState(false)
  const [isLoading, setIsLoading] = useState(false)

  const handleOpenIDE = async (ide: IDEType) => {
    setIsLoading(true)
    setIsOpen(false)
    try {
      await openProjectInIDE(projectName, ide)
    } catch (error) {
      console.error('Failed to open IDE:', error)
      alert(error instanceof Error ? error.message : 'Failed to open IDE')
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="relative">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="neo-btn bg-white text-[var(--color-neo-text)] text-sm"
        disabled={isLoading}
        title="Open in IDE"
      >
        {isLoading ? (
          <Loader2 size={18} className="animate-spin" />
        ) : (
          <Code size={18} />
        )}
        <span className="hidden sm:inline">Open IDE</span>
        <ChevronDown size={16} className={`transition-transform ${isOpen ? 'rotate-180' : ''}`} />
      </button>

      {isOpen && (
        <>
          {/* Backdrop */}
          <div
            className="fixed inset-0 z-40"
            onClick={() => setIsOpen(false)}
          />

          {/* Menu */}
          <div className="absolute top-full right-0 mt-2 neo-dropdown z-50 min-w-[160px]">
            {IDE_OPTIONS.map((ide) => (
              <button
                key={ide.id}
                onClick={() => handleOpenIDE(ide.id)}
                className="w-full neo-dropdown-item flex items-center gap-2"
              >
                <span>{ide.icon}</span>
                <span>{ide.label}</span>
              </button>
            ))}
          </div>
        </>
      )}
    </div>
  )
}
