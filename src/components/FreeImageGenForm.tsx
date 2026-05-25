import { useState, useEffect, useRef } from 'react'
import { Info, Sparkles, Loader2, Download, Trash2, X } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import ReferenceImageUploader from './ReferenceImageUploader'
import ModelSelector from './ModelSelector'
import type { ReferenceUrlsByType } from '../lib/types'

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
}

export default function FreeImageGenForm({
  freePrompt, freeNegative, freeSize, freeCount, freeGenerating, freeError, freeResults,
  resolutions, ratioGroups, selectedRatio, freeModel, referenceUrls,
  presets, selectedPreset,
  currentTaskId, onCancel,
  onPromptChange, onNegativeChange, onSizeChange, onCountChange,
  onRatioChange, onModelChange, onReferenceUrlsChange, onReferenceUrlsByTypeChange,
  referenceUrlsByType, onPresetSelect, onGenerate, onClearResults, onPreview,
}: FreeImageGenFormProps) {
  const promptRef = useRef<HTMLTextAreaElement>(null)

  useEffect(() => {
    if (promptRef.current) {
      promptRef.current.style.height = 'auto'
      promptRef.current.style.height = promptRef.current.scrollHeight + 'px'
    }
  }, [freePrompt])
  const navigate = useNavigate()
  const [elapsed, setElapsed] = useState(0)
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
      <div className="glass-card card-glow rounded-2xl p-6 mb-6">
        <label className="text-xs font-medium text-muted-foreground uppercase tracking-wider mb-2 block">描述画面</label>
        <textarea ref={promptRef} value={freePrompt} onChange={e => onPromptChange(e.target.value)} placeholder="一只优雅的白猫坐在月光下的窗台上，周围是盛开的樱花，赛博朋克风格，4K..."
          className="w-full bg-muted border border-border rounded-xl px-4 py-3 min-h-[7rem] resize-none text-sm mb-4" />

        <ReferenceImageUploader urls={referenceUrlsByType} onChange={(v) => {
          onReferenceUrlsByTypeChange?.(v)
          onReferenceUrlsChange([...v.character, ...v.scene, ...v.prop])
        }} />

        {presets.length > 0 && (
          <div className="mb-4">
            <label className="text-xs font-medium text-muted-foreground uppercase tracking-wider mb-2 block">🎨 风格预设</label>
            <div className="flex flex-wrap gap-1.5">
              <button onClick={() => onPresetSelect(null)}
                className={`px-3 py-1.5 rounded-lg text-[10px] border transition-all ${
                  !selectedPreset ? 'bg-primary/20 text-primary border-primary/40' : 'bg-muted text-muted-foreground border-border/50 hover:border-primary/30'
                }`}>
                无
              </button>
              {presets.map((p: any) => (
                <button key={p.id} onClick={() => onPresetSelect(p)}
                  className={`px-3 py-1.5 rounded-lg text-[10px] border transition-all ${
                    selectedPreset?.id === p.id ? 'bg-primary/20 text-primary border-primary/40' : 'bg-muted text-muted-foreground border-border/50 hover:border-primary/30'
                  }`}
                  title={p.description}>
                  {p.name}
                </button>
              ))}
            </div>
          </div>
        )}

        <div className="grid grid-cols-3 gap-4 mb-4">
          <div>
            <label className="text-xs text-muted-foreground block mb-1">模型</label>
            <ModelSelector type="image" value={freeModel} onChange={onModelChange} />
          </div>
          <div>
            <label className="text-xs text-muted-foreground block mb-1">比例</label>
            <select value={selectedRatio} onChange={e => { onRatioChange(e.target.value); const rs = ratioGroups[e.target.value]; if (rs && rs.length > 0) onSizeChange(rs[0]) }}
              className="w-full bg-muted border border-border rounded-xl px-3 py-2.5 text-sm">
              {Object.keys(ratioGroups).map(r => (<option key={r} value={r}>{r}</option>))}
            </select>
          </div>
          <div>
            <label className="text-xs text-muted-foreground block mb-1">尺寸</label>
            <select value={freeSize} onChange={e => onSizeChange(e.target.value)} className="w-full bg-muted border border-border rounded-xl px-3 py-2.5 text-sm">
              {(ratioGroups[selectedRatio] || resolutions).map(r => (<option key={r} value={r}>{r}</option>))}
            </select>
          </div>
          <div>
            <label className="text-xs text-muted-foreground block mb-1">数量</label>
            <select value={freeCount} onChange={e => onCountChange(Number(e.target.value))} className="w-full bg-muted border border-border rounded-xl px-3 py-2.5 text-sm">
              <option value={1}>1 张</option>
              <option value={2}>2 张</option>
              <option value={4}>4 张</option>
            </select>
          </div>
          <div>
            <label className="text-xs text-muted-foreground block mb-1">负面提示</label>
            <input value={freeNegative} onChange={e => onNegativeChange(e.target.value)} placeholder="如: 模糊"
              className="w-full bg-muted border border-border rounded-xl px-3 py-2.5 text-sm" />
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
        <div className="glass-card card-glow rounded-2xl p-5">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-semibold text-sm">生成结果</h3>
            <button onClick={onClearResults} className="text-xs text-muted-foreground hover:text-red-400 flex items-center gap-1">
              <Trash2 className="w-3 h-3" /> 清空
            </button>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
            {freeResults.map((img, i) => {
              const src = img.local ? `/generated/${img.local.split('\\').pop() || img.local.split('/').pop()}` : img.url
              return (
                <div key={src} className="bg-muted rounded-xl overflow-hidden group relative cursor-pointer" onClick={() => onPreview?.(src)}>
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