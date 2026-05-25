import { useState, useCallback, useEffect } from 'react'
import { X, Sparkles, Moon, Waves, Sun, Mountain } from 'lucide-react'
import type { SceneTheme } from './SceneBackground'

interface PaletteOption {
  id: string
  label: string
  color: string
}

const PALETTES: PaletteOption[] = [
  { id: 'nebula', label: '星云紫', color: 'hsl(270, 80%, 65%)' },
  { id: 'aurora', label: '极光蓝', color: 'hsl(195, 90%, 58%)' },
  { id: 'amber', label: '琥珀橙', color: 'hsl(30, 95%, 60%)' },
  { id: 'jade', label: '翡翠绿', color: 'hsl(155, 75%, 45%)' },
  { id: 'rose', label: '玫瑰红', color: 'hsl(340, 80%, 60%)' },
  { id: 'moonlight', label: '月光白', color: 'hsl(250, 70%, 55%)' },
]

const SCENES: { key: SceneTheme; icon: React.ReactNode; label: string }[] = [
  { key: 'space', icon: <Moon className="w-4 h-4" />, label: '星空' },
  { key: 'ocean', icon: <Waves className="w-4 h-4" />, label: '海洋' },
  { key: 'city', icon: <Sun className="w-4 h-4" />, label: '城市' },
  { key: 'mt', icon: <Mountain className="w-4 h-4" />, label: '山脉' },
  { key: 'plain', icon: <div className="w-4 h-4 rounded-sm bg-white/20" />, label: '纯色' },
]

const PALETTE_KEY = 'theme_palette'
const SCENE_KEY = 'theme_scene'

export default function ThemeSwitcher() {
  const [open, setOpen] = useState(false)
  const [palette, setPaletteState] = useState(() => {
    try { return JSON.parse(localStorage.getItem(PALETTE_KEY) || '"nebula"') } catch { return 'nebula' }
  })
  const [scene, setSceneState] = useState<SceneTheme>(() => {
    try { return JSON.parse(localStorage.getItem(SCENE_KEY) || '"space"') as SceneTheme } catch { return 'space' }
  })

  // 支持从外部通过自定义事件打开（如首页 header 中的快捷按钮）
  useEffect(() => {
    const handler = () => setOpen(true)
    window.addEventListener('openthemeswitcher', handler)
    return () => window.removeEventListener('openthemeswitcher', handler)
  }, [])

  const setPalette = useCallback((v: string) => {
    setPaletteState(v)
    localStorage.setItem(PALETTE_KEY, JSON.stringify(v))
    const html = document.documentElement
    html.className = html.className.split(' ').filter(c => !c.startsWith('palette-')).join(' ')
    if (v !== 'nebula') html.className = (html.className + ` palette-${v}`).trim()
  }, [])

  const setScene = useCallback((s: SceneTheme) => {
    setSceneState(s)
    localStorage.setItem(SCENE_KEY, JSON.stringify(s))
    window.dispatchEvent(new CustomEvent('scenechange', { detail: s }))
  }, [])

  return (
    <>
      {open && (
        <div className="fixed inset-0 z-40 bg-black/20 backdrop-blur-sm"
          onClick={() => setOpen(false)} />
      )}

      <div className={`fixed top-0 right-0 z-50 h-full w-72 glass-card border-l border-border transform transition-transform duration-300 ease-out ${open ? 'translate-x-0' : 'translate-x-full'}`}>
        <div className="flex items-center justify-between p-4 border-b border-border">
          <h2 className="text-sm font-semibold flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-primary" />
            主题定制
          </h2>
          <button onClick={() => setOpen(false)} className="p-1 rounded-lg hover:bg-muted transition-colors">
            <X className="w-4 h-4 text-muted-foreground" />
          </button>
        </div>

        <div className="p-4 space-y-6">
          {/* 色系 */}
          <div>
            <h3 className="text-xs text-muted-foreground font-medium mb-3">🌈 色系</h3>
            <div className="grid grid-cols-3 gap-3">
              {PALETTES.map(p => (
                <button key={p.id} onClick={() => setPalette(p.id)}
                  className={`flex flex-col items-center gap-1.5 p-2 rounded-xl transition-all ${
                    palette === p.id ? 'bg-primary/10 ring-2 ring-primary/30' : 'hover:bg-muted'
                  }`}>
                  <span className="w-8 h-8 rounded-full" style={{ background: p.color }} />
                  <span className="text-[10px] text-muted-foreground">{p.label}</span>
                </button>
              ))}
            </div>
          </div>

          {/* 背景场景 */}
          <div>
            <h3 className="text-xs text-muted-foreground font-medium mb-3">🖼 背景场景</h3>
            <div className="flex flex-col gap-2">
              {SCENES.map(s => (
                <button key={s.key} onClick={() => setScene(s.key)}
                  className={`flex items-center gap-3 px-3 py-2.5 rounded-xl text-xs transition-all ${
                    scene === s.key ? 'bg-primary/10 ring-2 ring-primary/30 font-medium' : 'hover:bg-muted text-muted-foreground'
                  }`}>
                  <span className={scene === s.key ? 'text-primary' : ''}>{s.icon}</span>
                  <span>{s.label}</span>
                  {scene === s.key && <span className="ml-auto w-1.5 h-1.5 rounded-full bg-primary" />}
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>
    </>
  )
}
