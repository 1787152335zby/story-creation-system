import { useState, useEffect, useRef, useCallback } from 'react'
import { Info, Sparkles, Loader2, Download, Trash2, X, History, Image as ImageIcon } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import ReferenceImageUploader from './ReferenceImageUploader'
import ModelSelector from './ModelSelector'
import { fetchGenerationHistory } from '../lib/api'
import type { ReferenceUrlsByType, FreeRefImage } from '../lib/types'

interface FreeImageGenFormProps {
  freePrompt: string
  freeNegative: string
  freeSize: string
  freeCount: number
  freeGenerating: boolean
  freeError: string
  freeResults: { url: string; local: string }[]
  resolutions: string[]
  ratioGroups: Record<string, string[]>
  selectedRatio: string
  freeModel: string
  referenceUrls: string[]
  presets: any[]
  selectedPreset: any | null
  onPromptChange: (v: string) => void
  onNegativeChange: (v: string) => void
  onSizeChange: (v: string) => void
  onCountChange: (v: number) => void
  onRatioChange: (v: string) => void
  onModelChange: (v: string) => void
  onReferenceUrlsChange: (urls: string[]) => void
  referenceUrlsByType: ReferenceUrlsByType
  onReferenceUrlsByTypeChange?: (urls: ReferenceUrlsByType) => void
  currentTaskId: string | null
  onCancel: () => void
  onPresetSelect: (preset: any | null) => void
  onGenerate: () => void
  onClearResults: () => void
  onPreview?: (src: string) => void
  onFreeRefImagesChange?: (images: FreeRefImage[]) => void
  modelCap?: { max_ref_images: number; supports_img2img: boolean }
}

