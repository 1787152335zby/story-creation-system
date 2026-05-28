import { useRef, useState, useCallback } from 'react'
import { Loader2, ImagePlus, X, Link, History, Image as ImageIcon } from 'lucide-react'
import { uploadReferenceImage, fetchGenerationHistory } from '../lib/api'
import type { ReferenceUrlsByType } from '../lib/types'

type RefTab = 'character' | 'scene' | 'prop' | 'style'

interface ReferenceImageUploaderProps {
  urls?: ReferenceUrlsByType
  onChange?: (urls: ReferenceUrlsByType) => void
  autoUrls?: string[]
  manualUrls?: string[]
  autoUrlsByType?: ReferenceUrlsByType
  manualUrlsByType?: ReferenceUrlsByType
  onManualChange?: (urls: string[]) => void
  onManualByTypeChange?: (v: ReferenceUrlsByType) => void
  refTypeEnabled?: Record<string, boolean>
  onRefTypeToggle?: (type: string) => void
  generalRefUrls?: string[]
  generalRefEnabled?: boolean
  onGeneralRefToggle?: (v: boolean) => void
}

const TAB_LABELS: Record<RefTab, string> = { style: '🎨 画风', character: '👤 人物', scene: '🏠 场景', prop: '🔧 道具' }

export default function ReferenceImageUploader({ urls = { style: [], character: [], scene: [], prop: [] }, onChange, autoUrls, manualUrls, autoUrlsByType, manualUrlsByType, onManualChange, onManualByTypeChange, refTypeEnabled, onRefTypeToggle, generalRefUrls, generalRefEnabled, onGeneralRefToggle }: ReferenceImageUploaderProps) {
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [activeTab, setActiveTab] = useState<RefTab>('character')
  const [urlInput, setUrlInput] = useState('')
  const [uploading, setUploading] = useState(false)
  const [dragOver, setDragOver] = useState(false)
  const [showHistory, setShowHistory] = useState(false)
  const [historyImages, setHistoryImages] = useState<{ name: string; url: string }[]>([])
  const [loadingHistory, setLoadingHistory] = useState(false)

  const currentUrls = urls[activeTab]

  const openHistory = useCallback(async () => {
    setShowHistory(true)
    setLoadingHistory(true)
    try {
      const h = await fetchGenerationHistory()
      const all = [...(h.images_free || []), ...(h.images_project || [])]
      setHistoryImages(all)
    } catch {
    } finally {
      setLoadingHistory(false)
    }
  }, [])

  const handleFileSelect = useCallback(async (files: FileList | null) => {
    if (!files || files.length === 0) return
    setUploading(true)
    try {
      const uploadedUrls: string[] = []
      for (let i = 0; i < files.length; i++) {
        const url = await uploadReferenceImage(files[i])
        uploadedUrls.push(url)
      }
      onChange?.({ ...urls, [activeTab]: [...currentUrls, ...uploadedUrls] })
    } catch {
    } finally {
      setUploading(false)
    }
  }, [urls, activeTab, currentUrls, onChange])

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setDragOver(false)
    handleFileSelect(e.dataTransfer.files)
  }, [handleFileSelect])

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setDragOver(true)
  }, [])

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setDragOver(false)
  }, [])

  const handleUrlAdd = useCallback(() => {
    const trimmed = urlInput.trim()
    if (!trimmed) return
    if (currentUrls.includes(trimmed)) return
    onChange?.({ ...urls, [activeTab]: [...currentUrls, trimmed] })
    setUrlInput('')
  }, [urlInput, urls, activeTab, currentUrls, onChange])

  const handleUrlKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (e.key === 'Enter') { e.preventDefault(); handleUrlAdd() }
  }, [handleUrlAdd])

  const handleRemoveUrl = useCallback((url: string) => {
    onChange?.({ ...urls, [activeTab]: currentUrls.filter(u => u !== url) })
  }, [urls, activeTab, currentUrls, onChange])

  return (
    <div className="premium-section mb-4">
      <label className="premium-label mb-1 flex items-center gap-1.5">
        <ImagePlus className="w-3 h-3" />
        参考图片
      </label>

      <div className="flex gap-1 mb-2 flex-wrap premium-btn-group">
        {(Object.keys(TAB_LABELS) as RefTab[]).map(tab => (
          <button key={tab} onClick={() => setActiveTab(tab)}
            className={`${activeTab === tab ? 'active' : ''}`}>
            {TAB_LABELS[tab]}
            {urls[tab].length > 0 && <span className="ml-1 text-[9px] opacity-50">({urls[tab].length})</span>}
          </button>
        ))}
      </div>

      <div
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        className={`relative premium-upload rounded-xl p-3 ${dragOver ? 'bg-primary/10 !border-primary/40' : ''}`}
      >
        {currentUrls.length > 0 && (
          <div className="flex flex-wrap gap-2 mb-3">
            {currentUrls.map((url, i) => (
              <div key={i} className="relative group w-16 h-16">
                <img src={url} alt="" className="w-full h-full rounded object-cover" style={{ background: 'rgba(0,0,0,0.2)' }}
                  onError={e => { (e.target as HTMLImageElement).style.display = 'none' }} />
                <button onClick={() => handleRemoveUrl(url)}
                  className="absolute -top-1.5 -right-1.5 w-5 h-5 rounded-full bg-black/60 text-white flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity"
                  title="移除">
                  <X className="w-3 h-3" />
                </button>
              </div>
            ))}
          </div>
        )}

        <div className="flex items-center gap-2">
          <button onClick={() => fileInputRef.current?.click()} disabled={uploading}
            className="w-16 h-16 rounded-lg border border-dashed" style={{ borderColor: 'rgba(255,255,255,0.08)', color: 'rgba(167, 139, 250, 0.4)' }}>
            {uploading ? <Loader2 className="w-5 h-5 animate-spin" /> : <ImagePlus className="w-5 h-5" />}
          </button>
          <div className="flex-1 flex items-center gap-2">
            <Link className="w-3.5 h-3.5 text-muted-foreground flex-shrink-0" />
            <input value={urlInput} onChange={e => setUrlInput(e.target.value)} onKeyDown={handleUrlKeyDown}
              placeholder="粘贴图片 URL 按回车添加..."
              className="flex-1 bg-transparent border-b border-border/40 pb-1 text-xs text-foreground outline-none focus:border-border transition-colors" />
            <button onClick={handleUrlAdd} disabled={!urlInput.trim()}
              className="text-xs text-primary hover:underline disabled:opacity-30 flex-shrink-0">添加</button>
          </div>
        </div>
      </div>

      <button onClick={openHistory} type="button"
        className="mt-2 flex items-center gap-1.5 text-[10px] text-muted-foreground hover:text-primary transition-colors">
        <History className="w-3 h-3" />
        从历史作品选择
      </button>

      <input ref={fileInputRef} type="file" accept="image/*" multiple
        className="hidden" onChange={e => handleFileSelect(e.target.files)} />

      {showHistory && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm" onClick={() => setShowHistory(false)}>
          <div className="bg-background border border-border rounded-2xl p-5 max-w-lg w-full mx-4 max-h-[80vh] flex flex-col shadow-2xl" onClick={e => e.stopPropagation()}>
            <div className="flex items-center justify-between mb-3">
              <h3 className="font-semibold text-sm flex items-center gap-1.5">
                <ImageIcon className="w-4 h-4" />
                选择历史作品 → {TAB_LABELS[activeTab]}
              </h3>
              <button onClick={() => setShowHistory(false)} className="text-muted-foreground hover:text-foreground text-xs">✕</button>
            </div>
            {loadingHistory ? (
              <div className="flex items-center justify-center py-10">
                <Loader2 className="w-5 h-5 animate-spin text-muted-foreground" />
              </div>
            ) : historyImages.length === 0 ? (
              <p className="text-xs text-muted-foreground text-center py-10">暂无历史作品</p>
            ) : (
              <div className="grid grid-cols-3 sm:grid-cols-4 gap-2 overflow-y-auto max-h-64">
                {historyImages.map((img, i) => (
                  <div key={img.url} className="group relative cursor-pointer rounded-lg overflow-hidden border border-border/30 hover:border-primary/50 transition-colors"
                    onClick={() => {
                      if (!currentUrls.includes(img.url)) {
                        onChange?.({ ...urls, [activeTab]: [...currentUrls, img.url] })
                      }
                      setShowHistory(false)
                    }}>
                    <img src={img.url} alt="" className="w-full h-20 object-cover bg-muted" />
                    <div className="absolute inset-0 bg-black/0 group-hover:bg-primary/20 transition-all flex items-center justify-center opacity-0 group-hover:opacity-100">
                      <span className="text-[10px] text-white bg-black/60 px-2 py-0.5 rounded-full">选择</span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {dragOver && (
        <div className="absolute inset-0 rounded-xl bg-primary/10 border-2 border-primary border-dashed flex items-center justify-center pointer-events-none z-10">
          <span className="text-sm font-medium text-primary">释放以上传到 {TAB_LABELS[activeTab]}</span>
        </div>
      )}
    </div>
  )
}
