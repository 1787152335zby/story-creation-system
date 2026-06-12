import { ReactNode, lazy, Suspense } from 'react'
import { Routes, Route } from 'react-router-dom'
import { ToastProvider } from './components/Toast'
import ErrorBoundary from './components/ErrorBoundary'
import GlassShell from './components/GlassShell'
import PersistentCosmicBg from './components/PersistentCosmicBg'
import AllProjectsPage from './pages/AllProjectsPage'
import NewProjectWizard from './pages/NewProjectWizard'
import Workspace from './pages/Workspace'
import SettingsPage from './pages/SettingsPage'
import ImageGenPage from './pages/ImageGenPage'
import VideoGenPage from './pages/VideoGenPage'
import HistoryPage from './pages/HistoryPage'

const CosmicHomePage = lazy(() => import('./pages/CosmicHomePage'))

function E({ children }: { children: ReactNode }) {
  return <ErrorBoundary>{children}</ErrorBoundary>
}

function Fallback() {
  return (
    <div className="flex items-center justify-center h-screen bg-black">
      <div className="w-8 h-8 border-2 border-white/20 border-t-white/60 rounded-full animate-spin" />
    </div>
  )
}

export default function App() {
  return (
    <ToastProvider>
      <PersistentCosmicBg />
      <Routes>
        <Route path="/" element={<Suspense fallback={<Fallback />}><E><CosmicHomePage /></E></Suspense>} />
        <Route path="/home" element={<Suspense fallback={<Fallback />}><E><CosmicHomePage /></E></Suspense>} />
        <Route path="/projects" element={<AllProjectsPage />} />
        <Route path="/new" element={<GlassShell><E><NewProjectWizard /></E></GlassShell>} />
        <Route path="/project/:name" element={<GlassShell><E><Workspace /></E></GlassShell>} />
        <Route path="/settings" element={<GlassShell><E><SettingsPage /></E></GlassShell>} />
        <Route path="/image-gen" element={<GlassShell><E><ImageGenPage /></E></GlassShell>} />
        <Route path="/video-gen" element={<GlassShell><E><VideoGenPage /></E></GlassShell>} />
        <Route path="/history" element={<GlassShell><E><HistoryPage /></E></GlassShell>} />
      </Routes>
    </ToastProvider>
  )
}
