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
  chunk_name?: string
  chunk_index?: number
  total_chunks?: number
}

export interface ChunkInfo {
  name: string
  index: number
  total: number
  filePath?: string
}

export interface EpisodeInfo {
  phase_index: number
  chunk_name: string
  chunk_index: number
  total_chunks: number
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
  const [awaitingProceed, setAwaitingProceed] = useState(false)
  const [contentWarnings, setContentWarnings] = useState<{ phase_index: number; warnings: string[]; stats: Record<string, number> }[]>([])
  const [isComplete, setIsComplete] = useState(false)
  const [streamDone, setStreamDone] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [chunksCompleted, setChunksCompleted] = useState<Record<number, ChunkInfo[]>>({})
  const [awaitingEpisodeApproval, setAwaitingEpisodeApproval] = useState(false)
  const [currentEpisode, setCurrentEpisode] = useState<EpisodeInfo | null>(null)
  const [confirmedPhaseIndex, setConfirmedPhaseIndex] = useState<number | null>(null)
  const [pausedPhaseIndex, setPausedPhaseIndex] = useState<number | null>(null)

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
    setAwaitingProceed(false)
    setContentWarnings([])
    setAwaitingEpisodeApproval(false)
    setCurrentEpisode(null)

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
          setAwaitingApproval(false)
          setAwaitingVersion(false)
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
          setAwaitingApproval(true)
          break
        case 'awaiting_approval':
          setAwaitingApproval(true)
          break
        case 'awaiting_version':
          setAwaitingVersion(true)
          break
        case 'waiting_for_proceed':
          setAwaitingProceed(true)
          break
        case 'content_warning':
          setContentWarnings(prev => [...prev, { phase_index: msg.phase_index, warnings: msg.warnings || [], stats: msg.stats || {} }])
          break
        case 'version_applied':
          setAwaitingVersion(false)
          break
        case 'phase_confirmed':
          setConfirmedPhaseIndex(msg.phase_index ?? null)
          setPausedPhaseIndex(null)
          setStreamDone(true)
          setAwaitingEpisodeApproval(false)
          break
        case 'chunk_saved':
          if (msg.phase_index !== undefined && msg.chunk_name) {
            setChunksCompleted(prev => {
              const pi = msg.phase_index!
              const chunks = [...(prev[pi] || [])]
              // 去重：同一 index 的已存在则替换
              const existingIdx = chunks.findIndex(c => c.index === (msg.chunk_index ?? 0))
              const entry = { name: msg.chunk_name!, index: msg.chunk_index ?? 0, total: msg.total_chunks ?? 1, filePath: msg.file_path }
              if (existingIdx >= 0) {
                chunks[existingIdx] = entry
              } else {
                chunks.push(entry)
              }
              return { ...prev, [pi]: chunks }
            })
          }
          break
        case 'episode_complete':
          setAwaitingEpisodeApproval(true)
          setStreamDone(true)
          if (msg.phase_index !== undefined && msg.chunk_name) {
            setCurrentEpisode({
              phase_index: msg.phase_index,
              chunk_name: msg.chunk_name,
              chunk_index: msg.chunk_index ?? 0,
              total_chunks: msg.total_chunks ?? 1,
            })
          }
          break
        case 'phase_paused':
          setStreamDone(true)
          setConfirmedPhaseIndex(null)
          setPausedPhaseIndex(msg.phase_index ?? null)
          setAwaitingEpisodeApproval(false)
          if (msg.phase_index !== undefined) setCurrentPhase(msg.phase_index)
          setPhases(prev => {
            const next = [...prev]
            if (msg.phase_index !== undefined && next[msg.phase_index]) {
              next[msg.phase_index] = { ...next[msg.phase_index], status: 'paused' }
            }
            return next
          })
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
        case 'reconnect_status':
          // 后台任务仍在运行，不做特殊处理
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

  const proceedGeneration = useCallback(() => {
    send({ action: 'proceed' })
    setPausedPhaseIndex(null)
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

  const episodeConfirm = useCallback((phaseIndex?: number) => {
    send({ action: 'episode_confirm' })
    setAwaitingEpisodeApproval(false)
    if (phaseIndex !== undefined) setPausedPhaseIndex(phaseIndex)
    setStreamDone(false)
  }, [send])

  const episodeApprove = useCallback(() => {
    send({ action: 'episode_approve' })
    setAwaitingEpisodeApproval(false)
    setStreamDone(false)
  }, [send])

  const episodeRevise = useCallback((feedback: string) => {
    send({ action: 'episode_revise', feedback })
    setAwaitingEpisodeApproval(false)
    setStreamDone(false)
  }, [send])

  const clearConfirmedPhase = useCallback(() => {
    setConfirmedPhaseIndex(null)
  }, [])

  return {
    connect, send, approve, revise, reject, confirmPhase, proceedGeneration, selectVersion, disconnect, clearStream,
    episodeConfirm, episodeApprove, episodeRevise,
    connected, streamContent, currentPhase, phases,
    progress, awaitingApproval, awaitingVersion, awaitingProceed, contentWarnings, isComplete, streamDone, error, chunksCompleted,
    awaitingEpisodeApproval, currentEpisode, confirmedPhaseIndex, clearConfirmedPhase, pausedPhaseIndex,
  }
}
