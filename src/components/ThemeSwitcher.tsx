import { useEffect, useState, useCallback } from 'react'
import { Palette, X, Sparkles } from 'lucide-react'

interface PaletteOption {
  id: string
  label: string
  color: string
}

interface LayerOption {
  id: string
  label: string
}

const PALETTES: PaletteOption[] = [
  { id: 'nebula', label: '星云紫', color: 'hsl(270, 80%, 65%)' },
  { id: 'aurora', label: '极光蓝', color: 'hsl(195, 90%, 58%)' },
  { id: 'amber', label: '琥珀橙', color: 'hsl(30, 95%, 60%)' },
  { id: 'jade', label: '翡翠绿', color: 'hsl(155, 75%, 45%)' },
  { id: 'rose', label: '玫瑰红', color: 'hsl(340, 80%, 60%)' },
  { id: 'moonlight', label: '月光白', color: 'hsl(250, 70%, 55%)' },
]

const BACKGROUNDS: LayerOption[] = [
  { id: 'solid', label: '纯色' },
  { id: 'subtle', label: '微渐变' },
  { id: 'aurora-grad', label: '极光' },
  { id: 'dusk', label: '黄昏' },
  { id: 'deep', label: '深海' },
  { id: 'nebula-grad', label: '星云' },
]

const TEXTURES: LayerOption[] = [
  { id: 'none', label: '无' },
  { id: 'noise', label: '噪点' },
  { id: 'grid', label: '网格' },
  { id: 'dots', label: '点阵' },
  { id: 'ripple', label: '波纹' },
]

const AMBIENTS: LayerOption[] = [
  { id: 'none', label: '无' },
  { id: 'top-glow', label: '顶光' },
  { id: 'edge-glow', label: '边缘' },
  { id: 'corner', label: '角落' },
  { id: 'orbit', label: '环绕' },
  { id: 'stardust', label: '星尘' },
]

const STORAGE_KEYS = {
  palette: 'theme_palette',
  background: 'theme_background',
  texture: 'theme_texture',
  ambient: 'theme_ambient',
  animated: 'theme_animated',
  presets: 'theme_presets',
} as const

interface Preset {
  name: string
  palette: string
  background: string
  texture: string
  ambient: string
  animated: boolean
}

function migrateOldTheme() {
  const oldTheme = localStorage.getItem('app_theme')
  if (oldTheme && !localStorage.getItem(STORAGE_KEYS.palette)) {
    const oldMap: Record<string, string> = {
      default: 'nebula',
      aurora: 'aurora',
      blaze: 'amber',
      jade: 'jade',
      light: 'moonlight',
    }
    const newPalette = oldMap[oldTheme] || 'nebula'
    localStorage.setItem(STORAGE_KEYS.palette, newPalette)
    localStorage.removeItem('app_theme')
  }
}

function loadLayer<T>(key: string, fallback: T): T {
  try {
    const v = localStorage.getItem(key)
    return v !== null ? JSON.parse(v) : fallback
  } catch { return fallback }
}

function saveLayer(key: string, value: unknown) {
  localStorage.setItem(key, JSON.stringify(value))
}

function loadPresets(): Preset[] {
  try {
    const v = localStorage.getItem(STORAGE_KEYS.presets)
    return v ? JSON.parse(v) : []
  } catch { return [] }
}

function applyTheme(palette: string, background: string, texture: string, ambient: string, animated: boolean) {
  const html = document.documentElement
  html.className = html.className
    .split(' ').filter(c => !c.startsWith('palette-') && !c.startsWith('bg-') && !c.startsWith('texture-') && !c.startsWith('ambient-') && c !== 'theme-animated')
    .join(' ')

  const classes: string[] = []
  if (palette !== 'nebula') classes.push(`palette-${palette}`)
  if (background !== 'solid') classes.push(`bg-${background}`)
  if (texture !== 'none') classes.push(`texture-${texture}`)
  if (ambient !== 'none') classes.push(`ambient-${ambient}`)
  if (animated) classes.push('theme-animated')

  if (classes.length > 0) {
    html.className = (html.className + ' ' + classes.join(' ')).trim()
  }
}

function LayerSection({ title, icon, children }: { title: string; icon: string; children: React.ReactNode }) {
  return (
    <div>
      <h3 className="text-xs text-muted-foreground font-medium mb-2">{icon} {title}</h3>
      <div className="flex flex-wrap gap-1.5">
        {children}
      </div>
    </div>
  )
}

