import { CheckCircle2, Circle, Loader2 } from 'lucide-react'
import { useQuery } from '@tanstack/react-query'
import { getFeatureSteps } from '../lib/api'
import type { Feature } from '../lib/types'

interface FeatureCardProps {
  feature: Feature
  projectName: string
  onClick: () => void
  isInProgress?: boolean
}

// Generate consistent color for category
function getCategoryColor(category: string): string {
  const colors = [
    '#ff006e', // pink
    '#00b4d8', // cyan
    '#70e000', // green
    '#ffd60a', // yellow
    '#ff5400', // orange
    '#8338ec', // purple
    '#3a86ff', // blue
  ]

  let hash = 0
  for (let i = 0; i < category.length; i++) {
    hash = category.charCodeAt(i) + ((hash << 5) - hash)
  }

  return colors[Math.abs(hash) % colors.length]
}

export function FeatureCard({ feature, projectName, onClick, isInProgress }: FeatureCardProps) {
  const categoryColor = getCategoryColor(feature.category)

  // Fetch step progress data
  const { data: stepsData } = useQuery({
    queryKey: ['featureSteps', projectName, feature.id],
    queryFn: () => getFeatureSteps(projectName, feature.id),
    refetchInterval: 2000, // Refresh every 2 seconds for live updates
  })

  return (
    <button
      onClick={onClick}
      className={`
        w-full text-left neo-card p-4 cursor-pointer
        ${isInProgress ? 'animate-pulse-neo' : ''}
        ${feature.passes ? 'border-[var(--color-neo-done)]' : ''}
      `}
    >
      {/* Header */}
      <div className="flex items-start justify-between gap-2 mb-2">
        <div className="flex items-center gap-2 flex-wrap">
          <span
            className="neo-badge"
            style={{ backgroundColor: categoryColor, color: 'white' }}
          >
            {feature.category}
          </span>
          {/* Type badge */}
          <span
            className={`neo-badge text-xs ${
              feature.type === 'bug'
                ? 'bg-red-600 text-white'
                : 'bg-green-600 text-white'
            }`}
          >
            {feature.type === 'bug' ? '🐛 BUG' : '✨ FEATURE'}
          </span>
        </div>
        <span className="font-mono text-sm text-[var(--color-neo-text-secondary)]">
          #{feature.priority}
        </span>
      </div>

      {/* Name */}
      <h3 className="font-display font-bold mb-1 line-clamp-2">
        {feature.name}
      </h3>

      {/* Description */}
      <p className="text-sm text-[var(--color-neo-text-secondary)] line-clamp-2 mb-3">
        {feature.description}
      </p>

      {/* Progress bar */}
      {stepsData && stepsData.total_steps > 0 && (
        <div className="mb-3">
          <div className="flex items-center gap-2 mb-1">
            <span className="font-mono text-xs font-bold">
              {stepsData.completed_steps}/{stepsData.total_steps} steps
            </span>
            <div className="flex-1 h-2 bg-[var(--color-neo-bg)] border-2 border-[var(--color-neo-border)] overflow-hidden">
              <div
                className="h-full bg-[var(--color-neo-done)] transition-all duration-300"
                style={{
                  width: `${(stepsData.completed_steps / stepsData.total_steps) * 100}%`,
                }}
              />
            </div>
          </div>
        </div>
      )}

      {/* Status */}
      <div className="flex items-center gap-2 text-sm flex-wrap">
        {isInProgress ? (
          <>
            <Loader2 size={16} className="animate-spin text-[var(--color-neo-progress)]" />
            <span className="text-[var(--color-neo-progress)] font-bold">Processing...</span>
          </>
        ) : feature.passes ? (
          <>
            <CheckCircle2 size={16} className="text-[var(--color-neo-done)]" />
            <span className="text-[var(--color-neo-done)] font-bold">Complete</span>
          </>
        ) : (
          <>
            <Circle size={16} className="text-[var(--color-neo-text-secondary)]" />
            <span className="text-[var(--color-neo-text-secondary)]">Pending</span>
          </>
        )}
        {/* Show agent ID if assigned (parallel mode) */}
        {feature.assigned_agent_id && (
          <span className="neo-badge bg-purple-600 text-white text-xs">
            🤖 {feature.assigned_agent_id}
          </span>
        )}
      </div>
    </button>
  )
}
