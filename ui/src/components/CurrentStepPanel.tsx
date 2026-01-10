import { Loader2, CheckCircle2, Circle } from 'lucide-react'
import { useQuery } from '@tanstack/react-query'
import { getFeatureSteps } from '../lib/api'
import type { WSStepUpdateMessage } from '../lib/types'
import { useEffect, useState } from 'react'

interface CurrentStepPanelProps {
  projectName: string
  currentFeatureId: number | null
  stepUpdates: WSStepUpdateMessage[]
}

export function CurrentStepPanel({
  projectName,
  currentFeatureId,
  stepUpdates,
}: CurrentStepPanelProps) {
  const [displayedStep, setDisplayedStep] = useState<{
    featureId: number
    stepIndex: number
    stepText: string
    status: 'started' | 'completed'
  } | null>(null)

  // Fetch step progress data for current feature
  const { data: stepsData } = useQuery({
    queryKey: ['featureSteps', projectName, currentFeatureId],
    queryFn: () => currentFeatureId
      ? getFeatureSteps(projectName, currentFeatureId)
      : null,
    enabled: !!currentFeatureId,
    refetchInterval: 2000,
  })

  // Update displayed step when step updates arrive
  useEffect(() => {
    if (stepUpdates.length > 0) {
      const latestUpdate = stepUpdates[stepUpdates.length - 1]

      // Find step text from stepsData
      const step = stepsData?.steps.find(
        s => s.step_index === latestUpdate.step_index
      )

      if (step) {
        setDisplayedStep({
          featureId: latestUpdate.feature_id,
          stepIndex: latestUpdate.step_index,
          stepText: step.step_text,
          status: latestUpdate.status,
        })
      }
    }
  }, [stepUpdates, stepsData])

  // Auto-clear completed steps after 3 seconds
  useEffect(() => {
    if (displayedStep?.status === 'completed') {
      const timer = setTimeout(() => {
        setDisplayedStep(null)
      }, 3000)
      return () => clearTimeout(timer)
    }
  }, [displayedStep])

  // If no current step, show "idle" state
  if (!displayedStep && (!stepsData || !currentFeatureId)) {
    return (
      <div className="neo-card p-4 bg-[var(--color-neo-bg)]">
        <div className="flex items-center gap-3">
          <Circle size={20} className="text-[var(--color-neo-text-secondary)]" />
          <div className="flex-1">
            <div className="font-mono text-sm text-[var(--color-neo-text-secondary)]">
              No active step
            </div>
            <div className="text-xs text-[var(--color-neo-text-secondary)]">
              Waiting for agent to start...
            </div>
          </div>
        </div>
      </div>
    )
  }

  // Find current in-progress step from stepsData if no displayedStep
  const currentInProgressStep = !displayedStep && stepsData?.steps.find(
    s => s.started_at && !s.completed
  )

  const stepToShow = displayedStep || (currentInProgressStep ? {
    featureId: currentFeatureId!,
    stepIndex: currentInProgressStep.step_index,
    stepText: currentInProgressStep.step_text,
    status: 'started' as const,
  } : null)

  if (!stepToShow) {
    return (
      <div className="neo-card p-4 bg-[var(--color-neo-bg)]">
        <div className="flex items-center gap-3">
          <Circle size={20} className="text-[var(--color-neo-text-secondary)]" />
          <div className="flex-1">
            <div className="font-mono text-sm text-[var(--color-neo-text-secondary)]">
              No active step
            </div>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className={`neo-card p-4 ${
      stepToShow.status === 'completed'
        ? 'border-[var(--color-neo-done)] bg-[var(--color-neo-done)]/10'
        : 'border-[var(--color-neo-progress)] bg-[var(--color-neo-progress)]/10 animate-pulse-neo'
    }`}>
      <div className="flex items-start gap-3">
        {stepToShow.status === 'completed' ? (
          <CheckCircle2
            size={20}
            className="text-[var(--color-neo-done)] flex-shrink-0 mt-0.5"
          />
        ) : (
          <Loader2
            size={20}
            className="text-[var(--color-neo-progress)] animate-spin flex-shrink-0 mt-0.5"
          />
        )}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <span className="neo-badge bg-[var(--color-neo-accent)] text-white text-xs">
              Step {stepToShow.stepIndex + 1}
            </span>
            <span className={`text-xs font-bold ${
              stepToShow.status === 'completed'
                ? 'text-[var(--color-neo-done)]'
                : 'text-[var(--color-neo-progress)]'
            }`}>
              {stepToShow.status === 'completed' ? 'COMPLETED' : 'IN PROGRESS'}
            </span>
          </div>
          <div className="font-mono text-sm break-words">
            {stepToShow.stepText}
          </div>
          {stepsData && (
            <div className="mt-2 text-xs text-[var(--color-neo-text-secondary)]">
              Progress: {stepsData.completed_steps}/{stepsData.total_steps} steps
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
