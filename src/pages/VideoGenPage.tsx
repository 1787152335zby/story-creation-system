import { useEffect, useState, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { ArrowLeft, Sparkles, Loader2, RefreshCw, Upload, Download, X, Video } from 'lucide-react'
import { fetchProjects, fetchVideoClips, getMediaUrl, freeVideoGen, fetchVideoResolutions, fetchActiveConfig, fetchGenerationHistory, fetchProjectImages, fetchConfirmedImages, fetchProjectVisualAssets } from '../lib/api'
import ModelSelector from '../components/ModelSelector'
import VideoProjectPanel from '../components/VideoProjectPanel'
import ImagePreview from '../components/ImagePreview'
import ProjectAssetPicker from '../components/ProjectAssetPicker'

import type { ProjectInfo, EntityImage, EntityImagesMap } from '../lib/types'
import { useToast } from '../components/Toast'
import Starfield from '../components/Starfield'

const VIDEO_BACKEND_LABELS: Record<string, { label: string; color: string }> = {
  seedance: { label: '火山引擎 Seedance', color: 'rgba(129,140,248,0.20)' },
  kling: { label: '可灵 Kling', color: 'rgba(74,222,128,0.18)' },
  runway: { label: 'Runway Gen', color: 'rgba(251,191,36,0.18)' },
  pika: { label: 'Pika', color: 'rgba(244,114,182,0.18)' },
  luma: { label: 'Luma Dream Machine', color: 'rgba(56,189,248,0.18)' },
  unknown: { label: '未知接口', color: 'rgba(239,68,68,0.15)' },
}

const MODEL_VIDEO_BACKEND_KEYS: [string, string][] = [
  ['seedance', 'seedance'], ['doubao-seedance', 'seedance'],
  ['kling', 'kling'], ['kling-v1', 'kling'], ['kling-v1-6', 'kling'],
  ['kling-v2', 'kling'], ['kling-v2-master', 'kling'],
  ['kling-v2-1-master', 'kling'], ['kling-v2-5-turbo', 'kling'],
  ['kling-video-o1', 'kling'],
  ['runway', 'runway'], ['gen3', 'runway'], ['gen3-alpha', 'runway'], ['gen4', 'runway'],
  ['pika', 'pika'], ['pika-2', 'pika'], ['pika-2.2', 'pika'],
  ['luma', 'luma'], ['dream-machine', 'luma'], ['ray', 'luma'], ['ray2', 'luma'],
]

function detectVideoBackend(model: string): string {
  if (!model) return 'seedance'
  const ml = model.toLowerCase()
  for (const [key, bk] of MODEL_VIDEO_BACKEND_KEYS) {
    if (ml.includes(key)) return bk
  }
  return 'unknown'
}

export default function VideoGenPage() {
  const navigate = useNavigate()
  const { toast } = useToast()
  const fileInputRef = useRef<HTMLInputElement>(null)
  const freePromptRef = useRef<HTMLTextAreaElement>(null)
  const [mode, setMode] = useState<'free' | 'project'>('free')

  // Free mode
  const [freePrompt, setFreePrompt] = useState('')
  const [freeFiles, setFreeFiles] = useState<{ file: File; preview: string }[]>([])
  const [dragIndex, setDragIndex] = useState<number | null>(null)
  const [freeGenerating, setFreeGenerating] = useState(false)
  const [freeResult, setFreeResult] = useState<{ video_url?: string; local?: string; error?: string } | null>(null)
  const [resolutions, setResolutions] = useState<string[]>([])
  const [ratioGroups, setRatioGroups] = useState<Record<string, string[]>>({})
  const [selectedRatio, setSelectedRatio] = useState('')
  const [freeResolution, setFreeResolution] = useState('')
  const [videoModel, setVideoModel] = useState('')
  const [freeElapsed, setFreeElapsed] = useState(0)
  const [generateAudio, setGenerateAudio] = useState(false)
  const [freeDuration, setFreeDuration] = useState(5)
  const [resolutionSource, setResolutionSource] = useState<'known' | 'standard'>('standard')
  const [refProjects, setRefProjects] = useState<ProjectInfo[]>([])
  const [selectedRefProject, setSelectedRefProject] = useState('')
  const [refProjectImages, setRefProjectImages] = useState<EntityImagesMap>({ characters: {}, scenes: {} })
  const [historyVideos, setHistoryVideos] = useState<{ name: string; url: string }[]>([])
  const [projectImages, setProjectImages] = useState<EntityImagesMap>({ characters: {}, scenes: {} })
  const [confirmedImages, setConfirmedImages] = useState<EntityImagesMap>({ characters: {}, scenes: {} })
  const [selectedRefEntity, setSelectedRefEntity] = useState<string | null>(null)
  const [previewSrc, setPreviewSrc] = useState<string | null>(null)

  // Project mode
  const [projects, setProjects] = useState<ProjectInfo[]>([])
  const [selectedProject, setSelectedProject] = useState<string>('')
  const [clips, setClips] = useState<{ name: string; file: string }[]>([])
  const [finalClip, setFinalClip] = useState<{ name: string; file: string } | null>(null)
  const [generating, setGenerating] = useState<string | null>(null)
  const [log, setLog] = useState<string[]>([])

  useEffect(() => {
    if (freePromptRef.current) {
      freePromptRef.current.style.height = 'auto'
      freePromptRef.current.style.height = freePromptRef.current.scrollHeight + 'px'
    }
  }, [freePrompt])

  useEffect(() => {
    fetchProjects().then(list => {
      setProjects(list)
      setRefProjects(list)
      const savedProject = localStorage.getItem('lastProject')
      if (savedProject && list.some(p => p.name === savedProject)) {
        setSelectedProject(savedProject)
        setSelectedRefProject(savedProject)
        setMode('project')
      }
    })
    fetchGenerationHistory().then(h => setHistoryVideos(h.videos))
    fetchActiveConfig('video').then(cfg => {
      const model = cfg?.model || ''
      setVideoModel(model)
      fetchVideoResolutions(model || undefined).then(r => {
        setResolutions(r.resolutions)
        setRatioGroups(r.groups)
        setResolutionSource(r.source === 'known' ? 'known' : 'standard')
        const ratios = Object.keys(r.groups)
        const defaultRatio = ratios.includes('16:9') ? '16:9' : (ratios[0] || '')
        setSelectedRatio(defaultRatio)
        setFreeResolution(r.resolutions[0] || '1024x1024')
      })
    })
  }, [])

  useEffect(() => {
    fetchVideoResolutions(videoModel || undefined).then(r => {
      setResolutions(r.resolutions)
      setRatioGroups(r.groups)
      setResolutionSource(r.source === 'known' ? 'known' : 'standard')
      const ratios = Object.keys(r.groups)
      const first = ratios.includes('16:9') ? '16:9' : (ratios[0] || '')
      setSelectedRatio(first)
      setFreeResolution(r.resolutions[0] || '1024x1024')
    })
  }, [videoModel])

  useEffect(() => {
    if (!selectedProject) return
    refreshClips()
    fetchProjectImages(selectedProject).then(setProjectImages)
    fetchConfirmedImages(selectedProject).then(setConfirmedImages)
  }, [selectedProject])

  useEffect(() => {
    if (!selectedRefProject) return
    fetchProjectVisualAssets(selectedRefProject).then(setRefProjectImages)
  }, [selectedRefProject])

  const refreshClips = () => {
    if (!selectedProject) return
    fetchVideoClips(selectedProject).then(data => { setClips(data.clips); setFinalClip(data.final) })
  }

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFiles = e.target.files
    if (!selectedFiles || selectedFiles.length === 0) return
    const newEntries: { file: File; preview: string }[] = []
    for (let i = 0; i < selectedFiles.length; i++) {
      const file = selectedFiles[i]
      const reader = new FileReader()
      reader.onload = (ev) => {
        newEntries.push({ file, preview: ev.target?.result as string })
        if (newEntries.length === selectedFiles.length) {
          setFreeFiles(prev => [...prev, ...newEntries])
        }
      }
      reader.readAsDataURL(file)
    }
  }

  const removeFile = (index: number) => {
    setFreeFiles(prev => prev.filter((_, i) => i !== index))
  }

  const handleFreeGen = async () => {
    if (!freePrompt.trim()) return
    setFreeGenerating(true)
    setFreeResult(null)
    setFreeElapsed(0)
    const startTime = Date.now()
    const timer = setInterval(() => setFreeElapsed(Math.floor((Date.now() - startTime) / 1000)), 1000)
    try {
      const files = freeFiles.length > 0 ? freeFiles.map(f => f.file) : undefined
      const result = await freeVideoGen(freePrompt, files, videoModel, freeResolution || undefined, freeDuration, generateAudio)
      setFreeResult(result)
    } catch (e: any) {
      setFreeResult({ error: e.message })
      toast(e.message, 'error')
    }
    clearInterval(timer)
    setFreeGenerating(false)
  }

  const handleDragStart = (i: number) => setDragIndex(i)
  const handleDragOver = (e: React.DragEvent, i: number) => {
    e.preventDefault()
    if (dragIndex === null || dragIndex === i) return
    const newFiles = [...freeFiles]
    const [moved] = newFiles.splice(dragIndex, 1)
    newFiles.splice(i, 0, moved)
    setFreeFiles(newFiles)
    setDragIndex(i)
  }
  const handleDragEnd = () => setDragIndex(null)

  return (
    <div className="min-h-screen relative overflow-hidden">
      <Starfield />

      <div className="max-w-5xl mx-auto px-6 py-10 relative z-10">
        <button onClick={() => navigate('/home')} className="flex items-center gap-1.5 text-white/40 hover:text-white/70 mb-8 transition-all text-xs">
          <ArrowLeft className="w-3.5 h-3.5" /> 返回首页
        </button>

        <h1 className="text-[clamp(28px,5vw,42px)] font-black tracking-[-0.04em] leading-none mb-2"
          style={{
            background: 'linear-gradient(180deg, rgba(255,255,255,0.95) 0%, rgba(255,255,255,0.55) 100%)',
            WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent', backgroundClip: 'text',
          }}>
          🎬 视频生成
        </h1>
        <p className="text-xs text-white/15 tracking-wider mb-4">图生视频 · 多图片参考 · 自由创作</p>

        <div className="grid grid-cols-2 gap-3 mb-6">
          <button onClick={() => setMode('free')}
            className={`p-4 rounded-xl text-left transition-all duration-200 glow-border shimmer-hover relative overflow-hidden ${mode === 'free' ? 'selected' : ''}`}
            style={{
              background: mode === 'free' ? 'rgba(167,139,250,0.12)' : 'rgba(255,255,255,0.03)',
              border: `1px solid ${mode === 'free' ? 'rgba(167,139,250,0.35)' : 'rgba(255,255,255,0.06)'}`,
              boxShadow: mode === 'free' ? '0 0 20px rgba(167,139,250,0.08)' : 'none',
            }}>
            <div className="relative z-[1]">
              <div className="text-2xl mb-2">✏️</div>
              <div className="font-semibold text-sm mb-0.5" style={{ color: mode === 'free' ? 'rgba(220,210,255,0.95)' : 'rgba(255,255,255,0.55)' }}>自由创作</div>
              <div className="text-[10px]" style={{ color: mode === 'free' ? 'rgba(167,139,250,0.6)' : 'rgba(255,255,255,0.2)' }}>上传参考图片，AI 生成视频</div>
            </div>
          </button>
          <button onClick={() => setMode('project')}
            className={`p-4 rounded-xl text-left transition-all duration-200 glow-border shimmer-hover relative overflow-hidden ${mode === 'project' ? 'selected' : ''}`}
            style={{
              background: mode === 'project' ? 'rgba(167,139,250,0.12)' : 'rgba(255,255,255,0.03)',
              border: `1px solid ${mode === 'project' ? 'rgba(167,139,250,0.35)' : 'rgba(255,255,255,0.06)'}`,
              boxShadow: mode === 'project' ? '0 0 20px rgba(167,139,250,0.08)' : 'none',
            }}>
            <div className="relative z-[1]">
              <div className="text-2xl mb-2">📂</div>
              <div className="font-semibold text-sm mb-0.5" style={{ color: mode === 'project' ? 'rgba(220,210,255,0.95)' : 'rgba(255,255,255,0.55)' }}>项目模式</div>
              <div className="text-[10px]" style={{ color: mode === 'project' ? 'rgba(167,139,250,0.6)' : 'rgba(255,255,255,0.2)' }}>为项目中的角色/场景生成视频</div>
            </div>
          </button>
        </div>

        {mode === 'free' ? (
          <>
            <div className="rounded-2xl p-6 mb-6 premium-panel">
              {/* Reference images */}
              <label className="premium-label">参考图片（可上传多张）</label>
              <div className="premium-upload rounded-xl p-6 text-center cursor-pointer mb-4"
                onClick={() => fileInputRef.current?.click()}>
                <Upload className="w-8 h-8 mx-auto mb-2" style={{ color: 'rgba(167, 139, 250, 0.5)' }} />
                <p className="text-sm" style={{ color: 'rgba(255, 255, 255, 0.4)' }}>点击上传参考图片（支持多选）</p>
                <input ref={fileInputRef} type="file" accept="image/*" multiple className="hidden" onChange={handleFileSelect} />
              </div>

              {freeFiles.length > 0 && (
                <div className="grid grid-cols-3 md:grid-cols-4 gap-3 mb-4">
                  {freeFiles.map((entry, i) => (
                    <div key={i} className={`relative group ${dragIndex === i ? 'opacity-50 ring-2 ring-[rgba(129,140,248,0.7)]' : ''}`}
                      draggable={true}
                      onDragStart={() => handleDragStart(i)}
                      onDragOver={(e) => handleDragOver(e, i)}
                      onDragEnd={handleDragEnd}>
                      <img src={entry.preview} alt="" className="w-full h-28 object-cover rounded-xl img-hover" />
                      <button onClick={() => removeFile(i)}
                        className="absolute -top-2 -right-2 w-6 h-6 rounded-full bg-red-500 text-white flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity shadow-lg">
                        <X className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  ))}
                </div>
              )}

              {/* Project reference gallery */}
              <ProjectAssetPicker
                projectName={selectedRefProject || ''}
                assets={{ characters: [], scenes: [] }}
                entityImages={refProjectImages}
                selectedEntity={selectedRefEntity}
                onSelectEntity={setSelectedRefEntity}
                onAddAsset={(url) => {
                  fetch(url).then(r => r.blob()).then(blob => {
                    const file = new File([blob], 'ref.png', { type: 'image/png' })
                    const reader = new FileReader()
                    reader.onload = (ev) => setFreeFiles(prev => [...prev, { file, preview: ev.target?.result as string }])
                    reader.readAsDataURL(blob)
                  })
                }}
              />

              {/* Prompt */}
              <div className="premium-divider" />
              <label className="premium-label">动作描述</label>
              <textarea ref={freePromptRef} value={freePrompt} onChange={e => setFreePrompt(e.target.value)}
                placeholder="例如：角色缓缓转身，风吹动衣角，背景的云层在流动..." className="w-full premium-input rounded-xl px-4 py-3 min-h-[6rem] resize-none text-sm mb-4" />

              {/* Resolution + Model + Duration */}
              <div className="grid grid-cols-4 gap-4 mb-4">
                <div>
                  <label className="premium-label" style={{ fontSize: '0.625rem' }}>模型</label>
                  <ModelSelector type="video" value={videoModel} onChange={setVideoModel} />
                  {(() => {
                    const bk = detectVideoBackend(videoModel)
                    const info = VIDEO_BACKEND_LABELS[bk] || VIDEO_BACKEND_LABELS.unknown
                    return (
                      <div className="flex items-center gap-1.5 mt-1.5">
                        <span className="inline-block px-2 py-0.5 rounded text-[10px]" style={{ background: info.color, color: bk === 'unknown' ? 'rgba(239,68,68,0.85)' : 'rgba(255,255,255,0.65)' }}>
                          调用: {info.label}
                        </span>
                        {bk === 'unknown' && (
                          <span className="text-[10px] italic" style={{ color: 'rgba(239,68,68,0.7)' }}>请确认该模型是否支持视频生成</span>
                        )}
                      </div>
                    )
                  })()}
                </div>
                <div>
                  <label className="premium-label" style={{ fontSize: '0.625rem' }}>比例</label>
                  <select value={selectedRatio} onChange={e => { const rs = ratioGroups[e.target.value]; setSelectedRatio(e.target.value); if (rs?.length) setFreeResolution(rs[0]) }}
                    className="w-full premium-select rounded-xl px-3 py-2.5 text-sm">
                    {Object.keys(ratioGroups).map(r => (<option key={r} value={r}>{r}</option>))}
                  </select>
                  {resolutionSource === 'standard' && (
                    <p className="text-[10px] mt-1 opacity-50">此模型使用标准尺寸列表，部分分辨率可能不被支持，遇到报错请更换尺寸</p>
                  )}
                </div>
                <div>
                  <label className="premium-label" style={{ fontSize: '0.625rem' }}>分辨率</label>
                  <select value={freeResolution} onChange={e => setFreeResolution(e.target.value)} className="w-full premium-select rounded-xl px-3 py-2.5 text-sm">
                    {(ratioGroups[selectedRatio] || resolutions).map(r => (<option key={r} value={r}>{r}</option>))}
                  </select>
                </div>
                <div>
                  <label className="premium-label" style={{ fontSize: '0.625rem' }}>时长</label>
                  <select value={freeDuration} onChange={e => setFreeDuration(Number(e.target.value))} className="w-full premium-select rounded-xl px-3 py-2.5 text-sm">
                    <option value="5">5 秒</option>
                    <option value="10">10 秒</option>
                  </select>
                </div>
              </div>

              {/* Audio toggle */}
              <div className="flex items-center gap-3 mb-4">
                <label className="relative inline-flex items-center cursor-pointer">
                  <input type="checkbox" className="sr-only peer" checked={generateAudio} onChange={e => setGenerateAudio(e.target.checked)} />
                  <div className="w-9 h-5 bg-white/[0.04] rounded-full peer peer-checked:after:translate-x-full after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-[rgba(129,140,248,0.7)]"></div>
                </label>
                <span className="text-xs text-white/55">生成音频（对白+音效）</span>
              </div>

              <button onClick={handleFreeGen} disabled={freeGenerating || !freePrompt.trim()}
                className="flex items-center gap-2 px-6 py-3 rounded-xl text-sm font-medium disabled:opacity-50 opt-btn"
                style={{ background: 'linear-gradient(135deg, rgba(129,140,248,0.22), rgba(167,139,250,0.2))', color: 'rgba(129,140,248,0.98)', border: '1px solid rgba(129,140,248,0.35)', boxShadow: '0 20px 40px -16px rgba(129,140,248,0.35)' }}>
                {freeGenerating ? <Loader2 className="w-4 h-4 animate-spin" /> : <Sparkles className="w-4 h-4" />}
                {freeGenerating ? `等待中 ${freeElapsed}s` : '生成视频'}
              </button>
            </div>

            {freeResult && (
              <div className="rounded-2xl p-5 card-glow premium-panel premium-glow-bottom">
                <h3 className="font-semibold text-sm mb-3">生成结果</h3>
                {freeResult.error ? (
                  <div className="p-4 bg-red-500/10 rounded-xl" style={{ border: '1px solid rgba(255,255,255,0.08)' }}>
                    <p className="text-red-400 text-sm">❌ {freeResult.error}</p>
                    {freeResult.task_id && <p className="text-xs text-white/55 mt-1">任务ID: {freeResult.task_id}</p>}
                  </div>
                ) : (
                  <div>
                    <video src={freeResult.local ? `/generated/${freeResult.local.split('\\').pop() || freeResult.local.split('/').pop()}` : freeResult.video_url}
                      controls className="w-full max-w-2xl rounded-xl" style={{ maxHeight: '450px' }} />
                    <div className="flex gap-2 mt-3">
                      <a href={freeResult.video_url} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl border border-white/[0.10] text-xs hover:bg-white/[0.04] transition-colors opt-btn">
                        <Download className="w-3.5 h-3.5" /> 下载原视频
                      </a>
                    </div>
                  </div>
                )}
              </div>
            )}

            {historyVideos.length > 0 && !freeResult && (
              <div className="rounded-2xl p-5 card-glow premium-panel premium-glow-bottom">
                <h3 className="font-semibold text-sm mb-4">📂 历史记录</h3>
                <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                  {historyVideos.map((v, i) => (
                    <div key={i} className="premium-grid-item">
                      <video src={v.url} className="w-full h-40 object-contain bg-white" />
                    </div>
                  ))}
                </div>
              </div>
            )}
          </>
        ) : (
          <>
            <div className="rounded-2xl p-5 mb-6 card-glow premium-panel premium-glow-bottom">
              <label className="premium-label">选择项目</label>
              <select value={selectedProject} onChange={e => { const v = e.target.value; setSelectedProject(v); localStorage.setItem('lastProject', v) }} className="w-full premium-select rounded-xl px-4 py-3 text-sm">
                <option value="">-- 请选择项目 --</option>
                {projects.map(p => (<option key={p.name} value={p.name}>{p.name}</option>))}
              </select>
            </div>

            {selectedProject && <VideoProjectPanel projectName={selectedProject} />}
          </>
        )}

        {previewSrc && <ImagePreview src={previewSrc} onClose={() => setPreviewSrc(null)} />}
      </div>
    </div>
  )
}
