import { useState, useRef, useEffect } from 'react'
import { Send, MessageSquare, Circle, X } from 'lucide-react'
import type { AgentStatus } from '../lib/types'

interface LiveChatPanelProps {
  chatMessages: Array<{ content: string; timestamp: string }>
  agentStatus: AgentStatus
  onSendMessage: (message: string) => void
  isConnected: boolean
  onClose: () => void
}

export function LiveChatPanel({
  chatMessages,
  agentStatus,
  onSendMessage,
  isConnected,
  onClose,
}: LiveChatPanelProps) {
  const [message, setMessage] = useState('')
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [chatMessages])

  const handleSend = () => {
    if (message.trim() && agentStatus === 'running' && isConnected) {
      onSendMessage(message.trim())
      setMessage('')
      inputRef.current?.focus()
    }
  }

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const isDisabled = agentStatus !== 'running' || !isConnected

  return (
    <div className="neo-card flex flex-col h-full">
      {/* Header */}
      <div className="px-4 py-3 border-b-3 border-[var(--color-neo-border)] bg-[var(--color-neo-accent)]">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <MessageSquare size={20} className="text-white" />
            <h2 className="font-display text-lg font-bold uppercase text-white">
              Live Chat
            </h2>
          </div>

          {/* Status Indicator + Close Button */}
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-2">
              <Circle
                size={12}
                className={`${
                  agentStatus === 'running' && isConnected
                    ? 'fill-green-400 text-green-400 animate-pulse'
                    : 'fill-gray-400 text-gray-400'
                }`}
              />
              <span className="text-xs font-mono text-white">
                {agentStatus === 'running' && isConnected
                  ? 'Active'
                  : agentStatus === 'running'
                  ? 'Connecting...'
                  : 'Inactive'}
              </span>
            </div>
            <button
              onClick={onClose}
              className="p-1 hover:bg-white/20 rounded transition-colors"
              title="Close chat (Press C or Esc)"
            >
              <X size={20} className="text-white" />
            </button>
          </div>
        </div>
      </div>

      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto p-4 space-y-3 bg-[var(--color-neo-bg)]">
        {chatMessages.length === 0 ? (
          <div className="flex items-center justify-center h-full text-center">
            <div className="text-[var(--color-neo-text-secondary)]">
              <MessageSquare size={48} className="mx-auto mb-2 opacity-30" />
              <p className="font-mono text-sm">
                {agentStatus === 'running'
                  ? 'Start chatting with the agent...'
                  : 'Start the agent to begin chatting'}
              </p>
            </div>
          </div>
        ) : (
          chatMessages.map((msg, index) => {
            // Simple heuristic: messages from agent typically start with agent indicators
            // This will be improved when we have proper message metadata
            const isAgent = msg.content.startsWith('Agent:') ||
                           msg.content.includes('🤖') ||
                           index % 2 === 1 // Temporary: assume alternating messages

            return (
              <div
                key={`${msg.timestamp}-${index}`}
                className={`flex ${isAgent ? 'justify-start' : 'justify-end'}`}
              >
                <div
                  className={`max-w-[80%] p-3 border-3 border-[var(--color-neo-border)] ${
                    isAgent
                      ? 'bg-white'
                      : 'bg-[var(--color-neo-accent)] text-white'
                  }`}
                >
                  <div className="font-mono text-sm whitespace-pre-wrap break-words">
                    {msg.content}
                  </div>
                  <div
                    className={`mt-1 text-xs font-mono ${
                      isAgent
                        ? 'text-[var(--color-neo-text-secondary)]'
                        : 'text-white/70'
                    }`}
                  >
                    {new Date(msg.timestamp).toLocaleTimeString()}
                  </div>
                </div>
              </div>
            )
          })
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input Area */}
      <div className="p-4 border-t-3 border-[var(--color-neo-border)] bg-white">
        {isDisabled && (
          <div className="mb-2 p-2 bg-yellow-50 border-2 border-yellow-400 text-xs font-mono text-yellow-800">
            ⚠️ {agentStatus !== 'running' ? 'Start the agent to chat' : 'Connecting to agent...'}
          </div>
        )}

        <div className="flex gap-2">
          <input
            ref={inputRef}
            type="text"
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            onKeyPress={handleKeyPress}
            disabled={isDisabled}
            placeholder={
              isDisabled
                ? 'Agent must be running...'
                : 'Type a message...'
            }
            className="flex-1 px-3 py-2 font-mono text-sm border-3 border-[var(--color-neo-border)] bg-white focus:outline-none focus:ring-2 focus:ring-[var(--color-neo-accent)] disabled:bg-gray-100 disabled:text-gray-400"
          />

          <button
            onClick={handleSend}
            disabled={isDisabled || !message.trim()}
            className="neo-btn bg-[var(--color-neo-accent)] text-white border-3 border-[var(--color-neo-border)] disabled:opacity-50 disabled:cursor-not-allowed px-4"
            title="Send message (Enter)"
          >
            <Send size={18} />
          </button>
        </div>

        <div className="mt-2 text-xs font-mono text-[var(--color-neo-text-secondary)]">
          Press <kbd className="px-1 py-0.5 bg-gray-200 border border-gray-400 rounded">Enter</kbd> to send
        </div>
      </div>
    </div>
  )
}
