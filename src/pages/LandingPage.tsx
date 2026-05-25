import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import * as THREE from 'three'

const PARTICLE_COUNT = 400
const EXPLOSION_DURATION = 2.5

export default function LandingPage() {
  const mountRef = useRef<HTMLDivElement>(null)
  const navigate = useNavigate()
  const [entering, setEntering] = useState(false)
  const [visible, setVisible] = useState(true)
  const explodeRef = useRef<() => void>(() => {})

  useEffect(() => {
    const container = mountRef.current
    if (!container) return

    const scene = new THREE.Scene()
    const camera = new THREE.PerspectiveCamera(60, window.innerWidth / window.innerHeight, 0.1, 1000)
    camera.position.z = 6

    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true })
    renderer.setSize(window.innerWidth, window.innerHeight)
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
    renderer.setClearColor(0x000000, 1)
    container.appendChild(renderer.domElement)

    // Grid floor
    const gridHelper = new THREE.PolarGridHelper(8, 32, 20, 64, 0x111111, 0x111111)
    gridHelper.position.z = -3
    scene.add(gridHelper)

    // Subtle ring
    const ringGeo = new THREE.TorusGeometry(3, 0.002, 16, 120)
    const ringMat = new THREE.MeshBasicMaterial({ color: 0x222233 })
    const ring = new THREE.Mesh(ringGeo, ringMat)
    ring.rotation.x = Math.PI * 0.45
    ring.position.z = -0.5
    scene.add(ring)

    // Particles
    const particleGeo = new THREE.BufferGeometry()
    const positions = new Float32Array(PARTICLE_COUNT * 3)
    const basePositions = new Float32Array(PARTICLE_COUNT * 3)
    const velocities = new Float32Array(PARTICLE_COUNT * 3)
    const colors = new Float32Array(PARTICLE_COUNT * 3)
    const sizes = new Float32Array(PARTICLE_COUNT)

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
      // Pre-compute explosion velocity: outward from center + random jitter
      const len = Math.sqrt(x * x + y * y + z * z) || 1
      const speed = 1.5 + Math.random() * 4
      velocities[i3] = (x / len) * speed + (Math.random() - 0.5) * 2
      velocities[i3 + 1] = (y / len) * speed + (Math.random() - 0.5) * 2
      velocities[i3 + 2] = (z / len) * speed + (Math.random() - 0.5) * 2
      const c = new THREE.Color().setHSL(0.65 + Math.random() * 0.1, 0.5, 0.5 + Math.random() * 0.3)
      colors[i3] = c.r; colors[i3 + 1] = c.g; colors[i3 + 2] = c.b
      sizes[i] = Math.random() * 3 + 0.5
    }
    particleGeo.setAttribute('position', new THREE.BufferAttribute(positions, 3))
    particleGeo.setAttribute('color', new THREE.BufferAttribute(colors, 3))
    particleGeo.setAttribute('size', new THREE.BufferAttribute(sizes, 1))

    const particleMat = new THREE.PointsMaterial({
      size: 0.03,
      vertexColors: true,
      blending: THREE.AdditiveBlending,
      depthWrite: false,
      transparent: true,
      opacity: 0.8,
    })
    const particleSystem = new THREE.Points(particleGeo, particleMat)
    scene.add(particleSystem)

    // Glow ball in center
    const glowGeo = new THREE.SphereGeometry(0.15, 32, 32)
    const glowMat = new THREE.MeshBasicMaterial({ color: 0x334466 })
    const glow = new THREE.Mesh(glowGeo, glowMat)
    scene.add(glow)

    const glowOuterGeo = new THREE.SphereGeometry(0.35, 32, 32)
    const glowOuterMat = new THREE.MeshBasicMaterial({ color: 0x111133, transparent: true, opacity: 0.4 })
    const glowOuter = new THREE.Mesh(glowOuterGeo, glowOuterMat)
    scene.add(glowOuter)

    // Thin orbit rings
    for (let i = 0; i < 3; i++) {
      const r = 1.2 + i * 0.9
      const orbitGeo = new THREE.TorusGeometry(r, 0.001, 8, 80)
      const orbitMat = new THREE.MeshBasicMaterial({ color: 0x111122 })
      const orbit = new THREE.Mesh(orbitGeo, orbitMat)
      orbit.rotation.x = Math.random() * Math.PI
      orbit.rotation.y = Math.random() * Math.PI
      scene.add(orbit)
    }

    let explosionProgress = -1
    let animId = 0
    const clock = new THREE.Clock()

    explodeRef.current = () => {
      explosionProgress = 0
      // Flash white overlay
      const flash = document.createElement('div')
      flash.className = 'fixed inset-0 bg-white pointer-events-none'
      flash.style.zIndex = '102'
      flash.style.opacity = '0.6'
      flash.style.transition = 'opacity 0.8s ease-out'
      container.appendChild(flash)
      requestAnimationFrame(() => { flash.style.opacity = '0' })
      setTimeout(() => flash.remove(), 900)
    }

    const animate = () => {
      const t = clock.getElapsedTime()

      if (explosionProgress < 0) {
        particleSystem.rotation.y += 0.001
        particleSystem.rotation.x += 0.0003
        ring.rotation.z += 0.0005
        glowOuter.scale.setScalar(1 + Math.sin(t * 2) * 0.2)
      } else {
        explosionProgress += 0.016 / EXPLOSION_DURATION
        if (explosionProgress >= 1) {
          cancelAnimationFrame(animId)
          setVisible(false)
          navigate('/home')
          return
        }
        // Move particles outward by velocity each frame
        const posArr = particleGeo.attributes.position.array as Float32Array
        for (let i = 0; i < PARTICLE_COUNT; i++) {
          const i3 = i * 3
          posArr[i3] += velocities[i3] * 0.016
          posArr[i3 + 1] += velocities[i3 + 1] * 0.016
          posArr[i3 + 2] += velocities[i3 + 2] * 0.016
        }
        particleGeo.attributes.position.needsUpdate = true
        // Keep fully visible for most of the explosion
        particleMat.opacity = explosionProgress < 0.7 ? 0.9 : 0.9 * (1 - (explosionProgress - 0.7) / 0.3)
        // Fade canvas only at the very end
        renderer.domElement.style.opacity = explosionProgress < 0.8 ? '1' : String(Math.max(0, 1 - (explosionProgress - 0.8) / 0.2))
      }

      renderer.render(scene, camera)
      animId = requestAnimationFrame(animate)
    }

    animate()

    const onResize = () => {
      camera.aspect = window.innerWidth / window.innerHeight
      camera.updateProjectionMatrix()
      renderer.setSize(window.innerWidth, window.innerHeight)
    }
    window.addEventListener('resize', onResize)

    return () => {
      cancelAnimationFrame(animId)
      window.removeEventListener('resize', onResize)
      renderer.dispose()
      container.removeChild(renderer.domElement)
    }
  }, [navigate])

  if (!visible) return null

  return (
    <div ref={mountRef} className="fixed inset-0" style={{ zIndex: 100, background: '#000' }}>
      <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none select-none" style={{ zIndex: 101 }}>
        <h1
          className="text-[clamp(48px,12vw,120px)] font-black tracking-[-0.06em] leading-none"
          style={{
            color: 'rgba(255,255,255,0.92)',
            textShadow: '0 0 120px rgba(150,170,255,0.2), 0 0 40px rgba(120,140,255,0.1)',
          }}
        >
          织境
        </h1>
        <p
          className="mt-6 text-[clamp(11px,1.5vw,14px)] tracking-[0.25em] uppercase"
          style={{ color: 'rgba(255,255,255,0.15)' }}
        >
          AI Story Studio
        </p>
      </div>
      <button
        onClick={() => { setEntering(true); explodeRef.current() }}
        disabled={entering}
        className={`absolute bottom-12 left-1/2 -translate-x-1/2 px-8 py-3 rounded-xl border text-sm font-medium transition-all duration-500 z-[102]
          ${entering ? 'opacity-0 pointer-events-none' : 'opacity-100'}
          border-white/10 text-white/30 hover:border-white/25 hover:text-white/60`}
        style={{ background: 'transparent' }}
      >
        {entering ? '...' : '进入'}
      </button>
    </div>
  )
}
