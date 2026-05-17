import { ReactNode } from 'react'
import { Routes, Route } from 'react-router-dom'
import { ToastProvider } from './components/Toast'
import ErrorBoundary from './components/ErrorBoundary'
import ThemeSwitcher from './components/ThemeSwitcher'
import HomePage from './pages/HomePage'
import NewProjectWizard from './pages/NewProjectWizard'
import Workspace from './pages/Workspace'
import SettingsPage from './pages/SettingsPage'
import ImageGenPage from './pages/ImageGenPage'
import VideoGenPage from './pages/VideoGenPage'

function E({ children }: { children: ReactNode }) {
  return <ErrorBoundary>{children}</ErrorBoundary>
}

export default function App() {
  return (
    <div className="min-h-screen bg-background text-foreground">
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
