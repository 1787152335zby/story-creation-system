import { useEffect, useRef, useState, useMemo, useCallback, CSSProperties } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import * as THREE from 'three'
import { getCircleTexture } from '../lib/three-utils'
import { Sparkles, Search, Plus, Pencil, Check, X, FolderOpen, Trash2 } from 'lucide-react'
import ConfirmModal from '../components/ConfirmModal'
import { fetchProjects, deleteProject, openProjectFolder, renameProject } from '../lib/api'
import { useToast } from '../components/Toast'
import type { ProjectInfo } from '../lib/types'
import { getPhaseNames } from '../lib/constants'

const PARTICLE_COUNT = 400
const DRIFT_COUNT = 400
const STAR_COUNT = 800
const EXPLOSION_DURATION = 2.5

type Phase = 'gate' | 'exploding' | 'settled'

function TiltPanel({ children, className = '', style, onClick }: { children: React.ReactNode; className?: string; style?: CSSProperties; onClick?: () => void }) {
  const ref = useRef<HTMLDivElement>(null)
  const handleMove = useCallback((e: React.MouseEvent) => {
    const el = ref.current; if (!el) return
    const rect = el.getBoundingClientRect()
    const x = (e.clientX - rect.left) / rect.width - 0.5
    const y = (e.clientY - rect.top) / rect.height - 0.5
    el.style.setProperty('--tilt-x', `${x}`)
    el.style.setProperty('--tilt-y', `${y}`)
    el.style.setProperty('--tilt-x-pos', `${(x + 0.5) * 100}%`)
    el.style.setProperty('--tilt-y-pos', `${(y + 0.5) * 100}%`)
    el.style.transform = `perspective(800px) rotateY(${x * 8}deg) rotateX(${-y * 8}deg) scale(1.02)`
    el.style.boxShadow = `0 20px 50px rgba(99,102,241,${0.1 + Math.abs(x + y) * 0.08}), 0 0 0 1px rgba(255,255,255,${0.08 + Math.abs(x + y) * 0.1}) inset`
  }, [])
  const handleLeave = useCallback(() => {
    const el = ref.current; if (!el) return
    el.style.setProperty('--tilt-x', '0')
    el.style.setProperty('--tilt-y', '0')
    el.style.transform = 'perspective(800px) rotateY(0deg) rotateX(0deg) scale(1)'
    el.style.boxShadow = 'none'
  }, [])
  return (
    <div ref={ref} className={className} style={style}
      onMouseMove={handleMove} onMouseLeave={handleLeave} onClick={onClick}>
      {children}
    </div>
  )
}

