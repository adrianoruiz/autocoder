import { useState } from 'react'
import { X, CheckCircle2, Circle, SkipForward, Trash2, Loader2, AlertCircle, Edit2, Save, Plus, Minus } from 'lucide-react'
import { useSkipFeature, useDeleteFeature, useUpdateFeature } from '../hooks/useProjects'
import type { Feature } from '../lib/types'

interface FeatureModalProps {
  feature: Feature
  projectName: string
  onClose: () => void
}

interface EditableStep {
  id: string
  content: string
}

export function FeatureModal({ feature, projectName, onClose }: FeatureModalProps) {
  const [error, setError] = useState<string | null>(null)
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false)
  const [isEditMode, setIsEditMode] = useState(false)

  // Editable fields
  const [editCategory, setEditCategory] = useState(feature.category)
  const [editName, setEditName] = useState(feature.name)
  const [editDescription, setEditDescription] = useState(feature.description)
  const [editSteps, setEditSteps] = useState<EditableStep[]>(
    feature.steps.map((step, index) => ({ id: `step-${index}`, content: step }))
  )

  const skipFeature = useSkipFeature(projectName)
  const deleteFeature = useDeleteFeature(projectName)
  const updateFeature = useUpdateFeature(projectName)

  const handleSkip = async () => {
    setError(null)
    try {
      await skipFeature.mutateAsync(feature.id)
      onClose()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to skip feature')
    }
  }

  const handleDelete = async () => {
    setError(null)
    try {
      await deleteFeature.mutateAsync(feature.id)
      onClose()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete feature')
    }
  }

  const handleEdit = () => {
    setIsEditMode(true)
    setError(null)
  }

  const handleCancelEdit = () => {
    setIsEditMode(false)
    // Reset to original values
    setEditCategory(feature.category)
    setEditName(feature.name)
    setEditDescription(feature.description)
    setEditSteps(feature.steps.map((step, index) => ({ id: `step-${index}`, content: step })))
    setError(null)
  }

  const handleSave = async () => {
    setError(null)

    // Validation
    if (!editCategory.trim()) {
      setError('Category cannot be empty')
      return
    }
    if (!editName.trim()) {
      setError('Name cannot be empty')
      return
    }
    if (!editDescription.trim()) {
      setError('Description cannot be empty')
      return
    }
    if (editSteps.length === 0 || editSteps.some(step => !step.content.trim())) {
      setError('All steps must have content')
      return
    }

    try {
      await updateFeature.mutateAsync({
        featureId: feature.id,
        update: {
          category: editCategory.trim(),
          name: editName.trim(),
          description: editDescription.trim(),
          steps: editSteps.map(step => step.content.trim()),
        },
      })
      setIsEditMode(false)
      onClose()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update feature')
    }
  }

  const handleAddStep = () => {
    setEditSteps([...editSteps, { id: `step-${Date.now()}`, content: '' }])
  }

  const handleRemoveStep = (id: string) => {
    if (editSteps.length > 1) {
      setEditSteps(editSteps.filter(step => step.id !== id))
    }
  }

  const handleStepChange = (id: string, content: string) => {
    setEditSteps(editSteps.map(step => (step.id === id ? { ...step, content } : step)))
  }

  return (
    <div className="neo-modal-backdrop" onClick={onClose}>
      <div
        className="neo-modal w-full max-w-2xl p-0"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-start justify-between p-6 border-b-3 border-[var(--color-neo-border)]">
          <div className="flex-1">
            {isEditMode ? (
              <div className="space-y-3">
                <input
                  type="text"
                  value={editCategory}
                  onChange={(e) => setEditCategory(e.target.value)}
                  className="neo-input w-full"
                  placeholder="Category"
                />
                <input
                  type="text"
                  value={editName}
                  onChange={(e) => setEditName(e.target.value)}
                  className="neo-input w-full"
                  placeholder="Feature name"
                />
              </div>
            ) : (
              <>
                <span className="neo-badge bg-[var(--color-neo-accent)] text-white mb-2">
                  {feature.category}
                </span>
                <h2 className="font-display text-2xl font-bold">
                  {feature.name}
                </h2>
              </>
            )}
          </div>
          <button
            onClick={onClose}
            className="neo-btn neo-btn-ghost p-2"
          >
            <X size={24} />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 space-y-6">
          {/* Error Message */}
          {error && (
            <div className="flex items-center gap-3 p-4 bg-[var(--color-neo-danger)] text-white border-3 border-[var(--color-neo-border)]">
              <AlertCircle size={20} />
              <span>{error}</span>
              <button
                onClick={() => setError(null)}
                className="ml-auto"
              >
                <X size={16} />
              </button>
            </div>
          )}

          {/* Status */}
          <div className="flex items-center gap-3 p-4 bg-[var(--color-neo-bg)] border-3 border-[var(--color-neo-border)]">
            {feature.passes ? (
              <>
                <CheckCircle2 size={24} className="text-[var(--color-neo-done)]" />
                <span className="font-display font-bold text-[var(--color-neo-done)]">
                  COMPLETE
                </span>
              </>
            ) : (
              <>
                <Circle size={24} className="text-[var(--color-neo-text-secondary)]" />
                <span className="font-display font-bold text-[var(--color-neo-text-secondary)]">
                  PENDING
                </span>
              </>
            )}
            <span className="ml-auto font-mono text-sm">
              Priority: #{feature.priority}
            </span>
          </div>

          {/* Description */}
          <div>
            <h3 className="font-display font-bold mb-2 uppercase text-sm">
              Description
            </h3>
            {isEditMode ? (
              <textarea
                value={editDescription}
                onChange={(e) => setEditDescription(e.target.value)}
                className="neo-input w-full min-h-[100px]"
                placeholder="Feature description"
              />
            ) : (
              <p className="text-[var(--color-neo-text-secondary)]">
                {feature.description}
              </p>
            )}
          </div>

          {/* Steps */}
          {(isEditMode || feature.steps.length > 0) && (
            <div>
              <div className="flex items-center justify-between mb-2">
                <h3 className="font-display font-bold uppercase text-sm">
                  Test Steps
                </h3>
                {isEditMode && (
                  <button
                    onClick={handleAddStep}
                    className="neo-btn neo-btn-sm neo-btn-primary"
                  >
                    <Plus size={16} />
                    Add Step
                  </button>
                )}
              </div>
              {isEditMode ? (
                <div className="space-y-2">
                  {editSteps.map((step, index) => (
                    <div key={step.id} className="flex gap-2">
                      <span className="font-mono text-sm pt-3">{index + 1}.</span>
                      <input
                        type="text"
                        value={step.content}
                        onChange={(e) => handleStepChange(step.id, e.target.value)}
                        className="neo-input flex-1"
                        placeholder={`Step ${index + 1}`}
                      />
                      {editSteps.length > 1 && (
                        <button
                          onClick={() => handleRemoveStep(step.id)}
                          className="neo-btn neo-btn-ghost p-2"
                        >
                          <Minus size={18} />
                        </button>
                      )}
                    </div>
                  ))}
                </div>
              ) : (
                <ol className="list-decimal list-inside space-y-2">
                  {feature.steps.map((step, index) => (
                    <li
                      key={index}
                      className="p-3 bg-[var(--color-neo-bg)] border-3 border-[var(--color-neo-border)]"
                    >
                      {step}
                    </li>
                  ))}
                </ol>
              )}
            </div>
          )}
        </div>

        {/* Actions */}
        <div className="p-6 border-t-3 border-[var(--color-neo-border)] bg-[var(--color-neo-bg)]">
          {showDeleteConfirm ? (
            <div className="space-y-4">
              <p className="font-bold text-center">
                {feature.passes
                  ? 'Are you sure you want to delete this feature? Note: The code will remain in the codebase.'
                  : 'Are you sure you want to delete this feature?'}
              </p>
              <div className="flex gap-3">
                <button
                  onClick={handleDelete}
                  disabled={deleteFeature.isPending}
                  className="neo-btn neo-btn-danger flex-1"
                >
                  {deleteFeature.isPending ? (
                    <Loader2 size={18} className="animate-spin" />
                  ) : (
                    'Yes, Delete'
                  )}
                </button>
                <button
                  onClick={() => setShowDeleteConfirm(false)}
                  disabled={deleteFeature.isPending}
                  className="neo-btn neo-btn-ghost flex-1"
                >
                  Cancel
                </button>
              </div>
            </div>
          ) : isEditMode ? (
            <div className="flex gap-3">
              <button
                onClick={handleSave}
                disabled={updateFeature.isPending}
                className="neo-btn neo-btn-primary flex-1"
              >
                {updateFeature.isPending ? (
                  <Loader2 size={18} className="animate-spin" />
                ) : (
                  <>
                    <Save size={18} />
                    Save Changes
                  </>
                )}
              </button>
              <button
                onClick={handleCancelEdit}
                disabled={updateFeature.isPending}
                className="neo-btn neo-btn-ghost flex-1"
              >
                Cancel
              </button>
            </div>
          ) : (
            <div className="flex gap-3">
              <button
                onClick={handleEdit}
                className="neo-btn neo-btn-primary flex-1"
              >
                <Edit2 size={18} />
                Edit
              </button>
              {!feature.passes && (
                <button
                  onClick={handleSkip}
                  disabled={skipFeature.isPending}
                  className="neo-btn neo-btn-warning flex-1"
                >
                  {skipFeature.isPending ? (
                    <Loader2 size={18} className="animate-spin" />
                  ) : (
                    <>
                      <SkipForward size={18} />
                      Skip
                    </>
                  )}
                </button>
              )}
              <button
                onClick={() => setShowDeleteConfirm(true)}
                disabled={skipFeature.isPending}
                className="neo-btn neo-btn-danger"
              >
                <Trash2 size={18} />
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
