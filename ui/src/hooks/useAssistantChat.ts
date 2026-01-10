/**
 * Hook for managing assistant chat WebSocket connection
 */

import { useState, useCallback, useRef, useEffect } from 'react'
import type { ChatMessage, AssistantChatServerMessage } from '../lib/types'

type ConnectionStatus = 'disconnected' | 'connecting' | 'connected' | 'error'

interface UseAssistantChatOptions {
  projectName: string
  onError?: (error: string) => void
}

interface UseAssistantChatReturn {
  messages: ChatMessage[]
  isLoading: boolean
  connectionStatus: ConnectionStatus
  conversationId: number | null
  start: (conversationId?: number | null) => void
  sendMessage: (content: string) => void
  disconnect: () => void
  clearMessages: () => void
}

function generateId(): string {
  return `${Date.now()}-${Math.random().toString(36).substring(2, 9)}`
}

// Helper functions for tool call descriptions
function getStringValue(obj: Record<string, unknown>, key: string): string | undefined {
  const value = obj[key]
  return typeof value === 'string' ? value : undefined
}

function getFeatureId(obj: Record<string, unknown>): number | undefined {
  const featureId = obj.feature_id ?? obj.featureId
  return typeof featureId === 'number' ? featureId : undefined
}

function getToolDescription(tool: string, input: Record<string, unknown>): string {
  switch (tool) {
    case 'mcp__features__feature_create':
      return `Creating feature: ${getStringValue(input, 'name') || 'unnamed'}`
    case 'mcp__features__feature_update': {
      const id = getFeatureId(input)
      return id ? `Updating feature #${id}` : 'Updating feature'
    }
    case 'mcp__features__feature_delete': {
      const id = getFeatureId(input)
      return id ? `Deleting feature #${id}` : 'Deleting feature'
    }
    case 'mcp__features__feature_skip': {
      const id = getFeatureId(input)
      return id ? `Skipping feature #${id}` : 'Skipping feature'
    }
    case 'mcp__features__feature_get_stats':
      return 'Getting feature statistics'
    case 'mcp__features__feature_get_next':
      return 'Getting next feature'
    case 'mcp__features__feature_get_for_regression':
      return 'Getting features for regression testing'
    case 'mcp__features__feature_get_existing':
      return 'Listing existing features'
    case 'mcp__features__feature_get_labels':
      return 'Getting feature labels'
    case 'Read':
      return `Reading: ${getStringValue(input, 'file_path') || 'file'}`
    case 'Glob':
      return `Searching files: ${getStringValue(input, 'pattern') || 'pattern'}`
    case 'Grep':
      return `Searching code: ${getStringValue(input, 'pattern') || 'pattern'}`
    case 'WebFetch':
      return `Fetching: ${getStringValue(input, 'url') || 'URL'}`
    case 'WebSearch':
      return `Searching: ${getStringValue(input, 'query') || 'query'}`
    default:
      return `Using tool: ${tool}`
  }
}

