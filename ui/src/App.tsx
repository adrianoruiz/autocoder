import { useState, useEffect, useCallback, useMemo } from 'react'
import { useTranslation } from 'react-i18next'
import { useProjects, useFeatures, useAgentStatus } from './hooks/useProjects'
import { useProjectWebSocket } from './hooks/useWebSocket'
import { useFeatureSound } from './hooks/useFeatureSound'
import { useCelebration } from './hooks/useCelebration'

const STORAGE_KEY = 'autocoder-selected-project'
import { ProjectSelector } from './components/ProjectSelector'
import { LanguageSelector } from './components/LanguageSelector'
import { KanbanBoard } from './components/KanbanBoard'
import { AgentControl } from './components/AgentControl'
import { ProgressDashboard } from './components/ProgressDashboard'
import { SetupWizard } from './components/SetupWizard'
import { AddFeatureForm } from './components/AddFeatureForm'
import { AddFeaturesChat } from './components/AddFeaturesChat'
import { FeatureModal } from './components/FeatureModal'
import { DebugLogViewer } from './components/DebugLogViewer'
import { AgentThought } from './components/AgentThought'
import { CurrentStepPanel } from './components/CurrentStepPanel'
import { LiveChatPanel } from './components/LiveChatPanel'
import { LiveChatFAB } from './components/LiveChatFAB'
import { AssistantFAB } from './components/AssistantFAB'
import { AssistantPanel } from './components/AssistantPanel'
import { ProcessManager } from './components/ProcessManager'
import { OpenInIDEButton } from './components/OpenInIDEButton'
import SettingsModal from './components/SettingsModal'
import { Plus, Loader2, Sparkles, Settings } from 'lucide-react'
import type { Feature } from './lib/types'

