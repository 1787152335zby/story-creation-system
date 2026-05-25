import { useState, useEffect, ReactNode } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { LayoutDashboard, PanelLeft, PanelTop, Image, Video, Settings, FolderOpen } from 'lucide-react'

type LayoutMode = 'sidebar' | 'topnav' | 'dashboard'

const NAV_ITEMS = [
  { path: '/home', label: '首页', icon: LayoutDashboard },
  { path: '/image-gen', label: '智能生图', icon: Image },
  { path: '/video-gen', label: '视频生成', icon: Video },
  { path: '/settings', label: '设置', icon: Settings },
]

function getStoredMode(): LayoutMode {
  try { return (localStorage.getItem('app-layout') as LayoutMode) || 'sidebar' }
  catch { return 'sidebar' }
}

export default function AppShell({ children }: { children: ReactNode }) {
  const [mode, setMode] = useState<LayoutMode>(getStoredMode)
  const navigate = useNavigate()
  const location = useLocation()

  const setPersistedMode = (m: LayoutMode) => {
    setMode(m)
    localStorage.setItem('app-layout', m)
  }

  useEffect(() => {
    const el = document.documentElement
    el.setAttribute('data-layout', mode)
    return () => el.removeAttribute('data-layout')
  }, [mode])

  return (
    <div className="min-h-screen flex flex-col cosmic-bg">
      {mode === 'sidebar' && <SidebarLayout mode={mode} setMode={setPersistedMode} location={location} navigate={navigate}>{children}</SidebarLayout>}
      {mode === 'topnav' && <TopNavLayout mode={mode} setMode={setPersistedMode} location={location} navigate={navigate}>{children}</TopNavLayout>}
      {mode === 'dashboard' && <DashboardLayout mode={mode} setMode={setPersistedMode} location={location} navigate={navigate}>{children}</DashboardLayout>}
    </div>
  )
}

function LayoutToggle({ mode, setMode }: { mode: LayoutMode; setMode: (m: LayoutMode) => void }) {
  return (
    <div className="flex items-center gap-0.5 bg-white/[0.04] rounded-lg p-0.5 border border-white/[0.06]">
      {(['sidebar', 'topnav', 'dashboard'] as LayoutMode[]).map(m => {
        const Icon = m === 'sidebar' ? PanelLeft : m === 'topnav' ? PanelTop : LayoutDashboard
        return (
          <button key={m} onClick={() => setMode(m)}
            className={`p-1.5 rounded-md transition-all ${mode === m ? 'bg-indigo-500/25 text-indigo-300' : 'text-white/30 hover:text-white/60'}`}
            title={m === 'sidebar' ? '侧边栏布局' : m === 'topnav' ? '顶部导航布局' : '仪表盘布局'}>
            <Icon className="w-3.5 h-3.5" />
          </button>
        )
      })}
    </div>
  )
}

function SidebarLayout({ children, mode, setMode, location, navigate }: {
  children: ReactNode; mode: LayoutMode; setMode: (m: LayoutMode) => void
  location: ReturnType<typeof useLocation>; navigate: ReturnType<typeof useNavigate>
}) {
  return (
    <div className="flex h-screen">
      <aside className="w-56 flex-shrink-0 flex flex-col border-r border-white/[0.06] bg-black/[0.35] backdrop-blur-xl">
        <div className="p-5 border-b border-white/[0.05]">
          <div className="flex items-center gap-2.5 mb-4">
            <div className="w-7 h-7 rounded-lg bg-indigo-500/20 flex items-center justify-center">
              <span className="text-sm">✦</span>
            </div>
            <span className="text-sm font-semibold tracking-wide text-indigo-200/80">故事创作</span>
          </div>
          <LayoutToggle mode={mode} setMode={setMode} />
        </div>
        <nav className="flex-1 p-3 space-y-0.5 overflow-y-auto">
          {NAV_ITEMS.map(item => {
            const isActive = location.pathname === item.path || (item.path !== '/' && location.pathname.startsWith(item.path))
            return (
              <button key={item.path} onClick={() => navigate(item.path)}
                className={`w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-all ${
                  isActive ? 'bg-indigo-500/20 text-indigo-200 font-medium' : 'text-white/35 hover:text-white/65 hover:bg-white/[0.04]'
                }`}>
                <item.icon className="w-4 h-4" />
                <span>{item.label}</span>
              </button>
            )
          })}
        </nav>
        <div className="p-4 border-t border-white/[0.05]">
          <div className="flex items-center gap-2 px-1">
            <div className="w-6 h-6 rounded-full bg-indigo-500/20 flex items-center justify-center text-[10px] text-indigo-300/60">✦</div>
            <span className="text-[11px] text-white/25 truncate">粒子宇宙 · v2.0</span>
          </div>
        </div>
      </aside>
      <main className="flex-1 overflow-y-auto" style={{ zIndex: 1 }}>
        {children}
      </main>
    </div>
  )
}

