import { useState, useEffect, useRef } from 'react'
import { Sparkles, Loader2, Upload, X, Download, Play, CheckSquare, Square, RefreshCw, ChevronDown, ChevronRight } from 'lucide-react'
import ModelSelector from './ModelSelector'
import ImagePreview from './ImagePreview'
import { fetchVideoResolutions, freeVideoGen, fetchProjectVisualAssets, fetchCharacters, fetchScenes, fetchPhaseContent, fetchConfirmedImages } from '../lib/api'

interface ExtractedShot {
  index: number
  act: string
  scene: string
  prompt: string
}

interface Props {
  projectName: string
}

export default function VideoProjectPanel({ projectName }: Props) {
  const fileInputRef = useRef<HTMLInputElement>(null)

  // Project data
  const [characters, setCharacters] = useState<any[]>([])
  const [scenes, setScenes] = useState<any[]>([])
  const [shots, setShots] = useState<ExtractedShot[]>([])
  const [loading, setLoading] = useState(false)
  const [extracting, setExtracting] = useState(false)
  const [extractLog, setExtractLog] = useState('')
  const [extractedOnce, setExtractedOnce] = useState(false)

  // Selection
  const [selectedCharNames, setSelectedCharNames] = useState<string[]>([])
  const [selectedSceneNames, setSelectedSceneNames] = useState<string[]>([])
  const [selectedShotIndices, setSelectedShotIndices] = useState<number[]>([])

  // Generate mode
  const [genMode, setGenMode] = useState<'single' | 'batch'>('single')
  const [batchStart, setBatchStart] = useState(1)
  const [batchEnd, setBatchEnd] = useState(10)

  // Prompt
  const [prompt, setPrompt] = useState('')

  // Reference images
  const [refFiles, setRefFiles] = useState<{ file: File; preview: string }[]>([])
  const [projectImages, setProjectImages] = useState<{ characters: Record<string, { name: string; url: string }[]>; scenes: Record<string, { name: string; url: string }[]> }>({ characters: {}, scenes: {} })
  const [confirmedImages, setConfirmedImages] = useState<{ characters: Record<string, { name: string; url: string }[]>; scenes: Record<string, { name: string; url: string }[]> }>({ characters: {}, scenes: {} })
  const [previewSrc, setPreviewSrc] = useState<string | null>(null)

  // Parameters
  const [videoModel, setVideoModel] = useState('')
  const [resolutions, setResolutions] = useState<string[]>([])
  const [ratioGroups, setRatioGroups] = useState<Record<string, string[]>>({})
  const [selectedRatio, setSelectedRatio] = useState('')
  const [videoResolution, setVideoResolution] = useState('')
  const [duration, setDuration] = useState(5)
  const [generateAudio, setGenerateAudio] = useState(false)

  // Generation
  const [generating, setGenerating] = useState(false)
  const [result, setResult] = useState<{ video_url?: string; local?: string; error?: string } | null>(null)
  const [elapsed, setElapsed] = useState(0)
  const [batchResults, setBatchResults] = useState<string[]>([])
  const [batchProgress, setBatchProgress] = useState('')

  // Shots expanded state
  const [expandedActs, setExpandedActs] = useState<Record<string, boolean>>({})

  useEffect(() => {
    fetchVideoResolutions().then(r => {
      setResolutions(r.resolutions)
      setRatioGroups(r.groups)
      const ratios = Object.keys(r.groups)
      const first = ratios.includes('16:9') ? '16:9' : (ratios[0] || '')
      setSelectedRatio(first)
      setVideoResolution(r.resolutions[0] || '1280x720')
    })
  }, [])

  useEffect(() => {
    if (!projectName) return
    setLoading(true)
    Promise.all([
      fetchCharacters(projectName).then(setCharacters),
      fetchScenes(projectName).then(setScenes),
      loadShots(projectName),
      fetchProjectVisualAssets(projectName).then(setProjectImages),
      fetchConfirmedImages(projectName).then(setConfirmedImages),
    ]).finally(() => setLoading(false))
  }, [projectName])

  const loadShots = async (name: string) => {
    try {
      const c = await fetchPhaseContent(name, '06_提示词/分镜提示词.md')
      const text = c?.content || ''
      if (!text) { setShots([]); return }

      const extracted: ExtractedShot[] = []
      let currentAct = '全部'
      const actRegex = /^#{1,2}\s+(第[^场\n]+?)(?:\s*分镜提示词)?\s*$/m
      const shotHeaderRegex = /^###\s+(镜头\d+)/m
      const lines = text.split('\n')
      let currentBlock: string[] = []
      let inShot = false

      for (let i = 0; i < lines.length; i++) {
        const line = lines[i]
        const actMatch = line.match(actRegex)
        if (actMatch) { currentAct = actMatch[1].trim(); continue }
        const shotMatch = line.match(shotHeaderRegex)
        if (shotMatch) {
          if (inShot && currentBlock.length > 0) {
            extracted.push({ index: extracted.length + 1, act: currentAct, scene: shotMatch[1], prompt: currentBlock.join('\n').trim() })
          }
          currentBlock = [line]; inShot = true; continue
        }
        if (inShot) {
          if (line.trim() === '---') {
            if (currentBlock.length > 0) extracted.push({ index: extracted.length + 1, act: currentAct, scene: '', prompt: currentBlock.join('\n').trim() })
            currentBlock = []; inShot = false
          } else { currentBlock.push(line) }
        }
      }
      if (inShot && currentBlock.length > 0) extracted.push({ index: extracted.length + 1, act: currentAct, scene: '', prompt: currentBlock.join('\n').trim() })
      setShots(extracted)
    } catch { setShots([]) }
  }

  const handleExtract = async () => {
    setExtracting(true)
    setExtractLog('⏳ 正在提取角色/场景...')
    try {
      const start = Date.now()
      const res = await fetch(`/api/projects/${encodeURIComponent(projectName)}/visual-extract`, { method: 'POST' })
      if (!res.ok) throw new Error('提取失败')
      const [chars, scns] = await Promise.all([
        fetchCharacters(projectName),
        fetchScenes(projectName),
      ])
      setCharacters(chars)
      setScenes(scns)
      await loadShots(projectName)
      setExtractedOnce(true)
      setExtractLog(`✅ 提取完成：${chars.length} 个角色，${scns.length} 个场景（用时 ${Math.round((Date.now() - start) / 1000)} 秒）`)
    } catch (e: any) {
      setExtractLog(`❌ 提取失败：${e.message}`)
    }
    setExtracting(false)
  }

  const handleConfirm = async () => {
    await fetch(`/api/projects/${encodeURIComponent(projectName)}/visual-extract/confirm`, { method: 'POST' })
    setExtractLog('✅ 已确认')
  }

  // Auto-generate prompt when selection changes
  useEffect(() => {
    if (selectedCharNames.length === 0 && selectedSceneNames.length === 0 && selectedShotIndices.length === 0) return
    const timer = setTimeout(async () => {
      const parts: string[] = []
      const selectedShots = shots.filter(s => selectedShotIndices.includes(s.index))
      for (const s of selectedShots) {
        parts.push(`### ${s.act} ${s.scene || '镜头'+s.index}\n${s.prompt}`)
      }
      if (selectedCharNames.length > 0) {
        parts.push(`角色：${selectedCharNames.join('、')}`)
      }
      if (selectedSceneNames.length > 0) {
        parts.push(`场景：${selectedSceneNames.join('、')}`)
      }
      setPrompt(parts.join('\n\n---\n\n'))
    }, 300)
    return () => clearTimeout(timer)
  }, [selectedCharNames, selectedSceneNames, selectedShotIndices, shots])

  // File handling
  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selected = Array.from(e.target.files || [])
    for (const file of selected) {
      const reader = new FileReader()
      reader.onload = (ev) => setRefFiles(prev => [...prev, { file, preview: ev.target?.result as string }])
      reader.readAsDataURL(file)
    }
  }

  const removeFile = (i: number) => setRefFiles(prev => prev.filter((_, idx) => idx !== i))

  // Add project image as reference
  const addProjectImage = async (url: string, name: string) => {
    try {
      const resp = await fetch(url)
      const blob = await resp.blob()
      const file = new File([blob], `${name}.png`, { type: 'image/png' })
      const reader = new FileReader()
      reader.onload = (ev) => setRefFiles(prev => [...prev, { file, preview: ev.target?.result as string }])
      reader.readAsDataURL(file)
    } catch {}
  }

  // Single generate
  const handleGenerate = async () => {
    if (!prompt.trim()) return
    setGenerating(true)
    setResult(null)
    setElapsed(0)
    const startTime = Date.now()
    const timer = setInterval(() => setElapsed(Math.floor((Date.now() - startTime) / 1000)), 1000)
    try {
      const files = refFiles.length > 0 ? refFiles.map(f => f.file) : undefined
      const res = await freeVideoGen(prompt, files, videoModel, videoResolution || undefined, undefined, generateAudio, duration)
      setResult(res)
    } catch (e: any) {
      setResult({ error: e.message })
    }
    clearInterval(timer)
    setGenerating(false)
  }

  // Batch generate
  const handleBatchGenerate = async () => {
    setGenerating(true)
    setBatchResults([])
    const start = batchStart
    const end = Math.min(batchEnd, shots.length)
    setBatchProgress(`准备生成镜头 ${start}-${end}...`)

    for (let i = start; i <= end; i++) {
      const shot = shots.find(s => s.index === i)
      if (!shot) continue
      setBatchProgress(`正在生成镜头 ${i}/${end}...`)
      try {
        const res = await fetch(`/api/projects/${encodeURIComponent(projectName)}/video/shots/generate`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            shot_index: i,
            prompt: shot.prompt,
            resolution: videoResolution,
            generate_audio: generateAudio,
            model: videoModel,
          }),
        })
        const data = await res.json()
        if (data.video_url) setBatchResults(prev => [...prev, `✅ 镜头${i} 完成`])
        else setBatchResults(prev => [...prev, `❌ 镜头${i}: ${data.error || '失败'}`])
      } catch (e: any) {
        setBatchResults(prev => [...prev, `❌ 镜头${i}: ${e.message}`])
      }
    }
    setBatchProgress(`完成 ${end - start + 1} 个镜头`)
    setGenerating(false)
  }

  const toggleChar = (name: string) => {
    const willSelect = !selectedCharNames.includes(name)
    setSelectedCharNames(prev => prev.includes(name) ? prev.filter(n => n !== name) : [...prev, name])
    // Auto-add confirmed character images to reference
    if (willSelect) {
      const imgs = confirmedImages.characters[name]
      if (imgs?.length) {
        imgs.forEach((img: any) => addProjectImage(img.url, `char_${name}`))
      }
    }
  }
  const toggleScene = (name: string) => {
    const willSelect = !selectedSceneNames.includes(name)
    setSelectedSceneNames(prev => prev.includes(name) ? prev.filter(n => n !== name) : [...prev, name])
    // Auto-add confirmed scene images to reference
    if (willSelect) {
      const imgs = confirmedImages.scenes[name]
      if (imgs?.length) {
        imgs.forEach((img: any) => addProjectImage(img.url, `scene_${name}`))
      }
    }
  }
  const toggleShot = (index: number) => {
    setSelectedShotIndices(prev => prev.includes(index) ? prev.filter(i => i !== index) : [...prev, index])
  }
  const toggleAllShots = () => {
    if (selectedShotIndices.length === shots.length) setSelectedShotIndices([])
    else setSelectedShotIndices(shots.map(s => s.index))
  }

  // Group shots by act
  const shotGroups: Record<string, ExtractedShot[]> = {}
  for (const s of shots) {
    if (!shotGroups[s.act]) shotGroups[s.act] = []
    shotGroups[s.act].push(s)
  }

  return (
    <div>
      {/* Project selector + extract */}
      <div className="glass-card rounded-2xl p-5 mb-6">
        <div className="flex items-end gap-4">
          <div className="flex-1">
            <label className="text-xs font-medium text-muted-foreground uppercase tracking-wider mb-2 block">当前项目</label>
            <p className="text-sm font-medium">{projectName}</p>
          </div>
          <button onClick={handleExtract} disabled={extracting}
            className="flex items-center gap-1.5 px-4 py-3 rounded-xl border-2 border-border text-sm font-medium hover:border-primary/30 disabled:opacity-50 transition-all whitespace-nowrap">
            {extracting ? <Loader2 className="w-4 h-4 animate-spin" /> : <Sparkles className="w-4 h-4" />}
            {extracting ? '提取中...' : '🔄 视觉提取'}
          </button>
          {extractedOnce && characters.length > 0 && !extracting && (
            <button onClick={handleConfirm}
              className="px-4 py-3 rounded-xl border-2 border-green-400/30 text-sm font-medium text-green-400 hover:bg-green-400/5 transition-all whitespace-nowrap">
              ✓ 确认
            </button>
          )}
        </div>
        {extractLog && (
          <p className={`text-xs mt-3 ${extractLog.includes('✅') ? 'text-green-400' : extractLog.includes('❌') ? 'text-red-400' : 'text-muted-foreground'}`}>
            {extractLog}
          </p>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left: Characters + Scenes */}
        <div className="lg:col-span-1 space-y-4">
          <div className="glass-card rounded-2xl p-4 border-2 border-primary/10">
            <div className="flex items-center justify-between mb-3">
              <h3 className="font-semibold text-xs">🧑 角色 ({characters.length})</h3>
              {selectedCharNames.length > 0 && <span className="text-[9px] px-2 py-0.5 rounded-full bg-primary/20 text-primary font-medium">{selectedCharNames.length} 已选</span>}
            </div>
            {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : characters.length === 0 ? (
              <p className="text-[10px] text-muted-foreground">点击「视觉提取」</p>
            ) : (
              <div className="space-y-1 max-h-48 overflow-y-auto">
                {characters.map((c: any) => {
                  const sel = selectedCharNames.includes(c.name)
                  const imgs = confirmedImages.characters[c.name]
                  return (
                    <button key={c._file} onClick={() => toggleChar(c.name)}
                      className={`w-full flex items-center gap-2.5 px-3 py-2.5 rounded-lg text-[11px] text-left transition-all ${
                        sel ? 'bg-primary/20 text-primary font-medium border border-primary/30' : 'hover:bg-muted/80 text-muted-foreground border border-transparent'
                      }`}>
                      {sel ? <CheckSquare className="w-4 h-4 text-primary flex-shrink-0" /> : <Square className="w-4 h-4 text-muted-foreground/40 flex-shrink-0" />}
                      <span className="flex-1 truncate">{c.name}</span>
                      {imgs?.length ? <img src={imgs[0].url} alt="" className="w-6 h-6 rounded object-cover border border-border/40" onClick={e => { e.stopPropagation(); setPreviewSrc(imgs[0].url) }} /> : null}
                    </button>
                  )
                })}
              </div>
            )}
          </div>
          <div className="glass-card rounded-2xl p-4 border-2 border-primary/10">
            <div className="flex items-center justify-between mb-3">
              <h3 className="font-semibold text-xs">🌆 场景 ({scenes.length})</h3>
              {selectedSceneNames.length > 0 && <span className="text-[9px] px-2 py-0.5 rounded-full bg-primary/20 text-primary font-medium">{selectedSceneNames.length} 已选</span>}
            </div>
            {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : scenes.length === 0 ? (
              <p className="text-[10px] text-muted-foreground">点击「视觉提取」</p>
            ) : (
              <div className="space-y-1 max-h-48 overflow-y-auto">
                {scenes.map((s: any) => {
                  const sel = selectedSceneNames.includes(s.name)
                  const imgs = confirmedImages.scenes[s.name]
                  return (
                    <button key={s._file} onClick={() => toggleScene(s.name)}
                      className={`w-full flex items-center gap-2.5 px-3 py-2.5 rounded-lg text-[11px] text-left transition-all ${
                        sel ? 'bg-primary/20 text-primary font-medium border border-primary/30' : 'hover:bg-muted/80 text-muted-foreground border border-transparent'
                      }`}>
                      {sel ? <CheckSquare className="w-4 h-4 text-primary flex-shrink-0" /> : <Square className="w-4 h-4 text-muted-foreground/40 flex-shrink-0" />}
                      <span className="flex-1 truncate">{s.name}</span>
                      {imgs?.length ? <img src={imgs[0].url} alt="" className="w-6 h-6 rounded object-cover border border-border/40" onClick={e => { e.stopPropagation(); setPreviewSrc(imgs[0].url) }} /> : null}
                    </button>
                  )
                })}
              </div>
            )}
          </div>
        </div>

        {/* Right: Shots + Prompt + Params + Generate */}
        <div className="lg:col-span-2 space-y-6">
          {/* Shots list */}
          <div className="glass-card rounded-2xl p-4 border-2 border-accent/20">
            <div className="flex items-center justify-between mb-3">
              <h3 className="font-semibold text-xs">🎬 分镜 ({shots.length})</h3>
              <div className="flex items-center gap-2">
                <button onClick={toggleAllShots} className="text-[9px] text-muted-foreground hover:text-primary px-2 py-0.5 rounded hover:bg-muted transition-all">
                  {selectedShotIndices.length === shots.length && shots.length > 0 ? '取消全选' : '全选'}
                </button>
                <button onClick={() => loadShots(projectName)} className="p-1 rounded hover:bg-muted"><RefreshCw className="w-3 h-3" /></button>
              </div>
            </div>
            {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : shots.length === 0 ? (
              <p className="text-[10px] text-muted-foreground">暂无分镜内容</p>
            ) : (
              <div className="max-h-48 overflow-y-auto space-y-1">
                {shots.map(shot => {
                  const sel = selectedShotIndices.includes(shot.index)
                  return (
                    <button key={shot.index} onClick={() => toggleShot(shot.index)}
                      className={`w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-[11px] text-left transition-all ${
                        sel ? 'bg-primary/20 text-primary font-medium border border-primary/30' : 'hover:bg-muted/80 text-muted-foreground border border-transparent'
                      }`}>
                      {sel ? <CheckSquare className="w-4 h-4 text-primary flex-shrink-0" /> : <Square className="w-4 h-4 text-muted-foreground/40 flex-shrink-0" />}
                      <span className="flex-1 truncate">{shot.act} 镜头{shot.index}</span>
                    </button>
                  )
                })}
              </div>
            )}
          </div>

          {/* Prompt */}
          <div className="glass-card rounded-2xl p-5">
            <div className="flex items-center justify-between mb-2">
              <label className="text-xs font-medium text-muted-foreground uppercase tracking-wider">提示词</label>
              <button onClick={() => setPrompt('')} className="text-[10px] text-muted-foreground hover:text-red-400 px-2 py-0.5 rounded hover:bg-red-400/5 transition-all">清空</button>
            </div>
            <textarea value={prompt} onChange={e => setPrompt(e.target.value)}
              placeholder={`在左侧勾选角色/场景/分镜，提示词将自动组合。\n也可以手动输入。`}
              className="w-full bg-muted border border-border rounded-xl px-4 py-3 h-32 resize-none text-sm font-mono" />

            {/* Reference images */}
            <div className="mt-4">
              <div className="flex items-center gap-2 mb-2">
                <span className="text-[10px] text-muted-foreground font-medium">参考图</span>
                <button onClick={() => fileInputRef.current?.click()} className="text-[9px] text-primary px-2 py-0.5 rounded hover:bg-primary/10 transition-all">
                  + 上传
                </button>
                <input ref={fileInputRef} type="file" accept="image/*" multiple className="hidden" onChange={handleFileSelect} />
              </div>
              {refFiles.length > 0 && (
                <div className="flex flex-wrap gap-2 mb-2">
                  {refFiles.map((entry, i) => (
                    <div key={i} className="relative group">
                      <img src={entry.preview} alt="" className="w-12 h-12 object-cover rounded-lg" />
                      <button onClick={() => removeFile(i)}
                        className="absolute -top-1.5 -right-1.5 w-4 h-4 rounded-full bg-red-500 text-white flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity">
                        <X className="w-2.5 h-2.5" />
                      </button>
                    </div>
                  ))}
                </div>
              )}
              {/* Project image references */}
              {Object.keys(projectImages.characters).length > 0 && (
                <div className="mb-1">
                  <p className="text-[9px] text-muted-foreground mb-1">👤 角色图</p>
                  <div className="flex flex-wrap gap-1.5">
                    {Object.entries(projectImages.characters).slice(0, 6).map(([name, imgs]) =>
                      (imgs as any[]).slice(0, 1).map((img, i) => (
                        <img key={`${name}-${i}`} src={img.url} alt={name}
                          className="w-10 h-10 object-contain rounded-lg bg-muted border border-border cursor-pointer hover:ring-2 hover:ring-primary/50"
                          onClick={() => addProjectImage(img.url, name)} title={`点击添加${name}`} />
                      ))
                    )}
                  </div>
                </div>
              )}
              {Object.keys(projectImages.scenes).length > 0 && (
                <div>
                  <p className="text-[9px] text-muted-foreground mb-1">🌆 场景图</p>
                  <div className="flex flex-wrap gap-1.5">
                    {Object.entries(projectImages.scenes).slice(0, 6).map(([name, imgs]) =>
                      (imgs as any[]).slice(0, 1).map((img, i) => (
                        <img key={`${name}-${i}`} src={img.url} alt={name}
                          className="w-10 h-10 object-contain rounded-lg bg-muted border border-border cursor-pointer hover:ring-2 hover:ring-primary/50"
                          onClick={() => addProjectImage(img.url, name)} title={`点击添加${name}`} />
                      ))
                    )}
                  </div>
                </div>
              )}
            </div>

            {/* Parameters */}
            <div className="space-y-3 mt-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                <div>
                  <label className="text-[10px] text-muted-foreground block mb-1">模型</label>
                  <ModelSelector type="video" value={videoModel} onChange={setVideoModel} />
                </div>
                <div className="grid grid-cols-3 gap-3">
                  <div>
                    <label className="text-[10px] text-muted-foreground block mb-1">比例</label>
                    <select value={selectedRatio} onChange={e => { const rs = ratioGroups[e.target.value]; setSelectedRatio(e.target.value); if (rs?.length) setVideoResolution(rs[0]) }}
                      className="w-full bg-muted border border-border rounded-xl px-2 py-2 text-xs">
                      {Object.keys(ratioGroups).map(r => (<option key={r} value={r}>{r}</option>))}
                    </select>
                  </div>
                  <div>
                    <label className="text-[10px] text-muted-foreground block mb-1">分辨率</label>
                    <select value={videoResolution} onChange={e => setVideoResolution(e.target.value)} className="w-full bg-muted border border-border rounded-xl px-2 py-2 text-xs">
                      {(ratioGroups[selectedRatio] || resolutions).map(r => (<option key={r} value={r}>{r}</option>))}
                    </select>
                  </div>
                  <div>
                    <label className="text-[10px] text-muted-foreground block mb-1">时长(秒)</label>
                    <select value={duration} onChange={e => setDuration(Number(e.target.value))} className="w-full bg-muted border border-border rounded-xl px-2 py-2 text-xs">
                      <option value={3}>3秒</option>
                      <option value={5}>5秒</option>
                      <option value={10}>10秒</option>
                      <option value={15}>15秒</option>
                    </select>
                  </div>
                </div>
              </div>
              <div className="flex items-center gap-4">
                <label className="relative inline-flex items-center cursor-pointer">
                  <input type="checkbox" className="sr-only peer" checked={generateAudio} onChange={e => setGenerateAudio(e.target.checked)} />
                  <div className="w-8 h-4 bg-muted rounded-full peer peer-checked:after:translate-x-full after:content-[''] after:absolute after:top-[1px] after:left-[1px] after:bg-white after:rounded-full after:h-3.5 after:w-3.5 after:transition-all peer-checked:bg-primary"></div>
                  <span className="text-[10px] text-muted-foreground ml-2">生成音频</span>
                </label>
              </div>
            </div>

            {/* Generate buttons */}
            <div className="flex items-center gap-3 mt-4">
              <button onClick={handleGenerate} disabled={generating || !prompt.trim()}
                className="btn-gradient flex items-center gap-1.5 px-5 py-2.5 rounded-xl text-sm font-medium disabled:opacity-50">
                {generating && genMode === 'single' ? <Loader2 className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
                {generating && genMode === 'single' ? `生成中 ${elapsed}s` : '生成单段'}
              </button>

              {shots.length > 0 && (
                <div className="flex items-center gap-2 border-l border-border pl-3">
                  <span className="text-[10px] text-muted-foreground">批量：镜头</span>
                  <input type="number" min={1} max={shots.length} value={batchStart}
                    onChange={e => setBatchStart(Number(e.target.value))}
                    className="w-12 bg-muted border border-border rounded-lg px-1.5 py-1 text-xs text-center" />
                  <span className="text-[10px] text-muted-foreground">到</span>
                  <input type="number" min={1} max={shots.length} value={batchEnd}
                    onChange={e => setBatchEnd(Number(e.target.value))}
                    className="w-12 bg-muted border border-border rounded-lg px-1.5 py-1 text-xs text-center" />
                  <button onClick={handleBatchGenerate} disabled={generating}
                    className="px-4 py-2 rounded-xl border border-border text-xs hover:bg-muted transition-colors disabled:opacity-50">
                    {generating && genMode === 'batch' ? <Loader2 className="w-3 h-3 inline animate-spin mr-1" /> : null}
                    批量生成
                  </button>
                </div>
              )}
            </div>

            {batchProgress && <p className="text-xs text-muted-foreground mt-2">{batchProgress}</p>}
            {batchResults.length > 0 && (
              <div className="mt-3 max-h-32 overflow-y-auto space-y-0.5">
                {batchResults.map((r, i) => (
                  <p key={i} className={`text-[10px] ${r.startsWith('✅') ? 'text-green-400' : 'text-red-400'}`}>{r}</p>
                ))}
              </div>
            )}
          </div>

          {/* Result */}
          {result && (
            <div className="glass-card rounded-2xl p-5">
              <h3 className="font-semibold text-sm mb-3">生成结果</h3>
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
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
      {previewSrc && <ImagePreview src={previewSrc} onClose={() => setPreviewSrc(null)} />}
    </div>
  )
}
