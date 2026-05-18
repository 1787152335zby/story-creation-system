import { useState, useEffect, ReactNode } from 'react'
import { Routes, Route, useNavigate } from 'react-router-dom'
import { ToastProvider } from './components/Toast'
import ErrorBoundary from './components/ErrorBoundary'
import ThemeSwitcher from './components/ThemeSwitcher'
import SceneBackground from './components/SceneBackground'
import HomePage from './pages/HomePage'
import NewProjectWizard from './pages/NewProjectWizard'
import Workspace from './pages/Workspace'
import SettingsPage from './pages/SettingsPage'
import ImageGenPage from './pages/ImageGenPage'
import VideoGenPage from './pages/VideoGenPage'
import type { SceneTheme } from './components/SceneBackground'

function E({ children }: { children: ReactNode }) {
  return <ErrorBoundary>{children}</ErrorBoundary>
}

export default function App() {
  const navigate = useNavigate()
  const [scene, setScene] = useState<SceneTheme>('space')

  useEffect(() => {
    try { const s = localStorage.getItem('theme_scene'); if (s) setScene(JSON.parse(s)) } catch {}
    const handler = (e: Event) => setScene((e as CustomEvent).detail as SceneTheme)
    window.addEventListener('scenechange', handler)
    return () => window.removeEventListener('scenechange', handler)
  }, [])

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement || e.target instanceof HTMLSelectElement) return
      if (e.ctrlKey || e.metaKey || e.altKey) return
      const map: Record<string, string> = {
        '1': '/',
        '2': '/image-gen',
        '3': '/video-gen',
        '4': '/settings',
      }
      const path = map[e.key]
      if (path) {
        e.preventDefault()
        navigate(path)
      }
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [navigate])

  return (
    <div className="min-h-screen text-foreground">
      <SceneBackground scene={scene} />
      <ToastProvider>
        <Routes>
          <Route path="/" element={<E><HomePage /></E>} />
          <Route path="/new" element={<E><NewProjectWizard /></E>} />
          <Route path="/project/:name" element={<E><Workspace /></E>} />
          <Route path="/settings" element={<E><SettingsPage /></E>} />
          <Route path="/image-gen" element={<E><ImageGenPage /></E>} />
          <Route path="/video-gen" element={<E><VideoGenPage /></E>} />
        </Routes>
        <ThemeSwitcher />
      </ToastProvider>
    </div>
  )
}
