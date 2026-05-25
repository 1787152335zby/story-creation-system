import { useState, useEffect } from 'react'

export type SceneTheme = 'space' | 'ocean' | 'city' | 'mt' | 'plain'

interface SceneBackgroundProps {
  scene?: SceneTheme
  projectName?: string
  scenes?: any[]
  enabled?: boolean
  onToggle?: (v: boolean) => void
}

export default function SceneBackground({ scene = 'space', projectName, scenes, enabled, onToggle }: SceneBackgroundProps) {
  const [primaryColor, setPrimaryColor] = useState('170, 70%, 55%')

  useEffect(() => {
    const updateColor = () => {
      const val = getComputedStyle(document.documentElement).getPropertyValue('--primary').trim()
      if (val) setPrimaryColor(val)
    }
    updateColor()
    const observer = new MutationObserver(updateColor)
    observer.observe(document.documentElement, { attributes: true, attributeFilter: ['style', 'class'] })
    return () => observer.disconnect()
  }, [])

  return (
    <div className="absolute inset-0 pointer-events-none overflow-hidden" style={{ borderRadius: 'inherit' }}>
      {scene === 'space' && (
        <div className="absolute inset-0" style={{ background: `linear-gradient(180deg, hsl(${primaryColor} / 0.02) 0%, hsl(${primaryColor} / 0.06) 25%, hsl(${primaryColor} / 0.10) 50%, hsl(${primaryColor} / 0.08) 75%, hsl(${primaryColor} / 0.03) 100%)` }}>
          <div className="absolute w-[2px] h-[2px] rounded-full animate-pulse" style={{ top: '5%', left: '12%', animationDuration: '3s', background: `hsl(${primaryColor} / 0.7)` }} />
          <div className="absolute w-[3px] h-[3px] rounded-full shadow-[0_0_8px_rgba(255,255,255,0.4)] animate-pulse" style={{ top: '8%', left: '45%', animationDuration: '2.5s', background: `hsl(${primaryColor} / 0.8)` }} />
          <div className="absolute w-[2px] h-[2px] rounded-full animate-pulse" style={{ top: '15%', left: '70%', animationDuration: '4s', background: `hsl(${primaryColor} / 0.7)` }} />
          <div className="absolute w-[3px] h-[3px] rounded-full shadow-[0_0_8px_rgba(255,255,255,0.4)] animate-pulse" style={{ top: '3%', left: '80%', animationDuration: '3.5s', background: `hsl(${primaryColor} / 0.8)` }} />
          <div className="absolute w-[2px] h-[2px] rounded-full" style={{ top: '22%', left: '25%', background: `hsl(${primaryColor} / 0.7)` }} />
          <div className="absolute w-[2px] h-[2px] rounded-full" style={{ top: '10%', left: '55%', background: `hsl(${primaryColor} / 0.7)` }} />
          <div className="absolute w-[2px] h-[2px] rounded-full" style={{ top: '18%', left: '90%', background: `hsl(${primaryColor} / 0.7)` }} />
          <div className="absolute w-[3px] h-[3px] rounded-full shadow-[0_0_8px_rgba(255,255,255,0.4)]" style={{ top: '28%', left: '8%', background: `hsl(${primaryColor} / 0.8)` }} />
          <div className="absolute w-[2px] h-[2px] rounded-full" style={{ top: '35%', left: '65%', background: `hsl(${primaryColor} / 0.7)` }} />
          <div className="absolute w-[2px] h-[2px] rounded-full" style={{ top: '30%', left: '35%', background: `hsl(${primaryColor} / 0.7)` }} />
          <div className="absolute w-[2px] h-[2px] rounded-full" style={{ top: '40%', left: '15%', background: `hsl(${primaryColor} / 0.7)` }} />
          <div className="absolute w-[3px] h-[3px] rounded-full shadow-[0_0_8px_rgba(255,255,255,0.4)]" style={{ top: '45%', left: '80%', background: `hsl(${primaryColor} / 0.8)` }} />
          <div className="absolute w-[2px] h-[2px] rounded-full" style={{ top: '50%', left: '50%', background: `hsl(${primaryColor} / 0.7)` }} />
          <div className="absolute w-[400px] h-[300px] rounded-full" style={{ top: '5%', left: '55%', background: `radial-gradient(ellipse, hsl(${primaryColor} / 0.15), transparent 70%)` }} />
          <div className="absolute w-[350px] h-[350px] rounded-full" style={{ bottom: '15%', right: '5%', background: `radial-gradient(circle, hsl(${primaryColor} / 0.08), transparent 70%)` }} />
          <div className="absolute w-[60px] h-[60px] rounded-full" style={{ top: '12%', left: '22%', background: `radial-gradient(circle at 40% 35%, hsl(${primaryColor} / 0.4), hsl(${primaryColor} / 0.2))`, boxShadow: `0 0 50px hsl(${primaryColor} / 0.15)` }} />
        </div>
      )}

      {scene === 'ocean' && (
        <div className="absolute inset-0" style={{ background: `linear-gradient(180deg, hsl(${primaryColor} / 0.04) 0%, hsl(${primaryColor} / 0.08) 25%, hsl(${primaryColor} / 0.12) 45%, hsl(${primaryColor} / 0.15) 55%, hsl(${primaryColor} / 0.10) 70%, hsl(${primaryColor} / 0.04) 100%)` }}>
          <div className="absolute w-[100px] h-[100px] rounded-full" style={{ top: '34%', left: '50%', transform: 'translateX(-50%)', background: `radial-gradient(circle, hsl(${primaryColor} / 0.3), hsl(${primaryColor} / 0.1) 50%, transparent 100%)`, boxShadow: `0 0 80px hsl(${primaryColor} / 0.12)` }} />
          <div className="absolute w-[4px]" style={{ top: '44%', left: '50%', transform: 'translateX(-50%)', bottom: '40%', background: `linear-gradient(0deg, transparent, hsl(${primaryColor} / 0.1) 20%, hsl(${primaryColor} / 0.03))` }} />
          <div className="absolute bottom-0 left-0 right-0" style={{ height: '55%', background: `linear-gradient(180deg, hsl(${primaryColor} / 0.25), hsl(${primaryColor} / 0.08))` }} />
          <div className="absolute bottom-0 left-0 right-0" style={{ height: '60%', background: `repeating-linear-gradient(90deg, transparent, transparent 50px, hsl(${primaryColor} / 0.04) 50px, hsl(${primaryColor} / 0.04) 52px, transparent 52px, transparent 100px)` }} />
          <div className="absolute bottom-[12%] left-0 right-0" style={{ height: '60%', background: `repeating-linear-gradient(105deg, transparent, transparent 70px, hsl(${primaryColor} / 0.025) 70px, hsl(${primaryColor} / 0.025) 72px, transparent 72px, transparent 140px)` }} />
          <div className="absolute bottom-[25%] left-0 right-0" style={{ height: '60%', background: `repeating-linear-gradient(75deg, transparent, transparent 90px, hsl(${primaryColor} / 0.025) 90px, hsl(${primaryColor} / 0.025) 93px, transparent 93px, transparent 180px)` }} />
        </div>
      )}

      {scene === 'city' && (
        <div className="absolute inset-0" style={{ background: `linear-gradient(180deg, hsl(${primaryColor} / 0.02) 0%, hsl(${primaryColor} / 0.05) 15%, hsl(${primaryColor} / 0.10) 28%, hsl(${primaryColor} / 0.15) 38%, hsl(${primaryColor} / 0.18) 45%, hsl(${primaryColor} / 0.20) 50%, hsl(${primaryColor} / 0.15) 58%, hsl(${primaryColor} / 0.08) 70%, hsl(${primaryColor} / 0.03) 100%)` }}>
          <div className="absolute w-[2px] h-[2px] rounded-full" style={{ top: '5%', left: '10%', background: `hsl(${primaryColor} / 0.5)` }} />
          <div className="absolute w-[2px] h-[2px] rounded-full" style={{ top: '12%', left: '35%', background: `hsl(${primaryColor} / 0.5)` }} />
          <div className="absolute w-[2px] h-[2px] rounded-full" style={{ top: '6%', left: '65%', background: `hsl(${primaryColor} / 0.5)` }} />
          <div className="absolute w-[2px] h-[2px] rounded-full" style={{ top: '18%', left: '80%', background: `hsl(${primaryColor} / 0.5)` }} />
          <div className="absolute w-[50px] h-[50px] rounded-full" style={{ top: '8%', right: '20%', background: `radial-gradient(circle at 40% 35%, hsl(${primaryColor} / 0.5), hsl(${primaryColor} / 0.3))`, boxShadow: `0 0 60px hsl(${primaryColor} / 0.2)` }} />
          <div className="absolute bottom-[15%] left-0 right-0" style={{ height: '55%', background: `linear-gradient(0deg, hsl(${primaryColor} / 0.15) 0%, hsl(${primaryColor} / 0.10) 25%, hsl(${primaryColor} / 0.05) 50%, transparent 100%)` }} />
          <div className="absolute bottom-0 left-0 right-0" style={{ height: '48%' }}>
            <svg viewBox="0 0 1200 400" preserveAspectRatio="none" className="absolute bottom-0 w-full h-full">
              <rect x="0" y="160" width="84" height="240" fill={`hsl(${primaryColor} / 0.12)`} />
              <rect x="92" y="60" width="72" height="340" fill={`hsl(${primaryColor} / 0.10)`} />
              <rect x="172" y="200" width="120" height="200" fill={`hsl(${primaryColor} / 0.14)`} />
              <rect x="300" y="100" width="84" height="300" fill={`hsl(${primaryColor} / 0.10)`} />
              <rect x="392" y="40" width="144" height="360" fill={`hsl(${primaryColor} / 0.08)`} />
              <rect x="544" y="180" width="60" height="220" fill={`hsl(${primaryColor} / 0.14)`} />
              <rect x="612" y="80" width="108" height="320" fill={`hsl(${primaryColor} / 0.10)`} />
              <rect x="728" y="220" width="96" height="180" fill={`hsl(${primaryColor} / 0.14)`} />
              <rect x="832" y="120" width="132" height="280" fill={`hsl(${primaryColor} / 0.10)`} />
              <rect x="972" y="48" width="84" height="352" fill={`hsl(${primaryColor} / 0.08)`} />
              <rect x="1064" y="168" width="72" height="232" fill={`hsl(${primaryColor} / 0.12)`} />
              <rect x="1144" y="88" width="108" height="312" fill={`hsl(${primaryColor} / 0.10)`} />
              <rect x="104" y="222" width="6" height="8" rx="1" fill={`hsl(${primaryColor} / 0.6)`} />
              <rect x="205" y="255" width="6" height="8" rx="1" fill={`hsl(${primaryColor} / 0.5)`} />
              <rect x="410" y="100" width="6" height="8" rx="1" fill={`hsl(${primaryColor} / 0.6)`} />
              <rect x="420" y="100" width="6" height="8" rx="1" fill={`hsl(${primaryColor} / 0.6)`} />
              <rect x="430" y="100" width="6" height="8" rx="1" fill={`hsl(${primaryColor} / 0.5)`} />
              <rect x="316" y="170" width="6" height="8" rx="1" fill={`hsl(${primaryColor} / 0.6)`} />
              <rect x="1000" y="108" width="6" height="8" rx="1" fill={`hsl(${primaryColor} / 0.6)`} />
              <rect x="632" y="148" width="6" height="8" rx="1" fill={`hsl(${primaryColor} / 0.6)`} />
            </svg>
          </div>
          <div className="absolute bottom-0 left-0 right-0" style={{ height: '15%', background: `linear-gradient(0deg, hsl(${primaryColor} / 0.04), hsl(${primaryColor} / 0.08))`, borderTop: `1px solid hsl(${primaryColor} / 0.1)` }} />
          <div className="absolute left-0 right-0" style={{ bottom: '15%', height: '2px', background: `linear-gradient(90deg, transparent 5%, hsl(${primaryColor} / 0.2), hsl(${primaryColor} / 0.15), transparent 95%)` }} />
        </div>
      )}

      {scene === 'mt' && (
        <div className="absolute inset-0" style={{ background: `linear-gradient(180deg, hsl(${primaryColor} / 0.03) 0%, hsl(${primaryColor} / 0.07) 20%, hsl(${primaryColor} / 0.12) 35%, hsl(${primaryColor} / 0.18) 48%, hsl(${primaryColor} / 0.22) 55%, hsl(${primaryColor} / 0.25) 62%, hsl(${primaryColor} / 0.28) 68%, hsl(${primaryColor} / 0.22) 72%)` }}>
          <div className="absolute w-[2px] h-[2px] rounded-full animate-pulse" style={{ top: '6%', left: '15%', animationDuration: '3s', background: `hsl(${primaryColor} / 0.6)` }} />
          <div className="absolute w-[2px] h-[2px] rounded-full animate-pulse" style={{ top: '10%', left: '50%', animationDuration: '2.8s', background: `hsl(${primaryColor} / 0.6)` }} />
          <div className="absolute w-[2px] h-[2px] rounded-full animate-pulse" style={{ top: '4%', left: '75%', animationDuration: '3.5s', background: `hsl(${primaryColor} / 0.6)` }} />
          <div className="absolute w-[2px] h-[2px] rounded-full" style={{ top: '16%', left: '35%', background: `hsl(${primaryColor} / 0.6)` }} />
          <div className="absolute w-[300px] h-[180px]" style={{ bottom: '28%', left: '50%', transform: 'translateX(-50%)', background: `radial-gradient(ellipse, hsl(${primaryColor} / 0.18), transparent 70%)` }} />
          <svg viewBox="0 0 1200 400" preserveAspectRatio="none" className="absolute bottom-0 w-full h-[52%]">
            <polygon points="0,400 180,68 380,155 580,28 780,135 1200,300 1200,400" fill={`hsl(${primaryColor} / 0.06)`} />
            <polygon points="0,400 130,210 330,55 580,130 830,42 1020,190 1200,400" fill={`hsl(${primaryColor} / 0.08)`} />
            <polygon points="180,400 460,110 680,190 1200,110 1200,400" fill={`hsl(${primaryColor} / 0.10)`} />
            <rect x="0" y="300" width="1200" height="100" fill="url(#mg)" />
            <defs><linearGradient id="mg" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stop-color={`hsl(${primaryColor} / 0)`}/><stop offset="100%" stop-color={`hsl(${primaryColor} / 0.04)`}/></linearGradient></defs>
          </svg>
        </div>
      )}

      {scene === 'plain' && (
        <div className="absolute inset-0" style={{ background: `linear-gradient(180deg, hsl(${primaryColor} / 0.04) 0%, hsl(${primaryColor} / 0.03) 50%, hsl(${primaryColor} / 0.02) 100%)` }}>
          <div className="absolute w-[400px] h-[400px] rounded-full" style={{ top: '-15%', right: '-10%', background: `radial-gradient(circle, hsl(${primaryColor} / 0.04), transparent 70%)` }} />
          <div className="absolute w-[300px] h-[300px] rounded-full" style={{ bottom: '-10%', left: '-5%', background: `radial-gradient(circle, hsl(${primaryColor} / 0.03), transparent 70%)` }} />
        </div>
      )}
    </div>
  )
}