export default function CosmicHomePage() {
  const threeRef = useRef<HTMLDivElement>(null)
  const bgCanvasRef = useRef<HTMLCanvasElement>(null)
  const navigate = useNavigate()
  const location = useLocation()
  const skipGate = location.pathname === '/home'
  const { toast } = useToast()
  const [phase, setPhase] = useState<Phase>(skipGate ? 'settled' : 'gate')
  const [contentVisible, setContentVisible] = useState(skipGate)
  const [bgReady, setBgReady] = useState(skipGate)
  const phaseRef = useRef<Phase>(skipGate ? 'settled' : 'gate')
  phaseRef.current = phase

  const [projects, setProjects] = useState<ProjectInfo[]>([])
  const [loading, setLoading] = useState(true)
  const [deleteTarget, setDeleteTarget] = useState<string | null>(null)
  const [searchText, setSearchText] = useState('')
  const [renaming, setRenaming] = useState<string | null>(null)
  const [renameInput, setRenameInput] = useState('')
  const [showStagger, setShowStagger] = useState(false)

  useEffect(() => {
    if (contentVisible) {
      setTimeout(() => setShowStagger(true), 100)
    } else {
      setShowStagger(false)
    }
  }, [contentVisible])

  const filteredProjects = useMemo(() => {
    if (!searchText.trim()) return projects
    return projects.filter(p => p.name?.toLowerCase().includes(searchText.trim().toLowerCase()))
  }, [projects, searchText])

  const load = async () => {
    try { setProjects(await fetchProjects()) } catch (e) { toast('加载失败', 'error') } finally { setLoading(false) }
  }
  const handleRename = async (old: string) => {
    if (!renameInput.trim() || renameInput.trim() === old) { setRenaming(null); return }
    try { await renameProject(old, renameInput.trim()); toast('已重命名', 'success'); setRenaming(null); load() } catch (e: any) { toast(e.message || '失败', 'error') }
  }

  useEffect(() => { load() }, [])
  useEffect(() => {
    if (!projects.some(p => p.running)) return
    const t = setInterval(() => { fetchProjects().then(setProjects).catch(() => {}) }, 3000)
    return () => clearInterval(t)
  }, [projects])

  // Three.js scene (gate + explosion + settled background)
  useEffect(() => {
    if (skipGate) return
    const container = threeRef.current
    if (!container) return

    const scene = new THREE.Scene()
    const camera = new THREE.PerspectiveCamera(60, window.innerWidth / window.innerHeight, 0.1, 1000)
    camera.position.z = 6

    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true })
    renderer.setSize(window.innerWidth, window.innerHeight)
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
    renderer.setClearColor(0x000000, 1)
    container.appendChild(renderer.domElement)

    const gridHelper = new THREE.PolarGridHelper(8, 32, 20, 64, 0x111111, 0x111111)
    gridHelper.position.z = -3
    scene.add(gridHelper)

    const ringGeo = new THREE.TorusGeometry(3, 0.002, 16, 120)
    const ringMat = new THREE.MeshBasicMaterial({ color: 0x222233 })
    const ring = new THREE.Mesh(ringGeo, ringMat)
    ring.rotation.x = Math.PI * 0.45; ring.position.z = -0.5
    scene.add(ring)

    for (let i = 0; i < 3; i++) {
      const orbitGeo = new THREE.TorusGeometry(1.2 + i * 0.9, 0.001, 8, 80)
      const orbit = new THREE.Mesh(orbitGeo, new THREE.MeshBasicMaterial({ color: 0x111122 }))
      orbit.rotation.x = Math.random() * Math.PI; orbit.rotation.y = Math.random() * Math.PI
      scene.add(orbit)
    }

    const glow = new THREE.Mesh(new THREE.SphereGeometry(0.15, 32, 32), new THREE.MeshBasicMaterial({ color: 0x334466 }))
    scene.add(glow)
    const glowOuter = new THREE.Mesh(new THREE.SphereGeometry(0.35, 32, 32), new THREE.MeshBasicMaterial({ color: 0x111133, transparent: true, opacity: 0.4 }))
    scene.add(glowOuter)

    // Main particles (400 sphere)
    const particleGeo = new THREE.BufferGeometry()
    const positions = new Float32Array(PARTICLE_COUNT * 3)
    const basePositions = new Float32Array(PARTICLE_COUNT * 3)
    const velocities = new Float32Array(PARTICLE_COUNT * 3)
    const colors = new Float32Array(PARTICLE_COUNT * 3)

    for (let i = 0; i < PARTICLE_COUNT; i++) {
      const i3 = i * 3
      const theta = Math.random() * Math.PI * 2
      const phi = Math.acos(2 * Math.random() - 1)
      const radius = 1.8 + Math.random() * 3.5
      const x = Math.sin(phi) * Math.cos(theta) * radius
      const y = Math.sin(phi) * Math.sin(theta) * radius + 0.5
      const z = Math.cos(phi) * radius
      basePositions[i3] = positions[i3] = x
      basePositions[i3 + 1] = positions[i3 + 1] = y
      basePositions[i3 + 2] = positions[i3 + 2] = z
      const len = Math.sqrt(x * x + y * y + z * z) || 1
      const speed = 3 + Math.random() * 6
      velocities[i3] = (x / len) * speed + (Math.random() - 0.5) * 3
      velocities[i3 + 1] = (y / len) * speed + (Math.random() - 0.5) * 2
      velocities[i3 + 2] = (z / len) * speed + (Math.random() - 0.5) * 2
      const c = new THREE.Color().setHSL(0.65 + Math.random() * 0.1, 0.5, 0.5 + Math.random() * 0.3)
      colors[i3] = c.r; colors[i3 + 1] = c.g; colors[i3 + 2] = c.b
    }
    particleGeo.setAttribute('position', new THREE.BufferAttribute(positions, 3))
    particleGeo.setAttribute('color', new THREE.BufferAttribute(colors, 3))

    const particleMat = new THREE.PointsMaterial({
      size: 0.055, vertexColors: true, blending: THREE.AdditiveBlending,
      depthWrite: false, transparent: true, opacity: 0, map: getCircleTexture(),
    })
    const particleSystem = new THREE.Points(particleGeo, particleMat)
    scene.add(particleSystem)

    // Background stars (500)
    const starGeo = new THREE.BufferGeometry()
    const starPos = new Float32Array(STAR_COUNT * 3)
    const starCol = new Float32Array(STAR_COUNT * 3)
    for (let i = 0; i < STAR_COUNT; i++) {
      const i3 = i * 3
      starPos[i3] = (Math.random() - 0.5) * 100
      starPos[i3 + 1] = (Math.random() - 0.5) * 60
      starPos[i3 + 2] = -10 - Math.random() * 50
      const c = new THREE.Color().setHSL(0.62, 0.3, 0.12 + Math.random() * 0.18)
      starCol[i3] = c.r; starCol[i3 + 1] = c.g; starCol[i3 + 2] = c.b
    }
    starGeo.setAttribute('position', new THREE.BufferAttribute(starPos, 3))
    starGeo.setAttribute('color', new THREE.BufferAttribute(starCol, 3))
    const starMat = new THREE.PointsMaterial({
      size: 0.05, vertexColors: true, blending: THREE.AdditiveBlending,
      depthWrite: false, transparent: true, opacity: 0, map: getCircleTexture(),
    })
    scene.add(new THREE.Points(starGeo, starMat))

    // Drift particles (400) for settled phase
    const driftGeo = new THREE.BufferGeometry()
    const driftPos = new Float32Array(DRIFT_COUNT * 3)
    const driftVel = new Float32Array(DRIFT_COUNT * 3)
    for (let i = 0; i < DRIFT_COUNT; i++) {
      const i3 = i * 3
      driftPos[i3] = (Math.random() - 0.5) * 80
      driftPos[i3 + 1] = (Math.random() - 0.5) * 50
      driftPos[i3 + 2] = (Math.random() - 0.5) * 40
      driftVel[i3] = (Math.random() - 0.5) * 0.05
      driftVel[i3 + 1] = (Math.random() - 0.5) * 0.05
      driftVel[i3 + 2] = (Math.random() - 0.5) * 0.03
    }
    driftGeo.setAttribute('position', new THREE.BufferAttribute(driftPos, 3))
    const driftMat = new THREE.PointsMaterial({
      size: 0.1, color: 0x88aadd, blending: THREE.AdditiveBlending,
      depthWrite: false, transparent: true, opacity: 0, map: getCircleTexture(),
    })
    const driftPs = new THREE.Points(driftGeo, driftMat)
    scene.add(driftPs)

    let fadeInProgress = 0
    let explosionProgress = -1
    let camTargetZ = 6
    let settled = false
    let animId = 0
    const clock = new THREE.Clock()
    const posArr = particleGeo.attributes.position.array as Float32Array
    const dpArr = driftGeo.attributes.position.array as Float32Array

    const animate = () => {
      const t = clock.getElapsedTime()

      if (fadeInProgress < 1) {
        fadeInProgress = Math.min(1, fadeInProgress + 0.006)
        particleMat.opacity = 0.8 * fadeInProgress
        starMat.opacity = fadeInProgress
      }

      camera.position.z += (camTargetZ - camera.position.z) * 0.01
      gridHelper.position.z = -3 - (camTargetZ - 6) * 0.5

      if (settled) {
        const pulse = 0.7 + 0.3 * Math.sin(t * 0.3)
        glowOuter.material.color.setHSL(0.68, 0.4, 0.12 * pulse)

        // Ring breathing
        const ringHue = 0.65 + 0.04 * Math.sin(t * 0.2)
        const ringSat = 0.2 + 0.1 * Math.sin(t * 0.35)
        ring.material.color.setHSL(ringHue, ringSat, 0.15)
        ring.rotation.z += 0.0003 + 0.0002 * Math.sin(t * 0.15)

        // Orbit rings slow sway
        scene.children.forEach(child => {
          if (child.isMesh && child !== ring && child !== glow && child !== glowOuter && child !== gridHelper) {
            child.rotation.x += 0.0001 * Math.sin(t * 0.1 + (child.id % 3))
            child.rotation.y += 0.00015 * Math.sin(t * 0.08 + (child.id % 5))
          }
        })

        // Star breathing
        starMat.size = 0.05 + 0.02 * Math.sin(t * 0.4)

        // Drift particles breathing
        driftMat.size = 0.1 + 0.03 * Math.sin(t * 0.5 + 1)
        driftMat.opacity = 0.85 + 0.05 * Math.sin(t * 0.2 + 2)

        // Explosion residual particles slow drift with wave
        if (explosionProgress >= 1) {
          for (let i = 0; i < PARTICLE_COUNT; i++) {
            const i3 = i * 3
            posArr[i3] += Math.sin(t * 0.1 + i * 0.01) * 0.0005
            posArr[i3 + 1] += Math.cos(t * 0.12 + i * 0.01) * 0.0005
            posArr[i3 + 2] += Math.sin(t * 0.08 + i * 0.02) * 0.0003
          }
          particleGeo.attributes.position.needsUpdate = true
        }

        driftPs.rotation.y += 0.0003
        driftPs.rotation.x += 0.0001
        for (let i = 0; i < DRIFT_COUNT; i++) {
          const i3 = i * 3
          dpArr[i3] += driftVel[i3]
          dpArr[i3 + 1] += driftVel[i3 + 1]
          dpArr[i3 + 2] += driftVel[i3 + 2]
        }
        driftGeo.attributes.position.needsUpdate = true
      }

      if (explosionProgress >= 0) {
        explosionProgress += 0.016 / EXPLOSION_DURATION
        if (explosionProgress < 1) {
          for (let i = 0; i < PARTICLE_COUNT; i++) {
            const i3 = i * 3
            posArr[i3] += velocities[i3] * 0.016
            posArr[i3 + 1] += velocities[i3 + 1] * 0.016
            posArr[i3 + 2] += velocities[i3 + 2] * 0.016
          }
          particleGeo.attributes.position.needsUpdate = true
          particleMat.opacity = explosionProgress < 0.6 ? 0.9 : 0.9 * (1 - (explosionProgress - 0.6) / 0.2)
        }
        if (explosionProgress >= 0.6) {
          particleMat.opacity = 0.4
          particleMat.size = 0.08
          for (let i = 0; i < PARTICLE_COUNT; i++) {
            const i3 = i * 3
            posArr[i3] += (Math.random() - 0.5) * 0.004
            posArr[i3 + 1] += (Math.random() - 0.5) * 0.004
            posArr[i3 + 2] += (Math.random() - 0.5) * 0.003
          }
          particleGeo.attributes.position.needsUpdate = true
        }
        if (explosionProgress >= 0.5 && !settled) {
          settled = true
          driftMat.opacity = 0.85
          renderer.setClearColor(new THREE.Color(0x050510), 1)
        }
      } else {
        particleSystem.rotation.y += 0.001
        particleSystem.rotation.x += 0.0003
        ring.rotation.z += 0.0005
        glowOuter.scale.setScalar(1 + Math.sin(t * 2) * 0.2)
      }

      renderer.render(scene, camera)
      animId = requestAnimationFrame(animate)
    }
    animate(); window.__explodeCosmicHome = () => { if (explosionProgress >= 0) return; explosionProgress = 0; camTargetZ = 12; particleMat.size = 0.1; };

    const onResize = () => {
      camera.aspect = window.innerWidth / window.innerHeight
      camera.updateProjectionMatrix()
      renderer.setSize(window.innerWidth, window.innerHeight)
    }
    window.addEventListener('resize', onResize)

    return () => {
      cancelAnimationFrame(animId)
      window.__cancelCanvas2D?.()
      window.removeEventListener('resize', onResize)
      if (container.contains(renderer.domElement)) container.removeChild(renderer.domElement)
      renderer.dispose()
    }
  }, [])

  // Canvas 2D background for skipGate mode
  useEffect(() => {
    if (!skipGate) return
    const canvas = bgCanvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    if (!ctx) return
    canvas.style.display = 'block'
    canvas.style.pointerEvents = 'none'
    canvas.width = window.innerWidth
    canvas.height = window.innerHeight

    const stars: { x: number; y: number; r: number; baseR: number; opacity: number; hue: number; p: number; vx: number; vy: number }[] = []
    for (let i = 0; i < 300; i++) {
      stars.push({
        x: Math.random() * canvas.width, y: Math.random() * canvas.height,
        r: Math.random() * 1.8 + 0.2, baseR: Math.random() * 1.8 + 0.2,
        opacity: Math.random() * 0.5 + 0.15, hue: [235, 248, 265, 280][Math.floor(Math.random() * 4)],
        p: Math.random() * Math.PI * 2, vx: (Math.random() - 0.5) * 0.1, vy: (Math.random() - 0.5) * 0.08 - 0.02,
      })
    }

    const mouse = { x: -1000, y: -1000 }
    const track = (e: MouseEvent) => { mouse.x = e.clientX; mouse.y = e.clientY }
    const leave = () => { mouse.x = -1000; mouse.y = -1000 }
    window.addEventListener('mousemove', track)
    window.addEventListener('mouseleave', leave)

    const resize = () => { canvas.width = window.innerWidth; canvas.height = window.innerHeight }
    window.addEventListener('resize', resize)

    let id = 0
    const draw = () => {
      const w = canvas.width, h = canvas.height
      ctx.clearRect(0, 0, w, h)

      const g1 = ctx.createRadialGradient(w * 0.28, h * 0.32, 0, w * 0.5, h * 0.5, w * 0.65)
      g1.addColorStop(0, 'rgba(35,28,90,0.14)'); g1.addColorStop(0.5, 'rgba(18,14,55,0.08)'); g1.addColorStop(1, 'rgba(0,0,0,0)')
      ctx.fillStyle = g1; ctx.fillRect(0, 0, w, h)
      const g2 = ctx.createRadialGradient(w * 0.72, h * 0.58, 0, w * 0.42, h * 0.42, w * 0.5)
      g2.addColorStop(0, 'rgba(55,35,130,0.06)'); g2.addColorStop(1, 'rgba(0,0,0,0)')
      ctx.fillStyle = g2; ctx.fillRect(0, 0, w, h)

      if (mouse.x > -500) {
        const a = ctx.createRadialGradient(mouse.x, mouse.y, 0, mouse.x, mouse.y, 280)
        a.addColorStop(0, 'rgba(99,102,241,0.04)'); a.addColorStop(1, 'rgba(0,0,0,0)')
        ctx.fillStyle = a; ctx.fillRect(0, 0, w, h)
      }

      for (let i = 0; i < stars.length; i += 3) {
        for (let j = i + 3; j < stars.length; j += 3) {
          const dx = stars[i].x - stars[j].x, dy = stars[i].y - stars[j].y
          const d = Math.sqrt(dx * dx + dy * dy)
          if (d < 110) { ctx.beginPath(); ctx.moveTo(stars[i].x, stars[i].y); ctx.lineTo(stars[j].x, stars[j].y); ctx.strokeStyle = `rgba(120,140,245,${(1 - d / 110) * 0.05})`; ctx.lineWidth = 0.4; ctx.stroke() }
        }
      }

      stars.forEach(s => {
        s.x += s.vx + Math.sin(Date.now() * 0.0004 + s.p) * 0.05
        s.y += s.vy
        if (mouse.x > -500) {
          const dx = mouse.x - s.x, dy = mouse.y - s.y
          const d = Math.sqrt(dx * dx + dy * dy)
          if (d < 180 && d > 1) { const f = (1 - d / 180) * 0.07; s.x += (dx / d) * f; s.y += (dy / d) * f }
        }
        if (s.y < -10) s.y = h + 10; if (s.y > h + 10) s.y = -10; if (s.x < -10) s.x = w + 10; if (s.x > w + 10) s.x = -10
        s.r += (s.baseR - s.r) * 0.03
        const a = s.opacity * (0.5 + 0.5 * Math.sin(Date.now() * 0.003 + s.p))
        ctx.beginPath(); ctx.arc(s.x, s.y, s.r, 0, Math.PI * 2); ctx.fillStyle = `hsla(${s.hue},65%,72%,${a})`; ctx.fill()
        if (s.baseR > 1.0) { ctx.beginPath(); ctx.arc(s.x, s.y, s.r * 2.5, 0, Math.PI * 2); ctx.fillStyle = `hsla(${s.hue},65%,72%,${a * 0.05})`; ctx.fill() }
      })

      id = requestAnimationFrame(draw)
    }
    draw()

    return () => {
      cancelAnimationFrame(id)
      window.removeEventListener('resize', resize)
      window.removeEventListener('mousemove', track)
      window.removeEventListener('mouseleave', leave)
    }
  }, [])

  const navItems = [
    { label: '开始创作', desc: '从一句话想法开始', path: '/new', icon: '✦' },
    { label: '智能生图', desc: '角色 · 场景 · 道具', path: '/image-gen', icon: '◈' },
    { label: '视频生成', desc: '图生视频 · 拼接成片', path: '/video-gen', icon: '◉' },
    { label: '创作历史', desc: '已生成内容', path: '/history', icon: '⬡' },
  ]

  const handleEnter = () => {
    if (phase !== 'gate') return
    setPhase('exploding')
    setBgReady(true)
    window.__explodeCosmicHome?.()
  }

  // Auto-transition from exploding to settled
  const enterTimerRef = useRef<ReturnType<typeof setTimeout>>()
  useEffect(() => {
    if (phase === 'exploding') {
      initSettledCanvasBg()
      enterTimerRef.current = setTimeout(() => {
        setContentVisible(true)
        setPhase('settled')
      }, 1800)
    }
    return () => { if (enterTimerRef.current) clearTimeout(enterTimerRef.current) }
  }, [phase])

  // Enhanced Canvas 2D for non-skipGate mode (triggered on explode)
  const initSettledCanvasBg = () => {
    const canvas = bgCanvasRef.current
    if (!canvas || canvas.dataset.inited) return
    canvas.dataset.inited = '1'
    const ctx = canvas.getContext('2d')
    if (!ctx) return
    canvas.style.display = 'block'
    canvas.width = window.innerWidth
    canvas.height = window.innerHeight

    // Rich star particles
    const bp: { x: number; y: number; r: number; baseR: number; o: number; v: number; ph: number; h: number; vx: number }[] = []
    for (let i = 0; i < 300; i++) {
      bp.push({
        x: Math.random() * window.innerWidth, y: Math.random() * window.innerHeight,
        r: Math.random() * 2.2 + 0.3, baseR: Math.random() * 2.2 + 0.3,
        o: Math.random() * 0.5 + 0.12,
        v: (Math.random() - 0.5) * 0.2, ph: Math.random() * Math.PI * 2,
        h: 210 + Math.random() * 80,
        vx: (Math.random() - 0.5) * 0.12,
      })
    }

    // Mouse interaction
    const mouse = { x: -1000, y: -1000 }
    const track = (e: MouseEvent) => { mouse.x = e.clientX; mouse.y = e.clientY }
    const leave = () => { mouse.x = -1000; mouse.y = -1000 }
    window.addEventListener('mousemove', track)
    window.addEventListener('mouseleave', leave)
    const resize = () => { canvas.width = window.innerWidth; canvas.height = window.innerHeight }
    window.addEventListener('resize', resize)

    // Shooting stars
    let shootingStars: { sx: number; sy: number; angle: number; speed: number; life: number; maxLife: number; len: number }[] = []
    let spawnTimer = 0

    let cid = 0
    let nebulaHueOffset = 0
    const draw = () => {
      const w = window.innerWidth, hh = window.innerHeight
      ctx.clearRect(0, 0, w, hh)
      const t = Date.now()

      // Slowly evolving nebula colors
      nebulaHueOffset += 0.002
      const hue1 = 235 + Math.sin(nebulaHueOffset) * 15
      const hue2 = 265 + Math.sin(nebulaHueOffset * 0.7 + 1) * 20

      const g1 = ctx.createRadialGradient(w * 0.28, hh * 0.32, 0, w * 0.5, hh * 0.5, w * 0.65)
      g1.addColorStop(0, `hsla(${hue1},70%,28%,0.12)`); g1.addColorStop(0.5, `hsla(${hue1},60%,18%,0.06)`); g1.addColorStop(1, 'transparent')
      ctx.fillStyle = g1; ctx.fillRect(0, 0, w, hh)
      const g2 = ctx.createRadialGradient(w * 0.72, hh * 0.58, 0, w * 0.42, hh * 0.42, w * 0.5)
      g2.addColorStop(0, `hsla(${hue2},65%,30%,0.05)`); g2.addColorStop(1, 'transparent')
      ctx.fillStyle = g2; ctx.fillRect(0, 0, w, hh)

      // Mouse-follow glow
      if (mouse.x > -500) {
        const a = ctx.createRadialGradient(mouse.x, mouse.y, 0, mouse.x, mouse.y, 280)
        a.addColorStop(0, 'rgba(99,102,241,0.04)'); a.addColorStop(1, 'transparent')
        ctx.fillStyle = a; ctx.fillRect(0, 0, w, hh)
      }

      // Connecting lines between nearby stars
      for (let i = 0; i < bp.length; i += 4) {
        for (let j = i + 4; j < bp.length; j += 4) {
          const dx = bp[i].x - bp[j].x, dy = bp[i].y - bp[j].y
          const d = Math.sqrt(dx * dx + dy * dy)
          if (d < 120) {
            ctx.beginPath(); ctx.moveTo(bp[i].x, bp[i].y); ctx.lineTo(bp[j].x, bp[j].y)
            ctx.strokeStyle = `rgba(120,140,245,${(1 - d / 120) * 0.04})`; ctx.lineWidth = 0.35; ctx.stroke()
          }
        }
      }

      // Shooting stars
      spawnTimer += 0.016
      if (spawnTimer > 8 + Math.random() * 6) {
        spawnTimer = 0
        const angle = -Math.PI * 0.35 + (Math.random() - 0.5) * 0.3
        shootingStars.push({
          sx: Math.random() * w * 1.2 - w * 0.1,
          sy: Math.random() * hh * 0.3,
          angle, speed: 4 + Math.random() * 4,
          life: 0, maxLife: 0.5 + Math.random() * 0.4,
          len: 30 + Math.random() * 40,
        })
      }
      shootingStars = shootingStars.filter(s => {
        s.life += 0.016
        if (s.life >= s.maxLife) return false
        const p = s.life / s.maxLife
        s.sx += Math.cos(s.angle) * s.speed
        s.sy += Math.sin(s.angle) * s.speed
        const alpha = (1 - p) * 0.7
        ctx.beginPath()
        ctx.moveTo(s.sx, s.sy)
        ctx.lineTo(s.sx - Math.cos(s.angle) * s.len * (1 - p * 0.5), s.sy - Math.sin(s.angle) * s.len * (1 - p * 0.5))
        ctx.strokeStyle = `rgba(200,210,255,${alpha})`
        ctx.lineWidth = 1.2 * (1 - p)
        ctx.stroke()
        // Bright head
        ctx.beginPath(); ctx.arc(s.sx, s.sy, 1.5 * (1 - p * 0.3), 0, Math.PI * 2)
        ctx.fillStyle = `rgba(220,230,255,${alpha * 1.2})`
        ctx.fill()
        return true
      })

      // Update and draw particles
      bp.forEach(p => {
        p.y += p.v
        p.x += Math.sin(t * 0.001 + p.ph) * 0.15 + p.vx * 0.3
        if (mouse.x > -500) {
          const dx = mouse.x - p.x, dy = mouse.y - p.y
          const d = Math.sqrt(dx * dx + dy * dy)
          if (d < 180 && d > 1) {
            const f = (1 - d / 180) * 0.05
            p.x += (dx / d) * f; p.y += (dy / d) * f
          }
        }
        if (p.y < -10) p.y = hh + 10; if (p.y > hh + 10) p.y = -10
        if (p.x < -10) p.x = w + 10; if (p.x > w + 10) p.x = -10
        p.r += (p.baseR - p.r) * 0.02
        const a = p.o * (0.5 + 0.5 * Math.sin(t * 0.002 + p.ph))
        ctx.beginPath()
        ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2)
        ctx.fillStyle = `hsla(${p.h},65%,78%,${a})`
        ctx.fill()
        if (p.baseR > 1.5) {
          ctx.beginPath(); ctx.arc(p.x, p.y, p.r * 2, 0, Math.PI * 2)
          ctx.fillStyle = `hsla(${p.h},65%,78%,${a * 0.04})`; ctx.fill()
        }
      })
      cid = requestAnimationFrame(draw)
    }
    draw()
    window.__cancelCanvas2D = () => { cancelAnimationFrame(cid); window.removeEventListener('resize', resize); window.removeEventListener('mousemove', track); window.removeEventListener('mouseleave', leave) }
  }

  return (
    <div className="fixed inset-0" style={{ background: '#000', overflow: 'hidden' }}>
      {/* Three.js canvas */}
      <div ref={threeRef} className="absolute inset-0" style={{ zIndex: 1, display: skipGate ? 'none' : 'block' }} />

      {/* Canvas 2D background */}
      <canvas ref={bgCanvasRef} className="absolute inset-0" style={{ zIndex: 2, display: 'none' }} />

      {/* Gate UI */}
      {phase === 'gate' && (
        <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none select-none" style={{ zIndex: 10 }}>
          <h1 className="text-[clamp(48px,12vw,120px)] font-black tracking-[-0.06em] leading-none"
            style={{
              background: 'linear-gradient(135deg,#fff 20%,rgba(180,200,255,0.85) 50%,rgba(167,139,250,0.5) 80%)',
              WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent',
              backgroundClip: 'text',
              filter: 'drop-shadow(0 0 80px rgba(129,140,248,0.15))',
            }}>
            织境
          </h1>
          <p className="mt-6 text-[clamp(11px,1.5vw,14px)] tracking-[0.25em] uppercase" style={{ color: 'rgba(255,255,255,0.30)' }}>AI Story Studio</p>
        </div>
      )}

      {/* Gate button */}
      {phase === 'gate' && (
        <button onClick={handleEnter}
          className="absolute bottom-12 left-1/2 -translate-x-1/2 px-10 py-3 rounded-xl border border-white/10 text-white/55 hover:text-white/80 hover:border-white/25 transition-all duration-500"
          style={{ zIndex: 20, background: 'transparent', fontSize: '13px', fontFamily: 'inherit', cursor: 'pointer', letterSpacing: '0.05em' }}>
          进入
        </button>
      )}

      {/* Settled content */}
      {phase === 'settled' && (
        <div className={`absolute inset-0 overflow-y-auto transition-opacity duration-700 ${contentVisible ? 'opacity-100' : 'opacity-0'}`} style={{ zIndex: 10 }}>
          <header className="sticky top-0 flex items-center justify-between px-6 py-4 border-b border-white/[0.04]" style={{ background: 'rgba(0,0,0,0.6)', backdropFilter: 'blur(20px)' }}>
            <div className="flex items-center gap-8">
              <span className="text-lg font-bold tracking-tight" style={{ background: 'linear-gradient(135deg,rgba(255,255,255,0.9),rgba(180,200,255,0.7))', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent', backgroundClip: 'text' }}>织境</span>
              <nav className="flex items-center gap-1">
                {[{ path: '/new', label: '新建' }, { path: '/image-gen', label: '生图' }, { path: '/video-gen', label: '视频' }, { path: '/history', label: '历史' }].map(item => (
                  <button key={item.path} onClick={() => navigate(item.path)} className="px-3 py-1.5 rounded-lg text-[12px] text-white/40 hover:text-white/60 hover:bg-white/[0.02] transition-all">{item.label}</button>
                ))}
              </nav>
            </div>
            <button onClick={() => navigate('/settings')} className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg border border-white/[0.08] text-xs text-white/55 hover:text-white/80 hover:border-white/[0.15] transition-all">
              ⚙ 设置
            </button>
          </header>

          <div className="px-6 py-16 max-w-4xl mx-auto">
            {/* Hero */}
            <div className={`h-hero-wrap ${showStagger ? 'stagger-in' : ''}`} style={{ transitionDelay: '0ms' }}>
              <h2 className="text-[clamp(36px,7vw,64px)] font-black tracking-[-0.04em] leading-none mb-4"
                style={{ background: 'linear-gradient(180deg, rgba(255,255,255,0.95) 0%, rgba(255,255,255,0.55) 100%)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent', backgroundClip: 'text' }}>
                从灵感到银幕
              </h2>
              <p className="text-sm text-white/40 tracking-wider">AI-Powered Story Creation</p>
            </div>

            {/* Energy bar */}
            <div className="energy-bar" />

            {/* Cards */}
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-24">
              {navItems.map((item, idx) => (
                <TiltPanel key={item.label} onClick={() => navigate(item.path)}
                  className={`h-card tilt-card group p-6 rounded-2xl border border-white/[0.08] cursor-pointer ${showStagger ? 'stagger-in' : ''}`}
                  style={{
                    background: 'rgba(255,255,255,0.10)',
                    backdropFilter: 'blur(24px)',
                    transitionDelay: showStagger ? `${120 + idx * 80}ms` : '0ms',
                  }}>
                  {/* Stars */}
                  <div className="stars">
                    <div className="sd" /><div className="sd" /><div className="sd" /><div className="sd" />
                    <div className="sd" /><div className="sd" /><div className="sd" /><div className="sd" />
                  </div>
                  {/* Starburst */}
                  <div className="star-burst" />
                  {/* Sweep */}
                  <div className="sweep" />
                  {/* Bottom glow */}
                  <div className="bottom-glow" />
                  {/* Conic border */}
                  <div className="c-border" />
                  {/* Content */}
                  <div className="relative z-[1]">
                    <div className="icon-glow w-9 h-9 rounded-xl flex items-center justify-center text-[15px] mb-4"
                      style={{
                        background: 'rgba(255,255,255,0.10)',
                        color: 'rgba(255,255,255,0.75)',
                        border: '1px solid rgba(255,255,255,0.06)',
                        transition: 'all 0.3s',
                        position: 'relative',
                        overflow: 'hidden',
                      }}>
                      <span className="relative z-[1]">{item.icon}</span>
                    </div>
                    <div className="text-[14px] font-semibold text-white/80 mb-1.5 transition-colors group-hover:text-white">{item.label}</div>
                    <div className="text-[11px] leading-relaxed text-white/55">{item.desc}</div>
                  </div>
                </TiltPanel>
              ))}
            </div>

            {/* Project list */}
            <div className="relative">
              <div className="project-ambient-glow" />
              <div className="project-list-header flex items-end justify-between mb-8">
                <div>
                  <div className="text-[10px] text-white/40 tracking-[0.15em] uppercase mb-2">Projects</div>
                  <h3 className="text-lg font-semibold text-white/80">项目列表 <span className="text-xs text-white/40 ml-1.5">{filteredProjects.length}/{projects.length}</span></h3>
                </div>
                <div className="flex items-center gap-3">
                  <button onClick={() => navigate('/projects')}
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border text-[10px] transition-all"
                    style={{ borderColor: 'rgba(255,255,255,0.15)', color: 'rgba(255,255,255,0.55)' }}
                    onMouseOver={e => { e.currentTarget.style.borderColor = 'rgba(255,255,255,0.25)'; e.currentTarget.style.background = 'rgba(255,255,255,0.05)'; e.currentTarget.style.color = 'rgba(255,255,255,0.80)' }}
                    onMouseOut={e => { e.currentTarget.style.borderColor = 'rgba(255,255,255,0.15)'; e.currentTarget.style.background = 'transparent'; e.currentTarget.style.color = 'rgba(255,255,255,0.55)' }}>
                    <span>查看所有</span>
                    <span style={{ color: 'rgba(255,255,255,0.45)' }}>{filteredProjects.length}</span>
                  </button>
                  <div className="relative w-40">
                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-3 h-3" style={{ color: 'rgba(255,255,255,0.40)' }} />
                    <input value={searchText} onChange={e => setSearchText(e.target.value)} placeholder="搜索..."
                      style={{ borderBottom: '1px solid rgba(255,255,255,0.12)', color: 'rgba(255,255,255,0.75)' }}
                      className="w-full bg-transparent pb-2 pt-1 pl-8 pr-2 text-xs placeholder:text-white/15 focus:outline-none transition-all"
                      onFocus={e => e.currentTarget.style.borderBottomColor = 'rgba(255,255,255,0.30)'}
                      onBlur={e => e.currentTarget.style.borderBottomColor = 'rgba(255,255,255,0.12)'} />
                  </div>
                  <button onClick={() => navigate('/new')}
                    className="flex items-center gap-1.5 px-4 py-2 rounded-xl border text-[11px] transition-all"
                    style={{ borderColor: 'rgba(255,255,255,0.15)', color: 'rgba(255,255,255,0.55)' }}
                    onMouseOver={e => { e.currentTarget.style.borderColor = 'rgba(255,255,255,0.25)'; e.currentTarget.style.background = 'rgba(255,255,255,0.05)'; e.currentTarget.style.color = 'rgba(255,255,255,0.80)' }}
                    onMouseOut={e => { e.currentTarget.style.borderColor = 'rgba(255,255,255,0.15)'; e.currentTarget.style.background = 'transparent'; e.currentTarget.style.color = 'rgba(255,255,255,0.55)' }}>
                    <Plus className="w-3 h-3" /> 新建
                  </button>
                </div>
              </div>

              {loading ? (
                <div className="space-y-2">{[1, 2, 3, 4].map(i => <div key={i} className="rounded-2xl p-5 glass-surface" style={{ border: '1px solid rgba(255,255,255,0.10)' }}><div className="skeleton h-4 w-48" /></div>)}</div>
              ) : filteredProjects.length === 0 ? (
                <div className="py-24 text-center">
                  <p className="text-white/40 text-sm mb-2">还没有项目</p>
                  <p className="text-white/15 text-xs mb-8">输入一个故事想法，开始你的第一次创作</p>
                  <button onClick={() => navigate('/new')} className="inline-flex items-center gap-2 px-6 py-3 rounded-2xl bg-white text-black text-sm font-semibold hover:bg-white/90 transition-all">
                    <Sparkles className="w-4 h-4" /> 开始创作
                  </button>
                </div>
              ) : (
                <>
                <div className="space-y-2">
                  {filteredProjects.slice(0, 5).map((p, idx) => {
                    const names = getPhaseNames(p.style_type)
                    const done = (p.phases || []).slice(0, names.length).filter((ph: any) => ph.done).length
                    const total = names.length
                    const pct = total > 0 ? (done / total) * 100 : 0
                    return (
                      <TiltPanel key={p.name} onClick={() => { if (renaming !== p.name) navigate(`/project/${encodeURIComponent(p.name)}`) }}
                        className={`tilt-card project-item group relative flex items-center gap-4 px-5 py-4 rounded-2xl glass-surface-visible cursor-pointer ${showStagger ? 'stagger-in' : ''}`}
                        style={{ zIndex: 1, transitionDelay: showStagger ? `${520 + idx * 70}ms` : '0ms', border: '1px solid rgba(255,255,255,0.12)' }}>
                        <div className="p-bottom-glow" />
                        <div className="p-border" />
                        <div className="p-sweep" />
                        <div className="relative z-[1] flex items-center gap-4 w-full">
                          <span className="relative inline-flex items-center justify-center w-[20px] h-[20px] flex-shrink-0">
                            <span className={`absolute inset-0 rotate-45 blur-[3px] transition-all duration-700 ${p.running || p.pending_approval ? 'opacity-100' : 'opacity-60'}`}
                              style={{
                                background: p.running ? 'rgba(34,211,238,0.25)' :
                                  done >= total ? 'rgba(167,139,250,0.18)' :
                                    p.pending_approval ? 'rgba(244,114,182,0.22)' :
                                      done > 0 ? 'rgba(129,140,248,0.3)' : 'rgba(255,255,255,0.10)',
                                animation: p.running || p.pending_approval ? 'status-glow 2s ease-in-out infinite' : 'none',
                              }} />
                            <span className={`absolute w-[10px] h-[10px] rotate-45 transition-all duration-300`}
                              style={{
                                background: p.running ? 'rgba(34,211,238,0.85)' :
                                  done >= total ? 'rgba(167,139,250,0.85)' :
                                    p.pending_approval ? 'rgba(244,114,182,0.85)' :
                                      done > 0 ? 'rgba(129,140,248,0.85)' : 'rgba(255,255,255,0.2)',
                                boxShadow: p.running ? '0 0 12px rgba(34,211,238,0.35)' :
                                  done >= total ? '0 0 8px rgba(167,139,250,0.2)' :
                                    p.pending_approval ? '0 0 12px rgba(244,114,182,0.35)' :
                                      done > 0 ? '0 0 8px rgba(129,140,248,0.3)' : 'none',
                                animation: p.running ? 'status-core 1.5s ease-in-out infinite' :
                                  p.pending_approval ? 'status-core 1.8s ease-in-out infinite' : 'none',
                              }} />
                          </span>
                          <div className="flex-1 min-w-0">
                            {renaming === p.name ? (
                              <div className="flex items-center gap-1" onClick={e => e.stopPropagation()}>
                                <input className="bg-white/[0.04] border border-white/[0.08] rounded-lg px-2 py-1 text-sm font-medium text-white/85 focus:outline-none focus:border-white/20 w-56"
                                  value={renameInput} onChange={e => setRenameInput(e.target.value)} autoFocus
                                  onKeyDown={e => { if (e.key === 'Enter') handleRename(p.name); if (e.key === 'Escape') setRenaming(null) }} />
                                <button onClick={() => handleRename(p.name)} className="p-1 rounded hover:bg-green-500/10 text-green-400"><Check className="w-3 h-3" /></button>
                                <button onClick={() => setRenaming(null)} className="p-1 rounded hover:bg-white/[0.04] text-white/40"><X className="w-3 h-3" /></button>
                              </div>
                            ) : (
                              <h3 className="text-sm font-medium text-white/85 group-hover:text-white/90 transition-colors truncate">{p.name}</h3>
                            )}
                            <div className="flex items-center gap-3 mt-0.5">
                              <span className="text-[10px]" style={{ color: 'rgba(255,255,255,0.50)' }}>{p.genre || '未分类'}</span>
                              <span className="text-[10px]" style={{ color: 'rgba(255,255,255,0.40)' }}>{p.updated_at?.slice(0, 10)}</span>
                              <span className="text-[10px]" style={{ color: 'rgba(255,255,255,0.40)' }}>{done}/{total}</span>
                            </div>
                          </div>
                          <div className="w-24 h-[3px] bg-white/[0.04] rounded-full overflow-hidden flex-shrink-0 hidden sm:block star-progress-track p-progress-glow">
                            <div className={`star-progress-fill ${pct === 100 ? 'complete' : ''}`} style={{ width: `${pct}%` }}>
                              <div className="sp-stars" />
                              <div className="sp-edge" />
                            </div>
                          </div>
                          <span className={`p-status-badge text-[10px] px-2 py-0.5 rounded-full flex-shrink-0 hidden sm:inline-block ${p.running ? 'text-cyan-400/50 bg-cyan-500/[0.06]' : done >= total ? 'text-purple-400/50 bg-purple-500/[0.06]' : p.pending_approval ? 'text-pink-400/50 bg-pink-500/[0.06]' : done > 0 ? 'text-indigo-400/50 bg-indigo-500/[0.06]' : 'text-white/30 bg-white/[0.03]'}`}
                            style={p.running ? { '--badge-color': '34,211,238' } as React.CSSProperties : done >= total ? { '--badge-color': '167,139,250' } as React.CSSProperties : p.pending_approval ? { '--badge-color': '244,114,182' } as React.CSSProperties : done > 0 ? { '--badge-color': '129,140,248' } as React.CSSProperties : undefined}>
                            {p.running ? '生成中' : done >= total ? '已完成' : p.pending_approval ? '待审核' : done > 0 ? '创作中' : '新建'}
                          </span>
                          <div className="flex items-center gap-0.5 opacity-0 group-hover:opacity-100 transition-all flex-shrink-0 relative z-[1]">
                            <button onClick={e => { e.stopPropagation(); setRenaming(p.name); setRenameInput(p.name) }} className="p-action-btn p-1.5 rounded-lg hover:bg-white/[0.04] text-white/30" title="重命名"><Pencil className="w-3 h-3" /></button>
                            <button onClick={e => { e.stopPropagation(); openProjectFolder(p.name) }} className="p-action-btn p-1.5 rounded-lg hover:bg-white/[0.04] text-white/30" title="打开文件夹"><FolderOpen className="w-3 h-3" /></button>
                            <button onClick={e => { e.stopPropagation(); setDeleteTarget(p.name) }} className="p-action-btn p-1.5 rounded-lg hover:bg-red-500/[0.08] text-white/30 hover:text-red-400/60" title="删除"><Trash2 className="w-3 h-3" /></button>
                          </div>
                        </div>
                      </TiltPanel>
                    )
                  })}
                </div>
                </>
              )}
            </div>
            <div className="h-36" />
          </div>
        </div>
      )}

      {deleteTarget && (
        <ConfirmModal title="删除项目" message={`确定删除「${deleteTarget}」及其所有文件？`}
          onConfirm={async () => { await deleteProject(deleteTarget); setDeleteTarget(null); toast('已删除', 'success'); load() }}
          onCancel={() => setDeleteTarget(null)} />
      )}
    </div>
  )
}

// Global expose for Three.js explode trigger from React
declare global {
  interface Window {
    __explodeCosmicHome?: () => void
    __cancelCanvas2D?: () => void
  }
}