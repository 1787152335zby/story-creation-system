import { useState, useEffect, useRef } from 'react'
import { Sparkles, Loader2, Upload, X, Download, Play } from 'lucide-react'
import ModelSelector from './ModelSelector'
import { fetchVideoResolutions, freeVideoGen, fetchProjectVisualAssets } from '../lib/api'

interface Props {
  projectName: string
}

export default function FreeVideoPanel({ projectName }: Props) {
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [freePrompt, setFreePrompt] = useState('')
  const [freeFiles, setFreeFiles] = useState<{ file: File; preview: string }[]>([])
  const [videoModel, setVideoModel] = useState('')
  const [resolutions, setResolutions] = useState<string[]>([])
  const [ratioGroups, setRatioGroups] = useState<Record<string, string[]>>({})
  const [selectedRatio, setSelectedRatio] = useState('')
  const [freeResolution, setFreeResolution] = useState('')
  const [generateAudio, setGenerateAudio] = useState(false)
  const [generating, setGenerating] = useState(false)
  const [result, setResult] = useState<{ video_url?: string; local?: string; error?: string } | null>(null)
  const [elapsed, setElapsed] = useState(0)
  const [refProjectImages, setRefProjectImages] = useState<{ characters: Record<string, { name: string; url: string }[]>; scenes: Record<string, { name: string; url: string }[]> }>({ characters: {}, scenes: {} })

  useEffect(() => {
    fetchVideoResolutions().then(r => {
      setResolutions(r.resolutions)
      setRatioGroups(r.groups)
      const ratios = Object.keys(r.groups)
      const first = ratios.includes('16:9') ? '16:9' : (ratios[0] || '')
      setSelectedRatio(first)
      setFreeResolution(r.resolutions[0] || '1280x720')
    })
    if (projectName) {
      fetchProjectVisualAssets(projectName).then(setRefProjectImages)
    }
  }, [projectName])

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFiles = Array.from(e.target.files || [])
    const entries = selectedFiles.map(file => ({
      file,
      preview: URL.createObjectURL(file),
    }))
    setFreeFiles(prev => [...prev, ...entries])
  }

  const removeFile = (i: number) => {
    setFreeFiles(prev => prev.filter((_, idx) => idx !== i))
  }

  const handleGenerate = async () => {
    if (!freePrompt.trim()) return
    setGenerating(true)
    setResult(null)
    setElapsed(0)
    const startTime = Date.now()
    const timer = setInterval(() => setElapsed(Math.floor((Date.now() - startTime) / 1000)), 1000)
    try {
      const files = freeFiles.length > 0 ? freeFiles.map(f => f.file) : undefined
      const res = await freeVideoGen(freePrompt, files, videoModel, freeResolution || undefined, undefined, generateAudio)
      setResult(res)
    } catch (e: any) {
      setResult({ error: e.message })
    }
    clearInterval(timer)
    setGenerating(false)
  }

  return (
    <div className="glass-card rounded-2xl p-6">
      <h3 className="text-sm font-semibold mb-4 flex items-center gap-2">
        <Sparkles className="w-4 h-4" style={{ color: 'hsl(252, 87%, 67%)' }} />
        自由创作视频
      </h3>

      {/* Reference images */}
      <label className="text-xs font-medium text-muted-foreground uppercase tracking-wider mb-2 block">参考图片</label>
      <div className="border-2 border-dashed border-border rounded-xl p-4 text-center cursor-pointer hover:border-primary/50 transition-colors mb-3"
        onClick={() => fileInputRef.current?.click()}>
        <Upload className="w-6 h-6 mx-auto mb-1 text-muted-foreground" />
        <p className="text-xs text-muted-foreground">上传参考图片（可选，不传则为文生视频）</p>
        <input ref={fileInputRef} type="file" accept="image/*" multiple className="hidden" onChange={handleFileSelect} />
      </div>

      {freeFiles.length > 0 && (
        <div className="flex flex-wrap gap-2 mb-3">
          {freeFiles.map((entry, i) => (
            <div key={i} className="relative group">
              <img src={entry.preview} alt="" className="w-16 h-16 object-cover rounded-lg" />
              <button onClick={() => removeFile(i)}
                className="absolute -top-1.5 -right-1.5 w-5 h-5 rounded-full bg-red-500 text-white flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity shadow-lg">
                <X className="w-3 h-3" />
              </button>
            </div>
          ))}
        </div>
      )}

      {/* Project reference gallery */}
      {(Object.keys(refProjectImages.characters).length > 0 || Object.keys(refProjectImages.scenes).length > 0) && (
        <div className="mb-3 p-3 rounded-xl bg-muted/50">
          <p className="text-[10px] text-muted-foreground mb-2 font-medium">📂 项目素材（点击添加到参考）</p>
          {Object.keys(refProjectImages.characters).length > 0 && (
            <div className="mb-2">
              <p className="text-[10px] text-muted-foreground mb-1">👤 角色</p>
              <div className="flex flex-wrap gap-1.5">
                {Object.entries(refProjectImages.characters).map(([name, imgs]) =>
                  (imgs as any[]).slice(0, 3).map((img, i) => (
                    <img key={`${name}-${i}`} src={img.url} alt={name}
                      className="w-12 h-12 object-contain rounded-lg bg-muted border border-border cursor-pointer hover:ring-2 hover:ring-primary/50 transition-all"
                      onClick={() => {
                        fetch(img.url).then(r => r.blob()).then(blob => {
                          const file = new File([blob], `${name}.png`, { type: 'image/png' })
                          const reader = new FileReader()
                          reader.onload = (ev) => setFreeFiles(prev => [...prev, { file, preview: ev.target?.result as string }])
                          reader.readAsDataURL(blob)
                        })
                      }} title={name} />
                  ))
                )}
              </div>
            </div>
          )}
          {Object.keys(refProjectImages.scenes).length > 0 && (
            <div>
              <p className="text-[10px] text-muted-foreground mb-1">🌆 场景</p>
              <div className="flex flex-wrap gap-1.5">
                {Object.entries(refProjectImages.scenes).map(([name, imgs]) =>
                  (imgs as any[]).slice(0, 3).map((img, i) => (
                    <img key={`${name}-${i}`} src={img.url} alt={name}
                      className="w-12 h-12 object-contain rounded-lg bg-muted border border-border cursor-pointer hover:ring-2 hover:ring-primary/50 transition-all"
                      onClick={() => {
                        fetch(img.url).then(r => r.blob()).then(blob => {
                          const file = new File([blob], `${name}.png`, { type: 'image/png' })
                          const reader = new FileReader()
                          reader.onload = (ev) => setFreeFiles(prev => [...prev, { file, preview: ev.target?.result as string }])
                          reader.readAsDataURL(blob)
                        })
                      }} title={name} />
                  ))
                )}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Prompt */}
      <label className="text-xs font-medium text-muted-foreground uppercase tracking-wider mb-2 block">动作描述</label>
      <textarea value={freePrompt} onChange={e => setFreePrompt(e.target.value)}
        placeholder="例如：角色缓缓转身，风吹动衣角，背景的云层在流动..."
        className="w-full bg-muted border border-border rounded-xl px-4 py-3 h-24 resize-none text-sm mb-4" />

      {/* Parameters */}
      <div className="grid grid-cols-4 gap-3 mb-3">
        <div>
          <label className="text-[10px] text-muted-foreground block mb-1">模型</label>
          <ModelSelector type="video" value={videoModel} onChange={setVideoModel} />
        </div>
        <div>
          <label className="text-[10px] text-muted-foreground block mb-1">比例</label>
          <select value={selectedRatio} onChange={e => { const rs = ratioGroups[e.target.value]; setSelectedRatio(e.target.value); if (rs?.length) setFreeResolution(rs[0]) }}
            className="w-full bg-muted border border-border rounded-xl px-2 py-2 text-xs">
            {Object.keys(ratioGroups).map(r => (<option key={r} value={r}>{r}</option>))}
          </select>
        </div>
        <div>
          <label className="text-[10px] text-muted-foreground block mb-1">分辨率</label>
          <select value={freeResolution} onChange={e => setFreeResolution(e.target.value)} className="w-full bg-muted border border-border rounded-xl px-2 py-2 text-xs">
            {(ratioGroups[selectedRatio] || resolutions).map(r => (<option key={r} value={r}>{r}</option>))}
          </select>
        </div>
        <div className="flex items-end pb-1">
          <label className="relative inline-flex items-center cursor-pointer">
            <input type="checkbox" className="sr-only peer" checked={generateAudio} onChange={e => setGenerateAudio(e.target.checked)} />
            <div className="w-8 h-4 bg-muted rounded-full peer peer-checked:after:translate-x-full after:content-[''] after:absolute after:top-[1px] after:left-[1px] after:bg-white after:rounded-full after:h-3.5 after:w-3.5 after:transition-all peer-checked:bg-primary"></div>
            <span className="text-[10px] text-muted-foreground ml-2">音频</span>
          </label>
        </div>
      </div>

      <button onClick={handleGenerate} disabled={generating || !freePrompt.trim()}
        className="btn-gradient flex items-center gap-1.5 px-5 py-2.5 rounded-xl text-sm font-medium disabled:opacity-50">
        {generating ? <Loader2 className="w-4 h-4 animate-spin" /> : <Sparkles className="w-4 h-4" />}
        {generating ? `生成中 ${elapsed}s` : '生成视频'}
      </button>

      {result && (
        <div className="mt-4 p-3 rounded-xl bg-muted/50">
          {result.error ? (
            <p className="text-red-400 text-xs">❌ {result.error}</p>
          ) : (
            <div>
              <video src={result.video_url} controls className="w-full max-w-md rounded-xl" style={{ maxHeight: '300px' }} />
              <div className="flex gap-2 mt-2">
                <a href={result.video_url} target="_blank" rel="noopener noreferrer"
                  className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg border border-border text-xs hover:bg-muted transition-colors">
                  <Download className="w-3 h-3" /> 下载
                </a>
                <a href={result.video_url} target="_blank" rel="noopener noreferrer"
                  className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg border border-border text-xs hover:bg-muted transition-colors">
                  <Play className="w-3 h-3" /> 新标签页打开
                </a>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