function TopNavLayout({ children, mode, setMode, location, navigate }: {
  children: ReactNode; mode: LayoutMode; setMode: (m: LayoutMode) => void
  location: ReturnType<typeof useLocation>; navigate: ReturnType<typeof useNavigate>
}) {
  return (
    <div className="flex flex-col h-screen">
      <header className="flex-shrink-0 flex items-center gap-4 px-5 py-2.5 border-b border-white/[0.06] bg-black/[0.35] backdrop-blur-xl">
        <div className="flex items-center gap-2.5 mr-4">
          <div className="w-6 h-6 rounded-lg bg-indigo-500/20 flex items-center justify-center">
            <span className="text-[11px]">✦</span>
          </div>
          <span className="text-xs font-semibold tracking-wide text-indigo-200/80">故事创作系统</span>
        </div>
        <nav className="flex items-center gap-1">
          {NAV_ITEMS.map(item => {
            const isActive = location.pathname === item.path || (item.path !== '/' && location.pathname.startsWith(item.path))
            return (
              <button key={item.path} onClick={() => navigate(item.path)}
                className={`px-3.5 py-1.5 rounded-lg text-[13px] transition-all ${
                  isActive ? 'bg-indigo-500/20 text-indigo-200 font-medium' : 'text-white/30 hover:text-white/55 hover:bg-white/[0.03]'
                }`}>
                {item.label}
              </button>
            )
          })}
        </nav>
        <div className="flex-1" />
        <LayoutToggle mode={mode} setMode={setMode} />
      </header>
      <main className="flex-1 overflow-y-auto" style={{ zIndex: 1 }}>
        {children}
      </main>
    </div>
  )
}

function DashboardLayout({ children, mode, setMode, location, navigate }: {
  children: ReactNode; mode: LayoutMode; setMode: (m: LayoutMode) => void
  location: ReturnType<typeof useLocation>; navigate: ReturnType<typeof useNavigate>
}) {
  return (
    <div className="flex flex-col h-screen">
      <header className="flex-shrink-0 flex items-center gap-4 px-6 py-3 border-b border-white/[0.06] bg-black/[0.35] backdrop-blur-xl">
        <div className="w-7 h-7 rounded-lg bg-indigo-500/20 flex items-center justify-center">
          <span className="text-sm">✦</span>
        </div>
        <span className="text-sm font-semibold tracking-wide text-indigo-200/80">故事创作系统</span>
        <span className="text-white/15 text-xs">·</span>
        <span className="text-white/25 text-xs">粒子宇宙</span>
        <div className="flex-1" />
        <LayoutToggle mode={mode} setMode={setMode} />
      </header>
      <main className="flex-1 overflow-y-auto p-6" style={{ zIndex: 1 }}>
        {/* Dashboard grid */}
        <div className="grid grid-cols-3 gap-4 h-full">
          {/* 项目卡片 */}
          <div className="col-span-2 row-span-2 rounded-2xl border border-white/[0.07] bg-white/[0.03] backdrop-blur-xl p-6 flex flex-col">
            <div className="flex items-center gap-3 mb-4">
              <FolderOpen className="w-4 h-4 text-indigo-300/60" />
              <span className="text-xs font-medium text-white/40 uppercase tracking-widest">当前项目</span>
            </div>
            <div className="flex-1 flex items-center justify-center">
              <div className="text-center">
                <div className="w-14 h-14 rounded-2xl bg-indigo-500/15 mx-auto mb-4 flex items-center justify-center">
                  <FolderOpen className="w-7 h-7 text-indigo-300/50" />
                </div>
                <p className="text-white/20 text-sm">选择或新建项目以开始</p>
                <button onClick={() => navigate('/')} className="mt-3 px-4 py-1.5 rounded-lg bg-indigo-500/20 text-indigo-300/80 text-xs hover:bg-indigo-500/30 transition-all">
                  前往项目列表 →
                </button>
              </div>
            </div>
          </div>

          {/* 右侧快捷面板 */}
          <div className="rounded-2xl border border-white/[0.07] bg-white/[0.03] backdrop-blur-xl p-5 flex flex-col gap-3">
            <div className="text-xs font-medium text-white/40 uppercase tracking-widest mb-1">快捷入口</div>
            {[
              { path: '/image-gen', label: '智能生图', icon: Image, desc: '角色/场景/道具生成' },
              { path: '/video-gen', label: '视频生成', icon: Video, desc: '分镜动画制作' },
              { path: '/settings', label: '系统设置', icon: Settings, desc: '模型与参数配置' },
            ].map(item => (
              <button key={item.path} onClick={() => navigate(item.path)}
                className="flex items-center gap-3 p-3 rounded-xl border border-white/[0.05] bg-white/[0.02] hover:bg-indigo-500/10 hover:border-indigo-500/20 transition-all group text-left">
                <div className="w-8 h-8 rounded-lg bg-indigo-500/10 flex items-center justify-center group-hover:bg-indigo-500/20 transition-all">
                  <item.icon className="w-4 h-4 text-indigo-300/60" />
                </div>
                <div>
                  <div className="text-[13px] text-white/60 group-hover:text-white/85 transition-colors">{item.label}</div>
                  <div className="text-[10px] text-white/20">{item.desc}</div>
                </div>
              </button>
            ))}
          </div>

          {/* 底部状态 */}
          <div className="col-span-2 rounded-2xl border border-white/[0.07] bg-white/[0.03] backdrop-blur-xl p-5 flex items-center gap-6">
            <div className="flex items-center gap-2">
              <div className="w-1.5 h-1.5 rounded-full bg-green-400/60" />
              <span className="text-[11px] text-white/30">背景渲染: 活跃</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-1.5 h-1.5 rounded-full bg-indigo-400/60" />
              <span className="text-[11px] text-white/30">粒子引擎: 160 星点</span>
            </div>
            <div className="flex-1" />
            <span className="text-[10px] text-white/15">v2.0 · 粒子宇宙</span>
          </div>
        </div>
      </main>
    </div>
  )
}
