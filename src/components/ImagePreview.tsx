import { useEffect } from 'react'
import { X } from 'lucide-react'

interface Props {
  src: string
  onClose: () => void
}

export default function ImagePreview({ src, onClose }: Props) {
  useEffect(() => {
    const handler = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [onClose])

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm" onClick={onClose}>
      <div className="relative max-w-[90vw] max-h-[90vh]" onClick={e => e.stopPropagation()}>
        <img src={src} alt="" className="max-w-full max-h-[90vh] rounded-2xl shadow-2xl" />
        <button onClick={onClose}
          className="absolute -top-3 -right-3 w-8 h-8 rounded-full bg-background/80 backdrop-blur-sm border border-border flex items-center justify-center hover:bg-background transition-all">
          <X className="w-4 h-4" />
        </button>
      </div>
    </div>
  )
}
