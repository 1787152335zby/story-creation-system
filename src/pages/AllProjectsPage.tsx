import { useEffect, useRef, useState, useMemo, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { Search, Plus, ArrowLeft, Sparkles, Pencil, Trash2, Check, X, ExternalLink, FolderOpen } from 'lucide-react'
import * as THREE from 'three'
import { fetchProjects, deleteProject, renameProject, openProjectFolder } from '../lib/api'
import { getPhaseNames } from '../lib/constants'
import type { ProjectInfo } from '../lib/types'

const COLORS: Record<string, [number, number, number]> = {
  running: [34, 211, 238],
  complete: [167, 139, 250],
  pending: [244, 114, 182],
  progress: [129, 140, 248],
  new: [200, 200, 220],
}

const GENRE_COLORS: Record<string, [number, number, number]> = {
  '悬疑': [34, 211, 238], '奇幻': [167, 139, 250], '科幻': [129, 140, 248], '言情': [244, 114, 182],
  '都市': [251, 191, 36], '历史': [236, 164, 116], '恐怖': [34, 197, 94], '喜剧': [250, 204, 21],
  '热血': [248, 113, 113], '冒险': [52, 211, 153],
}

const PHASE_ICONS = ['📋', '📖', '🎭', '🔍', '🎬', '🖼️']
const PANEL_WIDTH = 300

function starStatus(p: ProjectInfo): string {
  const names = getPhaseNames(p.style_type)
  const done = (p.phases || []).slice(0, names.length).filter(ph => ph.done).length
  const total = names.length
  if (p.running) return 'running'
  if (done >= total) return 'complete'
  if (p.pending_approval) return 'pending'
  if (done > 0) return 'progress'
  return 'new'
}

function seededRandom(seed: number): number {
  const x = Math.sin(seed + 1) * 10000
  return x - Math.floor(x)
}

function easeOutCubic(t: number): number {
  return 1 - Math.pow(1 - t, 3)
}

const CARD_TRANSITION = 'opacity 0.5s cubic-bezier(0.23,1,0.32,1), transform 0.5s cubic-bezier(0.23,1,0.32,1)'

interface BurstParticle { id: number; x: number; y: number; color: [number, number, number] }
let burstIdCounter = 0

export default function AllProjectsPage() {
  const navigate = useNavigate()
  const threeRef = useRef<HTMLDivElement>(null)
  const mouseRef = useRef({ x: 0.5, y: 0.5 })
  const universeRef = useRef<HTMLDivElement>(null)
  const [projects, setProjects] = useState<ProjectInfo[]>([])
  const [searchText, setSearchText] = useState('')
  const [visible, setVisible] = useState(false)
  const [, setEntryTick] = useState(0)
  const entryRef = useRef(0)
  const entryIdRef = useRef(0)
  const [renaming, setRenaming] = useState<string | null>(null)
  const [renameInput, setRenameInput] = useState('')
  const [deleteTarget, setDeleteTarget] = useState<string | null>(null)
  const [hoveredStar, setHoveredStar] = useState<string | null>(null)
  const [bursts, setBursts] = useState<BurstParticle[]>([])
  const [selectedProject, setSelectedProject] = useState<ProjectInfo | null>(null)
  const [viewMode, setViewMode] = useState<'universe' | 'cards'>('universe')
  const [showStagger, setShowStagger] = useState(false)
  const [zoom, setZoom] = useState(1)
  const zoomRef = useRef(1)
  const [panX, setPanX] = useState(0)
  const [panY, setPanY] = useState(0)
  const panXRef = useRef(0)
  const panYRef = useRef(0)
  const [isDragging, setIsDragging] = useState(false)
  const isDraggingRef = useRef(false)
  const dragStartRef = useRef({ x: 0, y: 0, px: 0, py: 0 })
  const [vw, setVw] = useState(window.innerWidth)
  const [vh, setVh] = useState(window.innerHeight)

  // Listen to viewport resize
  useEffect(() => {
    const resize = () => { setVw(window.innerWidth); setVh(window.innerHeight) }
    window.addEventListener('resize', resize)
    return () => window.removeEventListener('resize', resize)
  }, [])

  // ── Three.js background ──
  useEffect(() => {
    const container = threeRef.current
    if (!container) return
    const scene = new THREE.Scene()
    const camera = new THREE.PerspectiveCamera(60, window.innerWidth / window.innerHeight, 0.1, 200)
    camera.position.z = 15
    const renderer = new THREE.WebGLRenderer({ antialias: false, alpha: true, powerPreference: 'high-performance' })
    renderer.setSize(window.innerWidth, window.innerHeight)
    renderer.setPixelRatio(1)
    renderer.setClearColor(0x01010a, 1)
    container.appendChild(renderer.domElement)

    const N = 600
    const geo = new THREE.BufferGeometry()
    const pos = new Float32Array(N * 3); const col = new Float32Array(N * 3)
    for (let i = 0; i < N; i++) {
      const i3 = i * 3; pos[i3] = (Math.random() - 0.5) * 180; pos[i3 + 1] = (Math.random() - 0.5) * 120; pos[i3 + 2] = -1 - Math.random() * 100
      const c = new THREE.Color().setHSL(0.62 + Math.random() * 0.08, 0.3, 0.06 + Math.random() * 0.15)
      col[i3] = c.r; col[i3 + 1] = c.g; col[i3 + 2] = c.b
    }
    geo.setAttribute('position', new THREE.BufferAttribute(pos, 3)); geo.setAttribute('color', new THREE.BufferAttribute(col, 3))
    const mat = new THREE.PointsMaterial({ size: 0.15, vertexColors: true, blending: THREE.AdditiveBlending, depthWrite: false, transparent: true, opacity: 0, sizeAttenuation: false })
    scene.add(new THREE.Points(geo, mat))

    let animId = 0; let fadeIn = 0
    let panTargetX = 0, panTargetY = 0
    const animate = () => {
      if (fadeIn < 1) { fadeIn = Math.min(1, fadeIn + 0.008); mat.opacity = fadeIn }
      // Follow universe pan with smooth damping
      panTargetX += (panXRef.current - panTargetX) * 0.04
      panTargetY += (panYRef.current - panTargetY) * 0.04
      const mx = mouseRef.current.x; const my = mouseRef.current.y
      camera.position.x += ((mx - 0.5) * 1.5 - camera.position.x - panTargetX * 0.02) * 0.03
      camera.position.y += (((my - 0.5) * -1) * 1.2 - camera.position.y - panTargetY * 0.02) * 0.03
      const targetFov = 60 / zoomRef.current
      camera.fov += (targetFov - camera.fov) * 0.06
      camera.updateProjectionMatrix()
      const targetZ = 15 / zoomRef.current
      camera.position.z += (targetZ - camera.position.z) * 0.04
      renderer.render(scene, camera); animId = requestAnimationFrame(animate)
    }
    animate()
    const resize = () => { camera.aspect = window.innerWidth / window.innerHeight; camera.updateProjectionMatrix(); renderer.setSize(window.innerWidth, window.innerHeight) }
    window.addEventListener('resize', resize)
    const onWheel = (e: WheelEvent) => {
      const delta = e.deltaY > 0 ? -0.12 : 0.12
      const next = Math.max(1, Math.min(2, zoomRef.current + delta))
      zoomRef.current = next; setZoom(next)
    }
    window.addEventListener('wheel', onWheel, { passive: true })
    return () => { cancelAnimationFrame(animId); window.removeEventListener('resize', resize); window.removeEventListener('wheel', onWheel); if (container.contains(renderer.domElement)) container.removeChild(renderer.domElement); renderer.dispose() }
  }, [])

  useEffect(() => {
    fetchProjects().then(setProjects).catch(() => {})
    setTimeout(() => setVisible(true), 80)
    entryRef.current = 0
    const start = performance.now()
    const animateEntry = (now: number) => { entryRef.current = Math.min((now - start) / 5000, 1); setEntryTick(n => n + 1); if (entryRef.current < 1) entryIdRef.current = requestAnimationFrame(animateEntry) }
    entryIdRef.current = requestAnimationFrame(animateEntry)
    return () => { cancelAnimationFrame(entryIdRef.current); clearInterval(burstTimerRef.current) }
  }, [])

  const hoverTimerRef = useRef(0)
  const burstTimerRef = useRef(0)
  useEffect(() => {
    burstTimerRef.current = window.setInterval(() => setBursts([]), 1200)
    return () => clearInterval(burstTimerRef.current)
  }, [])

  useEffect(() => {
    const onMove = (e: MouseEvent) => {
      const rx = e.clientX / window.innerWidth; const ry = e.clientY / window.innerHeight
      mouseRef.current.x = rx; mouseRef.current.y = ry
      const mx = (rx - 0.5).toFixed(4); const my = (ry - 0.5).toFixed(4)
      document.documentElement.style.setProperty('--mouse-px', mx)
      document.documentElement.style.setProperty('--mouse-py', my)
    }
    window.addEventListener('mousemove', onMove, { passive: true })
    return () => window.removeEventListener('mousemove', onMove)
  }, [])

  const filtered = projects.filter(p => p.name.toLowerCase().includes(searchText.toLowerCase()))
  const entryProgress = entryRef.current
  const sel = selectedProject

  const closePanel = useCallback(() => {
    setSelectedProject(null)
  }, [])

  // Zoom helpers
  const zoomIn = useCallback(() => {
    const next = Math.min(2, zoomRef.current + 0.12)
    zoomRef.current = next; setZoom(next)
  }, [])
  const zoomOut = useCallback(() => {
    const next = Math.max(1, zoomRef.current - 0.12)
    zoomRef.current = next; setZoom(next)
  }, [])

  // ── Star positions (pixel-based universe) ──
  const starMeta = useMemo((): { stars: { x: number; y: number }[]; avgX: number; avgY: number } => {
    const count = filtered.length
    if (count === 0) return { stars: [], avgX: 0, avgY: 0 }
    const area = Math.max(vh * 0.75, 400)
    const spacing = Math.max(70, Math.min(200, area / Math.sqrt(count)))
    const cols = Math.max(2, Math.ceil(Math.sqrt(count * 1.5)))
    const positions: { x: number; y: number }[] = []
    let sumX = 0, sumY = 0
    for (let i = 0; i < count; i++) {
      const seed = i * 13.7 + 42
      const col = i % cols
      const row = Math.floor(i / cols)
      const jitterX = (seededRandom(seed + 100) - 0.5) * spacing * 0.7
      const jitterY = (seededRandom(seed + 200) - 0.5) * spacing * 0.7
      const x = col * spacing + spacing * 0.5 + jitterX
      const y = row * spacing + spacing * 0.5 + jitterY
      positions.push({ x, y })
      sumX += x; sumY += y
    }
    return {
      stars: positions,
      avgX: sumX / count,
      avgY: sumY / count,
    }
  }, [filtered, vh])

  // ── Default pan (center universe in viewport, accounting for top 80px header) ──
  const defaultPan = useMemo(() => {
    if (starMeta.stars.length === 0) return { x: 0, y: 0 }
    const leftZoneCenter = (vw - (sel ? PANEL_WIDTH : 0)) / 2
    const visualCenterY = (vh + 80) / 2
    return {
      x: leftZoneCenter - starMeta.avgX,
      y: visualCenterY - starMeta.avgY,
    }
  }, [starMeta, vw, vh, sel])

  // ── Navigate to a star smoothly ──
  const flyToStar = useCallback((index: number) => {
    if (index < 0 || index >= starMeta.stars.length) return
    const star = starMeta.stars[index]
    const leftZoneCenter = (vw - PANEL_WIDTH) / 2
    const visualCenterY = (vh + 80) / 2
    const tx = leftZoneCenter - star.x
    const ty = visualCenterY - star.y
    panXRef.current = tx; setPanX(tx)
    panYRef.current = ty; setPanY(ty)
  }, [starMeta.stars, vw, vh])

  // ── Reset to default view ──
  const resetView = useCallback(() => {
    panXRef.current = defaultPan.x; setPanX(defaultPan.x)
    panYRef.current = defaultPan.y; setPanY(defaultPan.y)
  }, [defaultPan])

  // ── Initialize pan on mount ──
  const initialPanSet = useRef(false)
  useEffect(() => {
    if (!initialPanSet.current && starMeta.stars.length > 0) {
      resetView()
      initialPanSet.current = true
    }
  }, [starMeta, resetView])

  // ── Handle selection → fly to star ──
  useEffect(() => {
    if (sel && starMeta.stars.length > 0) {
      const idx = filtered.findIndex(p => p.name === sel.name)
      if (idx >= 0) flyToStar(idx)
    } else {
      resetView()
    }
  }, [sel])
  // ── Clear hoveredStar when switching modes; trigger stagger entrance ──
  useEffect(() => {
    setHoveredStar(null)
    if (viewMode === 'cards') {
      setTimeout(() => setShowStagger(true), 60)
    } else {
      setShowStagger(false)
    }
  }, [viewMode])

  // ── Find nearest star from pixel coords ──
  const findNearest = useCallback((cx: number, cy: number): number => {
    let nearest = -1; let nearDist = Infinity
    for (let i = 0; i < starMeta.stars.length; i++) {
      const dx = cx - starMeta.stars[i].x; const dy = cy - starMeta.stars[i].y
      const d = dx * dx + dy * dy
      if (d < nearDist) { nearDist = d; nearest = i }
    }
    return nearest
  }, [starMeta.stars])

  // ── Drag handlers ──
  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    if (renaming || deleteTarget) return
    setIsDragging(true)
    isDraggingRef.current = true
    dragStartRef.current = { x: e.clientX, y: e.clientY, px: panXRef.current, py: panYRef.current }
  }, [renaming, deleteTarget])

  const handleMouseMove = useCallback((e: React.MouseEvent) => {
    if (isDraggingRef.current) {
      const dx = e.clientX - dragStartRef.current.x
      const dy = e.clientY - dragStartRef.current.y
      panXRef.current = dragStartRef.current.px + dx; setPanX(panXRef.current)
      panYRef.current = dragStartRef.current.py + dy; setPanY(panYRef.current)
    }
    // Hover detection (throttled)
    const now = performance.now()
    if (now - hoverTimerRef.current < 50) return
    hoverTimerRef.current = now
    const universeX = e.clientX - panXRef.current
    const universeY = e.clientY - panYRef.current
    const nearest = findNearest(universeX, universeY)
    // Only hover if within 60px of a star (avoid ghost hovers)
    const nearDist = nearest >= 0
      ? Math.hypot(universeX - starMeta.stars[nearest].x, universeY - starMeta.stars[nearest].y)
      : Infinity
    const name = nearest >= 0 && nearDist < 60 ? filtered[nearest].name : null
    if (name !== hoveredStar) setHoveredStar(name)
  }, [findNearest, filtered, hoveredStar, starMeta.stars])

  const handleMouseUp = useCallback((e: React.MouseEvent) => {
    if (!isDraggingRef.current) return
    const moved = Math.abs(e.clientX - dragStartRef.current.x) + Math.abs(e.clientY - dragStartRef.current.y)
    setIsDragging(false)
    isDraggingRef.current = false
    setHoveredStar(null)
    // If barely moved, treat as click
    if (moved < 8 && !renaming && !deleteTarget) {
      const universeX = e.clientX - panXRef.current
      const universeY = e.clientY - panYRef.current
      const nearest = findNearest(universeX, universeY)
      if (nearest >= 0) {
        const nearDist = Math.hypot(universeX - starMeta.stars[nearest].x, universeY - starMeta.stars[nearest].y)
        if (nearDist < 80) {
          const p = filtered[nearest]
          if (sel?.name === p.name) { closePanel(); return }
          setSelectedProject(p)
        }
      }
    }
  }, [renaming, deleteTarget, findNearest, filtered, sel, closePanel, starMeta.stars])

  // ── Constellation lines ──
  const connectLines = useMemo(() => {
    const result: { from: number; to: number; genre: string }[] = []
    const count = starMeta.stars.length
    for (let i = 0; i < count; i++) {
      for (let j = i + 1; j < count; j++) {
        if (filtered[i].genre !== filtered[j].genre) continue
        const dx = starMeta.stars[i].x - starMeta.stars[j].x
        const dy = starMeta.stars[i].y - starMeta.stars[j].y
        const dist = Math.sqrt(dx * dx + dy * dy)
        if (dist < 250) {
          result.push({ from: i, to: j, genre: filtered[i].genre || '未分类' })
        }
        if (result.length > 24) break
      }
      if (result.length > 24) break
    }
    return result
  }, [starMeta.stars, filtered])

  return (
    <div className="fixed inset-0 bg-[#01010a] overflow-hidden">
      <div ref={threeRef} className="fixed inset-0 w-full h-full pointer-events-none z-0" />

      {/* Burst particles */}
      {bursts.map(b => (
        <div key={b.id} className="fixed inset-0 pointer-events-none z-50">
          <div className="absolute rounded-full" style={{
            left: b.x, top: b.y, width: 0, height: 0,
            animation: 'burst-flash 0.45s ease-out forwards',
            background: `radial-gradient(circle, rgba(255,255,255,0.5), rgba(${b.color[0]},${b.color[1]},${b.color[2]},0.15), transparent)`,
            transform: 'translate(-50%, -50%)',
          }} />
          {Array.from({ length: 30 }, (_, i) => {
            const angle = (360 / 30) * i + seededRandom(i * 7) * 15
            const dist = 30 + seededRandom(i * 11) * 70
            const size = 1 + seededRandom(i * 3) * 2
            return (
              <div key={i} className="absolute rounded-full" style={{
                left: b.x, top: b.y, width: size, height: size,
                animation: `burst-particle 0.6s cubic-bezier(0,.8,.4,1) ${seededRandom(i * 5) * 0.05}s forwards`,
                background: i % 3 === 0 ? `rgba(${b.color[0]},${b.color[1]},${b.color[2]},0.6)` :
                  i % 3 === 1 ? 'rgba(255,255,255,0.4)' : 'rgba(200,210,255,0.3)',
                boxShadow: `0 0 ${size * 1.5}px rgba(${b.color[0]},${b.color[1]},${b.color[2]},0.25)`,
                '--ba': `${angle}deg`, '--bd': `${dist}px`,
              } as React.CSSProperties} />
            )
          })}
        </div>
      ))}

      {/* Glass header */}
      <div className="fixed top-0 left-0 right-0 z-30" style={{ background: 'rgba(0,0,0,0.6)', backdropFilter: 'blur(20px)', WebkitBackdropFilter: 'blur(20px)', borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
        <div className="flex items-center justify-between px-6 py-3" style={{ marginRight: sel ? PANEL_WIDTH : 0, transition: 'margin 0.5s cubic-bezier(0.23,1,0.32,1)' }}>
          <button onClick={() => navigate('/home')} className="flex items-center gap-1.5 text-white/55 hover:text-white/80 transition-all text-xs">
            <ArrowLeft className="w-3.5 h-3.5" /> 返回
          </button>
          <div className="flex items-center gap-3">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-3 h-3 text-white/30" />
              <input value={searchText} onChange={e => setSearchText(e.target.value)}
                placeholder="搜索宇宙..." className="w-40 bg-white/[0.04] border border-white/[0.08] rounded-xl pl-8 pr-3 py-2 text-xs text-white/70 placeholder:text-white/12 focus:outline-none focus:border-white/[0.15] transition-all" />
            </div>
            <button onClick={() => setViewMode(viewMode === 'universe' ? 'cards' : 'universe')}
              className="flex items-center gap-1.5 px-3 py-2 rounded-xl text-[11px] transition-all"
              style={{
                background: viewMode === 'cards' ? 'rgba(129,140,248,0.15)' : 'rgba(255,255,255,0.05)',
                border: `1px solid ${viewMode === 'cards' ? 'rgba(129,140,248,0.2)' : 'rgba(255,255,255,0.12)'}`,
                color: viewMode === 'cards' ? 'rgba(129,140,248,0.85)' : 'rgba(255,255,255,0.55)',
              }}>
              {viewMode === 'universe' ? '☰ 列表' : '✦ 星图'}
            </button>
            <button onClick={() => navigate('/new')} className="flex items-center gap-1.5 px-4 py-2 rounded-xl border border-white/[0.08] text-[11px] text-white/55 hover:text-white/80 hover:border-white/[0.15] hover:bg-white/[0.03] transition-all bg-white/[0.03]">
              <Plus className="w-3 h-3" /> 新建
            </button>
          </div>
        </div>
      </div>

      {/* Hero title — with background gradient to mask scrolling cards */}
      <div className="fixed top-14 left-0 right-0 z-20 pointer-events-none text-center pt-6 pb-6"
        style={{
          opacity: Math.min(1, entryProgress * 2),
          background: 'linear-gradient(180deg, #01010a 50%, transparent 100%)',
        }}>
        <h1 className="text-[clamp(22px,4vw,36px)] font-black tracking-[-0.04em] leading-none mb-2"
          style={{
            background: 'linear-gradient(180deg, rgba(255,255,255,0.9) 0%, rgba(255,255,255,0.45) 100%)',
            WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent', backgroundClip: 'text',
          }}>
          {viewMode === 'cards' ? '你的项目' : '你的宇宙'}
        </h1>
        <p className="text-[10px] tracking-[0.2em] text-white/40">{viewMode === 'cards' ? `${filtered.length} 个项目` : `${filtered.length} 颗星`}</p>
        <div className="mx-auto mt-2" style={{ width: 'clamp(120px,30vw,300px)', height: 1, background: 'linear-gradient(90deg,transparent,rgba(129,140,248,0.3),rgba(167,139,250,0.5),rgba(129,140,248,0.3),transparent)' }} />
      </div>

      {/* Empty state */}
      {filtered.length === 0 && !searchText && (
        <div className="absolute inset-0 z-10 flex items-center justify-center">
          <div className="text-center">
            <div className="w-14 h-14 rounded-full bg-white/[0.02] border border-white/[0.06] flex items-center justify-center mx-auto mb-5">
              <Sparkles className="w-6 h-6 text-white/40" />
            </div>
            <h3 className="text-base font-medium text-white/60 mb-2">你的宇宙还是空的</h3>
            <p className="text-xs text-white/40 mb-6 leading-relaxed">创建第一个故事，它就会化作一颗星<br />点亮你的宇宙</p>
            <button onClick={() => navigate('/new')}
              className="inline-flex items-center gap-1.5 px-5 py-2.5 rounded-xl border border-white/[0.08] text-xs text-white/60 hover:text-white/85 hover:border-white/[0.15] hover:bg-white/[0.02] transition-all">
              <Plus className="w-3 h-3" /> 创建第一个故事
            </button>
          </div>
        </div>
      )}
      {searchText && filtered.length === 0 && (
        <div className="absolute inset-0 z-10 flex items-center justify-center">
          <div className="text-center">
            <Search className="w-5 h-5 mx-auto mb-2 text-white/30" />
            <p className="text-xs text-white/45">没有找到 "{searchText}"</p>
          </div>
        </div>
      )}

      {/* ═══ Card list view ═══ */}
      {viewMode === 'cards' && filtered.length > 0 && (
        <div className="fixed inset-0 z-10 overflow-y-auto" style={{ top: 0, paddingBottom: '80px' }}>
          <div className="max-w-3xl mx-auto px-4 pt-52 pb-6 space-y-2">
            {filtered.map((p, i) => {
              const status = starStatus(p)
              const c = COLORS[status]
              const names = getPhaseNames(p.style_type)
              const done = (p.phases || []).slice(0, names.length).filter(ph => ph.done).length
              const total = names.length
              const pct = total > 0 ? (done / total) * 100 : 0
              const labels: Record<string, string> = { running: '生成中', complete: '已完成', pending: '待审核', progress: '创作中', new: '新建' }
              const isSelected = sel?.name === p.name
              return (
                <div key={p.name}
                  onClick={() => setSelectedProject(isSelected ? null : p)}
                  className={`project-item group relative flex items-center gap-4 px-5 py-4 rounded-2xl glass-surface-visible border cursor-pointer ${isSelected ? 'border-white/[0.15]' : 'border-white/[0.08]'} ${showStagger ? 'stagger-in' : ''}`}
                  style={{
                    background: isSelected ? `rgba(255,255,255,0.1)` : undefined,
                    zIndex: 1,
                    transitionDelay: showStagger ? `${i * 50}ms` : '0ms',
                  }}>
                  <div className="p-bottom-glow" />
                  <div className="p-border" />
                  <div className="p-sweep" />
                  <div className="relative z-[1] flex items-center gap-4 w-full">
                    {/* Status diamond */}
                    <span className="relative inline-flex items-center justify-center w-[20px] h-[20px] flex-shrink-0">
                      <span className={`absolute inset-0 rotate-45 blur-[3px] transition-all duration-700 ${p.running || p.pending_approval ? 'opacity-100' : 'opacity-60'}`}
                        style={{
                          background: `rgba(${c[0]},${c[1]},${c[2]},0.2)`,
                          animation: p.running || p.pending_approval ? 'status-glow 2s ease-in-out infinite' : 'none',
                        }} />
                      <span className={`absolute w-[10px] h-[10px] rotate-45 transition-all duration-300`}
                        style={{
                          background: `rgba(${c[0]},${c[1]},${c[2]},0.85)`,
                          boxShadow: `0 0 12px rgba(${c[0]},${c[1]},${c[2]},0.35)`,
                          animation: p.running ? 'status-core 1.5s ease-in-out infinite' :
                            p.pending_approval ? 'status-core 1.8s ease-in-out infinite' : 'none',
                        }} />
                    </span>
                    {/* Info */}
                    <div className="flex-1 min-w-0">
                      <h3 className="text-sm font-medium text-white/85 group-hover:text-white/90 transition-colors truncate">{p.name}</h3>
                      <div className="flex items-center gap-3 mt-0.5">
                        <span className="text-[10px] text-white/40">{p.genre || '未分类'}</span>
                        <span className="text-[10px] text-white/30">{p.updated_at?.slice(0, 10)}</span>
                        <span className="text-[10px] text-white/30">{done}/{total}</span>
                      </div>
                    </div>
                    {/* Progress bar */}
                    <div className="w-24 h-[3px] bg-white/[0.04] rounded-full overflow-hidden flex-shrink-0 hidden sm:block star-progress-track p-progress-glow">
                      <div className={`star-progress-fill ${pct === 100 ? 'complete' : ''}`} style={{ width: `${pct}%` }}>
                        <div className="sp-stars" />
                        <div className="sp-edge" />
                      </div>
                    </div>
                    {/* Status badge */}
                    <span className={`p-status-badge text-[10px] px-2 py-0.5 rounded-full flex-shrink-0 hidden sm:inline-block`}
                      style={{
                        color: `rgba(${c[0]},${c[1]},${c[2]},0.6)`,
                        background: `rgba(${c[0]},${c[1]},${c[2]},0.06)`,
                        '--badge-color': `${c[0]},${c[1]},${c[2]}`,
                      } as React.CSSProperties}>
                      {labels[status]}
                    </span>
                    {/* Actions */}
                    <div className="flex items-center gap-0.5 opacity-0 group-hover:opacity-100 transition-all flex-shrink-0 relative z-[1]">
                      <button onClick={e => { e.stopPropagation(); setRenaming(p.name); setRenameInput(p.name) }}
                          className="p-action-btn p-1.5 rounded-lg hover:bg-white/[0.04] text-white/30" title="重命名">
                        <Pencil className="w-3 h-3" />
                      </button>
                      <button onClick={e => { e.stopPropagation(); navigate(`/project/${encodeURIComponent(p.name)}`) }}
                        className="p-action-btn p-1.5 rounded-lg hover:bg-white/[0.04] text-white/30" title="打开">
                        <ExternalLink className="w-3 h-3" />
                      </button>
                      <button onClick={e => { e.stopPropagation(); setDeleteTarget(p.name) }}
                          className="p-action-btn p-1.5 rounded-lg hover:bg-red-500/[0.08] text-white/30 hover:text-red-400/60" title="删除">
                        <Trash2 className="w-3 h-3" />
                      </button>
                    </div>
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      )}

      {/* ═══ Universe container ═══ */}
      {viewMode !== 'cards' && (
      <div ref={universeRef}
        className="fixed inset-0 z-10 cursor-grab select-none"
        style={{ top: 0, cursor: isDragging ? 'grabbing' : 'grab' }}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={() => { setIsDragging(false); setHoveredStar(null) }}>
        {/* Panning layer */}
        <div style={{
          transform: `translate(${panX}px, ${panY}px)`,
          transition: isDragging ? 'none' : 'transform 0.6s cubic-bezier(0.23,1,0.32,1)',
          position: 'absolute', top: 0, left: 0,
        }}>
          {/* Constellation lines */}
          {connectLines.length > 0 && (
            <svg className="absolute pointer-events-none" style={{ top: 0, left: 0, width: '10000px', height: '10000px', overflow: 'visible' }}>
              {connectLines.map((ln, idx) => {
                const f = starMeta.stars[ln.from]; const t = starMeta.stars[ln.to]
                const gc = GENRE_COLORS[ln.genre] || [167, 139, 250]
                return (
                  <line key={idx} x1={f.x} y1={f.y} x2={t.x} y2={t.y}
                    stroke={`rgba(${gc[0]},${gc[1]},${gc[2]},0.1)`} strokeWidth="0.8" className="constellation-line" />
                )
              })}
            </svg>
          )}

          {/* Stars */}
          {filtered.map((p, i) => {
            const status = starStatus(p)
            const c = COLORS[status]
            const names = getPhaseNames(p.style_type)
            const done = (p.phases || []).slice(0, names.length).filter(ph => ph.done).length
            const total = names.length
            const seed = i * 13.7 + 42
            const pos = starMeta.stars[i]
            const brightness = 0.6 + (done / Math.max(total, 1)) * 0.4
            const z = zoom
            const coreSize = (3 + done * 1.8) * z
            const breathDur = 2.2 + seededRandom(seed * 2) * 2.5
            const breathDelay = seededRandom(seed * 3) * 4
            const depth = 0.012 + seededRandom(seed) * 0.022
            const driftDur = 10 + seededRandom(seed * 5) * 8
            const rx = 2 + seededRandom(seed * 11) * 3
            const ry = 1.5 + seededRandom(seed * 13) * 2.5

            const entryDelay = i * 120 + seededRandom(seed * 17) * 80
            const entryDuration = 1800 + seededRandom(seed * 23) * 600
            const raw = Math.max(0, (entryProgress * 5000 - entryDelay) / entryDuration)
            const ep = Math.min(raw, 1)
            const enterOpacity = Math.min(ep * 3, 1)

            const isSelected = sel?.name === p.name
            const isHovered = hoveredStar === p.name && !isSelected
            const isDimmed = searchText && !p.name.toLowerCase().includes(searchText.toLowerCase())
            const isMatched = searchText && p.name.toLowerCase().includes(searchText.toLowerCase())

            return (
              <div key={p.name}
                className="absolute flex items-center justify-center"
                style={{
                  left: pos.x, top: pos.y,
                  width: '60px', height: '60px',
                  marginLeft: '-30px', marginTop: '-30px',
                  opacity: visible ? brightness * enterOpacity : 0,
                  transition: 'opacity 0.9s',
                  zIndex: isHovered || isSelected ? 20 : 10,
                  pointerEvents: 'none',
                }}>
                {/* Horizontal marker line — selected stars only */}
                {isSelected && (
                  <>
                    <div className="absolute pointer-events-none" style={{
                      top: '50%',
                      right: 'calc(100% + 8px)',
                      width: 'clamp(40px, 20vw, 200px)',
                      height: 1.5,
                      background: `linear-gradient(90deg, rgba(${c[0]},${c[1]},${c[2]},0.02), rgba(${c[0]},${c[1]},${c[2]},0.3), rgba(${c[0]},${c[1]},${c[2]},0.5))`,
                      boxShadow: `0 0 10px rgba(${c[0]},${c[1]},${c[2]},0.2)`,
                      filter: 'blur(0.5px)',
                    }} />
                    <div className="absolute pointer-events-none" style={{
                      top: '50%',
                      left: 'calc(100% + 8px)',
                      width: 'clamp(40px, 20vw, 200px)',
                      height: 1.5,
                      background: `linear-gradient(270deg, rgba(${c[0]},${c[1]},${c[2]},0.02), rgba(${c[0]},${c[1]},${c[2]},0.3), rgba(${c[0]},${c[1]},${c[2]},0.5))`,
                      boxShadow: `0 0 10px rgba(${c[0]},${c[1]},${c[2]},0.2)`,
                      filter: 'blur(0.5px)',
                    }} />
                  </>
                )}

                {/* Concentric ring */}
                {isSelected && (
                  <div className="absolute pointer-events-none" style={{
                    width: coreSize * 8, height: coreSize * 8,
                    borderRadius: '50%',
                    border: `1.5px solid rgba(${c[0]},${c[1]},${c[2]},0.25)`,
                    boxShadow: `0 0 12px rgba(${c[0]},${c[1]},${c[2]},0.1), inset 0 0 12px rgba(${c[0]},${c[1]},${c[2]},0.05)`,
                    animation: 'ring-pulse 2s ease-in-out infinite',
                  }} />
                )}

                {/* Star */}
                <div className={`flex items-center justify-center ${isDimmed ? 'opacity-15' : ''} ${isMatched ? 'scale-125' : ''}`}
                  style={{
                    filter: isDimmed ? 'grayscale(0.9)' : 'none',
                    transition: 'filter 0.5s, opacity 0.5s, transform 0.5s',
                  }}>
                  <div className="flex items-center justify-center" style={{
                    animation: `star-drift ${driftDur}s ease-in-out ${breathDelay}s infinite`,
                    '--drift-rx': `${rx}px`, '--drift-ry': `${ry}px`,
                  } as React.CSSProperties}>
                    <div className="absolute rounded-full pointer-events-none" style={{
                      width: '60px', height: '60px',
                      background: `radial-gradient(circle, rgba(${c[0]},${c[1]},${c[2]},${isHovered || isSelected ? 0.2 : 0.06 * brightness}) 0%, transparent 70%)`,
                      filter: `blur(${isSelected ? 20 : 35}px)`,
                      transition: 'all 0.5s',
                    }} />
                    <div className="relative flex items-center justify-center" style={{
                      animation: `star-breathe ${breathDur}s ease-in-out ${breathDelay}s infinite`,
                      transform: isHovered ? 'scale(1.8)' : isSelected ? 'scale(2.4)' : 'scale(1)',
                      transition: 'transform 0.4s cubic-bezier(0.23,1,0.32,1)',
                    }}>
                      <div className="absolute rounded-full pointer-events-none" style={{
                        width: '60px', height: '60px',
                        background: `radial-gradient(circle, rgba(${c[0]},${c[1]},${c[2]},${0.12 * brightness}) 0%, transparent 60%)`,
                        filter: 'blur(10px)',
                      }} />
                      <div className="absolute rounded-full pointer-events-none" style={{
                        width: '20px', height: '20px',
                        background: `radial-gradient(circle, rgba(255,255,255,${0.15 * brightness}) 0%, rgba(${c[0]},${c[1]},${c[2]},${0.2 * brightness}) 50%, transparent 70%)`,
                        filter: 'blur(2px)',
                      }} />
                      <div className="rounded-full" style={{
                        width: coreSize, height: coreSize,
                        background: `rgba(255,255,255,${0.9 * brightness})`,
                        boxShadow: `0 0 ${coreSize * 0.8}px rgba(255,255,255,${0.35 * brightness}), 0 0 ${coreSize * 4}px rgba(${c[0]},${c[1]},${c[2]},${0.35 * brightness})`,
                      }} />
                    </div>
                  </div>
                </div>

                {/* Name label — fades in as zoom increases */}
                <div className="absolute pointer-events-none whitespace-nowrap"
                  style={{
                    left: `calc(100% + ${coreSize * 0.8}px)`,
                    top: '50%',
                    transform: 'translateY(-50%)',
                    opacity: Math.min(1, (z - 1) * 2),
                  }}>
                  <span className="text-[11px] font-medium tracking-wide"
                    style={{ color: `rgba(${c[0]},${c[1]},${c[2]},0.7)` }}>
                    {p.name}
                  </span>
                </div>

                {/* Hover card */}
                {!sel && (
                  <div className={`absolute transition-all duration-500 ${isHovered ? 'opacity-100' : 'opacity-0 pointer-events-none'}`}
                    style={{
                      top: `calc(100% + 20px)`, left: '50%',
                      transform: `translateX(-50%) ${isHovered ? 'translateY(0)' : 'translateY(8px)'}`,
                      transition: CARD_TRANSITION,
                      width: 'clamp(200px, 40vw, 280px)',
                      background: 'rgba(255,255,255,0.10)',
                      backdropFilter: 'blur(24px)',
                      WebkitBackdropFilter: 'blur(24px)',
                      border: '1px solid rgba(255,255,255,0.10)',
                      borderRadius: '16px', overflow: 'hidden',
                    }}>
                    <div className="relative z-[1] px-4 py-3.5">
                      <div className="flex items-center gap-2.5 mb-2">
                        <span className="relative inline-flex items-center justify-center w-[16px] h-[16px] flex-shrink-0">
                          <span className={`absolute inset-0 rotate-45 blur-[2px] ${p.running || p.pending_approval ? 'opacity-100' : 'opacity-60'}`}
                            style={{ background: `rgba(${c[0]},${c[1]},${c[2]},0.2)`, animation: p.running || p.pending_approval ? 'status-glow 2s ease-in-out infinite' : 'none' }} />
                          <span className={`absolute w-[8px] h-[8px] rotate-45`} style={{ background: `rgba(${c[0]},${c[1]},${c[2]},0.8)`, boxShadow: `0 0 6px rgba(${c[0]},${c[1]},${c[2]},0.3)` }} />
                        </span>
                        <h4 className="text-xs font-medium text-white/80 truncate flex-1">{p.name}</h4>
                      </div>
                      <div className="w-full h-[2px] bg-white/[0.04] rounded-full overflow-hidden mb-2">
                        <div className="h-full rounded-full transition-all duration-700" style={{
                          width: `${total > 0 ? (done / total) * 100 : 0}%`,
                          background: `linear-gradient(90deg, rgba(${c[0]},${c[1]},${c[2]},0.3), rgba(${c[0]},${c[1]},${c[2]},0.5))`,
                          boxShadow: `0 0 6px rgba(${c[0]},${c[1]},${c[2]},0.15)`,
                        }} />
                      </div>
                      <div className="flex items-center justify-between">
                        <span className="text-[9px] text-white/55">{p.genre || '未分类'}</span>
                        <span className={`text-[9px] ${p.running ? 'text-cyan-400/60' : done >= total ? 'text-purple-400/60' : p.pending_approval ? 'text-pink-400/60' : done > 0 ? 'text-indigo-400/60' : 'text-white/45'}`}>{done}/{total}</span>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            )
          })}
        </div>
      </div>
      )}

      {/* ═══ Detail panel ═══ */}
      {sel && (
        <div className="fixed top-0 right-0 z-40 h-full" style={{
          width: PANEL_WIDTH,
          animation: 'panel-slide-in 0.5s cubic-bezier(0.23,1,0.32,1) forwards',
          background: 'rgba(8,8,20,0.85)',
          backdropFilter: 'blur(24px)',
          WebkitBackdropFilter: 'blur(24px)',
          borderLeft: '1px solid rgba(255,255,255,0.06)',
        }}>
          {(() => {
            const p = sel
            const status = starStatus(p)
            const c = COLORS[status]
            const names = getPhaseNames(p.style_type)
            const done = (p.phases || []).slice(0, names.length).filter(ph => ph.done).length
            const total = names.length
            const pct = total > 0 ? (done / total) * 100 : 0
            const labels: Record<string, string> = { running: '生成中', complete: '已完成', pending: '待审核', progress: '创作中', new: '新建' }

            return (
              <div className="h-full flex flex-col py-5 px-5 overflow-y-auto" style={{ height: '100vh' }}>
                <div className="flex justify-end mb-4">
                  <button onClick={closePanel} className="p-1.5 rounded-lg hover:bg-white/[0.04] text-white/55 hover:text-white/70 transition-all">
                    <X className="w-3.5 h-3.5" />
                  </button>
                </div>

                <div className="flex items-center gap-3 mb-4">
                  <span className="relative inline-flex items-center justify-center w-[24px] h-[24px] flex-shrink-0">
                    <span className={`absolute inset-0 rotate-45 blur-[3px] ${p.running || p.pending_approval ? 'opacity-100' : 'opacity-60'}`}
                      style={{ background: `rgba(${c[0]},${c[1]},${c[2]},0.25)`, animation: p.running || p.pending_approval ? 'status-glow 2s ease-in-out infinite' : 'none' }} />
                    <span className={`absolute w-[12px] h-[12px] rotate-45`}
                      style={{
                        background: `rgba(${c[0]},${c[1]},${c[2]},0.85)`,
                        boxShadow: `0 0 12px rgba(${c[0]},${c[1]},${c[2]},0.35)`,
                        animation: p.running ? 'status-core 1.5s ease-in-out infinite' : p.pending_approval ? 'status-core 1.8s ease-in-out infinite' : 'none',
                      }} />
                  </span>
                  <div className="flex-1 min-w-0">
                    {renaming === p.name ? (
                      <div className="flex items-center gap-1" onClick={e => e.stopPropagation()}>
                        <input className="bg-white/[0.06] border border-white/[0.1] rounded-lg px-2 py-1 text-xs font-medium text-white/75 focus:outline-none focus:border-white/20 w-full"
                          value={renameInput} onChange={e => setRenameInput(e.target.value)} autoFocus
                          onKeyDown={e => { if (e.key === 'Enter') handleRename(p.name); if (e.key === 'Escape') setRenaming(null) }} />
                        <button onClick={() => handleRename(p.name)} className="p-1 rounded hover:bg-green-500/10 text-green-400"><Check className="w-3 h-3" /></button>
                        <button onClick={() => setRenaming(null)} className="p-1 rounded hover:bg-white/[0.04] text-white/55"><X className="w-3 h-3" /></button>
                      </div>
                    ) : (
                      <div className="flex items-center gap-2">
                        <h2 className="text-sm font-medium text-white/85 truncate">{p.name}</h2>
                        <button onClick={() => { setRenaming(p.name); setRenameInput(p.name) }}
                          className="p-1 rounded hover:bg-white/[0.04] text-white/40 hover:text-white/65 transition-all flex-shrink-0">
                          <Pencil className="w-2.5 h-2.5" />
                        </button>
                      </div>
                    )}
                    <span className={`text-[10px] ${p.running ? 'text-cyan-400/60' : done >= total ? 'text-purple-400/60' : p.pending_approval ? 'text-pink-400/60' : done > 0 ? 'text-indigo-400/60' : 'text-white/55'}`}>
                      {labels[status]}
                    </span>
                  </div>
                </div>

                <div className="space-y-2 mb-4 pb-4" style={{ borderBottom: '1px solid rgba(255,255,255,0.06)' }}>
                  <div className="flex justify-between">
                    <span className="text-[10px] text-white/55">类型</span>
                    <span className="text-[10px] text-white/80">{p.genre || '未分类'}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-[10px] text-white/55">风格</span>
                    <span className="text-[10px] text-white/80">{p.style_type ? `类型 ${p.style_type}` : '-'}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-[10px] text-white/55">进度</span>
                    <span className="text-[10px] text-white/80">{done}/{total}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-[10px] text-white/55">更新</span>
                    <span className="text-[10px] text-white/80">{p.updated_at?.slice(0, 10) || '-'}</span>
                  </div>
                </div>

                <div className="mb-4">
                  <div className="w-full h-[3px] bg-white/[0.04] rounded-full overflow-hidden">
                    <div className="h-full rounded-full transition-all duration-700" style={{
                      width: `${pct}%`,
                      background: `linear-gradient(90deg, rgba(${c[0]},${c[1]},${c[2]},0.3), rgba(${c[0]},${c[1]},${c[2]},0.6))`,
                      boxShadow: `0 0 8px rgba(${c[0]},${c[1]},${c[2]},0.2)`,
                    }} />
                  </div>
                </div>

                <div className="space-y-1.5 mb-6 flex-1">
                  <h4 className="text-[10px] text-white/55 tracking-wider mb-2 uppercase">阶段列表</h4>
                  {names.map((name, idx) => {
                    const phase = (p.phases || [])[idx]
                    const isDone = phase?.done
                    return (
                      <div key={idx} className="flex items-center gap-2.5 px-3 py-2 rounded-lg transition-all"
                        style={{
                          background: isDone ? `rgba(${c[0]},${c[1]},${c[2]},0.04)` : 'rgba(255,255,255,0.02)',
                          border: '1px solid rgba(255,255,255,0.05)',
                        }}>
                        <span className="text-xs" style={{ opacity: isDone ? 0.7 : 0.35 }}>{PHASE_ICONS[idx] || '📄'}</span>
                        <span className="text-[10px] text-white/65" style={{ opacity: isDone ? 0.7 : 0.45 }}>{name}</span>
                        {isDone && <span className="ml-auto text-[8px] text-white/45">✓</span>}
                      </div>
                    )
                  })}
                </div>

                <div className="space-y-2 pt-4" style={{ borderTop: '1px solid rgba(255,255,255,0.06)' }}>
                  <button onClick={() => navigate(`/project/${encodeURIComponent(p.name)}`)}
                    className="w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl text-xs font-medium transition-all"
                    style={{
                      background: `rgba(${c[0]},${c[1]},${c[2]},0.1)`,
                      color: `rgba(${c[0]},${c[1]},${c[2]},0.7)`,
                      border: `1px solid rgba(${c[0]},${c[1]},${c[2]},0.15)`,
                    }}
                    onMouseEnter={e => { e.currentTarget.style.background = `rgba(${c[0]},${c[1]},${c[2]},0.18)`; e.currentTarget.style.color = `rgba(${c[0]},${c[1]},${c[2]},0.9)` }}
                    onMouseLeave={e => { e.currentTarget.style.background = `rgba(${c[0]},${c[1]},${c[2]},0.1)`; e.currentTarget.style.color = `rgba(${c[0]},${c[1]},${c[2]},0.7)` }}>
                    <ExternalLink className="w-3 h-3" /> 打开项目
                  </button>
                  <div className="flex gap-2">
                    <button onClick={() => openProjectFolder(p.name)}
                      className="flex-1 flex items-center justify-center gap-1.5 px-3 py-2 rounded-xl border border-white/[0.06] text-[10px] text-white/55 hover:text-white/70 hover:bg-white/[0.03] transition-all">
                      <FolderOpen className="w-2.5 h-2.5" /> 文件夹
                    </button>
                    <button onClick={() => setDeleteTarget(p.name)}
                      className="flex-1 flex items-center justify-center gap-1.5 px-3 py-2 rounded-xl border border-white/[0.06] text-[10px] text-red-400/55 hover:text-red-400/80 hover:bg-red-500/[0.08] transition-all">
                      <Trash2 className="w-2.5 h-2.5" /> 删除
                    </button>
                  </div>
                </div>
              </div>
            )
          })()}
        </div>
      )}

      {/* Genre legend */}
      {filtered.length > 0 && !sel && (
        <div className="fixed bottom-4 left-1/2 -translate-x-1/2 z-20 flex items-center gap-3 px-4 py-2 rounded-xl"
          style={{ background: 'rgba(255,255,255,0.06)', backdropFilter: 'blur(16px)', border: '1px solid rgba(255,255,255,0.10)' }}>
          {Array.from(new Set(filtered.map(p => p.genre))).filter(Boolean).map(genre => {
            const gc = GENRE_COLORS[genre!] || [167, 139, 250]
            const cnt = filtered.filter(p => p.genre === genre).length
            return (
              <div key={genre} className="flex items-center gap-1.5">
                <span className="w-2 h-[1.5px] rounded-full" style={{ background: `rgba(${gc[0]},${gc[1]},${gc[2]},0.6)` }} />
                <span className="text-[9px] text-white/45 tracking-wider">{genre}</span>
                <span className="text-[8px] text-white/30">{cnt}</span>
              </div>
            )
          })}
        </div>
      )}

      {/* Zoom controls */}
      <div className="fixed bottom-4 right-4 z-20 flex items-center gap-2">
        <button onClick={zoomOut}
          className="w-8 h-8 rounded-lg flex items-center justify-center text-white/55 hover:text-white/80 hover:bg-white/[0.04] transition-all text-sm"
          style={{ background: 'rgba(255,255,255,0.05)', backdropFilter: 'blur(8px)', border: '1px solid rgba(255,255,255,0.06)' }}>
          −
        </button>
        <div className="px-2.5 py-1.5 rounded-lg text-[10px] text-white/45 min-w-[40px] text-center"
          style={{ background: 'rgba(255,255,255,0.05)', backdropFilter: 'blur(8px)', border: '1px solid rgba(255,255,255,0.06)' }}>
          {Math.round(zoom * 100)}%
        </div>
        <button onClick={zoomIn}
          className="w-8 h-8 rounded-lg flex items-center justify-center text-white/55 hover:text-white/80 hover:bg-white/[0.04] transition-all text-base"
          style={{ background: 'rgba(255,255,255,0.05)', backdropFilter: 'blur(8px)', border: '1px solid rgba(255,255,255,0.06)' }}>
          +
        </button>
      </div>

      {/* Delete confirmation */}
      {deleteTarget && (
        <div className="fixed inset-0 z-50 flex items-center justify-center" style={{ background: 'rgba(0,0,0,0.6)', backdropFilter: 'blur(8px)' }}>
          <div className="px-6 py-5 rounded-2xl max-w-sm w-full mx-4" style={{ background: 'rgba(255,255,255,0.12)', backdropFilter: 'blur(24px)', border: '1px solid rgba(255,255,255,0.10)' }}>
            <h3 className="text-sm font-medium text-white/85 mb-2">确认删除</h3>
            <p className="text-xs text-white/55 mb-5">将永久删除项目 "{deleteTarget}"，此操作不可撤销。</p>
            <div className="flex justify-end gap-3">
              <button onClick={() => setDeleteTarget(null)} className="px-4 py-2 rounded-xl text-xs text-white/55 hover:text-white/70 transition-all">取消</button>
              <button onClick={handleDelete} className="px-4 py-2 rounded-xl text-xs bg-red-500/15 text-red-400/70 hover:bg-red-500/25 hover:text-red-400 transition-all">删除</button>
            </div>
          </div>
        </div>
      )}

      <style>{`
        @keyframes star-breathe { 0%,100%{transform:scale(1)} 50%{transform:scale(1.2)} }
        @keyframes star-drift {
          0%,100%{transform:translate(0,0)}
          25%{transform:translate(var(--drift-rx,3px),calc(var(--drift-ry,2px)*-1))}
          50%{transform:translate(calc(var(--drift-rx,3px)*-1),var(--drift-ry,2px))}
          75%{transform:translate(calc(var(--drift-rx,3px)*-0.5),calc(var(--drift-ry,2px)*-0.5))}
        }
        .constellation-line{stroke-dasharray:4 6;animation:line-pulse 4s ease-in-out infinite}
        @keyframes line-pulse{0%,100%{opacity:0.3}50%{opacity:1}}
        @keyframes burst-flash{0%{width:0;height:0;opacity:1}100%{width:80px;height:80px;opacity:0}}
        @keyframes burst-particle{0%{transform:rotate(var(--ba,0deg))translateY(0);opacity:1}100%{transform:rotate(var(--ba,0deg))translateY(calc(var(--bd,50px)*-1));opacity:0}}
        @keyframes panel-slide-in{0%{transform:translateX(100%)}100%{transform:translateX(0)}}
        @keyframes ring-pulse{0%,100%{transform:scale(1);opacity:0.6}50%{transform:scale(1.12);opacity:1}}
      `}</style>
    </div>
  )
}