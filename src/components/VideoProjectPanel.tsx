import { useState, useEffect, useRef } from 'react'
import { Sparkles, Loader2, Upload, X, Download, Play, CheckSquare, Square, RefreshCw, ChevronDown, ChevronRight, Film, Music, Type, Scissors } from 'lucide-react'
import ModelSelector from './ModelSelector'
import ImagePreview from './ImagePreview'
import { fetchVideoResolutions, freeVideoGen, fetchProjectVisualAssets, fetchCharacters, fetchScenes, fetchProps, fetchPhaseContent, fetchConfirmedImages, fetchProjectAssetLibrary, fetchSettings } from '../lib/api'
import type { AssetLibrary, PropInfo } from '../lib/types'

interface ExtractedShot {
  index: number
  shot_number: string
  episode: string
  scene_label: string
  scene_name: string
  prompt: string
  characters: string[]
  duration: string
  spatial_state?: string
}

interface SceneNode {
  label: string
  shots: ExtractedShot[]
}

interface EpisodeNode {
  label: string
  scenes: SceneNode[]
}

interface Props {
  projectName: string
}

export default function VideoProjectPanel({ projectName }: Props) {
  const fileInputRef = useRef<HTMLInputElement>(null)
  const promptRef = useRef<HTMLTextAreaElement>(null)

  // Project data
  const [characters, setCharacters] = useState<any[]>([])
  const [scenes, setScenes] = useState<any[]>([])
  const [shots, setShots] = useState<ExtractedShot[]>([])
  const [episodes, setEpisodes] = useState<EpisodeNode[]>([])
  const [loading, setLoading] = useState(false)
  const [extracting, setExtracting] = useState(false)
  const [extractLog, setExtractLog] = useState('')
  const [extractedOnce, setExtractedOnce] = useState(false)

  // Selection
  const [selectedCharNames, setSelectedCharNames] = useState<string[]>([])
  const [selectedSceneNames, setSelectedSceneNames] = useState<string[]>([])
  const [selectedShotIndices, setSelectedShotIndices] = useState<number[]>([])
  const [propsList, setPropsList] = useState<PropInfo[]>([])
  const [selectedProp, setSelectedProp] = useState<string | null>(null)

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
  const [assetLibrary, setAssetLibrary] = useState<AssetLibrary | null>(null)
  const [showAllVersions, setShowAllVersions] = useState(false)
  const [previewSrc, setPreviewSrc] = useState<string | null>(null)

  // Parameters
  const [videoModel, setVideoModel] = useState('')
  const [resolutions, setResolutions] = useState<string[]>([])
  const [ratioGroups, setRatioGroups] = useState<Record<string, string[]>>({})
  const [selectedRatio, setSelectedRatio] = useState('')
  const [videoResolution, setVideoResolution] = useState('')
  const [duration, setDuration] = useState(5)
  const [generateAudio, setGenerateAudio] = useState(false)
  const [seed, setSeed] = useState(-1)
  const [cameraFixed, setCameraFixed] = useState(false)

  // Generation
  const [generating, setGenerating] = useState(false)
  const [result, setResult] = useState<{ video_url?: string; local?: string; error?: string } | null>(null)
  const [elapsed, setElapsed] = useState(0)
  const [batchResults, setBatchResults] = useState<string[]>([])
  const [batchProgress, setBatchProgress] = useState('')
  const [shotStatuses, setShotStatuses] = useState<Record<number, 'pending' | 'done' | 'failed'>>({})
  const [shotVideoUrls, setShotVideoUrls] = useState<Record<number, string>>({})
  const [expandedPreviews, setExpandedPreviews] = useState<Record<string, boolean>>({})
  const [batchedBefore, setBatchedBefore] = useState(false)
  const [batchPaused, setBatchPaused] = useState(false)
  const batchPausedRef = useRef(false)
  const [failedShots, setFailedShots] = useState<number[]>([])

  const [showConcatPanel, setShowConcatPanel] = useState(false)
  const [concatTitle, setConcatTitle] = useState(projectName || '')
  const [concatTitleDuration, setConcatTitleDuration] = useState(2)
  const [concatTransition, setConcatTransition] = useState(0)
  const [concatSubtitle, setConcatSubtitle] = useState(false)
  const [concatBgmPath, setConcatBgmPath] = useState('')
  const [concatBgmVolume, setConcatBgmVolume] = useState(30)
  const [concatGenerating, setConcatGenerating] = useState(false)
  const [concatResult, setConcatResult] = useState<any>(null)
  const bgmInputRef = useRef<HTMLInputElement>(null)

  // Shots expanded state
  const [expandedEpisodes, setExpandedEpisodes] = useState<Record<string, boolean>>({})
  const [expandedScenes, setExpandedScenes] = useState<Record<string, boolean>>({})

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
    if (promptRef.current) {
      promptRef.current.style.height = 'auto'
      promptRef.current.style.height = promptRef.current.scrollHeight + 'px'
    }
  }, [prompt])

  useEffect(() => {
    fetchSettings().then(s => {
      if ((s as any)?.video_model && !videoModel) setVideoModel((s as any).video_model)
    }).catch(() => {})
  }, [])

  useEffect(() => {
    if (!projectName) return
    setLoading(true)
    Promise.all([
      fetchCharacters(projectName).then(setCharacters),
      fetchScenes(projectName).then(setScenes),
      fetchProps(projectName).then(setPropsList),
      loadShots(projectName),
      fetchProjectVisualAssets(projectName).then(setProjectImages),
      fetchConfirmedImages(projectName).then(setConfirmedImages),
    ]).finally(() => {
      setLoading(false)
      restoreCheckpoint(projectName)
    })
  }, [projectName])

  useEffect(() => {
    if (!projectName) return
    fetchProjectAssetLibrary(projectName).then(setAssetLibrary).catch(() => {})
  }, [projectName])

  const loadShots = async (name: string) => {
    try {
      const c = await fetchPhaseContent(name, '05_分镜脚本')
      const text = c?.content || ''
      if (!text) { setEpisodes([]); setShots([]); return }

      const episodes: EpisodeNode[] = []
      const allShots: ExtractedShot[] = []
      let globalIdx = 0
      let currentEpisode: EpisodeNode | null = null
      let currentScene: SceneNode | null = null
      let currentShot: Partial<ExtractedShot> | null = null
      let blockLines: string[] = []

      const episodeRegex = /^(?:#{1,3})\s+(第\S+集)/
      const sceneRegex = /^(?:#{2,3})\s+(第\d+场\s*[-—].+)/
      const shotHeaderRegex = /^镜头(\d+)\s*\|\s*(\S+)\s*\|/

      const flushShot = () => {
        if (currentShot && blockLines.length > 0) {
          currentShot.prompt = blockLines.join('\n').trim()
          const posMatch = currentShot.prompt.match(/(?:在|位于|站在|坐在|靠在|躺在|走在)(.{1,30}(?:门前|窗边|控制台旁|大厅中央|走廊|墙边|楼梯口|门口|桌旁|椅子|角落|入口|出口))/)
          if (posMatch) currentShot.spatial_state = posMatch[0]
          const shot = { ...currentShot, index: globalIdx, prompt: currentShot.prompt || '' } as ExtractedShot
          allShots.push(shot)
          if (currentScene) currentScene.shots.push(shot)
          globalIdx++
        }
        blockLines = []
      }

      const ensureEpisode = (label: string) => {
        if (!currentEpisode || currentEpisode.label !== label) {
          const existing = episodes.find(e => e.label === label)
          if (existing) {
            currentEpisode = existing
          } else {
            currentEpisode = { label, scenes: [] }
            episodes.push(currentEpisode)
          }
        }
      }

      const lines = text.split('\n')
      for (let i = 0; i < lines.length; i++) {
        const line = lines[i]

        const epMatch = line.match(episodeRegex)
        if (epMatch) {
          flushShot()
          currentShot = null
          currentScene = null
          ensureEpisode(epMatch[1])
          continue
        }

        const scMatch = line.match(sceneRegex)
        if (scMatch) {
          flushShot()
          currentShot = null
          currentScene = { label: scMatch[1], shots: [] }
          if (currentEpisode) currentEpisode.scenes.push(currentScene)
          else {
            // 没有 episode 时，自建一个
            ensureEpisode('默认')
            currentEpisode!.scenes.push(currentScene)
          }
          continue
        }

        const shMatch = line.match(shotHeaderRegex)
        if (shMatch) {
          flushShot()
          currentShot = { shot_number: shMatch[1], duration: shMatch[2], episode: currentEpisode?.label || '', scene_label: currentScene?.label || '', scene_name: '', characters: [] }
          blockLines = []
          continue
        }
        if (currentShot) {
          if (line.startsWith('出场角色：')) {
            const ch = line.replace('出场角色：', '').trim()
            currentShot.characters = ch === '-' ? [] : ch.split('、').map(s => s.trim()).filter(Boolean)
          } else if (line.startsWith('场景：')) {
            currentShot.scene_name = line.replace('场景：', '').trim()
          } else if (line.trim() === '---') {
            flushShot()
            currentShot = null
          } else if (line.trim()) {
            blockLines.push(line)
          }
        }
      }
      flushShot()
      // 过滤临时"默认" episode
      setEpisodes(episodes.filter(e => e.label !== '默认' && e.scenes.length > 0))
      setShots(allShots)
    } catch { setEpisodes([]); setShots([]) }
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
    if (selectedShotIndices.length === 0) return
    const timer = setTimeout(() => {
      const parts: string[] = []
      const selectedShots = shots.filter(s => selectedShotIndices.includes(s.index))
      for (const s of selectedShots) {
        parts.push(`### ${s.episode} 镜头${s.shot_number}\n${s.prompt}`)
      }
      setPrompt(parts.join('\n\n---\n\n'))
    }, 300)
    return () => clearTimeout(timer)
  }, [selectedShotIndices, shots])

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
    setBatchPaused(false)
    batchPausedRef.current = false
    setBatchResults([])
    setFailedShots([])
    const start = batchStart
    const end = Math.min(batchEnd, shots.length)
    setBatchProgress(`正在生成镜头 ${start}/${end - start + 1} 个...`)

    const newStatuses: Record<number, 'pending' | 'done' | 'failed'> = {}
    const newFailed: number[] = []
    for (let i = start; i <= end; i++) {
      if (batchPausedRef.current) {
        setBatchProgress(`已暂停，完成至镜头 ${i-1}`)
        setShotStatuses(prev => ({ ...prev, ...newStatuses }))
        setGenerating(false)
        return
      }
      const shot = shots.find(s => s.index === i)
      if (!shot) continue
      setBatchProgress(`正在生成镜头 ${i}/${end} (${i - start + 1}/${end - start + 1})`)
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
            scene_name: shot.scene_name,
            seed: seed >= 0 ? seed : -1,
            camera_fixed: cameraFixed,
            duration: duration,
            character_names: shot.characters || [],
          }),
        })
        const data = await res.json()
        if (data.video_url) {
          setBatchResults(prev => [...prev, `✅ 镜头${i} 完成`])
          newStatuses[i] = 'done'
          setShotVideoUrls(prev => ({ ...prev, [i]: data.video_url || data.local_path || `/api/projects/${encodeURIComponent(projectName)}/video/download` }))
          saveQuickCheckpoint({ ...shotStatuses, ...newStatuses, [i]: 'done' }, { ...shotVideoUrls, [i]: data.video_url || '' })
        } else {
          setBatchResults(prev => [...prev, `❌ 镜头${i}: ${data.error || '失败'}`])
          newStatuses[i] = 'failed'
          newFailed.push(i)
        }
      } catch (e: any) {
        setBatchResults(prev => [...prev, `❌ 镜头${i}: ${e.message}`])
        newStatuses[i] = 'failed'
        newFailed.push(i)
      }
    }
    setShotStatuses(prev => ({ ...prev, ...newStatuses }))
    setFailedShots(newFailed)
    setBatchProgress(end - start + 1 - newFailed.length === 0 ? '全部失败' : newFailed.length > 0 ? `完成，${newFailed.length} 个失败` : '全部完成')
    setGenerating(false)
    if (newFailed.length === 0) clearCheckpoint()
  }

  const getCheckpointPath = (proj?: string) => {
    const p = proj || projectName
    if (!p) return ''
    return `/api/projects/${encodeURIComponent(p)}/video/shots/generate`
  }

  const saveCheckpoint = () => {
    if (!projectName) return
    const cp = {
      shotStatuses,
      shotVideoUrls,
      batchStart,
      batchEnd,
      failedShots,
      savedAt: Date.now(),
    }
    try {
      localStorage.setItem(`video_gen_cp_${projectName}`, JSON.stringify(cp))
    } catch {}
  }

  const saveQuickCheckpoint = (statuses: Record<number, string>, urls: Record<number, string>) => {
    if (!projectName) return
    try {
      localStorage.setItem(`video_gen_cp_${projectName}`, JSON.stringify({
        shotStatuses: statuses,
        shotVideoUrls: urls,
        savedAt: Date.now(),
      }))
    } catch {}
  }

  const restoreCheckpoint = (proj: string) => {
    try {
      const raw = localStorage.getItem(`video_gen_cp_${proj}`)
      if (!raw) return
      const cp = JSON.parse(raw)
      if (Date.now() - cp.savedAt > 86400000) {
        localStorage.removeItem(`video_gen_cp_${proj}`)
        return
      }
      if (cp.shotStatuses && Object.keys(cp.shotStatuses).length > 0) {
        setShotStatuses(cp.shotStatuses || {})
        setShotVideoUrls(cp.shotVideoUrls || {})
        setBatchedBefore(true)
      }
    } catch {}
  }

  const clearCheckpoint = () => {
    if (!projectName) return
    try { localStorage.removeItem(`video_gen_cp_${projectName}`) } catch {}
  }

  const handleRetryFailed = () => {
    const start = failedShots.length > 0 ? failedShots[0] : batchStart
    const end = failedShots.length > 0 ? failedShots[failedShots.length - 1] : batchEnd
    setBatchStart(start)
    setBatchEnd(end)
    handleBatchGenerate()
  }

  const handleBgmUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file || !projectName) return
    const formData = new FormData()
    formData.append('file', file)
    try {
      const res = await fetch(`/api/projects/${encodeURIComponent(projectName)}/video/bgm/upload`, { method: 'POST', body: formData })
      const data = await res.json()
      setConcatBgmPath(data.filename)
    } catch {}
  }

  const handleConcat = async () => {
    setConcatGenerating(true)
    setConcatResult(null)
    try {
      const doneShots = Object.entries(shotStatuses)
        .filter(([, v]) => v === 'done')
        .map(([k]) => parseInt(k))
        .sort((a, b) => a - b)
      const allIndices = doneShots.length > 0 ? doneShots : shots.map(s => s.index)

      const res = await fetch(`/api/projects/${encodeURIComponent(projectName)}/video/shots/concat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          shot_indices: allIndices,
          title_text: concatTitle,
          title_duration: concatTitleDuration,
          transition_duration: concatTransition,
          subtitle_enabled: concatSubtitle,
          bgm_path: concatBgmPath,
          bgm_volume: concatBgmVolume / 100,
        }),
      })
      const data = await res.json()
      setConcatResult(data)
    } catch (e: any) {
      setConcatResult({ error: e.message })
    }
    setConcatGenerating(false)
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
              {selectedCharNames.length > 0 && <span className="text-[10px] px-2 py-0.5 rounded-full bg-primary/20 text-primary font-medium">{selectedCharNames.length} 已选</span>}
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
              {selectedSceneNames.length > 0 && <span className="text-[10px] px-2 py-0.5 rounded-full bg-primary/20 text-primary font-medium">{selectedSceneNames.length} 已选</span>}
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
          <div className="glass-card rounded-2xl p-4 border-2 border-primary/10">
            <h3 className="font-semibold text-xs mb-3">🔧 配饰/道具</h3>
            {(characters || []).filter(c => (c.accessories || []).length > 0).length === 0 ? (
              <p className="text-[10px] text-muted-foreground">暂无配饰数据</p>
            ) : (
              <div className="space-y-1 max-h-48 overflow-y-auto">
                {characters.filter(c => (c.accessories || []).length > 0).map(c =>
                  (c.accessories || []).map(prop => (
                    <div key={`${c.name}/${prop}`} className="flex items-center gap-2 px-3 py-2 text-[11px] text-muted-foreground">
                      <span className="text-[10px]">🎒</span>
                      <span className="truncate">{c.name} · {prop}</span>
                    </div>
                  ))
                )}
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
                <button onClick={toggleAllShots} className="text-[10px] text-muted-foreground hover:text-primary px-2 py-0.5 rounded hover:bg-muted transition-all">
                  {selectedShotIndices.length === shots.length && shots.length > 0 ? '取消全选' : '全选'}
                </button>
                <button onClick={() => loadShots(projectName)} className="p-1 rounded hover:bg-muted"><RefreshCw className="w-3 h-3" /></button>
              </div>
            </div>
            {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : episodes.length === 0 ? (
              <p className="text-[10px] text-muted-foreground">暂无分镜内容</p>
            ) : (
              <div className="max-h-[60vh] overflow-y-auto space-y-1">
                {episodes.map((ep, epIdx) => {
                  const epExpanded = expandedEpisodes[ep.label] ?? (epIdx === 0)
                  const setEpExp = (v: boolean) => setExpandedEpisodes(prev => ({ ...prev, [ep.label]: v }))
                  return (
                    <div key={ep.label}>
                      <button onClick={() => setEpExp(!epExpanded)}
                        className="w-full flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-[11px] font-medium hover:bg-muted/60 transition-all">
                        {epExpanded ? <ChevronDown className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />}
                        📺 {ep.label} ({ep.scenes.reduce((s, sc) => s + sc.shots.length, 0)}镜)
                      </button>
                      {epExpanded && (
                        <div className="ml-4 space-y-0.5">
                          {ep.scenes.map(sc => {
                            const scKey = `${ep.label}/${sc.label}`
                            const scExpanded = expandedScenes[scKey] ?? false
                            const setScExp = (v: boolean) => setExpandedScenes(prev => ({ ...prev, [scKey]: v }))
                            return (
                              <div key={scKey}>
                                <button onClick={() => setScExp(!scExpanded)}
                                  className="w-full flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-[10px] text-muted-foreground hover:bg-muted/40 transition-all">
                                  {scExpanded ? <ChevronDown className="w-2.5 h-2.5" /> : <ChevronRight className="w-2.5 h-2.5" />}
                                  🎞 {sc.label} ({sc.shots.length}镜)
                                </button>
                                {scExpanded && (
                                  <div className="ml-4 space-y-0.5">
                                    {sc.shots.map(shot => {
                                      const sel = selectedShotIndices.includes(shot.index)
                                      return (
                                        <div key={shot.index}>
                                          <button onClick={() => toggleShot(shot.index)}
                                            className={`w-full flex items-center gap-2 px-2.5 py-1 rounded-lg text-[10px] text-left transition-all ${
                                              sel ? 'bg-primary/20 text-primary font-medium border border-primary/30' : 'hover:bg-muted/80 text-muted-foreground/80 border border-transparent'
                                            }`}>
                                            {sel ? <CheckSquare className="w-3 h-3 text-primary flex-shrink-0" /> : <Square className="w-3 h-3 text-muted-foreground/40 flex-shrink-0" />}
                                            <span className="flex-1 truncate">镜头{shot.shot_number} {shot.scene_name ? `· ${shot.scene_name}` : ''}</span>
                                            {shotStatuses[shot.index] === 'done' && <span className="text-green-400 text-[9px] ml-1 cursor-pointer hover:text-green-300" onClick={e => { e.stopPropagation(); setExpandedPreviews(p => ({ ...p, [String(shot.index)]: !p[String(shot.index)] })) }} title="预览">▶</span>}
                                            {shotStatuses[shot.index] === 'done' && <span className="text-green-400 text-[9px] ml-0.5">✓</span>}
                                            {shotStatuses[shot.index] === 'failed' && <span className="text-red-400 text-[9px] ml-1">✗</span>}
                                          </button>
                                          {expandedPreviews[String(shot.index)] && shotVideoUrls[shot.index] && (
                                            <div className="ml-4 mt-1">
                                              <video src={shotVideoUrls[shot.index]} controls className="w-full max-w-xs rounded-lg border border-border/40" style={{ maxHeight: 180 }} />
                                            </div>
                                          )}
                                        </div>
                                      )
                                    })}
                                  </div>
                                )}
                              </div>
                            )
                          })}
                        </div>
                      )}
                    </div>
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
            <textarea ref={promptRef} value={prompt} onChange={e => setPrompt(e.target.value)}
              placeholder={`在左侧勾选角色/场景/分镜，提示词将自动组合。\n也可以手动输入。`}
              className="w-full bg-muted border border-border rounded-xl px-4 py-3 min-h-[8rem] resize-none text-sm font-mono" />

            {/* Reference images */}
            <div className="mt-4">
              <div className="flex items-center gap-2 mb-2">
                <span className="text-[10px] text-muted-foreground font-medium">参考图</span>
                <button onClick={() => fileInputRef.current?.click()} className="text-[10px] text-primary px-2 py-0.5 rounded hover:bg-primary/10 transition-all">
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
              {/* 项目素材库自动匹配 */}
              {assetLibrary && (
                <div className="mb-3">
                  <h4 className="text-[10px] font-medium text-muted-foreground mb-1.5">项目素材库</h4>
                  <div className="flex flex-wrap gap-1.5">
                    {Object.entries(assetLibrary.characters).map(([name, data]) => {
                      const img = data.latest_confirmed?.images[0]
                      if (!img) return null
                      return (
                        <div key={name}
                          onClick={() => addProjectImage(img.url, `char_${name}`)}
                          className="relative w-12 h-12 rounded-lg overflow-hidden cursor-pointer border border-border hover:border-primary/50 transition-all group"
                          title={`点击添加 ${name}`}>
                          <img src={img.url} alt={name} className="w-full h-full object-cover" />
                          <div className="absolute bottom-0 left-0 right-0 bg-black/60 text-[7px] text-white text-center py-0.5 truncate leading-none">
                            {name}
                          </div>
                        </div>
                      )
                    })}
                    {Object.entries(assetLibrary.scenes).map(([name, data]) => {
                      const img = data.latest_confirmed?.images[0]
                      if (!img) return null
                      return (
                        <div key={name}
                          onClick={() => addProjectImage(img.url, `scene_${name}`)}
                          className="relative w-12 h-12 rounded-lg overflow-hidden cursor-pointer border border-border hover:border-primary/50 transition-all group"
                          title={`点击添加 ${name}`}>
                          <img src={img.url} alt={name} className="w-full h-full object-cover" />
                          <div className="absolute bottom-0 left-0 right-0 bg-black/60 text-[7px] text-white text-center py-0.5 truncate leading-none">
                            {name}
                          </div>
                        </div>
                      )
                    })}
                  </div>
                  <button onClick={() => setShowAllVersions(!showAllVersions)}
                    className="text-[9px] text-muted-foreground hover:text-foreground mt-1 transition-colors">
                    {showAllVersions ? '收起所有版本' : '查看所有版本'}
                  </button>
                  {showAllVersions && (
                    <div className="mt-2 space-y-2 max-h-40 overflow-y-auto">
                      {Object.entries(assetLibrary.characters).map(([name, data]) => (
                        <div key={name}>
                          <p className="text-[9px] text-muted-foreground mb-1">{name}</p>
                          <div className="flex flex-wrap gap-1">
                            {data.all_versions.map(v => (
                              v.images.slice(0, 1).map((img, i) => (
                                <img key={`${v.version}-${i}`} src={img.url} alt={`${name} ${v.version}`}
                                  className={`w-8 h-8 object-cover rounded border cursor-pointer hover:ring-1 hover:ring-primary/50 ${v.confirmed ? 'ring-1 ring-green-400/60' : 'border-border'}`}
                                  onClick={() => addProjectImage(img.url, `${name}_${v.version}`)}
                                  title={`${v.version}${v.confirmed ? ' (已确认)' : ''}`} />
                              ))
                            ))}
                          </div>
                        </div>
                      ))}
                      {Object.entries(assetLibrary.scenes).map(([name, data]) => (
                        <div key={name}>
                          <p className="text-[9px] text-muted-foreground mb-1">{name}</p>
                          <div className="flex flex-wrap gap-1">
                            {data.all_versions.map(v => (
                              v.images.slice(0, 1).map((img, i) => (
                                <img key={`${v.version}-${i}`} src={img.url} alt={`${name} ${v.version}`}
                                  className={`w-8 h-8 object-cover rounded border cursor-pointer hover:ring-1 hover:ring-primary/50 ${v.confirmed ? 'ring-1 ring-green-400/60' : 'border-border'}`}
                                  onClick={() => addProjectImage(img.url, `${name}_${v.version}`)}
                                  title={`${v.version}${v.confirmed ? ' (已确认)' : ''}`} />
                              ))
                            ))}
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}
              {/* Project image references */}
              {Object.keys(projectImages.characters).length > 0 && (
                <div className="mb-1">
                  <p className="text-[10px] text-muted-foreground mb-1">👤 角色图</p>
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
                  <p className="text-[10px] text-muted-foreground mb-1">🌆 场景图</p>
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
                    <input type="number" min={2} max={12} value={duration} onChange={e => setDuration(Math.max(2, Math.min(12, Number(e.target.value))))} className="w-full bg-muted border border-border rounded-xl px-2 py-2 text-xs text-center" />
                  </div>
                </div>
              </div>
              <div className="flex items-center gap-4">
                <label className="relative inline-flex items-center cursor-pointer">
                  <input type="checkbox" className="sr-only peer" checked={generateAudio} onChange={e => setGenerateAudio(e.target.checked)} />
                  <div className="w-8 h-4 bg-muted rounded-full peer peer-checked:after:translate-x-full after:content-[''] after:absolute after:top-[1px] after:left-[1px] after:bg-white after:rounded-full after:h-3.5 after:w-3.5 after:transition-all peer-checked:bg-primary"></div>
                  <span className="text-[10px] text-muted-foreground ml-2">生成音频</span>
                </label>

                <label className="relative inline-flex items-center cursor-pointer group">
                  <input type="checkbox" className="sr-only peer" checked={cameraFixed} onChange={e => setCameraFixed(e.target.checked)} />
                  <div className="w-8 h-4 bg-muted rounded-full peer peer-checked:after:translate-x-full after:content-[''] after:absolute after:top-[1px] after:left-[1px] after:bg-white after:rounded-full after:h-3.5 after:w-3.5 after:transition-all peer-checked:bg-primary"></div>
                  <span className="text-[10px] text-muted-foreground ml-2">固定镜头</span>
                  <span className="hidden group-hover:block absolute bottom-full left-1/2 -translate-x-1/2 mb-1 px-2 py-1 bg-black/80 text-white text-[9px] rounded whitespace-nowrap z-50">镜头不移动，适合对话正反打</span>
                </label>

                <div className="flex items-center gap-1">
                  <span className="text-[10px] text-muted-foreground">种子:</span>
                  <input type="number" value={seed} onChange={e => setSeed(Number(e.target.value))}
                    placeholder="随机"
                    className="w-16 text-[10px] bg-muted border border-border rounded-lg px-2 py-1 text-center" />
                </div>
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
                  {generating && (
                    <button onClick={() => { batchPausedRef.current = true; setBatchPaused(true) }}
                      className="flex items-center gap-1.5 px-3 py-2 rounded-xl border border-amber-400/30 text-amber-400 text-sm hover:bg-amber-500/10 transition-colors">
                      ⏸ 暂停
                    </button>
                  )}
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
            {failedShots.length > 0 && !generating && (
              <button onClick={handleRetryFailed}
                className="mt-2 flex items-center gap-1 px-3 py-1.5 rounded-lg text-[11px] border border-amber-400/30 text-amber-400 hover:bg-amber-500/10 transition-colors">
                <RefreshCw className="w-3 h-3" /> 重试 {failedShots.length} 个失败镜头
              </button>
            )}

            {!generating && Object.values(shotStatuses).some(v => v === 'done') && (
              <div className="mt-4 border-t border-border/40 pt-4">
                <button onClick={() => setShowConcatPanel(!showConcatPanel)}
                  className="flex items-center gap-1.5 text-[11px] text-primary/70 hover:text-primary transition-colors">
                  <Film className="w-3.5 h-3.5" />
                  拼接导出 {showConcatPanel ? '▲' : '▼'}
                </button>
                {showConcatPanel && (
                  <div className="mt-3 p-4 rounded-xl bg-muted/30 border border-border/30 space-y-3">
                    <div className="flex items-center gap-2">
                      <Type className="w-3.5 h-3.5 text-muted-foreground" />
                      <label className="text-[10px] flex items-center gap-2">
                        <input type="checkbox" checked={!!concatTitle} onChange={e => setConcatTitle(e.target.checked ? projectName || '' : '')}
                          className="rounded border-border" />
                        片头标题
                      </label>
                      {concatTitle && (
                        <>
                          <input value={concatTitle} onChange={e => setConcatTitle(e.target.value)}
                            className="flex-1 bg-muted border border-border rounded-lg px-2 py-1 text-[11px]" />
                          <input type="number" value={concatTitleDuration} min={1} max={10}
                            onChange={e => setConcatTitleDuration(Number(e.target.value))}
                            className="w-10 bg-muted border border-border rounded-lg px-1 py-1 text-[10px] text-center" />
                          <span className="text-[10px] text-muted-foreground">秒</span>
                        </>
                      )}
                    </div>

                    <div className="flex items-center gap-2">
                      <Scissors className="w-3.5 h-3.5 text-muted-foreground" />
                      <label className="text-[10px] flex items-center gap-2">
                        <input type="checkbox" checked={concatTransition > 0} onChange={e => setConcatTransition(e.target.checked ? 0.3 : 0)}
                          className="rounded border-border" />
                        淡入淡出转场
                      </label>
                      {concatTransition > 0 && (
                        <>
                          <input type="number" value={concatTransition} min={0.1} max={2} step={0.1}
                            onChange={e => setConcatTransition(Number(e.target.value))}
                            className="w-14 bg-muted border border-border rounded-lg px-1 py-1 text-[10px] text-center" />
                          <span className="text-[10px] text-muted-foreground">秒</span>
                        </>
                      )}
                    </div>

                    <div className="flex items-center gap-2">
                      <Type className="w-3.5 h-3.5 text-muted-foreground" />
                      <label className="text-[10px] flex items-center gap-2">
                        <input type="checkbox" checked={concatSubtitle} onChange={e => setConcatSubtitle(e.target.checked)}
                          className="rounded border-border" />
                        从分镜提取字幕
                      </label>
                    </div>

                    <div className="flex items-center gap-2">
                      <Music className="w-3.5 h-3.5 text-muted-foreground" />
                      <label className="text-[10px] flex items-center gap-2">
                        <input type="checkbox" checked={!!concatBgmPath} onChange={e => {
                          if (!concatBgmPath) bgmInputRef.current?.click()
                          else setConcatBgmPath('')
                        }} className="rounded border-border" />
                        背景音乐
                      </label>
                      {concatBgmPath && (
                        <>
                          <span className="text-[10px] text-primary/60 truncate flex-1">{concatBgmPath.split('\\').pop() || concatBgmPath.split('/').pop()}</span>
                          <span className="text-[10px] text-muted-foreground">音量</span>
                          <input type="range" min={5} max={100} value={concatBgmVolume}
                            onChange={e => setConcatBgmVolume(Number(e.target.value))}
                            className="w-20 h-1" />
                          <span className="text-[10px] text-muted-foreground w-8">{concatBgmVolume}%</span>
                        </>
                      )}
                      <input ref={bgmInputRef} type="file" accept="audio/*" onChange={handleBgmUpload} className="hidden" />
                    </div>

                    <button onClick={handleConcat} disabled={concatGenerating}
                      className="w-full mt-2 btn-gradient flex items-center justify-center gap-1.5 px-4 py-2.5 rounded-xl text-sm font-medium disabled:opacity-50"
                      style={{ background: 'linear-gradient(135deg, hsl(150, 60%, 50%), hsl(170, 60%, 45%))' }}>
                      {concatGenerating ? <Loader2 className="w-4 h-4 animate-spin" /> : <Film className="w-4 h-4" />}
                      {concatGenerating ? '正在拼接导出...' : '开始拼接导出'}
                    </button>

                    {concatResult && !concatResult.error && (
                      <div className="mt-2 p-3 rounded-lg bg-green-500/10 border border-green-500/20">
                        <p className="text-[11px] text-green-400">✅ 导出完成</p>
                        <p className="text-[10px] text-muted-foreground mt-0.5">
                          {concatResult.shot_count} 个镜头 · 总时长 {concatResult.total_duration}s
                          {concatResult.title_applied && ' · 片头'} {concatResult.transition_applied && ' · 转场'}
                          {concatResult.subtitle_applied && ' · 字幕'} {concatResult.bgm_applied && ' · BGM'}
                        </p>
                        <a href={`/api/projects/${encodeURIComponent(projectName)}/video/download`} target="_blank" rel="noopener noreferrer"
                          className="inline-flex items-center gap-1 mt-2 px-3 py-1 rounded-lg border border-border text-[11px] hover:bg-muted transition-colors">
                          <Download className="w-3 h-3" /> 下载成片
                        </a>
                      </div>
                    )}
                    {concatResult?.error && (
                      <p className="text-[11px] text-red-400 mt-2">❌ {concatResult.error}</p>
                    )}
                  </div>
                )}
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
