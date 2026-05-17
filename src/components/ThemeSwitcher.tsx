import { useEffect, useState } from 'react'
import { Palette } from 'lucide-react'

const THEMES = [
  { id: 'default', label: '深空紫', color: 'hsl(252, 87%, 67%)', bg: 'hsl(222, 47%, 5%)' },
  { id: 'aurora', label: '极光蓝', color: 'hsl(200, 85%, 60%)', bg: 'hsl(220, 50%, 5%)' },
  { id: 'blaze', label: '烈焰橙', color: 'hsl(25, 90%, 60%)', bg: 'hsl(0, 40%, 5%)' },
  { id: 'jade', label: '翡翠绿', color: 'hsl(160, 75%, 45%)', bg: 'hsl(150, 40%, 5%)' },
  { id: 'light', label: '简约白', color: 'hsl(252, 87%, 60%)', bg: 'hsl(0, 0%, 98%)' },
]

const STORAGE_KEY = 'app_theme'

export default function ThemeSwitcher() {
  const [open, setOpen] = useState(false)
  const [theme, setTheme] = useState(() => localStorage.getItem(STORAGE_KEY) || 'default')

  useEffect(() => {
    document.documentElement.className = theme === 'default' ? '' : `theme-${theme}`
    localStorage.setItem(STORAGE_KEY, theme)
  }, [theme])

  return (
    <div className="fixed bottom-6 right-6 z-50">
      {open && (
        <div className="absolute bottom-14 right-0 glass-card rounded-2xl p-3 shadow-xl animate-fade-in-up" style={{ minWidth: 180 }}>
          <p className="text-[10px] text-muted-foreground mb-2 px-1 font-medium">切换主题</p>
          <div className="space-y-1">
            {THEMES.map(t => {
              const active = theme === t.id
              return (
                <button key={t.id} onClick={() => { setTheme(t.id); setOpen(false) }}
                  className={`w-full flex items-center gap-2.5 px-3 py-2 rounded-xl text-xs transition-all ${
                    active ? 'bg-primary/15 text-primary font-medium' : 'text-muted-foreground hover:text-foreground hover:bg-muted'
                  }`}>
                  <span className="w-4 h-4 rounded-full border border-border flex-shrink-0" style={{ background: t.color }} />
                  <span className="flex-1 text-left">{t.label}</span>
                  {t.id === 'default' && !active && <span className="text-[9px] text-muted-foreground">默认</span>}
                </button>
              )
            })}
          </div>
        </div>
      )}
      <button onClick={() => setOpen(!open)}
        className="w-10 h-10 rounded-xl glass-card flex items-center justify-center hover:bg-muted/80 transition-all shadow-lg"
        title="切换主题">
        <Palette className="w-4 h-4 text-muted-foreground" />
      </button>
    </div>
  )
}
