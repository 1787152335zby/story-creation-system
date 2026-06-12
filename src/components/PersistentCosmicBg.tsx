import { useEffect, useRef } from 'react'
import { useLocation } from 'react-router-dom'
import * as THREE from 'three'
import { getCircleTexture } from '../lib/three-utils'

const PARTICLE_COUNT = 200
const STAR_COUNT = 500
const DRIFT_COUNT = 400
const EXPLOSION_DURATION = 2.5

let sceneInstance: any = null
let animId = 0

export default function PersistentCosmicBg() {
  const containerRef = useRef<HTMLDivElement>(null)
  const location = useLocation()
  const isProjectsPage = location.pathname === '/projects'

  useEffect(() => {
    if (sceneInstance) return
    if (isProjectsPage) return
    const container = containerRef.current
    if (!container) return

    const scene = new THREE.Scene()
    const camera = new THREE.PerspectiveCamera(60, window.innerWidth / window.innerHeight, 0.1, 1000)
    camera.position.z = 6

    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true })
    renderer.setSize(window.innerWidth, window.innerHeight)
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 1.5))
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
    const clock = new THREE.Clock()
    const posArr = particleGeo.attributes.position.array as Float32Array
    const dpArr = driftGeo.attributes.position.array as Float32Array

    const animate = () => {
      if (document.hidden || !(window as any).__cosmicBgActive) { animId = requestAnimationFrame(animate); return }
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

        const ringHue = 0.65 + 0.04 * Math.sin(t * 0.2)
        const ringSat = 0.2 + 0.1 * Math.sin(t * 0.35)
        ring.material.color.setHSL(ringHue, ringSat, 0.15)
        ring.rotation.z += 0.0003 + 0.0002 * Math.sin(t * 0.15)

        scene.children.forEach(child => {
          if ((child as THREE.Mesh).isMesh && child !== ring && child !== glow && child !== glowOuter && child !== gridHelper) {
            child.rotation.x += 0.0001 * Math.sin(t * 0.1 + (child.id % 3))
            child.rotation.y += 0.00015 * Math.sin(t * 0.08 + (child.id % 5))
          }
        })

        starMat.size = 0.05 + 0.02 * Math.sin(t * 0.4)
        driftMat.size = 0.1 + 0.03 * Math.sin(t * 0.5 + 1)
        driftMat.opacity = 0.85 + 0.05 * Math.sin(t * 0.2 + 2)

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
    animate()

    sceneInstance = { scene, renderer, container }
    ;(window as any).__explodeCosmicHome = () => {
      if (explosionProgress >= 0) return
      explosionProgress = 0; camTargetZ = 12; particleMat.size = 0.1
    }

    const onResize = () => {
      camera.aspect = window.innerWidth / window.innerHeight
      camera.updateProjectionMatrix()
      renderer.setSize(window.innerWidth, window.innerHeight)
    }
    window.addEventListener('resize', onResize)

    return () => {
      cancelAnimationFrame(animId)
      window.removeEventListener('resize', onResize)
      scene.traverse((obj) => {
        if ((obj as any).geometry) (obj as any).geometry.dispose()
        if ((obj as any).material) {
          const mat = (obj as any).material
          if (Array.isArray(mat)) mat.forEach((m: any) => m.dispose())
          else mat.dispose()
        }
      })
      renderer.forceContextLoss()
      renderer.dispose()
      if (container.contains(renderer.domElement)) container.removeChild(renderer.domElement)
      sceneInstance = null
      delete (window as any).__explodeCosmicHome
    }
  }, [])

  return (
    <div ref={containerRef} className="fixed inset-0" style={{ zIndex: 1, pointerEvents: 'none', display: isProjectsPage ? 'none' : 'block' }} />
  )
}
