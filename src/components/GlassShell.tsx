import { ReactNode } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { Plus, Settings } from 'lucide-react'

const NAV = [
  { path: '/home', label: '项目' },
  { path: '/image-gen', label: '生图' },
  { path: '/video-gen', label: '视频' },
  { path: '/settings', label: '设置' },
]

export default function GlassShell({ children }: { children: ReactNode }) {
  const navigate = useNavigate()
  const location = useLocation()

  return (
    <div className="min-h-screen flex flex-col" style={{ background: '#000' }}>
      {/* Subtle grid background */}
      <div
        className="fixed inset-0 pointer-events-none"
        style={{
          backgroundImage: `
            linear-gradient(rgba(255,255,255,0.012) 1px, transparent 1px),
            linear-gradient(90deg, rgba(255,255,255,0.012) 1px, transparent 1px)
          `,
          backgroundSize: '60px 60px',
          zIndex: 0,
        }}
      />
      {/* Ambient glow */}
      <div
        className="fixed pointer-events-none"
        style={{
          top: '-20%', left: '30%', width: '50%', height: '60%',
          background: 'radial-gradient(ellipse, rgba(40,40,80,0.15) 0%, transparent 70%)',
          zIndex: 0,
        }}
      />

      {/* Top bar */}
      <header
        className="relative flex items-center justify-between px-6 py-4 border-b border-white/[0.04]"
        style={{ zIndex: 10, background: 'rgba(0,0,0,0.7)', backdropFilter: 'blur(20px)' }}
      >
        <div className="flex items-center gap-8">
          <button onClick={() => navigate('/home')} className="text-lg font-bold tracking-tight text-white/80 hover:text-white transition-colors">
            织境
          </button>
          <nav className="flex items-center gap-1">
            {NAV.map(item => {
              const active = location.pathname === item.path
              return (
                <button key={item.path} onClick={() => navigate(item.path)}
                  className={`px-3 py-1.5 rounded-lg text-[13px] transition-all ${
                    active
                      ? 'bg-white/[0.06] text-white/80'
                      : 'text-white/20 hover:text-white/40 hover:bg-white/[0.02]'
                  }`}>
                  {item.label}
                </button>
              )
            })}
          </nav>
        </div>
        <div className="flex items-center gap-2">
          <button onClick={() => navigate('/new')}
            className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg border border-white/[0.08] text-xs text-white/35 hover:text-white/60 hover:border-white/[0.15] transition-all">
            <Plus className="w-3 h-3" /> 新建
          </button>
          <button onClick={() => navigate('/settings')}
            className="p-2 rounded-lg text-white/20 hover:text-white/50 hover:bg-white/[0.03] transition-all">
            <Settings className="w-4 h-4" />
          </button>
        </div>
      </header>

      {/* Content */}
      <main className="flex-1 relative" style={{ zIndex: 10 }}>
        {children}
      </main>

      {/* Subtle particle overlay (pure CSS dots) */}
      <div className="fixed inset-0 pointer-events-none" style={{ zIndex: 1 }}>
        {Array.from({ length: 20 }).map((_, i) => (
          <div
            key={i}
            className="absolute rounded-full"
            style={{
              width: '2px', height: '2px',
              left: `${Math.random() * 100}%`, top: `${Math.random() * 100}%`,
              background: 'rgba(255,255,255,0.08)',
              animation: `fadeIn ${3 + Math.random() * 4}s ease-in-out infinite`,
              animationDelay: `${Math.random() * 5}s`,
            }}
          />
        ))}
      </div>
    </div>
  )
}