export function useAssistantChat({
  projectName,
  onError,
}: UseAssistantChatOptions): UseAssistantChatReturn {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>('disconnected')
  const [conversationId, setConversationId] = useState<number | null>(null)

  const wsRef = useRef<WebSocket | null>(null)
  const currentAssistantMessageRef = useRef<string | null>(null)
  const reconnectAttempts = useRef(0)
  const maxReconnectAttempts = 50 // Increased from 3 to 50
  const connectTimeout = 5000 // 5 second maximum
  const pingIntervalRef = useRef<number | null>(null)
  const reconnectTimeoutRef = useRef<number | null>(null)
  const connectTimeoutRef = useRef<number | null>(null)

  // Clean up on unmount
  useEffect(() => {
    return () => {
      if (pingIntervalRef.current) {
        clearInterval(pingIntervalRef.current)
      }
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current)
      }
      if (connectTimeoutRef.current) {
        clearTimeout(connectTimeoutRef.current)
      }
      if (wsRef.current) {
        wsRef.current.close()
      }
    }
  }, [])

  const connect = useCallback(() => {
    // Prevent multiple connection attempts
    if (wsRef.current?.readyState === WebSocket.OPEN ||
        wsRef.current?.readyState === WebSocket.CONNECTING) {
      return
    }

    setConnectionStatus('connecting')

    // Clear any existing ping interval before new connection
    if (pingIntervalRef.current) {
      clearInterval(pingIntervalRef.current)
      pingIntervalRef.current = null
    }

    // Clear any existing connect timeout
    if (connectTimeoutRef.current) {
      clearTimeout(connectTimeoutRef.current)
      connectTimeoutRef.current = null
    }

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const host = window.location.host
    const wsUrl = `${protocol}//${host}/api/assistant/ws/${encodeURIComponent(projectName)}`

    const ws = new WebSocket(wsUrl)
    wsRef.current = ws

    // Set connection timeout
    connectTimeoutRef.current = window.setTimeout(() => {
      if (ws.readyState !== WebSocket.OPEN) {
        ws.close()
        setConnectionStatus('error')
        onError?.('Connection timeout')
      }
    }, connectTimeout)

    ws.onopen = () => {
      // Verify this is still the current websocket (prevent stale handlers)
      if (wsRef.current !== ws) return

      // Clear connection timeout
      if (connectTimeoutRef.current) {
        clearTimeout(connectTimeoutRef.current)
        connectTimeoutRef.current = null
      }

      setConnectionStatus('connected')
      reconnectAttempts.current = 0

      // Start ping interval to keep connection alive
      pingIntervalRef.current = window.setInterval(() => {
        // Verify this is still the current websocket
        if (wsRef.current !== ws) {
          if (pingIntervalRef.current) {
            clearInterval(pingIntervalRef.current)
            pingIntervalRef.current = null
          }
          return
        }
        if (ws.readyState === WebSocket.OPEN) {
          ws.send(JSON.stringify({ type: 'ping' }))
        }
      }, 30000)
    }

    ws.onclose = () => {
      setConnectionStatus('disconnected')
      if (pingIntervalRef.current) {
        clearInterval(pingIntervalRef.current)
        pingIntervalRef.current = null
      }

      // Attempt reconnection if not intentionally closed
      if (reconnectAttempts.current < maxReconnectAttempts) {
        reconnectAttempts.current++
        const delay = Math.min(1000 * Math.pow(2, reconnectAttempts.current), 10000)
        reconnectTimeoutRef.current = window.setTimeout(connect, delay)
      }
    }

    ws.onerror = () => {
      setConnectionStatus('error')
      onError?.('WebSocket connection error')
    }

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data) as AssistantChatServerMessage

        switch (data.type) {
          case 'text': {
            // Append text to current assistant message or create new one
            setMessages((prev) => {
              const lastMessage = prev[prev.length - 1]
              if (lastMessage?.role === 'assistant' && lastMessage.isStreaming) {
                // Append to existing streaming message
                return [
                  ...prev.slice(0, -1),
                  {
                    ...lastMessage,
                    content: lastMessage.content + data.content,
                  },
                ]
              } else {
                // Create new assistant message
                currentAssistantMessageRef.current = generateId()
                return [
                  ...prev,
                  {
                    id: currentAssistantMessageRef.current,
                    role: 'assistant',
                    content: data.content,
                    timestamp: new Date(),
                    isStreaming: true,
                  },
                ]
              }
            })
            break
          }

          case 'tool_call': {
            // Show tool call as system message with user-friendly description
            const description = getToolDescription(data.tool, data.input)
            setMessages((prev) => [
              ...prev,
              {
                id: generateId(),
                role: 'system',
                content: description,
                timestamp: new Date(),
              },
            ])
            break
          }

          case 'conversation_created': {
            setConversationId(data.conversation_id)
            break
          }

          case 'response_done': {
            setIsLoading(false)

            // Find and mark the most recent streaming assistant message as done
            // (handles cases where tool calls appear between message chunks)
            setMessages((prev) => {
              for (let i = prev.length - 1; i >= 0; i--) {
                if (prev[i].role === 'assistant' && prev[i].isStreaming) {
                  return [
                    ...prev.slice(0, i),
                    { ...prev[i], isStreaming: false },
                    ...prev.slice(i + 1),
                  ]
                }
              }
              return prev
            })
            break
          }

          case 'error': {
            setIsLoading(false)
            onError?.(data.content)

            // Add error as system message
            setMessages((prev) => [
              ...prev,
              {
                id: generateId(),
                role: 'system',
                content: `Error: ${data.content}`,
                timestamp: new Date(),
              },
            ])
            break
          }

          case 'pong': {
            // Keep-alive response, nothing to do
            break
          }
        }
      } catch (e) {
        console.error('Failed to parse WebSocket message:', e)
      }
    }
  }, [projectName, onError])

  const start = useCallback((existingConversationId?: number | null) => {
    connect()

    // Wait for connection then send start message
    const checkAndSend = () => {
      if (wsRef.current?.readyState === WebSocket.OPEN) {
        setIsLoading(true)
        const payload: { type: string; conversation_id?: number } = { type: 'start' }
        if (existingConversationId) {
          payload.conversation_id = existingConversationId
          setConversationId(existingConversationId)
        }
        wsRef.current.send(JSON.stringify(payload))
      } else if (wsRef.current?.readyState === WebSocket.CONNECTING) {
        setTimeout(checkAndSend, 100)
      }
    }

    setTimeout(checkAndSend, 100)
  }, [connect])

  const sendMessage = useCallback((content: string) => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
      onError?.('Not connected')
      return
    }

    // Add user message to chat
    setMessages((prev) => [
      ...prev,
      {
        id: generateId(),
        role: 'user',
        content,
        timestamp: new Date(),
      },
    ])

    setIsLoading(true)

    // Send to server
    wsRef.current.send(
      JSON.stringify({
        type: 'message',
        content,
      })
    )
  }, [onError])

  const disconnect = useCallback(() => {
    reconnectAttempts.current = maxReconnectAttempts // Prevent reconnection

    // Clear all pending timeouts and intervals
    if (pingIntervalRef.current) {
      clearInterval(pingIntervalRef.current)
      pingIntervalRef.current = null
    }
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current)
      reconnectTimeoutRef.current = null
    }
    if (connectTimeoutRef.current) {
      clearTimeout(connectTimeoutRef.current)
      connectTimeoutRef.current = null
    }

    if (wsRef.current) {
      wsRef.current.close()
      wsRef.current = null
    }
    setConnectionStatus('disconnected')
  }, [])

  const clearMessages = useCallback(() => {
    setMessages([])
    setConversationId(null)
  }, [])

  return {
    messages,
    isLoading,
    connectionStatus,
    conversationId,
    start,
    sendMessage,
    disconnect,
    clearMessages,
  }
}
