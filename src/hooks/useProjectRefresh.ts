import { useEffect, useRef } from 'react'
import type { ProjectInfo } from '../lib/types'

type Subscriber = (projects: ProjectInfo[]) => void
const subscribers = new Set<Subscriber>()
let globalTimer: number | null = null
let lastFetchTime = 0

function startGlobalPoller() {
  if (globalTimer !== null) return
  globalTimer = window.setInterval(async () => {
    if (!document.hasFocus()) return
    const now = Date.now()
    if (now - lastFetchTime < 3000) return
    lastFetchTime = now
    try {
      const mod = await import('../lib/api')
      const projects = await mod.fetchProjects()
      subscribers.forEach(fn => fn(projects))
    } catch {}
  }, 4000)
}

function stopGlobalPoller() {
  if (globalTimer !== null) {
    clearInterval(globalTimer)
    globalTimer = null
  }
}

export function useProjectRefresh(
  hasRunning: boolean,
  setProjects: (projects: ProjectInfo[]) => void
) {
  const setProjectsRef = useRef(setProjects)
  setProjectsRef.current = setProjects

  useEffect(() => {
    if (!hasRunning) return
    const handler: Subscriber = (projects) => setProjectsRef.current(projects)
    subscribers.add(handler)
    startGlobalPoller()

    const onVisibilityChange = () => {
      if (document.hidden) stopGlobalPoller()
      else if (hasRunning) startGlobalPoller()
    }
    document.addEventListener('visibilitychange', onVisibilityChange)

    return () => {
      subscribers.delete(handler)
      document.removeEventListener('visibilitychange', onVisibilityChange)
      if (subscribers.size === 0) stopGlobalPoller()
    }
  }, [hasRunning])
}
