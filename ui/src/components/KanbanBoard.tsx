import { useTranslation } from 'react-i18next'
import { KanbanColumn } from './KanbanColumn'
import type { Feature, FeatureListResponse } from '../lib/types'

interface KanbanBoardProps {
  features: FeatureListResponse | undefined
  onFeatureClick: (feature: Feature) => void
}

export function KanbanBoard({ features, onFeatureClick }: KanbanBoardProps) {
  const { t } = useTranslation()

  if (!features) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {['pending', 'inProgress', 'done'].map(key => (
          <div key={key} className="neo-card p-4">
            <div className="h-8 bg-[var(--color-neo-bg)] animate-pulse mb-4" />
            <div className="space-y-3">
              {[1, 2, 3].map(i => (
                <div key={i} className="h-24 bg-[var(--color-neo-bg)] animate-pulse" />
              ))}
            </div>
          </div>
        ))}
      </div>
    )
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
      <KanbanColumn
        title={t('kanban.pending')}
        count={features.pending.length}
        features={features.pending}
        color="pending"
        onFeatureClick={onFeatureClick}
      />
      <KanbanColumn
        title={t('kanban.inProgress')}
        count={features.in_progress.length}
        features={features.in_progress}
        color="progress"
        onFeatureClick={onFeatureClick}
      />
      <KanbanColumn
        title={t('kanban.done')}
        count={features.done.length}
        features={features.done}
        color="done"
        onFeatureClick={onFeatureClick}
      />
    </div>
  )
}
