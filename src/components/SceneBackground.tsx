export type SceneTheme = 'space' | 'ocean' | 'city' | 'mt' | 'plain'

interface SceneBackgroundProps {
  scene: SceneTheme
}

export default function SceneBackground({ scene }: SceneBackgroundProps) {
  return (
    <div className="fixed inset-0 pointer-events-none overflow-hidden">
      {scene === 'space' && (
        <div className="absolute inset-0" style={{ background: 'linear-gradient(180deg, #020010 0%, #060828 25%, #0a1840 50%, #1a0a30 75%, #0a0a1a 100%)' }}>
          <div className="absolute w-[2px] h-[2px] bg-white/90 rounded-full animate-pulse" style={{ top: '5%', left: '12%', animationDuration: '3s' }} />
          <div className="absolute w-[3px] h-[3px] bg-white rounded-full shadow-[0_0_8px_rgba(255,255,255,0.6)] animate-pulse" style={{ top: '8%', left: '45%', animationDuration: '2.5s' }} />
          <div className="absolute w-[2px] h-[2px] bg-white/90 rounded-full animate-pulse" style={{ top: '15%', left: '70%', animationDuration: '4s' }} />
          <div className="absolute w-[3px] h-[3px] bg-white rounded-full shadow-[0_0_8px_rgba(255,255,255,0.6)] animate-pulse" style={{ top: '3%', left: '80%', animationDuration: '3.5s' }} />
          <div className="absolute w-[2px] h-[2px] bg-white/90 rounded-full" style={{ top: '22%', left: '25%' }} />
          <div className="absolute w-[2px] h-[2px] bg-white/90 rounded-full" style={{ top: '10%', left: '55%' }} />
          <div className="absolute w-[2px] h-[2px] bg-white/90 rounded-full" style={{ top: '18%', left: '90%' }} />
          <div className="absolute w-[3px] h-[3px] bg-white rounded-full shadow-[0_0_8px_rgba(255,255,255,0.6)]" style={{ top: '28%', left: '8%' }} />
          <div className="absolute w-[2px] h-[2px] bg-white/90 rounded-full" style={{ top: '35%', left: '65%' }} />
          <div className="absolute w-[2px] h-[2px] bg-white/90 rounded-full" style={{ top: '30%', left: '35%' }} />
          <div className="absolute w-[2px] h-[2px] bg-white/90 rounded-full" style={{ top: '40%', left: '15%' }} />
          <div className="absolute w-[3px] h-[3px] bg-white rounded-full shadow-[0_0_8px_rgba(255,255,255,0.6)]" style={{ top: '45%', left: '80%' }} />
          <div className="absolute w-[2px] h-[2px] bg-white/90 rounded-full" style={{ top: '50%', left: '50%' }} />
          <div className="absolute w-[400px] h-[300px] rounded-full" style={{ top: '5%', left: '55%', background: 'radial-gradient(ellipse, rgba(120,80,200,0.15), transparent 70%)' }} />
          <div className="absolute w-[350px] h-[350px] rounded-full" style={{ bottom: '15%', right: '5%', background: 'radial-gradient(circle, rgba(0,150,200,0.08), transparent 70%)' }} />
          <div className="absolute w-[60px] h-[60px] rounded-full shadow-[0_0_50px_rgba(192,96,48,0.25)]" style={{ top: '12%', left: '22%', background: 'radial-gradient(circle at 40% 35%, #f0d0a0, #c06030)' }} />
        </div>
      )}

      {scene === 'ocean' && (
        <div className="absolute inset-0" style={{ background: 'linear-gradient(180deg, #0a1628 0%, #0d2850 25%, #1a4a6a 45%, #1a6a7a 55%, #0d4070 70%, #0a2848 100%)' }}>
          <div className="absolute w-[100px] h-[100px] rounded-full shadow-[0_0_80px_rgba(255,180,60,0.15)]" style={{ top: '34%', left: '50%', transform: 'translateX(-50%)', background: 'radial-gradient(circle, #ffd070, #ff8020 50%, transparent 100%)' }} />
          <div className="absolute w-[4px]" style={{ top: '44%', left: '50%', transform: 'translateX(-50%)', bottom: '40%', background: 'linear-gradient(0deg, transparent, rgba(255,200,100,0.1) 20%, rgba(255,200,100,0.03))' }} />
          <div className="absolute bottom-0 left-0 right-0" style={{ height: '55%', background: 'linear-gradient(180deg, rgba(10,50,90,0.7), #081828)' }} />
          <div className="absolute bottom-0 left-0 right-0" style={{ height: '60%', background: 'repeating-linear-gradient(90deg, transparent, transparent 50px, rgba(0,200,255,0.04) 50px, rgba(0,200,255,0.04) 52px, transparent 52px, transparent 100px)' }} />
          <div className="absolute bottom-[12%] left-0 right-0" style={{ height: '60%', background: 'repeating-linear-gradient(105deg, transparent, transparent 70px, rgba(255,255,255,0.025) 70px, rgba(255,255,255,0.025) 72px, transparent 72px, transparent 140px)' }} />
          <div className="absolute bottom-[25%] left-0 right-0" style={{ height: '60%', background: 'repeating-linear-gradient(75deg, transparent, transparent 90px, rgba(0,220,255,0.025) 90px, rgba(0,220,255,0.025) 93px, transparent 93px, transparent 180px)' }} />
        </div>
      )}

      {scene === 'city' && (
        <div className="absolute inset-0" style={{ background: 'linear-gradient(180deg, #05001a 0%, #0a0030 15%, #200050 28%, #400060 38%, #600050 45%, #800040 50%, #600030 58%, #2a0020 70%, #0a0010 100%)' }}>
          <div className="absolute w-[2px] h-[2px] bg-white/60 rounded-full" style={{ top: '5%', left: '10%' }} />
          <div className="absolute w-[2px] h-[2px] bg-white/60 rounded-full" style={{ top: '12%', left: '35%' }} />
          <div className="absolute w-[2px] h-[2px] bg-white/60 rounded-full" style={{ top: '6%', left: '65%' }} />
          <div className="absolute w-[2px] h-[2px] bg-white/60 rounded-full" style={{ top: '18%', left: '80%' }} />
          <div className="absolute w-[50px] h-[50px] rounded-full shadow-[0_0_60px_rgba(255,0,102,0.3)]" style={{ top: '8%', right: '20%', background: 'radial-gradient(circle at 40% 35%, #ff88cc, #ff0066)' }} />
          <div className="absolute bottom-[15%] left-0 right-0" style={{ height: '55%', background: 'linear-gradient(0deg, rgba(255,50,100,0.08) 0%, rgba(0,220,255,0.07) 25%, rgba(100,0,200,0.05) 50%, transparent 100%)' }} />
          <div className="absolute bottom-0 left-0 right-0" style={{ height: '48%' }}>
            <svg viewBox="0 0 1200 400" preserveAspectRatio="none" className="absolute bottom-0 w-full h-full">
              <rect x="0" y="160" width="84" height="240" fill="url(#bc1)" />
              <rect x="92" y="60" width="72" height="340" fill="url(#bc2)" />
              <rect x="172" y="200" width="120" height="200" fill="url(#bc3)" />
              <rect x="300" y="100" width="84" height="300" fill="url(#bc4)" />
              <rect x="392" y="40" width="144" height="360" fill="url(#bc5)" />
              <rect x="544" y="180" width="60" height="220" fill="url(#bc6)" />
              <rect x="612" y="80" width="108" height="320" fill="url(#bc7)" />
              <rect x="728" y="220" width="96" height="180" fill="url(#bc8)" />
              <rect x="832" y="120" width="132" height="280" fill="url(#bc9)" />
              <rect x="972" y="48" width="84" height="352" fill="url(#bc10)" />
              <rect x="1064" y="168" width="72" height="232" fill="url(#bc11)" />
              <rect x="1144" y="88" width="108" height="312" fill="url(#bc12)" />
              <rect x="104" y="222" width="6" height="8" rx="1" fill="rgba(0,200,255,0.7)" />
              <rect x="205" y="255" width="6" height="8" rx="1" fill="rgba(255,0,128,0.6)" />
              <rect x="410" y="100" width="6" height="8" rx="1" fill="rgba(0,200,255,0.7)" />
              <rect x="420" y="100" width="6" height="8" rx="1" fill="rgba(0,200,255,0.7)" />
              <rect x="430" y="100" width="6" height="8" rx="1" fill="rgba(255,200,50,0.5)" />
              <rect x="316" y="170" width="6" height="8" rx="1" fill="rgba(0,200,255,0.7)" />
              <rect x="1000" y="108" width="6" height="8" rx="1" fill="rgba(0,200,255,0.7)" />
              <rect x="632" y="148" width="6" height="8" rx="1" fill="rgba(0,200,255,0.7)" />
              <defs>
                <linearGradient id="bc1" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stop-color="rgba(10,4,20,0.3)"/><stop offset="30%" stop-color="#0a0414"/></linearGradient>
                <linearGradient id="bc2" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stop-color="rgba(10,4,20,0.25)"/><stop offset="25%" stop-color="#0a0414"/></linearGradient>
                <linearGradient id="bc3" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stop-color="rgba(10,4,20,0.35)"/><stop offset="35%" stop-color="#0a0414"/></linearGradient>
                <linearGradient id="bc4" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stop-color="rgba(10,4,20,0.25)"/><stop offset="25%" stop-color="#0a0414"/></linearGradient>
                <linearGradient id="bc5" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stop-color="rgba(10,4,20,0.15)"/><stop offset="15%" stop-color="#0a0414"/></linearGradient>
                <linearGradient id="bc6" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stop-color="rgba(10,4,20,0.35)"/><stop offset="35%" stop-color="#0a0414"/></linearGradient>
                <linearGradient id="bc7" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stop-color="rgba(10,4,20,0.2)"/><stop offset="20%" stop-color="#0a0414"/></linearGradient>
                <linearGradient id="bc8" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stop-color="rgba(10,4,20,0.35)"/><stop offset="35%" stop-color="#0a0414"/></linearGradient>
                <linearGradient id="bc9" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stop-color="rgba(10,4,20,0.25)"/><stop offset="25%" stop-color="#0a0414"/></linearGradient>
                <linearGradient id="bc10" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stop-color="rgba(10,4,20,0.15)"/><stop offset="15%" stop-color="#0a0414"/></linearGradient>
                <linearGradient id="bc11" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stop-color="rgba(10,4,20,0.3)"/><stop offset="30%" stop-color="#0a0414"/></linearGradient>
                <linearGradient id="bc12" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stop-color="rgba(10,4,20,0.2)"/><stop offset="20%" stop-color="#0a0414"/></linearGradient>
              </defs>
            </svg>
          </div>
          <div className="absolute bottom-0 left-0 right-0" style={{ height: '15%', background: 'linear-gradient(0deg, #050208, #0a0414)', borderTop: '1px solid rgba(0,200,255,0.1)' }} />
          <div className="absolute left-0 right-0" style={{ bottom: '15%', height: '2px', background: 'linear-gradient(90deg, transparent 5%, rgba(255,0,128,0.25), rgba(0,200,255,0.25), transparent 95%)' }} />
        </div>
      )}

      {scene === 'mt' && (
        <div className="absolute inset-0" style={{ background: 'linear-gradient(180deg, #0d0418 0%, #1a0a2e 20%, #3a1a4e 35%, #6b3a5e 48%, #b06a4a 55%, #d89050 62%, #e8b070 68%, #d89860 72%)' }}>
          <div className="absolute w-[2px] h-[2px] bg-white/80 rounded-full animate-pulse" style={{ top: '6%', left: '15%', animationDuration: '3s' }} />
          <div className="absolute w-[2px] h-[2px] bg-white/80 rounded-full animate-pulse" style={{ top: '10%', left: '50%', animationDuration: '2.8s' }} />
          <div className="absolute w-[2px] h-[2px] bg-white/80 rounded-full animate-pulse" style={{ top: '4%', left: '75%', animationDuration: '3.5s' }} />
          <div className="absolute w-[2px] h-[2px] bg-white/80 rounded-full" style={{ top: '16%', left: '35%' }} />
          <div className="absolute w-[300px] h-[180px]" style={{ bottom: '28%', left: '50%', transform: 'translateX(-50%)', background: 'radial-gradient(ellipse, rgba(232,176,112,0.18), transparent 70%)' }} />
          <svg viewBox="0 0 1200 400" preserveAspectRatio="none" className="absolute bottom-0 w-full h-[52%]">
            <polygon points="0,400 180,68 380,155 580,28 780,135 1200,300 1200,400" fill="#0a0514" />
            <polygon points="0,400 130,210 330,55 580,130 830,42 1020,190 1200,400" fill="#0c0718" />
            <polygon points="180,400 460,110 680,190 1200,110 1200,400" fill="#0e081c" />
            <rect x="0" y="300" width="1200" height="100" fill="url(#mg)" />
            <defs><linearGradient id="mg" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stop-color="rgba(8,3,16,0)"/><stop offset="100%" stop-color="#080310"/></linearGradient></defs>
          </svg>
        </div>
      )}

      {scene === 'plain' && (
        <div className="absolute inset-0" style={{ background: 'linear-gradient(180deg, #0d0d15 0%, #0a0a12 50%, #08080f 100%)' }}>
          <div className="absolute w-[400px] h-[400px] rounded-full opacity-[0.03]" style={{ top: '-15%', right: '-10%', background: 'radial-gradient(circle, white, transparent 70%)' }} />
          <div className="absolute w-[300px] h-[300px] rounded-full opacity-[0.02]" style={{ bottom: '-10%', left: '-5%', background: 'radial-gradient(circle, white, transparent 70%)' }} />
        </div>
      )}
    </div>
  )
}
