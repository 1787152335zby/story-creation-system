import { ReactNode } from 'react'
import { Routes, Route } from 'react-router-dom'
import { ToastProvider } from './components/Toast'
import ErrorBoundary from './components/ErrorBoundary'
import GlassShell from './components/GlassShell'
import CosmicHomePage from './pages/CosmicHomePage'
import AllProjectsPage from './pages/AllProjectsPage'
import NewProjectWizard from './pages/NewProjectWizard'
import Workspace from './pages/Workspace'
import SettingsPage from './pages/SettingsPage'
import ImageGenPage from './pages/ImageGenPage'
import VideoGenPage from './pages/VideoGenPage'
import HistoryPage from './pages/HistoryPage'

function E({ children }: { children: ReactNode }) {
  return <ErrorBoundary>{children}</ErrorBoundary>
}

export default function App() {
  return (
    <ToastProvider>
      <Routes>
        <Route path="/" element={<CosmicHomePage />} />
        <Route path="/home" element={<CosmicHomePage />} />
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
