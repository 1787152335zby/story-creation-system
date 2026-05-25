import { useState, useRef, useEffect, useCallback } from 'react'
import { X, ZoomIn, ZoomOut, Loader2, ChevronLeft, ChevronRight } from 'lucide-react'

interface ImagePreviewProps {
  src: string
  onClose: () => void
  images?: string[]
  onNavigate?: (index: number) => void
}

export default function ImagePreview({ src, onClose, images, onNavigate }: ImagePreviewProps) {
  const imgRef = useRef<HTMLImageElement>(null)
  const containerRef = useRef<HTMLDivElement>(null)
  const [scale, setScale] = useState(1)
  const [position, setPosition] = useState({ x: 0, y: 0 })
  const [isDragging, setIsDragging] = useState(false)
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 })
  const [loaded, setLoaded] = useState(false)
  const [error, setError] = useState(false)
  const [upscaling, setUpscaling] = useState(false)

  const currentIndex = images ? images.indexOf(src) : -1
  const hasPrev = currentIndex > 0
  const hasNext = currentIndex >= 0 && currentIndex < (images?.length || 0) - 1

  const goPrev = () => {
    if (hasPrev && images && onNavigate) {
      onNavigate(currentIndex - 1)
    }
  }

  const goNext = () => {
    if (hasNext && images && onNavigate) {
      onNavigate(currentIndex + 1)
    }
  }

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
      if (e.key === 'ArrowLeft') goPrev()
      if (e.key === 'ArrowRight') goNext()
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [onClose, hasPrev, hasNext, currentIndex])

  // 滚轮缩放
  const handleWheel = useCallback((e: React.WheelEvent) => {
    e.preventDefault()
    setScale(prev => {
      const delta = e.deltaY > 0 ? -0.1 : 0.1
      return Math.max(0.5, Math.min(5, prev + delta))
    })
  }, [])

  // 拖拽开始
  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    if (scale <= 1) return
    e.preventDefault()
    setIsDragging(true)
    setDragStart({ x: e.clientX - position.x, y: e.clientY - position.y })
  }, [scale, position])

  // 拖拽移动 + 结束
  useEffect(() => {
    if (!isDragging) return
    const handleMove = (e: MouseEvent) => {
      setPosition({ x: e.clientX - dragStart.x, y: e.clientY - dragStart.y })
    }
    const handleUp = () => setIsDragging(false)
    window.addEventListener('mousemove', handleMove)
    window.addEventListener('mouseup', handleUp)
    return () => {
      window.removeEventListener('mousemove', handleMove)
      window.removeEventListener('mouseup', handleUp)
    }
  }, [isDragging, dragStart])

  // 图片加载成功/失败
  const handleLoad = useCallback(() => setLoaded(true), [])
  const handleError = useCallback(() => { setLoaded(true); setError(true) }, [])

  // 双击重置缩放
  const handleDoubleClick = useCallback(() => {
    setScale(1)
    setPosition({ x: 0, y: 0 })
  }, [])

  const handleUpscale = useCallback(async () => {
    setUpscaling(true)
    try {
      const res = await fetch('/api/image-gen/upscale', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url: src, scale: 2 }),
      })
      const data = await res.json()
      if (data.url) {
        window.open(data.url, '_blank')
      }
    } catch {
    } finally {
      setUpscaling(false)
    }
  }, [src])

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm"
      onClick={onClose}>
      <div className="relative flex items-center gap-3" onClick={e => e.stopPropagation()}>
        {hasPrev && (
          <button onClick={goPrev} className="p-2 rounded-full bg-white/10 hover:bg-white/20 text-white/70 hover:text-white transition-colors flex-shrink-0"
            title="上一张 (←)">
            <ChevronLeft className="w-6 h-6" />
          </button>
        )}
        <div className="flex flex-col items-center">
          {/* 顶部工具栏 */}
          <div className="flex items-center gap-2 mb-2 bg-black/40 rounded-lg px-3 py-1.5">
            <button onClick={() => setScale(prev => Math.max(0.5, prev - 0.2))}
              className="p-1 rounded hover:bg-white/10 text-white/70 hover:text-white transition-colors" title="缩小">
              <ZoomOut className="w-4 h-4" />
            </button>
            <span className="text-white/60 text-xs min-w-[3rem] text-center select-none">
              {Math.round(scale * 100)}%
            </span>
            <button onClick={() => setScale(prev => Math.min(5, prev + 0.2))}
              className="p-1 rounded hover:bg-white/10 text-white/70 hover:text-white transition-colors" title="放大">
              <ZoomIn className="w-4 h-4" />
            </button>
            <div className="w-px h-4 bg-white/20 mx-1" />
            <button onClick={() => { setScale(1); setPosition({ x: 0, y: 0 }) }}
              className="px-2 py-0.5 rounded text-[10px] text-white/60 hover:text-white hover:bg-white/10 transition-colors">
              适应
            </button>
            {loaded && !error && (
              <>
                <div className="w-px h-4 bg-white/20 mx-1" />
                <button onClick={handleUpscale} disabled={upscaling}
                  className="p-1 rounded hover:bg-white/10 text-white/70 hover:text-white transition-colors disabled:opacity-40" title="放大图片">
                  {upscaling ? <Loader2 className="w-4 h-4 animate-spin" /> : <span className="text-[10px] px-0.5">🔍+</span>}
                </button>
              </>
            )}
            {images && images.length > 1 && (
              <span className="text-white/40 text-[10px] px-1">{currentIndex + 1}/{images.length}</span>
            )}
            <div className="w-px h-4 bg-white/20 mx-1" />
            <button onClick={onClose}
              className="p-1 rounded hover:bg-white/10 text-white/70 hover:text-white transition-colors" title="关闭 (Esc)">
              <X className="w-4 h-4" />
            </button>
          </div>

        {/* 图片容器 */}
        <div
          ref={containerRef}
          className={`relative overflow-hidden rounded-xl bg-black/40 ${isDragging ? 'cursor-grabbing' : scale > 1 ? 'cursor-grab' : 'cursor-default'}`}
          onWheel={handleWheel}
          onMouseDown={handleMouseDown}
          onDoubleClick={handleDoubleClick}
          style={{ maxWidth: '90vw', maxHeight: '80vh' }}
        >
          {/* 加载中 */}
          {!loaded && (
            <div className="flex items-center justify-center w-64 h-64">
              <Loader2 className="w-8 h-8 animate-spin text-white/40" />
            </div>
          )}

          {/* 错误提示 */}
          {loaded && error && (
            <div className="flex items-center justify-center w-64 h-64 text-white/40 text-sm">
              图片加载失败
            </div>
          )}

          {/* 图片本体 */}
          <img
            ref={imgRef}
            src={src}
            alt=""
            onLoad={handleLoad}
            onError={handleError}
            className={`max-w-full max-h-[80vh] object-contain transition-opacity duration-200 ${loaded && !error ? 'opacity-100' : 'opacity-0 absolute pointer-events-none'}`}
            style={{
              transform: `scale(${scale}) translate(${position.x / scale}px, ${position.y / scale}px)`,
              transformOrigin: 'center center',
            }}
            draggable={false}
          />
        </div>

        {/* 底部提示 */}
        {scale > 1 && (
          <p className="mt-2 text-[10px] text-white/30">拖拽平移 · 滚轮缩放 · 双击重置</p>
        )}
      </div>
      {hasNext && (
        <button onClick={goNext} className="p-2 rounded-full bg-white/10 hover:bg-white/20 text-white/70 hover:text-white transition-colors flex-shrink-0"
          title="下一张 (→)">
          <ChevronRight className="w-6 h-6" />
        </button>
      )}
    </div>
    </div>
  )
}