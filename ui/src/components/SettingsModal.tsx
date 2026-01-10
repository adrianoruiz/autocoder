/**
 * Settings Modal Component
 * Neo-brutalist design for global settings (YOLO mode & model selection)
 */

import { useState, useEffect } from 'react'
import { X, Zap } from 'lucide-react'
import { useSettings, useAvailableModels, useUpdateSettings } from '../hooks/useProjects'

interface SettingsModalProps {
  isOpen: boolean
  onClose: () => void
}

export default function SettingsModal({ isOpen, onClose }: SettingsModalProps) {
  const { data: settings } = useSettings()
  const { data: modelsData } = useAvailableModels()
  const updateSettings = useUpdateSettings()

  // Local state for immediate UI feedback
  const [yoloMode, setYoloMode] = useState(settings?.yolo_mode ?? false)
  const [selectedModel, setSelectedModel] = useState(settings?.model ?? '')

  // Sync with server data when it changes
  useEffect(() => {
    if (settings) {
      setYoloMode(settings.yolo_mode)
      setSelectedModel(settings.model)
    }
  }, [settings])

  if (!isOpen) return null

  const handleSave = async () => {
    try {
      await updateSettings.mutateAsync({
        yolo_mode: yoloMode,
        model: selectedModel,
      })
      onClose()
    } catch (error) {
      console.error('Failed to save settings:', error)
    }
  }

  const handleYoloToggle = () => {
    setYoloMode(!yoloMode)
  }

  const handleModelSelect = (modelId: string) => {
    setSelectedModel(modelId)
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/50"
        onClick={onClose}
      />

      {/* Modal */}
      <div
        className="relative z-10 w-full max-w-md bg-white border-4 border-[var(--color-neo-border)] p-6"
        style={{ boxShadow: 'var(--shadow-neo-xl)' }}
      >
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-2xl font-bold font-[var(--font-neo-display)] text-[var(--color-neo-text)]">
            Settings
          </h2>
          <button
            onClick={onClose}
            className="p-2 hover:bg-gray-100 transition-colors border-2 border-[var(--color-neo-border)]"
            style={{ boxShadow: 'var(--shadow-neo-sm)' }}
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* YOLO Mode Toggle */}
        <div className="mb-6">
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-2">
              <Zap className="w-5 h-5 text-[var(--color-neo-pending)]" />
              <label className="text-lg font-bold font-[var(--font-neo-display)] text-[var(--color-neo-text)]">
                YOLO Mode
              </label>
            </div>
            <button
              onClick={handleYoloToggle}
              className={`
                relative w-16 h-8 border-3 border-[var(--color-neo-border)] transition-colors
                ${yoloMode ? 'bg-[var(--color-neo-pending)]' : 'bg-gray-200'}
              `}
              style={{ boxShadow: 'var(--shadow-neo-sm)' }}
            >
              <div
                className={`
                  absolute top-1 h-6 w-6 bg-white border-2 border-[var(--color-neo-border)] transition-transform
                  ${yoloMode ? 'translate-x-8' : 'translate-x-1'}
                `}
              />
            </button>
          </div>
          <p className="text-sm text-[var(--color-neo-text-secondary)] font-[var(--font-neo-sans)]">
            Skip testing for faster feature iteration (prototyping mode)
          </p>
        </div>

        {/* Model Selection */}
        <div className="mb-8">
          <label className="block text-lg font-bold font-[var(--font-neo-display)] text-[var(--color-neo-text)] mb-3">
            AI Model
          </label>
          <div className="flex flex-col gap-2">
            {modelsData?.models.map((model) => (
              <button
                key={model.id}
                onClick={() => handleModelSelect(model.id)}
                className={`
                  flex-1 p-4 text-left border-3 border-[var(--color-neo-border)] font-bold font-[var(--font-neo-sans)]
                  transition-all hover:translate-x-0.5 hover:translate-y-0.5
                  ${
                    selectedModel === model.id
                      ? 'bg-[var(--color-neo-accent)] text-white'
                      : 'bg-white text-[var(--color-neo-text)] hover:bg-gray-50'
                  }
                `}
                style={{
                  boxShadow:
                    selectedModel === model.id
                      ? 'var(--shadow-neo-sm)'
                      : 'var(--shadow-neo-md)',
                }}
              >
                <div className="flex items-center justify-between">
                  <span>{model.name}</span>
                  {model.id === modelsData.default && (
                    <span className="text-xs px-2 py-1 bg-black text-white font-mono">
                      DEFAULT
                    </span>
                  )}
                  {selectedModel === model.id && (
                    <span className="text-2xl">✓</span>
                  )}
                </div>
              </button>
            ))}
          </div>
        </div>

        {/* Actions */}
        <div className="flex gap-3">
          <button
            onClick={onClose}
            className="flex-1 px-6 py-3 bg-white border-3 border-[var(--color-neo-border)] font-bold font-[var(--font-neo-sans)] text-[var(--color-neo-text)] hover:bg-gray-50 transition-all hover:translate-x-0.5 hover:translate-y-0.5"
            style={{ boxShadow: 'var(--shadow-neo-md)' }}
          >
            Cancel
          </button>
          <button
            onClick={handleSave}
            disabled={updateSettings.isPending}
            className="flex-1 px-6 py-3 bg-[var(--color-neo-accent)] border-3 border-[var(--color-neo-border)] font-bold font-[var(--font-neo-sans)] text-white hover:bg-[var(--color-neo-accent)]/90 transition-all hover:translate-x-0.5 hover:translate-y-0.5 disabled:opacity-50 disabled:cursor-not-allowed"
            style={{ boxShadow: 'var(--shadow-neo-md)' }}
          >
            {updateSettings.isPending ? 'Saving...' : 'Save'}
          </button>
        </div>
      </div>
    </div>
  )
}
