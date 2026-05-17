import { useRef, useCallback, useState, useEffect } from 'react'

export interface WSMessage {
  type: string
  phase_index?: number
  phase_name?: string
  total_phases?: number
  chunk?: string
  file_path?: string
  message?: string
  current?: number
  total?: number
  error?: string
}

export function useWebSocket() {
  const wsRef = useRef<WebSocket | null>(null)
  const reconnectTimerRef = useRef<number | null>(null)
  const isGeneratingRef = useRef(false)
  const [connected, setConnected] = useState(false)
  const [streamContent, setStreamContent] = useState('')
  const [currentPhase, setCurrentPhase] = useState(-1)
  const [phases, setPhases] = useState<Array<{ name: string; status: string }>>([])
  const [progress, setProgress] = useState({ current: 0, total: 5 })
  const [awaitingApproval, setAwaitingApproval] = useState(false)
  const [awaitingVersion, setAwaitingVersion] = useState(false)
  const [isComplete, setIsComplete] = useState(false)
  const [streamDone, setStreamDone] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const cleanup = useCallback(() => {
    if (reconnectTimerRef.current !== null) {
      clearTimeout(reconnectTimerRef.current)
      reconnectTimerRef.current = null
    }
    if (wsRef.current) {
      wsRef.current.onclose = null
      wsRef.current.onmessage = null
      wsRef.current.onerror = null
      wsRef.current.onopen = null
      wsRef.current.close()
      wsRef.current = null
    }
  }, [])

  const connect = useCallback((projectName: string) => {
    cleanup()
    isGeneratingRef.current = true
    setStreamContent('')
    setCurrentPhase(-1)
    setStreamDone(false)
    setError(null)
    setIsComplete(false)
    setAwaitingApproval(false)
    setAwaitingVersion(false)

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const host = window.location.host
    const ws = new WebSocket(`${protocol}//${host}/api/ws/create/${encodeURIComponent(projectName)}`)
    wsRef.current = ws

    ws.onopen = () => setConnected(true)

    ws.onmessage = (event) => {
      const msg: WSMessage = JSON.parse(event.data)
      switch (msg.type) {
        case 'progress':
          setProgress({ current: msg.current || 0, total: msg.total || 6 })
          break
        case 'phase_start':
          setCurrentPhase(msg.phase_index || 0)
          setStreamContent('')
          setStreamDone(false)
          setPhases(prev => {
            const next = [...prev]
            if (msg.phase_index !== undefined) {
              next[msg.phase_index] = { name: msg.phase_name || '', status: 'active' }
            }
            return next
          })
          break
        case 'stream':
          setStreamContent(prev => prev + (msg.chunk || ''))
          break
        case 'stream_clear':
          setStreamContent('')
          break
        case 'phase_complete':
          setStreamDone(true)
          setPhases(prev => {
            const next = [...prev]
            if (msg.phase_index !== undefined && next[msg.phase_index]) {
              next[msg.phase_index] = { ...next[msg.phase_index], status: 'done' }
            }
            return next
          })
          if (msg.phase_index === 0) {
            setAwaitingVersion(true)
          } else {
            setAwaitingApproval(true)
          }
          break
        case 'awaiting_approval':
          setAwaitingApproval(true)
          break
        case 'awaiting_version':
          setAwaitingVersion(true)
          break
        case 'version_applied':
          setAwaitingVersion(false)
          setStreamContent('')
          break
        case 'all_complete':
          setIsComplete(true)
          setAwaitingApproval(false)
          setAwaitingVersion(false)
          isGeneratingRef.current = false
          break
        case 'error':
          setError(msg.message || 'Unknown error')
          isGeneratingRef.current = false
          break
      }
    }

    ws.onclose = () => {
      setConnected(false)
    }

    ws.onerror = () => ws.close()
  }, [cleanup])

  useEffect(() => {
    return () => {
      isGeneratingRef.current = false
      cleanup()
    }
  }, [cleanup])

  const send = useCallback((data: Record<string, any>) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(data))
    }
  }, [])

  const approve = useCallback((phaseIndex: number) => {
    send({ action: 'approve', phase_index: phaseIndex })
    setAwaitingApproval(false)
    setStreamContent('')
    setStreamDone(false)
  }, [send])

  const revise = useCallback((phaseIndex: number, feedback: string) => {
    send({ action: 'revise', phase_index: phaseIndex, feedback })
    setAwaitingApproval(false)
    setStreamContent('')
    setStreamDone(false)
  }, [send])

  const reject = useCallback((phaseIndex: number, reason: string) => {
    send({ action: 'reject', phase_index: phaseIndex, reason })
    setAwaitingApproval(false)
    setStreamContent('')
    setStreamDone(false)
  }, [send])

  const confirmPhase = useCallback((phaseIndex: number) => {
    send({ action: 'confirm_phase', phase_index: phaseIndex })
    setAwaitingApproval(false)
  }, [send])

  const disconnect = useCallback(() => {
    isGeneratingRef.current = false
    cleanup()
  }, [cleanup])

  const clearStream = useCallback(() => {
    setStreamContent('')
    setCurrentPhase(-1)
    setStreamDone(false)
  }, [])

  const selectVersion = useCallback((version: string, feedback: string = '') => {
    send({ action: 'version_select', version, feedback })
    setAwaitingVersion(false)
    setStreamContent('')
    setCurrentPhase(-1)
    setStreamDone(false)
  }, [send])

  return {
    connect, send, approve, revise, reject, confirmPhase, selectVersion, disconnect, clearStream,
    connected, streamContent, currentPhase, phases,
    progress, awaitingApproval, awaitingVersion, isComplete, streamDone, error,
  }
}
