import { useState, useEffect, useRef } from 'react'
import { Sparkles, Loader2, Upload, X, Download, Play, CheckSquare, Square, RefreshCw, ChevronDown, ChevronRight, Film, Music, Type, Scissors, Tag } from 'lucide-react'
import ModelSelector from './ModelSelector'
import ImagePreview from './ImagePreview'
import { fetchVideoResolutions, freeVideoGen, fetchProjectVisualAssets, fetchCharacters, fetchScenes, fetchPhaseContent, fetchConfirmedImages, fetchProjectAssetLibrary, fetchSettings, fetchVideoShotStatus, fetchImageDemands, fetchGenerationHistory } from '../lib/api'
import type { AssetLibrary } from '../lib/types'

interface RefFile {
  file: File
  preview: string
  label: string
  type: 'character' | 'scene' | 'image' | 'audio'
}

interface HistoryVideo {
  url: string
  label: string
  time: number
}

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
  const [imageDemands, setImageDemands] = useState<any>(null)
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
  const [selectedProp, setSelectedProp] = useState<string | null>(null)
  const [expandedCharGroups, setExpandedCharGroups] = useState<Record<string, boolean>>({})
  const [expandedSceneTemp, setExpandedSceneTemp] = useState<Record<string, boolean>>({})

  // Generate mode
  const [genMode, setGenMode] = useState<'single' | 'batch'>('single')
  const [batchStart, setBatchStart] = useState(1)
  const [batchEnd, setBatchEnd] = useState(10)

  // Prompt
  const [prompt, setPrompt] = useState('')

  // Reference images
  const [refFiles, setRefFiles] = useState<RefFile[]>([])
  const [editingLabel, setEditingLabel] = useState<number | null>(null)
  const [historyVideos, setHistoryVideos] = useState<HistoryVideo[]>([])
  const [projectImages, setProjectImages] = useState<{ characters: Record<string, { name: string; url: string }[]>; scenes: Record<string, { name: string; url: string }[]> }>({ characters: {}, scenes: {} })
  const [confirmedImages, setConfirmedImages] = useState<{ characters: Record<string, { name: string; url: string }[]>; scenes: Record<string, { name: string; url: string }[]> }>({ characters: {}, scenes: {} })
  const [assetLibrary, setAssetLibrary] = useState<AssetLibrary | null>(null)
  const [showAllVersions, setShowAllVersions] = useState(false)
  const [previewSrc, setPreviewSrc] = useState<string | null>(null)

  // Parameters
  const [videoModel, setVideoModel] = useState('')
  const [resolutions, setResolutions] = useState<string[]>([])
  const [ratioGroups, setRatioGroups] = useState<Record<string, string[]>>({})
  const [videoDurations, setVideoDurations] = useState<number[]>([5, 10])
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

  const [refUrlInput, setRefUrlInput] = useState('')
  const [showRefHistory, setShowRefHistory] = useState(false)
  const [refHistoryImages, setRefHistoryImages] = useState<{ name: string; url: string }[]>([])
  const [refHistoryLoading, setRefHistoryLoading] = useState(false)

  // Shots expanded state
  const [expandedEpisodes, setExpandedEpisodes] = useState<Record<string, boolean>>({})
  const [expandedScenes, setExpandedScenes] = useState<Record<string, boolean>>({})

  useEffect(() => {
    fetchVideoResolutions().then(r => {
      setResolutions(r.resolutions)
      setRatioGroups(r.groups)
      setVideoDurations((r as any).durations || [5, 10])
      const ratios = Object.keys(r.groups)
      const first = ratios.includes('16:9') ? '16:9' : (ratios[0] || '')
      setSelectedRatio(first)
      setVideoResolution(r.resolutions[0] || '1280x720')
    })
  }, [])

  useEffect(() => {
    if (!videoModel) return
    fetchVideoResolutions(videoModel).then(r => {
      setResolutions(r.resolutions)
      setRatioGroups(r.groups)
      setVideoDurations((r as any).durations || [5, 10])
      const ratios = Object.keys(r.groups)
      const first = ratios.includes('16:9') ? '16:9' : (ratios[0] || '')
      setSelectedRatio(first)
      setVideoResolution(r.resolutions[0] || '1280x720')
      const durs = (r as any).durations || [5, 10]
      setDuration(durs[0])
    })
  }, [videoModel])

  useEffect(() => {
    if (promptRef.current) {
      promptRef.current.style.height = 'auto'
      promptRef.current.style.height = promptRef.current.scrollHeight + 'px'
    }
  }, [prompt])

  useEffect(() => {
    fetchSettings().then(s => {
      const m = (s as any)?.aggregated_video_model || (s as any)?.video_model
      if (m && !videoModel) setVideoModel(m)
    }).catch(() => {})
  }, [])

  useEffect(() => {
    if (!projectName) return
    setLoading(true)
    Promise.all([
      fetchImageDemands(projectName).then(data => {
        setImageDemands(data)
        if (data?.characters) setCharacters(data.characters)
      }),
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
  const addRefFile = (file: File, label: string, type: RefFile['type']) => {
    const reader = new FileReader()
    reader.onload = (ev) => setRefFiles(prev => [...prev, { file, preview: ev.target?.result as string, label, type }])
    reader.readAsDataURL(file)
  }

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    Array.from(e.target.files || []).forEach(f => addRefFile(f, '手动上传', 'image'))
  }

  const removeFile = (i: number) => setRefFiles(prev => prev.filter((_, idx) => idx !== i))

  const updateLabel = (i: number, label: string) => {
    setRefFiles(prev => prev.map((rf, idx) => idx === i ? { ...rf, label } : rf))
    setEditingLabel(null)
  }

  const handleUrlAdd = async () => {
    const u = refUrlInput.trim()
    if (!u) return
    try {
      const resp = await fetch(u)
      const blob = await resp.blob()
      const file = new File([blob], 'ref_url.png', { type: blob.type || 'image/png' })
      addRefFile(file, 'URL图片', 'image')
    } catch {}
    setRefUrlInput('')
  }

  const openRefHistory = async () => {
    setShowRefHistory(true)
    setRefHistoryLoading(true)
    try {
      const h = await fetchGenerationHistory()
      const all = [...(h.images_free || []), ...(h.images_project || [])]
      setRefHistoryImages(all)
    } catch {} finally {
      setRefHistoryLoading(false)
    }
  }

  const addHistoryRef = async (url: string) => {
    try {
      const resp = await fetch(url)
      const blob = await resp.blob()
      const file = new File([blob], 'history_ref.png', { type: blob.type || 'image/png' })
      addRefFile(file, '历史作品', 'image')
    } catch {}
  }

  const addProjectImage = async (url: string, name: string) => {
    const isChar = selectedCharNames.includes(name) || Object.keys(confirmedImages.characters).includes(name)
    const label = isChar ? `角色·${name}` : `场景·${name}`
    const type: RefFile['type'] = isChar ? 'character' : 'scene'
    try {
      const resp = await fetch(url)
      const blob = await resp.blob()
      const file = new File([blob], `${name}.png`, { type: 'image/png' })
      addRefFile(file, label, type)
    } catch {}
  }

  const detectTypeFromName = (name: string): RefFile['type'] => {
    if (selectedCharNames.includes(name)) return 'character'
    if (selectedSceneNames.includes(name)) return 'scene'
    return 'image'
  }

  // Prompt injection for reference labels
  const buildPromptWithLabels = (basePrompt: string) => {
    const labeled = refFiles.filter(rf => rf.label && rf.label !== '手动上传' && rf.label !== 'URL图片' && rf.label !== '历史作品')
    if (labeled.length === 0) return basePrompt
    const refLines = labeled.map((rf, i) => `图${i+1}=${rf.label}`).join('\n')
    return `[参考图标注]\n${refLines}\n[/参考图标注]\n\n${basePrompt}`
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
      const labeledPrompt = buildPromptWithLabels(prompt)
      const files = refFiles.length > 0 ? refFiles.map(f => f.file) : undefined
      const res = await freeVideoGen(labeledPrompt, files, videoModel, videoResolution || undefined, undefined, generateAudio, duration)
      setResult(res)
      if (res.video_url) {
        setHistoryVideos(prev => [{ url: res.video_url, label: '单次生成', time: Date.now() }, ...prev.slice(0, 19)])
      }
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

  const restoreCheckpoint = async (proj: string) => {
    try {
      const data = await fetchVideoShotStatus(proj)
      if (data.shotStatuses && Object.keys(data.shotStatuses).length > 0) {
        setShotStatuses(data.shotStatuses || {})
        setShotVideoUrls(data.shotVideoUrls || {})
        setBatchedBefore(true)
      }
    } catch {}
    try {
      const raw = localStorage.getItem(`video_gen_cp_${proj}`)
      if (!raw) return
      const cp = JSON.parse(raw)
      if (Date.now() - cp.savedAt > 86400000) {
        localStorage.removeItem(`video_gen_cp_${proj}`)
        return
      }
      if (cp.shotStatuses && Object.keys(cp.shotStatuses).length > 0) {
        setShotStatuses(prev => ({ ...cp.shotStatuses, ...prev }))
        setShotVideoUrls(prev => ({ ...cp.shotVideoUrls, ...prev }))
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
      <div className="premium-panel p-5 mb-6 premium-glow-bottom">
        <div className="flex items-end gap-4">
          <div className="flex-1">
            <label className="premium-label">当前项目</label>
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
        {/* Left: Characters + Scenes + Props */}
        <div className="lg:col-span-1 space-y-4">
          <div className="premium-subpanel p-4 premium-glow-bottom">
            <div className="flex items-center justify-between mb-2">
              <h3 className="font-semibold text-xs" style={{ color: 'rgba(167, 139, 250, 0.7)' }}>🧑 角色 ({(imageDemands?.character_groups || []).length}组)</h3>
              {selectedCharNames.length > 0 && <span className="text-[10px] px-2 py-0.5 rounded-full bg-primary/20 text-primary font-medium">{selectedCharNames.length} 已选</span>}
            </div>
            {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : (imageDemands?.character_groups || []).length === 0 ? (
              <p className="text-[10px]" style={{ color: 'rgba(255, 255, 255, 0.3)' }}>暂未分析，请先生成需求清单</p>
            ) : (
              <div className="space-y-1 max-h-48 overflow-y-auto">
                {(imageDemands?.character_groups || []).map((group: any) => {
                  const members = group.members || []
                  const baseMember = members.find((m: any) => m.is_base) || members[0]
                  const baseName = baseMember?.name || group.name
                  const isSelected = selectedCharNames.includes(baseName) || members.some((m: any) => selectedCharNames.includes(m.name))
                  const hasChildren = members.length > 1
                  const expanded = expandedCharGroups[group.name]
                  const imgs = confirmedImages.characters[baseName]
                  const charPropsMap = imageDemands?.char_props || {}
                  const groupProps: any[] = []
                  for (const [owner, items] of Object.entries(charPropsMap)) {
                    if (owner === group.name || owner.startsWith(group.name + '（') || owner.startsWith(group.name + '(') || owner === group.name.replace(/^系统/, '').replace(/【】/, '')) {
                      groupProps.push(...(items as any[]))
                    }
                  }
                  return (
                    <div key={group.name}>
                      <div onClick={() => toggleChar(baseName)}
                        className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg cursor-pointer text-[11px] transition-all ${
                          isSelected ? 'bg-primary/20 text-primary font-medium border border-primary/30' : 'hover:bg-muted/80 text-muted-foreground border border-transparent'
                        }`}>
                        {hasChildren && (
                          <button onClick={(e) => { e.stopPropagation(); setExpandedCharGroups(prev => ({ ...prev, [group.name]: !prev[group.name] })) }}
                            className="p-0.5 hover:text-foreground">
                            {expanded ? <ChevronDown className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />}
                          </button>
                        )}
                        {isSelected ? <CheckSquare className="w-3 h-3 text-primary flex-shrink-0" /> : <Square className="w-3 h-3 text-muted-foreground/40 flex-shrink-0" />}
                        <span className="flex-1 truncate">{group.name}</span>
                        {imgs?.length ? <img src={imgs[0].url} alt="" className="w-5 h-5 rounded object-cover border border-border/40" onClick={e => { e.stopPropagation(); setPreviewSrc(imgs[0].url) }} /> : null}
                      </div>
                      {expanded && hasChildren && members.filter((m: any) => !m.is_base).map((member: any) => {
                        const mSel = selectedCharNames.includes(member.name)
                        const mImgs = confirmedImages.characters[member.name]
                        return (
                          <div key={member.name} onClick={() => toggleChar(member.name)}
                            className={`flex items-center gap-1.5 ml-4 px-2.5 py-1.5 rounded-lg cursor-pointer text-[11px] transition-all ${
                              mSel ? 'bg-primary/15 text-primary font-medium' : 'hover:bg-muted text-muted-foreground/80'
                            }`}>
                            <ChevronRight className="w-2.5 h-2.5 opacity-50" />
                            <span className="truncate">{member.variant_name || member.name}</span>
                            {mImgs?.length ? <img src={mImgs[0].url} alt="" className="w-4 h-4 rounded object-cover border border-border/40" onClick={e => { e.stopPropagation(); setPreviewSrc(mImgs[0].url) }} /> : null}
                          </div>
                        )
                      })}
                      {expanded && groupProps.length > 0 && (
                        <div className="ml-4 space-y-0.5 mt-0.5 mb-1">
                          <div className="text-[9px] text-muted-foreground/50 px-1">🔧 随身道具 · {groupProps.length}个</div>
                          {groupProps.map((prop: any) => (
                            <div key={prop.name} onClick={(e) => { e.stopPropagation(); setSelectedProp(prop.name) }}
                              className={`flex items-center gap-1.5 px-3 py-0.5 rounded cursor-pointer text-[10px] transition-all ${
                                selectedProp === prop.name ? 'bg-primary/15 text-primary font-medium' : 'hover:bg-muted text-muted-foreground/60'
                              }`}>
                              <span className="truncate">{prop.name}</span>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  )
                })}
              </div>
            )}
          </div>

          <div className="premium-subpanel p-4 premium-glow-bottom">
            <div className="flex items-center justify-between mb-2">
              <h3 className="font-semibold text-xs" style={{ color: 'rgba(167, 139, 250, 0.7)' }}>🏔️ 场景 ({(imageDemands?.scene_groups || []).length}组)</h3>
              {selectedSceneNames.length > 0 && <span className="text-[10px] px-2 py-0.5 rounded-full bg-primary/20 text-primary font-medium">{selectedSceneNames.length} 已选</span>}
            </div>
            {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : (imageDemands?.scene_groups || []).length === 0 ? (
              <p className="text-[10px]" style={{ color: 'rgba(255, 255, 255, 0.3)' }}>暂未分析</p>
            ) : (
              <div className="space-y-1 max-h-48 overflow-y-auto">
                {(imageDemands?.scene_groups || []).map((group: any) => {
                  const members = group.members || []
                  const baseMember = members.find((m: any) => m.is_base) || members[0]
                  const baseName = baseMember?.name || group.name
                  const isSelected = selectedSceneNames.includes(baseName) || members.some((m: any) => selectedSceneNames.includes(m.name))
                  const hasChildren = members.length > 1
                  const expanded = expandedSceneTemp[group.name]
                  const imgs = confirmedImages.scenes[baseName]
                  return (
                    <div key={group.name}>
                      <div onClick={() => toggleScene(baseName)}
                        className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg cursor-pointer text-[11px] transition-all ${
                          isSelected ? 'bg-primary/20 text-primary font-medium border border-primary/30' : 'hover:bg-muted/80 text-muted-foreground border border-transparent'
                        }`}>
                        {hasChildren && (
                          <button onClick={(e) => { e.stopPropagation(); setExpandedSceneTemp(prev => ({ ...prev, [group.name]: !prev[group.name] })) }}
                            className="p-0.5 hover:text-foreground">
                            {expanded ? <ChevronDown className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />}
                          </button>
                        )}
                        {isSelected ? <CheckSquare className="w-3 h-3 text-primary flex-shrink-0" /> : <Square className="w-3 h-3 text-muted-foreground/40 flex-shrink-0" />}
                        <span className="flex-1 truncate">{group.name}</span>
                        {imgs?.length ? <img src={imgs[0].url} alt="" className="w-5 h-5 rounded object-cover border border-border/40" onClick={e => { e.stopPropagation(); setPreviewSrc(imgs[0].url) }} /> : null}
                      </div>
                      {expanded && hasChildren && members.filter((m: any) => !m.is_base).map((member: any) => {
                        const mSel = selectedSceneNames.includes(member.name)
                        const mImgs = confirmedImages.scenes[member.name]
                        return (
                          <div key={member.name} onClick={() => toggleScene(member.name)}
                            className={`flex items-center gap-1.5 ml-4 px-2.5 py-1.5 rounded-lg cursor-pointer text-[11px] transition-all ${
                              mSel ? 'bg-primary/15 text-primary font-medium' : 'hover:bg-muted text-muted-foreground/80'
                            }`}>
                            <ChevronRight className="w-2.5 h-2.5 opacity-50" />
                            <span className="truncate">{member.variant_name || member.name}</span>
                            {mImgs?.length ? <img src={mImgs[0].url} alt="" className="w-4 h-4 rounded object-cover border border-border/40" onClick={e => { e.stopPropagation(); setPreviewSrc(mImgs[0].url) }} /> : null}
                          </div>
                        )
                      })}
                    </div>
                  )
                })}
              </div>
            )}
          </div>

          {(imageDemands?.cross_scene_props || []).length > 0 && (
            <div className="premium-subpanel p-4 premium-glow-bottom">
              <h3 className="font-semibold text-xs mb-2" style={{ color: 'rgba(167, 139, 250, 0.7)' }}>🔧 跨场景道具 ({(imageDemands?.cross_scene_props).length}个)</h3>
              <div className="space-y-1 max-h-32 overflow-y-auto">
                {(imageDemands?.cross_scene_props || []).map((prop: any) => (
                  <div key={prop.name} onClick={() => { setSelectedProp(selectedProp === prop.name ? null : prop.name) }}
                    className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg cursor-pointer text-[11px] transition-all ${
                      selectedProp === prop.name ? 'bg-primary/20 text-primary font-medium border border-primary/30' : 'hover:bg-muted/80 text-muted-foreground border border-transparent'
                    }`}>
                    {selectedProp === prop.name ? <CheckSquare className="w-3 h-3 text-primary flex-shrink-0" /> : <Square className="w-3 h-3 text-muted-foreground/40 flex-shrink-0" />}
                    <span className="truncate">{prop.name}</span>
                    <span className="text-[8px] text-muted-foreground/40 flex-shrink-0 ml-auto">{prop.scene_count || 0}景</span>
                  </div>
                ))}
              </div>
            </div>
          )}
          {(imageDemands?.scene_props || []).length > 0 && (
            <div className="premium-subpanel p-4 premium-glow-bottom">
              <h3 className="font-semibold text-xs mb-2" style={{ color: 'rgba(167, 139, 250, 0.7)' }}>🏗️ 场景道具 ({(imageDemands?.scene_props).length}个)</h3>
              <div className="space-y-1 max-h-40 overflow-y-auto">
                {(imageDemands?.scene_props || []).map((prop: any) => (
                  <div key={prop.name} onClick={() => { setSelectedProp(selectedProp === prop.name ? null : prop.name) }}
                    className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg cursor-pointer text-[11px] transition-all ${
                      selectedProp === prop.name ? 'bg-primary/20 text-primary font-medium border border-primary/30' : 'hover:bg-muted/80 text-muted-foreground border border-transparent'
                    }`}>
                    {selectedProp === prop.name ? <CheckSquare className="w-3 h-3 text-primary flex-shrink-0" /> : <Square className="w-3 h-3 text-muted-foreground/40 flex-shrink-0" />}
                    <span className="truncate">{prop.name}</span>
                    <span className="text-[8px] text-muted-foreground/40 flex-shrink-0 ml-auto">{prop.scene_count || 0}景</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Right: Shots + Prompt + Params + Generate */}
        <div className="lg:col-span-2 space-y-3">
          {/* Shots list — compact */}
          <div className="premium-panel p-3">
            <div className="flex items-center justify-between mb-2">
              <h3 className="font-semibold text-xs">
                🎬 分镜 ({shots.length}) {selectedShotIndices.length > 0 && <span className="text-primary">· 已选{selectedShotIndices.length}镜</span>}
              </h3>
              <div className="flex items-center gap-1.5">
                <button onClick={toggleAllShots} className="text-[10px] text-muted-foreground hover:text-primary px-1.5 py-0.5 rounded hover:bg-muted transition-all">
                  {selectedShotIndices.length === shots.length && shots.length > 0 ? '取消全选' : '全选'}
                </button>
                <button onClick={() => loadShots(projectName)} className="p-1 rounded hover:bg-muted"><RefreshCw className="w-3 h-3" /></button>
              </div>
            </div>
            {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : episodes.length === 0 ? (
              <p className="text-[10px] text-muted-foreground">暂无分镜内容</p>
            ) : (
              <div className="space-y-0.5 max-h-[22vh] overflow-y-auto">
                {episodes.map((ep, epIdx) => {
                  const epExpanded = expandedEpisodes[ep.label] ?? (epIdx === 0)
                  const setEpExp = (v: boolean) => setExpandedEpisodes(prev => ({ ...prev, [ep.label]: v }))
                  const epDone = ep.scenes.reduce((s, sc) => s + sc.shots.filter(sh => shotStatuses[sh.index] === 'done').length, 0)
                  const epTotal = ep.scenes.reduce((s, sc) => s + sc.shots.length, 0)
                  return (
                    <div key={ep.label}>
                      <div className="flex items-center gap-1">
                        <button onClick={() => setEpExp(!epExpanded)} className="p-0.5 hover:text-foreground flex-shrink-0">
                          {epExpanded ? <ChevronDown className="w-2.5 h-2.5" /> : <ChevronRight className="w-2.5 h-2.5" />}
                        </button>
                        <span className="text-[10px] font-medium text-muted-foreground flex-1 truncate">
                          📺 {ep.label}
                        </span>
                        <span className="text-[9px] text-muted-foreground/50 flex-shrink-0">{epDone}/{epTotal}</span>
                      </div>
                      {epExpanded && (
                        <div className="ml-4 flex flex-wrap gap-1 py-0.5">
                          {ep.scenes.map(sc => {
                            const scExpanded = expandedScenes[`${ep.label}/${sc.label}`] ?? false
                            const setScExp = (v: boolean) => setExpandedScenes(prev => ({ ...prev, [`${ep.label}/${sc.label}`]: v }))
                            return (
                              <div key={`${ep.label}/${sc.label}`}>
                                <button onClick={() => setScExp(!scExpanded)}
                                  className="text-[9px] text-muted-foreground/60 hover:text-muted-foreground px-1.5 py-0.5 rounded hover:bg-muted/40 transition-all">
                                  🎞 {sc.label} ({sc.shots.length})
                                </button>
                                {scExpanded && (
                                  <div className="flex flex-wrap gap-0.5 ml-1 mt-0.5 mb-1">
                                    {sc.shots.map(shot => {
                                      const sel = selectedShotIndices.includes(shot.index)
                                      const status = shotStatuses[shot.index]
                                      return (
                                        <button key={shot.index} onClick={() => toggleShot(shot.index)}
                                          className={`text-[9px] px-1.5 py-0.5 rounded transition-all flex items-center gap-0.5 ${
                                            sel ? 'bg-primary/20 text-primary font-medium border border-primary/30' :
                                            status === 'done' ? 'bg-green-500/5 text-green-400/80' :
                                            status === 'failed' ? 'bg-red-500/5 text-red-400/80' :
                                            'hover:bg-muted text-muted-foreground/70 border border-transparent'
                                          }`}>
                                          镜头{shot.shot_number}
                                          {status === 'done' && ' ✓'}
                                          {status === 'failed' && ' ✗'}
                                        </button>
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
          <div className="premium-panel p-5">
            <div className="premium-header">
              <label className="premium-label" style={{ marginBottom: 0 }}>提示词</label>
              <button onClick={() => setPrompt('')} className="text-[10px] text-rose-400/60 hover:text-rose-400 px-2 py-0.5 rounded hover:bg-rose-400/5 transition-all">清空</button>
            </div>
            <textarea ref={promptRef} value={prompt} onChange={e => setPrompt(e.target.value)}
              placeholder={`在左侧勾选角色/场景/分镜，提示词将自动组合。\n也可以手动输入。`}
              className="w-full premium-input rounded-xl px-4 py-3 min-h-[8rem] resize-none text-sm font-mono" />

            {/* Reference images */}
            <div className="mt-4">
              <div className="flex items-center justify-between mb-2">
                <span className="text-[10px] text-muted-foreground font-medium">
                  参考图 {refFiles.length > 0 && <span className="text-primary">({refFiles.length})</span>}
                </span>
                <div className="flex items-center gap-1">
                  <button onClick={openRefHistory} className="text-[10px] text-muted-foreground hover:text-primary px-1.5 py-0.5 rounded hover:bg-primary/10 transition-all">
                    历史
                  </button>
                  <button onClick={() => fileInputRef.current?.click()} className="text-[10px] text-primary px-1.5 py-0.5 rounded hover:bg-primary/10 transition-all">
                    上传
                  </button>
                  <input ref={fileInputRef} type="file" accept="image/*" multiple className="hidden" onChange={handleFileSelect} />
                </div>
              </div>

              {/* URL paste row */}
              <div className="flex items-center gap-1 mb-2">
                <input value={refUrlInput} onChange={e => setRefUrlInput(e.target.value)}
                  onKeyDown={e => { if (e.key === 'Enter') { e.preventDefault(); handleUrlAdd() } }}
                  placeholder="粘贴图片 URL，回车添加..."
                  className="flex-1 bg-transparent border-b border-border/30 pb-1 text-[10px] text-muted-foreground outline-none focus:border-primary/30 transition-colors" />
                <button onClick={handleUrlAdd} disabled={!refUrlInput.trim()}
                  className="text-[10px] text-primary hover:underline disabled:opacity-30 flex-shrink-0 px-1">添加</button>
              </div>

              {refFiles.length > 0 && (
                <div className="flex flex-wrap gap-2 mb-3">
                  {refFiles.map((entry, i) => (
                    <div key={i} className="relative group flex flex-col items-center gap-0.5">
                      <div className="relative">
                        <img src={entry.preview} alt="" className="w-14 h-14 object-cover rounded-xl border border-border/40" />
                        <button onClick={() => removeFile(i)}
                          className="absolute -top-1.5 -right-1.5 w-4 h-4 rounded-full bg-red-500 text-white flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity">
                          <X className="w-2.5 h-2.5" />
                        </button>
                        {entry.type === 'audio' && (
                          <div className="absolute inset-0 flex items-center justify-center bg-black/40 rounded-xl">
                            <Music className="w-4 h-4 text-white/70" />
                          </div>
                        )}
                      </div>
                      {editingLabel === i ? (
                        <input autoFocus value={entry.label}
                          onChange={e => setRefFiles(prev => prev.map((rf, idx) => idx === i ? { ...rf, label: e.target.value } : rf))}
                          onBlur={e => updateLabel(i, e.target.value)}
                          onKeyDown={e => { if (e.key === 'Enter') updateLabel(i, (e.target as HTMLInputElement).value) }}
                          className="text-[8px] w-16 text-center bg-muted border border-border rounded px-0.5 outline-none focus:border-primary/50" />
                      ) : (
                        <span onClick={() => setEditingLabel(i)}
                          className={`text-[8px] text-center leading-tight cursor-pointer hover:text-primary truncate max-w-[56px] ${
                            entry.label === '手动上传' || entry.label === 'URL图片' || entry.label === '历史作品'
                              ? 'text-muted-foreground/40' : 'text-muted-foreground'
                          }`}>
                          {entry.label}
                        </span>
                      )}
                    </div>
                  ))}
                </div>
              )}

              {/* History popup */}
              {showRefHistory && (
                <div className="mb-3 p-3 rounded-xl" style={{ background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.08)' }}>
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-[10px] text-muted-foreground">历史作品 · 点击添加为参考</span>
                    <button onClick={() => setShowRefHistory(false)} className="text-[9px] text-muted-foreground hover:text-foreground">关闭</button>
                  </div>
                  {refHistoryLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : (
                    <div className="flex flex-wrap gap-1.5 max-h-32 overflow-y-auto">
                      {refHistoryImages.slice(0, 40).map((img, i) => (
                        <img key={i} src={img.url} alt={img.name}
                          onClick={() => addHistoryRef(img.url)}
                          className="w-12 h-12 object-cover rounded border border-border/40 cursor-pointer hover:ring-1 hover:ring-primary/50 transition-all"
                          title={img.name} />
                      ))}
                    </div>
                  )}
                </div>
              )}

              {/* 项目已生成图库 */}
              {Object.keys(confirmedImages.characters).length > 0 && (
                <div className="mb-2">
                  <p className="text-[10px] text-muted-foreground mb-1.5">👤 角色定妆照 · 点击添加为参考</p>
                  <div className="flex flex-wrap gap-1.5">
                    {Object.entries(confirmedImages.characters).map(([name, imgs]) => {
                      const isSelected = selectedCharNames.includes(name)
                      const img = (imgs as any[])?.[0]
                      if (!img) return null
                      return (
                        <div key={name} onClick={() => addProjectImage(img.url, name)}
                          className={`relative w-14 h-14 rounded-lg overflow-hidden cursor-pointer border-2 transition-all group ${isSelected ? 'border-primary shadow-lg shadow-primary/20' : 'border-border hover:border-primary/50'}`}
                          title={isSelected ? `${name} (已选中)` : `点击添加 ${name}`}>
                          <img src={img.url} alt={name} className="w-full h-full object-cover" />
                          <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/70 to-transparent pt-3 pb-0.5 text-[8px] text-white text-center truncate">
                            {name}
                          </div>
                        </div>
                      )
                    })}
                  </div>
                </div>
              )}
              {Object.keys(confirmedImages.scenes).length > 0 && (
                <div>
                  <p className="text-[10px] text-muted-foreground mb-1.5">🌆 场景概念图 · 点击添加为参考</p>
                  <div className="flex flex-wrap gap-1.5">
                    {Object.entries(confirmedImages.scenes).map(([name, imgs]) => {
                      const isSelected = selectedSceneNames.includes(name)
                      const img = (imgs as any[])?.[0]
                      if (!img) return null
                      return (
                        <div key={name} onClick={() => addProjectImage(img.url, name)}
                          className={`relative w-14 h-14 rounded-lg overflow-hidden cursor-pointer border-2 transition-all group ${isSelected ? 'border-primary shadow-lg shadow-primary/20' : 'border-border hover:border-primary/50'}`}
                          title={isSelected ? `${name} (已选中)` : `点击添加 ${name}`}>
                          <img src={img.url} alt={name} className="w-full h-full object-cover" />
                          <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/70 to-transparent pt-3 pb-0.5 text-[8px] text-white text-center truncate">
                            {name}
                          </div>
                        </div>
                      )
                    })}
                  </div>
                </div>
              )}
            </div>

            {/* Parameters */}
            <div className="space-y-2.5 mt-3">
              <div className="grid grid-cols-2 md:grid-cols-5 gap-2">
                <div className="md:col-span-2">
                  <label className="premium-label" style={{ fontSize: '0.6rem' }}>模型</label>
                  <ModelSelector type="video" value={videoModel} onChange={setVideoModel} />
                </div>
                <div>
                  <label className="premium-label" style={{ fontSize: '0.6rem' }}>比例</label>
                  <select value={selectedRatio} onChange={e => { const rs = ratioGroups[e.target.value]; setSelectedRatio(e.target.value); if (rs?.length) setVideoResolution(rs[0]) }}
                    className="w-full premium-select rounded-lg px-2 py-1.5 text-[10px]">
                    {Object.keys(ratioGroups).map(r => (<option key={r} value={r}>{r}</option>))}
                  </select>
                </div>
                <div>
                  <label className="premium-label" style={{ fontSize: '0.6rem' }}>分辨率</label>
                  <select value={videoResolution} onChange={e => setVideoResolution(e.target.value)} className="w-full premium-select rounded-lg px-2 py-1.5 text-[10px]">
                    {(ratioGroups[selectedRatio] || resolutions).map(r => (<option key={r} value={r}>{r}</option>))}
                  </select>
                </div>
                <div>
                  <label className="premium-label" style={{ fontSize: '0.6rem' }}>时长(秒)</label>
                  <div className="flex gap-0.5">
                    <select value={duration} onChange={e => { const v = Number(e.target.value); if (v === -1) setDuration(15); else setDuration(v) }}
                      className="w-full premium-select rounded-lg px-1 py-1.5 text-[10px]">
                      {videoDurations.map(d => (<option key={d} value={d}>{d}秒</option>))}
                      <option value={-1}>自定义</option>
                    </select>
                    {!videoDurations.includes(duration) && (
                      <input type="number" min={2} max={30} value={duration}
                        onChange={e => setDuration(Math.max(2, Math.min(30, Number(e.target.value))))}
                        className="w-14 premium-input rounded-lg px-1 py-1.5 text-[10px] text-center" />
                    )}
                  </div>
                </div>
              </div>
              <div className="flex items-center gap-3 flex-wrap">
                <label className="relative inline-flex items-center cursor-pointer">
                  <input type="checkbox" className="sr-only peer" checked={generateAudio} onChange={e => setGenerateAudio(e.target.checked)} />
                  <div className="w-7 h-3.5 bg-muted rounded-full peer peer-checked:after:translate-x-full after:content-[''] after:absolute after:top-[1px] after:left-[1px] after:bg-white after:rounded-full after:h-3 after:w-3 after:transition-all peer-checked:bg-primary"></div>
                  <span className="text-[9px] text-muted-foreground ml-1.5">音频</span>
                </label>
                {generateAudio && (
                  <label className="relative cursor-pointer">
                    <input type="file" accept="audio/*" className="hidden"
                      onChange={e => { const f = e.target.files?.[0]; if (f) addRefFile(f, '音色参考', 'audio') }} />
                    <span className="text-[9px] px-2 py-1 rounded transition-all hover:bg-muted text-muted-foreground border border-border/30">
                      🔊 音色参考
                    </span>
                  </label>
                )}
                <label className="relative inline-flex items-center cursor-pointer">
                  <input type="checkbox" className="sr-only peer" checked={cameraFixed} onChange={e => setCameraFixed(e.target.checked)} />
                  <div className="w-7 h-3.5 bg-muted rounded-full peer peer-checked:after:translate-x-full after:content-[''] after:absolute after:top-[1px] after:left-[1px] after:bg-white after:rounded-full after:h-3 after:w-3 after:transition-all peer-checked:bg-primary"></div>
                  <span className="text-[9px] text-muted-foreground ml-1.5">固定镜头</span>
                </label>
                <div className="flex items-center gap-1">
                  <span className="text-[9px] text-muted-foreground/50">种子</span>
                  <input type="number" value={seed} onChange={e => setSeed(Number(e.target.value))}
                    placeholder="随机" className="w-12 text-[9px] premium-input rounded px-1.5 py-1 text-center" />
                </div>
              </div>
            </div>

            {/* Generate buttons */}
            <div className="flex items-center gap-2 mt-3">
              <button onClick={handleGenerate} disabled={generating || !prompt.trim()}
                className="btn-gradient flex items-center gap-1 px-4 py-2 rounded-xl text-xs font-medium disabled:opacity-50">
                {generating && genMode === 'single' ? <Loader2 className="w-3 h-3 animate-spin" /> : <Play className="w-3 h-3" />}
                {generating && genMode === 'single' ? `生成中 ${elapsed}s` : refFiles.length > 0 ? `图生 (${refFiles.length}图)` : '文生'}
              </button>

              {shots.length > 0 && (
                <div className="flex items-center gap-1.5 border-l border-border pl-2">
                  <span className="text-[9px] text-muted-foreground/50">批量</span>
                  <input type="number" min={1} max={shots.length} value={batchStart}
                    onChange={e => setBatchStart(Number(e.target.value))}
                    className="w-10 premium-input rounded px-1 py-1 text-[10px] text-center" />
                  <span className="text-[9px] text-muted-foreground/50">-</span>
                  <input type="number" min={1} max={shots.length} value={batchEnd}
                    onChange={e => setBatchEnd(Number(e.target.value))}
                    className="w-10 premium-input rounded px-1 py-1 text-[10px] text-center" />
                  <button onClick={handleBatchGenerate} disabled={generating}
                    className="px-3 py-1 rounded-lg border border-white/10 text-[10px] hover:bg-white/[0.04] transition-colors disabled:opacity-50">
                    {generating && genMode === 'batch' ? <Loader2 className="w-3 h-3 inline animate-spin mr-1" /> : null}
                    生成
                  </button>
                  {generating && (
                    <button onClick={() => { batchPausedRef.current = true; setBatchPaused(true) }}
                      className="flex items-center gap-1 px-2 py-1 rounded-lg border border-amber-400/30 text-amber-400 text-[10px] hover:bg-amber-500/10 transition-colors">
                      ⏸
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
                  <div className="mt-3 p-4 rounded-xl premium-inset space-y-3">
                    <div className="flex items-center gap-2">
                      <Type className="w-3.5 h-3.5" style={{ color: 'rgba(167, 139, 250, 0.5)' }} />
                      <label className="text-[10px] flex items-center gap-2">
                        <input type="checkbox" checked={!!concatTitle} onChange={e => setConcatTitle(e.target.checked ? projectName || '' : '')}
                          className="rounded border-border" />
                        片头标题
                      </label>
                      {concatTitle && (
                        <>
                          <input value={concatTitle} onChange={e => setConcatTitle(e.target.value)}
                            className="flex-1 premium-input rounded-lg px-2 py-1 text-[11px]" />
                          <input type="number" value={concatTitleDuration} min={1} max={10}
                            onChange={e => setConcatTitleDuration(Number(e.target.value))}
                            className="w-10 premium-input rounded-lg px-1 py-1 text-[10px] text-center" />
                          <span className="text-[10px]" style={{ color: 'rgba(167, 139, 250, 0.5)' }}>秒</span>
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

          {/* History: recently generated videos */}
          {(historyVideos.length > 0 || Object.values(shotVideoUrls).some(Boolean)) && (
            <div className="premium-panel p-3">
              <h3 className="font-semibold text-[10px] mb-2">📽️ 已生成视频</h3>
              <div className="flex flex-wrap gap-1.5 max-h-32 overflow-y-auto">
                {Object.entries(shotVideoUrls).filter(([, url]) => url).map(([idx, url]) => (
                  <div key={`shot-${idx}`} className="relative group">
                    <video src={url} className="w-20 h-14 object-cover rounded border border-border/40"
                      onMouseEnter={e => (e.target as HTMLVideoElement).play()}
                      onMouseLeave={e => { (e.target as HTMLVideoElement).pause(); (e.target as HTMLVideoElement).currentTime = 0 }} />
                    <div className="absolute bottom-0 left-0 right-0 bg-black/60 text-[7px] text-white text-center py-0.5 leading-none">
                      镜头{idx}
                    </div>
                  </div>
                ))}
                {historyVideos.map((v, i) => (
                  <div key={`hist-${i}`} className="relative group">
                    <video src={v.url} className="w-20 h-14 object-cover rounded border border-border/40"
                      onMouseEnter={e => (e.target as HTMLVideoElement).play()}
                      onMouseLeave={e => { (e.target as HTMLVideoElement).pause(); (e.target as HTMLVideoElement).currentTime = 0 }} />
                    <div className="absolute bottom-0 left-0 right-0 bg-black/60 text-[7px] text-white text-center py-0.5 leading-none truncate">
                      {v.label}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
      {previewSrc && <ImagePreview src={previewSrc} onClose={() => setPreviewSrc(null)} />}
    </div>
  )
}