function LayerButtons({ options, value, onChange }: { options: LayerOption[]; value: string; onChange: (id: string) => void }) {
  return (
    <>
      {options.map(o => (
        <button key={o.id} onClick={() => onChange(o.id)}
          className={`px-2.5 py-1.5 rounded-lg text-xs transition-all ${
            value === o.id
              ? 'bg-primary/15 text-primary font-medium'
              : 'text-muted-foreground hover:text-foreground hover:bg-muted'
          }`}>
          {o.label}
        </button>
      ))}
    </>
  )
}

function PresetList({ onLoad, onDelete }: { onLoad: (p: Preset) => void; onDelete: (i: number) => void }) {
  const presets = loadPresets()
  if (presets.length === 0) return null

  return (
    <div className="space-y-1">
      {presets.map((p, i) => (
        <div key={i} className="flex items-center gap-2 px-2 py-1.5 rounded-lg hover:bg-muted group">
          <button onClick={() => onLoad(p)}
            className="flex-1 text-xs text-left text-muted-foreground hover:text-foreground truncate">
            📁 {p.name}
          </button>
          <button onClick={() => onDelete(i)}
            className="opacity-0 group-hover:opacity-100 text-[10px] text-danger hover:text-danger/80 transition-all">
            删除
          </button>
        </div>
      ))}
    </div>
  )
}

