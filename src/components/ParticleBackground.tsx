import { useEffect, useRef } from 'react'

interface Star {
  x: number; y: number; r: number; baseR: number
  opacity: number; hue: number
  pulse: number; baseVx: number; baseVy: number
}

interface Line {
  x1: number; y1: number; x2: number; y2: number
  opacity: number; speed: number; width: number
}

export default function ParticleBackground() {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const mouseRef = useRef({ x: -1000, y: -1000 })
  const starsRef = useRef<Star[]>([])
  const linesRef = useRef<Line[]>([])
  const animRef = useRef(0)

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    if (!ctx) return

    const resize = () => {
      const dpr = Math.min(window.devicePixelRatio || 1, 2)
      canvas.width = window.innerWidth * dpr
      canvas.height = window.innerHeight * dpr
      canvas.style.width = window.innerWidth + 'px'
      canvas.style.height = window.innerHeight + 'px'
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
    }
    resize()
    window.addEventListener('resize', resize)

    const trackMouse = (e: MouseEvent) => {
      mouseRef.current = { x: e.clientX, y: e.clientY }
    }
    const lostMouse = () => {
      mouseRef.current = { x: -1000, y: -1000 }
    }
    window.addEventListener('mousemove', trackMouse)
    window.addEventListener('mouseleave', lostMouse)

    const stars: Star[] = []
    const lines: Line[] = []
    const w = canvas.width, h = canvas.height

    for (let i = 0; i < 160; i++) {
      const vx = (Math.random() - 0.5) * 0.25
      const vy = (Math.random() - 0.5) * 0.12 - 0.18
      const r = Math.random() * 2.2 + 0.3
      stars.push({
        x: Math.random() * w, y: Math.random() * h,
        r, baseR: r,
        opacity: Math.random() * 0.6 + 0.2,
        hue: [235, 248, 265, 280][Math.floor(Math.random() * 4)],
        pulse: Math.random() * Math.PI * 2,
        baseVx: vx, baseVy: vy,
      })
    }

    for (let i = 0; i < 22; i++) {
      lines.push({
        x1: Math.random() * w, y1: Math.random() * h,
        x2: Math.random() * w, y2: Math.random() * h,
        opacity: Math.random() * 0.12 + 0.02,
        speed: Math.random() * 0.25 + 0.08,
        width: Math.random() * 1 + 0.3,
      })
    }

    starsRef.current = stars
    linesRef.current = lines

    const draw = () => {
      const cw = canvas.width, ch = canvas.height
      ctx.clearRect(0, 0, cw, ch)

      const mx = mouseRef.current.x
      const my = mouseRef.current.y
      const mouseActive = mx > -500

      const g1 = ctx.createRadialGradient(cw * 0.28, ch * 0.32, 0, cw * 0.5, ch * 0.5, cw * 0.65)
      g1.addColorStop(0, 'rgba(35, 28, 90, 0.22)')
      g1.addColorStop(0.5, 'rgba(18, 14, 55, 0.14)')
      g1.addColorStop(1, 'rgba(6, 6, 14, 0)')
      ctx.fillStyle = g1
      ctx.fillRect(0, 0, cw, ch)

      const g2 = ctx.createRadialGradient(cw * 0.72, ch * 0.58, 0, cw * 0.42, ch * 0.42, cw * 0.5)
      g2.addColorStop(0, 'rgba(55, 35, 130, 0.1)')
      g2.addColorStop(1, 'rgba(6, 6, 14, 0)')
      ctx.fillStyle = g2
      ctx.fillRect(0, 0, cw, ch)

      // Mouse aura - subtle radial glow
      if (mouseActive) {
        const aura = ctx.createRadialGradient(mx, my, 0, mx, my, 300)
        aura.addColorStop(0, 'rgba(99, 102, 241, 0.06)')
        aura.addColorStop(0.4, 'rgba(99, 102, 241, 0.02)')
        aura.addColorStop(1, 'rgba(6, 6, 14, 0)')
        ctx.fillStyle = aura
        ctx.fillRect(0, 0, cw, ch)
      }

      linesRef.current.forEach(l => {
        l.y1 += l.speed * 0.4
        l.y2 += l.speed * 0.4
        if (l.y1 > ch + 50) { l.y1 = -50; l.y2 = l.y1 + (Math.random() * 180 - 90) }
        if (l.y2 > ch + 50) { l.y2 = -50; l.y1 = l.y2 + (Math.random() * 180 - 90) }
        ctx.beginPath()
        ctx.moveTo(l.x1, l.y1)
        ctx.lineTo(l.x2, l.y2)
        const la = l.opacity + Math.sin(Date.now() * 0.0012) * 0.04
        ctx.strokeStyle = `rgba(120, 140, 245, ${Math.max(0, la)})`
        ctx.lineWidth = l.width
        ctx.stroke()
      })

      starsRef.current.forEach(s => {
        // Base drift
        s.x += s.baseVx + Math.sin(Date.now() * 0.0006 + s.pulse) * 0.08
        s.y += s.baseVy

        // Mouse attraction - gentle pull, stronger when closer
        if (mouseActive) {
          const dx = mx - s.x
          const dy = my - s.y
          const dist = Math.sqrt(dx * dx + dy * dy)
          const maxDist = 250
          if (dist < maxDist && dist > 1) {
            const force = (1 - dist / maxDist) * 0.15
            s.x += (dx / dist) * force
            s.y += (dy / dist) * force
            // Grow slightly near mouse
            s.r = s.baseR * (1 + (1 - dist / maxDist) * 0.6)
          } else {
            s.r += (s.baseR - s.r) * 0.05
          }
        } else {
          s.r += (s.baseR - s.r) * 0.05
        }

        if (s.y < -10) s.y = ch + 10
        if (s.x < -10) s.x = cw + 10
        if (s.x > cw + 10) s.x = -10

        const a = s.opacity * (0.65 + 0.35 * Math.sin(Date.now() * 0.0025 + s.pulse))
        ctx.beginPath()
        ctx.arc(s.x, s.y, s.r, 0, Math.PI * 2)
        ctx.fillStyle = `hsla(${s.hue}, 65%, 72%, ${a})`
        ctx.fill()
        if (s.baseR > 1.3 || s.r > 1.8) {
          const glowR = s.r * 2.8
          ctx.beginPath()
          ctx.arc(s.x, s.y, glowR, 0, Math.PI * 2)
          ctx.fillStyle = `hsla(${s.hue}, 65%, 72%, ${a * 0.08})`
          ctx.fill()
        }
      })

      animRef.current = requestAnimationFrame(draw)
    }

    draw()

    return () => {
      cancelAnimationFrame(animRef.current)
      window.removeEventListener('resize', resize)
      window.removeEventListener('mousemove', trackMouse)
      window.removeEventListener('mouseleave', lostMouse)
    }
  }, [])

  return (
    <canvas
      ref={canvasRef}
      className="fixed inset-0"
      style={{ zIndex: 0, background: '#060610' }}
    />
  )
}