export default function FreeImageGenForm({
  freePrompt, freeNegative, freeSize, freeCount, freeGenerating, freeError, freeResults,
  resolutions, ratioGroups, selectedRatio, freeModel, referenceUrls,
  presets, selectedPreset,
  currentTaskId, onCancel,
  onPromptChange, onNegativeChange, onSizeChange, onCountChange,
  onRatioChange, onModelChange, onReferenceUrlsChange, onReferenceUrlsByTypeChange,
  referenceUrlsByType, onPresetSelect, onGenerate, onClearResults, onPreview,
  onFreeRefImagesChange, modelCap,
}: FreeImageGenFormProps) {
  const promptRef = useRef<HTMLTextAreaElement>(null)
  const [freeRefImages, setFreeRefImages] = useState<FreeRefImage[]>([])
  const fileInputRef2 = useRef<HTMLInputElement>(null)
  const [showRefHistory, setShowRefHistory] = useState(false)
  const [refHistoryImages, setRefHistoryImages] = useState<{ name: string; url: string }[]>([])
  const [refHistoryLoading, setRefHistoryLoading] = useState(false)

  const openRefHistory = useCallback(async () => {
    setShowRefHistory(true)
    setRefHistoryLoading(true)
    try {
      const h = await fetchGenerationHistory()
      const all = [...(h.images_free || []), ...(h.images_project || [])]
      setRefHistoryImages(all)
    } catch {
    } finally {
      setRefHistoryLoading(false)
    }
  }, [])

  useEffect(() => {
    if (promptRef.current) {
      promptRef.current.style.height = 'auto'
      promptRef.current.style.height = promptRef.current.scrollHeight + 'px'
    }
  }, [freePrompt])
  const navigate = useNavigate()
  const [elapsed, setElapsed] = useState(0)

  useEffect(() => {
    onFreeRefImagesChange?.(freeRefImages)
  }, [freeRefImages, onFreeRefImagesChange])
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null)

  useEffect(() => {
    if (freeGenerating) {
      setElapsed(0)
      const start = Date.now()
      timerRef.current = setInterval(() => {
        setElapsed(Math.floor((Date.now() - start) / 1000))
      }, 1000)
    } else {
      if (timerRef.current) {
        clearInterval(timerRef.current)
        timerRef.current = null
      }
    }
    return () => {
      if (timerRef.current) clearInterval(timerRef.current)
    }
  }, [freeGenerating])

  return (
    <>
      <div className="premium-panel p-6 mb-6">
        <div className="premium-header">
          <label className="premium-label" style={{ marginBottom: 0 }}>描述画面</label>
        </div>
        <textarea ref={promptRef} value={freePrompt} onChange={e => onPromptChange(e.target.value)} placeholder="一只优雅的白猫坐在月光下的窗台上，周围是盛开的樱花，赛博朋克风格，4K..."
          className="w-full premium-input rounded-xl px-4 py-3 min-h-[7rem] resize-none text-sm mb-4 premium-glow-bottom" />

        {/* 模式1：自由底图上传 */}
        {modelCap?.supports_img2img !== false && (
        <div className="premium-section-refmode mb-4">
          <div className="refmode-label">
            <span>🖼️ 参考图生图 — 底图上传</span>
            <span className="refmode-badge">模式1</span>
          </div>
          <p className="refmode-desc">上传原始底图，可同时上传多张。提示词中用 @图1/@图2 引用</p>

          <div className="refmode-grid">
            {freeRefImages.map((img, idx) => (
              <div key={img.id} className="refmode-thumb" style={{ borderColor: idx === 0 ? '#10b981' : undefined }}>
                <img src={img.url} alt="" style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
                <div style={{ position: 'absolute', top: '4px', left: '4px', fontSize: '9px', background: '#10b981', color: 'black', padding: '1px 6px', borderRadius: '4px', fontWeight: 700 }}>{img.label}</div>
                <button
                  onClick={() => setFreeRefImages(prev => prev.filter(r => r.id !== img.id).map((r, i) => ({ ...r, label: `图${i + 1}` })))}
                  style={{ position: 'absolute', top: '4px', right: '4px', width: '16px', height: '16px', borderRadius: '50%', background: 'rgba(0,0,0,0.6)', display: 'flex', alignItems: 'center', justifyContent: 'center', cursor: 'pointer', border: 'none', color: 'white', fontSize: '8px' }}>
                  ✕
                </button>
              </div>
            ))}
            <div
              onClick={() => fileInputRef2.current?.click()}
              onDrop={(e) => {
                e.preventDefault()
                const files = Array.from(e.dataTransfer.files)
                files.forEach(file => {
                  const url = URL.createObjectURL(file)
                  setFreeRefImages(prev => [...prev, { id: crypto.randomUUID(), url, label: `图${prev.length + 1}`, file }])
                })
              }}
              onDragOver={(e) => e.preventDefault()}
              className="refmode-add">
              <div style={{ fontSize: '22px', color: 'rgba(16,185,129,0.5)' }}>+</div>
              <div style={{ fontSize: '9px', color: 'rgba(16,185,129,0.5)' }}>拖入上传</div>
            </div>
            <input ref={fileInputRef2} type="file" accept="image/*" multiple
              style={{ display: 'none' }}
              onChange={(e) => {
                const files = Array.from(e.target.files || [])
                files.forEach(file => {
                  const url = URL.createObjectURL(file)
                  setFreeRefImages(prev => [...prev, { id: crypto.randomUUID(), url, label: `图${prev.length + 1}`, file }])
                })
                e.target.value = ''
              }} />
          </div>

          {freeRefImages.length > 0 && (
            <div className="refmode-at-bar">
              <span style={{ color: 'rgba(255,255,255,0.3)' }}>@引用：点击插入提示词</span>
              {freeRefImages.map(img => (
                <span key={img.id}
                  onClick={() => { onPromptChange(freePrompt + ` @${img.label} `) }}
                  style={{ display: 'inline-block', background: 'rgba(16,185,129,0.15)', color: '#10b981', padding: '2px 8px', borderRadius: '4px', cursor: 'pointer', fontWeight: 600, userSelect: 'none' }}>
                  @{img.label}
                </span>
              ))}
            </div>
          )}

          <button onClick={openRefHistory} type="button"
            className="mt-2 flex items-center gap-1.5 text-[10px] text-muted-foreground hover:text-primary transition-colors">
            <History className="w-3 h-3" /> 从历史作品选择
          </button>
        </div>
        )}

        {showRefHistory && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm" onClick={() => setShowRefHistory(false)}>
            <div className="bg-background border border-border rounded-2xl p-5 max-w-lg w-full mx-4 max-h-[80vh] flex flex-col shadow-2xl" onClick={e => e.stopPropagation()}>
              <div className="flex items-center justify-between mb-3">
                <h3 className="font-semibold text-sm flex items-center gap-1.5">
                  <ImageIcon className="w-4 h-4" />
                  选择历史作品 → 加入底图
                </h3>
                <button onClick={() => setShowRefHistory(false)} className="text-muted-foreground hover:text-foreground text-xs">✕</button>
              </div>
              {refHistoryLoading ? (
                <div className="flex items-center justify-center py-10">
                  <Loader2 className="w-5 h-5 animate-spin text-muted-foreground" />
                </div>
              ) : refHistoryImages.length === 0 ? (
                <p className="text-xs text-muted-foreground text-center py-10">暂无历史作品</p>
              ) : (
                <div className="grid grid-cols-3 sm:grid-cols-4 gap-2 overflow-y-auto max-h-64">
                  {refHistoryImages.map((img) => (
                    <div key={img.url} className="group relative cursor-pointer rounded-lg overflow-hidden border border-border/30 hover:border-green-500/50 transition-colors"
                      onClick={() => {
                        if (!freeRefImages.some(r => r.url === img.url)) {
                          setFreeRefImages(prev => [...prev, { id: crypto.randomUUID(), url: img.url, label: `图${prev.length + 1}` }])
                        }
                        setShowRefHistory(false)
                      }}>
                      <img src={img.url} alt="" className="w-full h-20 object-cover bg-muted" />
                      <div className="absolute inset-0 bg-black/0 group-hover:bg-green-500/20 transition-all flex items-center justify-center opacity-0 group-hover:opacity-100">
                        <span className="text-[10px] text-white bg-black/60 px-2 py-0.5 rounded-full">选择</span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}

        <ReferenceImageUploader urls={referenceUrlsByType} onChange={(v) => {
          onReferenceUrlsByTypeChange?.(v)
          onReferenceUrlsChange([...v.character, ...v.scene, ...v.prop])
        }} />

        {presets.length > 0 && (
          <div className="mb-4">
            <label className="premium-label">🎨 风格预设</label>
            <div className="premium-btn-group">
              <button onClick={() => onPresetSelect(null)}
                className={!selectedPreset ? 'active' : ''}>
                无
              </button>
              {presets.map((p: any) => (
                <button key={p.id} onClick={() => onPresetSelect(p)}
                  className={selectedPreset?.id === p.id ? 'active' : ''}
                  title={p.description}>
                  {p.name}
                </button>
              ))}
            </div>
          </div>
        )}

        <div className="grid grid-cols-3 gap-4 mb-4">
            <div>
              <label className="premium-label">模型</label>
              <ModelSelector type="image" value={freeModel} onChange={onModelChange} />
            </div>
            <div>
              <label className="premium-label">比例</label>
              <select value={selectedRatio} onChange={e => { onRatioChange(e.target.value); const rs = ratioGroups[e.target.value]; if (rs && rs.length > 0) onSizeChange(rs[0]) }}
                className="w-full premium-select rounded-xl px-3 py-2.5 text-sm">
                {Object.keys(ratioGroups).map(r => (<option key={r} value={r}>{r}</option>))}
              </select>
            </div>
            <div>
              <label className="premium-label">尺寸</label>
              <select value={freeSize} onChange={e => onSizeChange(e.target.value)} className="w-full premium-select rounded-xl px-3 py-2.5 text-sm">
                {(ratioGroups[selectedRatio] || resolutions).map(r => (<option key={r} value={r}>{r}</option>))}
              </select>
            </div>
            <div>
              <label className="premium-label">数量</label>
              <select value={freeCount} onChange={e => onCountChange(Number(e.target.value))} className="w-full premium-select rounded-xl px-3 py-2.5 text-sm">
                <option value={1}>1 张</option>
                <option value={2}>2 张</option>
                <option value={4}>4 张</option>
              </select>
            </div>
          </div>
        {freeGenerating ? (
          <div className="flex gap-2">
            <button disabled className="btn-gradient flex items-center gap-2 px-6 py-3 rounded-xl text-sm font-medium opacity-50 cursor-not-allowed">
              <Loader2 className="w-4 h-4 animate-spin" />
              生成中{elapsed > 0 ? ` (${elapsed}s)` : '...'}
            </button>
            {currentTaskId && (
              <button onClick={onCancel}
                className="flex items-center gap-1.5 px-4 py-3 rounded-xl border border-red-400/30 text-red-400 text-sm hover:bg-red-500/10 transition-colors">
                <X className="w-4 h-4" /> 取消
              </button>
            )}
          </div>
        ) : (
          <button onClick={onGenerate} disabled={!freePrompt.trim()}
            className="btn-gradient flex items-center gap-2 px-6 py-3 rounded-xl text-sm font-medium disabled:opacity-50">
            <Sparkles className="w-4 h-4" /> 生成
          </button>
        )}
        {freeError && (
          <div className="mt-3 p-3 rounded-xl bg-red-400/10 border border-red-400/20 text-xs text-red-400 flex items-start gap-2">
            <Info className="w-3.5 h-3.5 flex-shrink-0 mt-0.5" />
            <div className="flex-1">
              <span>{freeError}</span>
              {freeError.toLowerCase().includes('api key') && (
                <button onClick={() => navigate('/settings')} className="ml-2 underline hover:text-red-300">去设置</button>
              )}
            </div>
          </div>
        )}
      </div>
      {freeResults.length > 0 && (
        <div className="premium-panel p-5 mt-6">
          <div className="premium-header">
            <h3 className="font-semibold text-sm">生成结果</h3>
            <button onClick={onClearResults} className="text-xs text-muted-foreground hover:text-red-400 flex items-center gap-1">
              <Trash2 className="w-3 h-3" /> 清空
            </button>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
            {freeResults.map((img, i) => {
              const src = img.local ? `/generated/${img.local.split('\\').pop() || img.local.split('/').pop()}` : img.url
              return (
                <div key={src} className="premium-grid-item" onClick={() => onPreview?.(src)}>
                  <img src={src} alt="" className="w-full h-56 object-contain bg-white img-hover" />
                  <div className="absolute inset-0 bg-black/0 group-hover:bg-black/40 transition-all flex items-center justify-center gap-2 opacity-0 group-hover:opacity-100 pointer-events-none" onClick={e => e.stopPropagation()}>
                    <button onClick={(e) => { e.stopPropagation(); if (!referenceUrlsByType.character.includes(src)) onReferenceUrlsByTypeChange?.({ ...referenceUrlsByType, character: [...referenceUrlsByType.character, src] }) }}
                      className="p-2 rounded-lg bg-primary/60 hover:bg-primary text-white pointer-events-auto text-[10px]" title="用作参考图">
                      参考
                    </button>
                    <a href={src} download={img.local?.split('\\').pop()?.split('/').pop() || 'image'} className="p-2 rounded-lg bg-white/20 hover:bg-white/30 text-white pointer-events-auto" title="下载"><Download className="w-4 h-4" /></a>
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      )}
    </>
  )
}