function App() {
  const { t } = useTranslation()

  // Initialize selected project from localStorage
  const [selectedProject, setSelectedProject] = useState<string | null>(() => {
    try {
      return localStorage.getItem(STORAGE_KEY)
    } catch {
      return null
    }
  })
  const [showAddFeature, setShowAddFeature] = useState(false)
  const [showAddFeaturesChat, setShowAddFeaturesChat] = useState(false)
  const [selectedFeature, setSelectedFeature] = useState<Feature | null>(null)
  const [setupComplete, setSetupComplete] = useState(true) // Start optimistic
  const [debugOpen, setDebugOpen] = useState(false)
  const [debugPanelHeight, setDebugPanelHeight] = useState(288) // Default height
  const [assistantOpen, setAssistantOpen] = useState(false)
  const [chatOpen, setChatOpen] = useState(false)
  const [settingsOpen, setSettingsOpen] = useState(false)
  const [typeFilter, setTypeFilter] = useState<'all' | 'feature' | 'bug'>('all')

  const { data: projects, isLoading: projectsLoading } = useProjects()
  const { data: features } = useFeatures(selectedProject)
  const { data: agentStatusData } = useAgentStatus(selectedProject)
  const wsState = useProjectWebSocket(selectedProject)

  // Play sounds when features move between columns
  useFeatureSound(features)

  // Celebrate when all features are complete
  useCelebration(features, selectedProject)

  // Filter features by type
  const filteredFeatures = useMemo(() => {
    if (!features) return { pending: [], in_progress: [], done: [] }

    if (typeFilter === 'all') return features

    return {
      pending: features.pending.filter(f => f.type === typeFilter),
      in_progress: features.in_progress.filter(f => f.type === typeFilter),
      done: features.done.filter(f => f.type === typeFilter)
    }
  }, [features, typeFilter])

  // Persist selected project to localStorage
  const handleSelectProject = useCallback((project: string | null) => {
    setSelectedProject(project)
    try {
      if (project) {
        localStorage.setItem(STORAGE_KEY, project)
      } else {
        localStorage.removeItem(STORAGE_KEY)
      }
    } catch {
      // localStorage not available
    }
  }, [])

  // Validate stored project exists (clear if project was deleted)
  useEffect(() => {
    if (selectedProject && projects && !projects.some(p => p.name === selectedProject)) {
      handleSelectProject(null)
    }
  }, [selectedProject, projects, handleSelectProject])

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Ignore if user is typing in an input
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) {
        return
      }

      // D : Toggle debug window
      if (e.key === 'd' || e.key === 'D') {
        e.preventDefault()
        setDebugOpen(prev => !prev)
      }

      // N : Add new feature (when project selected)
      if ((e.key === 'n' || e.key === 'N') && selectedProject) {
        e.preventDefault()
        setShowAddFeature(true)
      }

      // A : Toggle assistant panel (when project selected)
      if ((e.key === 'a' || e.key === 'A') && selectedProject) {
        e.preventDefault()
        setAssistantOpen(prev => !prev)
      }

      // C : Toggle live chat panel (when project selected)
      if ((e.key === 'c' || e.key === 'C') && selectedProject) {
        e.preventDefault()
        setChatOpen(prev => !prev)
      }

      // I : Open Add Features with AI (when project selected)
      if ((e.key === 'i' || e.key === 'I') && selectedProject) {
        e.preventDefault()
        setShowAddFeaturesChat(true)
      }

      // Escape : Close modals
      if (e.key === 'Escape') {
        if (showAddFeaturesChat) {
          setShowAddFeaturesChat(false)
        } else if (settingsOpen) {
          setSettingsOpen(false)
        } else if (chatOpen) {
          setChatOpen(false)
        } else if (assistantOpen) {
          setAssistantOpen(false)
        } else if (showAddFeature) {
          setShowAddFeature(false)
        } else if (selectedFeature) {
          setSelectedFeature(null)
        } else if (debugOpen) {
          setDebugOpen(false)
        }
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [selectedProject, showAddFeature, showAddFeaturesChat, selectedFeature, debugOpen, assistantOpen, chatOpen, settingsOpen])

  // Combine WebSocket progress with feature data
  const progress = wsState.progress.total > 0 ? wsState.progress : {
    passing: features?.done.length ?? 0,
    total: (features?.pending.length ?? 0) + (features?.in_progress.length ?? 0) + (features?.done.length ?? 0),
    percentage: 0,
  }

  if (progress.total > 0 && progress.percentage === 0) {
    progress.percentage = Math.round((progress.passing / progress.total) * 100 * 10) / 10
  }

  if (!setupComplete) {
    return <SetupWizard onComplete={() => setSetupComplete(true)} />
  }

  return (
    <div className="min-h-screen bg-[var(--color-neo-bg)]">
      {/* Header */}
      <header className="bg-[var(--color-neo-text)] text-white border-b-4 border-[var(--color-neo-border)]">
        <div className="max-w-7xl mx-auto px-4">
          {/* Top Row: Branding + Global Settings */}
          <div className="flex items-center justify-between py-3 border-b border-white/10">
            <div className="flex items-center gap-4">
              <h1 className="font-display text-2xl font-bold tracking-tight uppercase">
                {t('app.title')}
              </h1>

              <div className="w-px h-6 bg-white/20" />

              <ProjectSelector
                projects={projects ?? []}
                selectedProject={selectedProject}
                onSelectProject={handleSelectProject}
                isLoading={projectsLoading}
              />
            </div>

            <div className="flex items-center gap-2">
              <LanguageSelector />
              <button
                onClick={() => setSettingsOpen(true)}
                className="neo-btn bg-white text-[var(--color-neo-text)] border-2 border-[var(--color-neo-border)] hover:bg-gray-50 transition-all text-sm px-3 py-2"
                title="Settings"
              >
                <Settings size={18} />
              </button>
            </div>
          </div>

          {/* Bottom Row: Project Actions */}
          {selectedProject && (
            <div className="flex flex-col gap-3 py-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-4">
                  {/* Add Features */}
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-display font-bold uppercase text-white/60">
                      Add:
                    </span>
                    <button
                      onClick={() => setShowAddFeaturesChat(true)}
                      className="neo-btn bg-gradient-to-r from-purple-500 to-pink-500 text-white border-2 border-[var(--color-neo-border)] shadow-[4px_4px_0px_rgba(0,0,0,1)] hover:shadow-[2px_2px_0px_rgba(0,0,0,1)] hover:translate-x-[2px] hover:translate-y-[2px] transition-all text-sm whitespace-nowrap"
                      title="Add Features with AI (Press I)"
                    >
                      <Sparkles size={16} />
                      AI
                      <kbd className="ml-1 px-1 py-0.5 text-xs bg-black/20 rounded font-mono">
                        I
                      </kbd>
                    </button>

                    <button
                      onClick={() => setShowAddFeature(true)}
                      className="neo-btn neo-btn-primary text-sm whitespace-nowrap"
                      title="Add Feature (Press N)"
                    >
                      <Plus size={16} />
                      Feature
                      <kbd className="ml-1 px-1 py-0.5 text-xs bg-black/20 rounded font-mono">
                        N
                      </kbd>
                    </button>
                  </div>

                  <div className="w-px h-6 bg-white/20" />

                  {/* Agent Control */}
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-display font-bold uppercase text-white/60">
                      Agent:
                    </span>
                    <OpenInIDEButton projectName={selectedProject} />
                    <AgentControl
                      projectName={selectedProject}
                      status={wsState.agentStatus}
                      yoloMode={agentStatusData?.yolo_mode ?? false}
                    />
                  </div>
                </div>
              </div>

              {/* Type Filter Row */}
              {features && (features.pending.length > 0 || features.in_progress.length > 0 || features.done.length > 0) && (
                <div className="flex items-center gap-2">
                  <span className="text-xs font-display font-bold uppercase text-white/60">
                    View:
                  </span>
                  <button
                    onClick={() => setTypeFilter('all')}
                    className={`neo-btn text-xs px-3 py-1 transition-all ${
                      typeFilter === 'all'
                        ? 'bg-[var(--color-neo-accent)] text-white'
                        : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
                    }`}
                  >
                    All
                  </button>
                  <button
                    onClick={() => setTypeFilter('feature')}
                    className={`neo-btn text-xs px-3 py-1 transition-all ${
                      typeFilter === 'feature'
                        ? 'bg-green-600 text-white'
                        : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
                    }`}
                  >
                    ✨ Features
                  </button>
                  <button
                    onClick={() => setTypeFilter('bug')}
                    className={`neo-btn text-xs px-3 py-1 transition-all ${
                      typeFilter === 'bug'
                        ? 'bg-red-600 text-white'
                        : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
                    }`}
                  >
                    🐛 Bugs
                  </button>
                </div>
              )}
            </div>
          )}
        </div>
      </header>

      {/* Main Content */}
      <main
        className="max-w-7xl mx-auto px-4 py-8"
        style={{ paddingBottom: debugOpen ? debugPanelHeight + 32 : undefined }}
      >
        {!selectedProject ? (
          <div className="neo-empty-state mt-12">
            <h2 className="font-display text-2xl font-bold mb-2">
              {t('app.welcome.title')}
            </h2>
            <p className="text-[var(--color-neo-text-secondary)] mb-4">
              {t('app.welcome.description')}
            </p>
          </div>
        ) : (
          <div className="space-y-8">
            {/* Progress Dashboard */}
            <ProgressDashboard
              passing={progress.passing}
              total={progress.total}
              percentage={progress.percentage}
              isConnected={wsState.isConnected}
            />

            {/* Agent Thought - shows latest agent narrative */}
            <AgentThought
              logs={wsState.logs}
              agentStatus={wsState.agentStatus}
            />

            {/* Current Step Panel - shows currently executing step */}
            {wsState.agentStatus === 'running' && (
              <CurrentStepPanel
                projectName={selectedProject}
                currentFeatureId={wsState.currentFeatureId}
                stepUpdates={wsState.stepUpdates}
              />
            )}

            {/* Initializing Features State - show when agent is running but no features yet */}
            {features &&
             features.pending.length === 0 &&
             features.in_progress.length === 0 &&
             features.done.length === 0 &&
             wsState.agentStatus === 'running' && (
              <div className="neo-card p-8 text-center">
                <Loader2 size={32} className="animate-spin mx-auto mb-4 text-[var(--color-neo-progress)]" />
                <h3 className="font-display font-bold text-xl mb-2">
                  {t('app.initializing.title')}
                </h3>
                <p className="text-[var(--color-neo-text-secondary)]">
                  {t('app.initializing.description')}
                </p>
              </div>
            )}

            {/* Kanban Board */}
            <KanbanBoard
              features={filteredFeatures}
              projectName={selectedProject}
              onFeatureClick={setSelectedFeature}
            />
          </div>
        )}
      </main>

      {/* Add Feature Modal */}
      {showAddFeature && selectedProject && (
        <AddFeatureForm
          projectName={selectedProject}
          onClose={() => setShowAddFeature(false)}
        />
      )}

      {/* Add Features with AI Modal */}
      {showAddFeaturesChat && selectedProject && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
          <div className="w-full max-w-4xl h-[80vh] mx-4 bg-white border-4 border-[var(--color-neo-border)] shadow-[8px_8px_0px_rgba(0,0,0,1)] overflow-hidden">
            <AddFeaturesChat
              projectName={selectedProject}
              onClose={() => setShowAddFeaturesChat(false)}
              onFeaturesAdded={() => {
                // Features will be automatically refreshed via React Query
              }}
            />
          </div>
        </div>
      )}

      {/* Feature Detail Modal */}
      {selectedFeature && selectedProject && (
        <FeatureModal
          feature={selectedFeature}
          projectName={selectedProject}
          onClose={() => setSelectedFeature(null)}
        />
      )}

      {/* Debug Log Viewer - fixed to bottom */}
      {selectedProject && (
        <DebugLogViewer
          logs={wsState.logs}
          isOpen={debugOpen}
          onToggle={() => setDebugOpen(!debugOpen)}
          onClear={wsState.clearLogs}
          onHeightChange={setDebugPanelHeight}
        />
      )}

      {/* Assistant FAB and Panel */}
      {selectedProject && (
        <>
          <AssistantFAB
            onClick={() => setAssistantOpen(!assistantOpen)}
            isOpen={assistantOpen}
          />
          <AssistantPanel
            projectName={selectedProject}
            isOpen={assistantOpen}
            onClose={() => setAssistantOpen(false)}
          />
        </>
      )}

      {/* Settings Modal */}
      <SettingsModal
        isOpen={settingsOpen}
        onClose={() => setSettingsOpen(false)}
      />

      {/* Live Chat FAB and Panel */}
      {selectedProject && (
        <>
          <LiveChatFAB
            onClick={() => setChatOpen(!chatOpen)}
            isOpen={chatOpen}
          />

          {/* Live Chat Panel - Right Sidebar */}
          <div
            className={`fixed top-0 right-0 h-screen w-[400px] bg-white border-l-4 border-[var(--color-neo-border)] shadow-[-8px_0px_0px_rgba(0,0,0,1)] z-50 transform transition-transform duration-300 ${
              chatOpen ? 'translate-x-0' : 'translate-x-full'
            }`}
          >
            <LiveChatPanel
              chatMessages={wsState.chatMessages}
              agentStatus={wsState.agentStatus}
              onSendMessage={wsState.sendMessage}
              isConnected={wsState.isConnected}
              onClose={() => setChatOpen(false)}
            />
          </div>
        </>
      )}

      {/* Process Manager - Global (always visible) */}
      <ProcessManager />
    </div>
  )
}

export default App