export default function ThemeSwitcher() {
  migrateOldTheme()
  const [open, setOpen] = useState(false)
  const [palette, setPaletteState] = useState(() => loadLayer(STORAGE_KEYS.palette, 'nebula'))
  const [background, setBackgroundState] = useState(() => loadLayer(STORAGE_KEYS.background, 'solid'))
  const [texture, setTextureState] = useState(() => loadLayer(STORAGE_KEYS.texture, 'none'))
  const [ambient, setAmbientState] = useState(() => loadLayer(STORAGE_KEYS.ambient, 'none'))
  const [animated, setAnimatedState] = useState(() => loadLayer(STORAGE_KEYS.animated, false))
  const [showPresetInput, setShowPresetInput] = useState(false)
  const [presetName, setPresetName] = useState('')

  const setPalette = useCallback((v: string) => { setPaletteState(v); saveLayer(STORAGE_KEYS.palette, v) }, [])
  const setBackground = useCallback((v: string) => { setBackgroundState(v); saveLayer(STORAGE_KEYS.background, v) }, [])
  const setTexture = useCallback((v: string) => { setTextureState(v); saveLayer(STORAGE_KEYS.texture, v) }, [])
  const setAmbient = useCallback((v: string) => { setAmbientState(v); saveLayer(STORAGE_KEYS.ambient, v) }, [])
  const setAnimated = useCallback((v: boolean) => { setAnimatedState(v); saveLayer(STORAGE_KEYS.animated, v) }, [])

  useEffect(() => {
    applyTheme(palette, background, texture, ambient, animated)
  }, [palette, background, texture, ambient, animated])

  const confirmSavePreset = useCallback(() => {
    const name = presetName.trim()
    if (!name) return
    const presets = loadPresets()
    presets.push({ name, palette, background, texture, ambient, animated })
    localStorage.setItem(STORAGE_KEYS.presets, JSON.stringify(presets))
    setShowPresetInput(false)
    setPresetName('')
    setPaletteState(p => p)
  }, [presetName, palette, background, texture, ambient, animated])

  const cancelSavePreset = useCallback(() => {
    setShowPresetInput(false)
    setPresetName('')
  }, [])

  const loadPresetAction = useCallback((preset: Preset) => {
    setPalette(preset.palette)
    setBackground(preset.background)
    setTexture(preset.texture)
    setAmbient(preset.ambient)
    setAnimated(preset.animated)
  }, [setPalette, setBackground, setTexture, setAmbient, setAnimated])

  const deletePreset = useCallback((index: number) => {
    const presets = loadPresets()
    presets.splice(index, 1)
    localStorage.setItem(STORAGE_KEYS.presets, JSON.stringify(presets))
    setPaletteState(p => p)
  }, [])

  return (
    <>
      <button onClick={() => setOpen(true)}
        className="fixed bottom-6 right-6 z-40 w-11 h-11 rounded-xl glass-card flex items-center justify-center hover:bg-muted/80 transition-all shadow-lg"
        title="定制主题">
        <Palette className="w-[18px] h-[18px] text-muted-foreground" />
      </button>

      {open && (
        <div className="fixed inset-0 z-40 bg-black/20 backdrop-blur-sm"
          onClick={() => setOpen(false)} />
      )}

      <div className={`fixed top-0 right-0 z-50 h-full w-80 glass-card border-l border-border transform transition-transform duration-300 ease-out ${open ? 'translate-x-0' : 'translate-x-full'}`}>
        <div className="flex items-center justify-between p-4 border-b border-border">
          <h2 className="text-sm font-semibold flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-primary" />
            主题定制
          </h2>
          <button onClick={() => setOpen(false)} className="p-1 rounded-lg hover:bg-muted transition-colors">
            <X className="w-4 h-4 text-muted-foreground" />
          </button>
        </div>

        <div className="p-4 space-y-5 overflow-y-auto" style={{ maxHeight: 'calc(100vh - 60px)' }}>
          <LayerSection title="色系" icon="🌈">
            <div className="flex gap-3">
              {PALETTES.map(p => (
                <button key={p.id} onClick={() => setPalette(p.id)}
                  className={`flex flex-col items-center gap-1 transition-all ${palette === p.id ? 'scale-110' : 'hover:scale-105'}`}>
                  <span className={`w-9 h-9 rounded-full border-2 transition-all ${palette === p.id ? 'border-foreground' : 'border-transparent'}`}
                    style={{ background: p.color }} />
                  <span className="text-[10px] text-muted-foreground">{p.label}</span>
                </button>
              ))}
            </div>
          </LayerSection>

          <LayerSection title="背景" icon="🖼">
            <LayerButtons options={BACKGROUNDS} value={background} onChange={setBackground} />
          </LayerSection>

          <LayerSection title="纹理" icon="✨">
            <LayerButtons options={TEXTURES} value={texture} onChange={setTexture} />
          </LayerSection>

          <LayerSection title="光效" icon="💡">
            <LayerButtons options={AMBIENTS} value={ambient} onChange={setAmbient} />
          </LayerSection>

          <div className="pt-2 space-y-3 border-t border-border">
            <label className="flex items-center justify-between text-xs text-muted-foreground cursor-pointer select-none">
              <span>🔄 动态背景动画</span>
              <button onClick={() => setAnimated(!animated)}
                className={`w-9 h-5 rounded-full relative transition-colors flex-shrink-0 ${animated ? 'bg-primary' : 'bg-muted'}`}>
                <span className={`absolute top-0.5 left-0.5 w-4 h-4 rounded-full bg-white shadow-sm transition-transform duration-200 ${animated ? 'translate-x-[18px]' : 'translate-x-0'}`} />
              </button>
            </label>

            {showPresetInput ? (
              <div className="space-y-2">
                <input
                  type="text"
                  value={presetName}
                  onChange={e => setPresetName(e.target.value)}
                  placeholder="输入预设名称"
                  className="w-full text-xs bg-muted border border-border rounded-lg px-2.5 py-1.5 text-foreground placeholder:text-muted-foreground/50 focus:outline-none focus:border-primary"
                  autoFocus
                  onKeyDown={e => { if (e.key === 'Enter') confirmSavePreset(); if (e.key === 'Escape') cancelSavePreset() }}
                />
                <div className="flex gap-2">
                  <button onClick={confirmSavePreset}
                    className="flex-1 text-xs bg-primary/15 text-primary font-medium py-1.5 px-3 rounded-lg hover:bg-primary/25 transition-all">
                    确认
                  </button>
                  <button onClick={cancelSavePreset}
                    className="flex-1 text-xs text-muted-foreground py-1.5 px-3 rounded-lg hover:bg-muted transition-all">
                    取消
                  </button>
                </div>
              </div>
            ) : (
              <button onClick={() => { setShowPresetInput(true); setPresetName('') }}
                className="w-full text-xs text-muted-foreground hover:text-foreground py-2 px-3 rounded-lg hover:bg-muted transition-all text-left">
                📂 保存为预设...
              </button>
            )}

            <PresetList onLoad={loadPresetAction} onDelete={deletePreset} />
          </div>
        </div>
      </div>
    </>
  )
}
