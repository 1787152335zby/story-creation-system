import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ArrowLeft, Sparkles, Loader2, Download, Trash2, Info, CheckSquare, Square } from 'lucide-react'
import { fetchProjects, fetchCharacters, fetchScenes, freeImageGen, fetchImageResolutions, generateSelectionPrompt, fetchActiveConfig, fetchGenerationHistory, projectImageGen, stitchImages, deleteGeneratedFile, clearProjectFolder, confirmVersion, deleteVersion, fetchProjectImages, fetchConfirmedImages } from '../lib/api'
import ModelSelector from '../components/ModelSelector'
import ImagePreview from '../components/ImagePreview'

import { useToast } from '../components/Toast'

export default function ImageGenPage() {
  const navigate = useNavigate()
  const { toast } = useToast()
  const [mode, setMode] = useState<'free' | 'project'>('free')

  // Free mode
  const [freePrompt, setFreePrompt] = useState('')
  const [freeNegative, setFreeNegative] = useState('')
  const [freeSize, setFreeSize] = useState('')
  const [freeCount, setFreeCount] = useState(1)
  const [freeGenerating, setFreeGenerating] = useState(false)
  const [freeResults, setFreeResults] = useState<{ url: string; local: string }[]>([])
  const [resolutions, setResolutions] = useState<string[]>([])
  const [ratioGroups, setRatioGroups] = useState<Record<string, string[]>>({})
  const [selectedRatio, setSelectedRatio] = useState('')
  const [freeModel, setFreeModel] = useState('')
  const [projectModel, setProjectModel] = useState('')

  // Project mode
  const [projects, setProjects] = useState<any[]>([])
  const [selectedProject, setSelectedProject] = useState<string>('')
  const [characters, setCharacters] = useState<any[]>([])
  const [scenes, setScenes] = useState<any[]>([])
  const [loading, setLoading] = useState(false)
  const [generatedImages, setGeneratedImages] = useState<{ characters: Record<string, { name: string; url: string }[]>; scenes: Record<string, { name: string; url: string }[]> }>({ characters: {}, scenes: {} })
  const [previewSrc, setPreviewSrc] = useState<string | null>(null)

  const [selectedCharNames, setSelectedCharNames] = useState<string[]>([])
  const [selectedSceneNames, setSelectedSceneNames] = useState<string[]>([])
  const [projectPrompt, setProjectPrompt] = useState('')
  const [projectNegative, setProjectNegative] = useState('')
  const [projectSize, setProjectSize] = useState('')
  const [projectCount, setProjectCount] = useState(1)
  const [projectGenerating, setProjectGenerating] = useState(false)
  const [projectResults, setProjectResults] = useState<{ url: string; local: string }[]>([])
  const [useCharTemplate, setUseCharTemplate] = useState(false)
  const [useSceneTemplate, setUseSceneTemplate] = useState(false)
  const [freeError, setFreeError] = useState('')
  const [projectError, setProjectError] = useState('')
  const [historyFree, setHistoryFree] = useState<{ name: string; url: string }[]>([])
  const [historyProject, setHistoryProject] = useState<{ name: string; url: string }[]>([])
  const [showAllFree, setShowAllFree] = useState(false)
  const [showAllProject, setShowAllProject] = useState(false)
  const [expandedVersions, setExpandedVersions] = useState<Record<string, boolean>>({})
  const [confirmDelete, setConfirmDelete] = useState<{ message: string; action: () => void } | null>(null)

  const toggleVersion = (key: string) => setExpandedVersions(prev => ({ ...prev, [key]: !prev[key] }))

  useEffect(() => {
    fetchProjects().then(setProjects)
    fetchGenerationHistory().then(h => { setHistoryFree(h.images_free); setHistoryProject(h.images_project) })
    fetchActiveConfig('image').then(cfg => {
      const model = cfg?.model || ''
      setFreeModel(model)
      setProjectModel(model)
      fetchImageResolutions(model || undefined).then(r => {
        setResolutions(r.resolutions)
        setRatioGroups(r.groups)
        const ratios = Object.keys(r.groups)
        const defaultRatio = ratios.includes('16:9') ? '16:9' : (ratios[0] || '')
        setSelectedRatio(defaultRatio)
        setFreeSize(r.resolutions[0] || '1024x1024')
        setProjectSize(r.resolutions[0] || '1024x1024')
      })
    })
  }, [])

  // 模型切换时更新分辨率列表和默认尺寸
  useEffect(() => {
    if (mode === 'free') {
      fetchImageResolutions(freeModel || undefined).then(r => {
        setResolutions(r.resolutions)
        setRatioGroups(r.groups)
        const ratios = Object.keys(r.groups)
        const first = ratios.includes('16:9') ? '16:9' : (ratios[0] || '')
        setSelectedRatio(first)
        setFreeSize(r.resolutions[0] || '1024x1024')
      })
    }
  }, [freeModel, mode])

  useEffect(() => {
    if (mode === 'project') {
      fetchImageResolutions(projectModel || undefined).then(r => {
        setResolutions(r.resolutions)
        setRatioGroups(r.groups)
        const ratios = Object.keys(r.groups)
        const first = ratios.includes('16:9') ? '16:9' : (ratios[0] || '')
        setSelectedRatio(first)
        setProjectSize(r.resolutions[0] || '1024x1024')
      })
    }
  }, [projectModel, mode])

  useEffect(() => {
    if (!selectedProject) { setCharacters([]); setScenes([]); setGeneratedImages({ characters: {}, scenes: {} }); return }
    setLoading(true)
    Promise.all([
      fetchCharacters(selectedProject),
      fetchScenes(selectedProject),
      fetchProjectImages(selectedProject),
    ]).then(([chars, scns, imgs]) => {
      const sortedChars = [...chars].sort((a, b) => {
        if (a.type === 'main' && b.type !== 'main') return -1
        if (a.type !== 'main' && b.type === 'main') return 1
        return 0
      })
      const seenScenes = new Set<string>()
      const sortedScenes: any[] = []
      for (const s of scns) {
        if (!seenScenes.has(s.name)) {
          seenScenes.add(s.name)
          sortedScenes.push(s)
        }
      }
      setCharacters(sortedChars)
      setScenes(sortedScenes)
      setGeneratedImages(imgs)
    }).finally(() => setLoading(false))
  }, [selectedProject])

  const toggleChar = (name: string) => {
    setSelectedCharNames(prev => prev.includes(name) ? prev.filter(n => n !== name) : [...prev, name])
  }

  const toggleScene = (name: string) => {
    setSelectedSceneNames(prev => prev.includes(name) ? prev.filter(n => n !== name) : [...prev, name])
  }

  // Auto-generate prompt when selection changes
  useEffect(() => {
    if (!selectedProject) return
    if (selectedCharNames.length === 0 && selectedSceneNames.length === 0) return
    const timer = setTimeout(() => {
      generateSelectionPrompt(selectedProject, selectedCharNames, selectedSceneNames).then(p => setProjectPrompt(p))
    }, 100)
    return () => clearTimeout(timer)
  }, [selectedCharNames, selectedSceneNames, selectedProject])

  const handleGen = async () => {
    if (!projectPrompt.trim()) return
    setProjectError('')
    // Fetch confirmed images as references (only characters, not scenes)
    // Scene images could conflict when generating a different scene
    let confRefs: string[] = []
    try {
      const confirmed = await fetchConfirmedImages(selectedProject)
      for (const cn of selectedCharNames) {
        const imgs = confirmed.characters[cn]
        if (imgs?.length) imgs.forEach((img: any) => confRefs.push(img.url))
      }
    } catch {}
    if (useSceneTemplate) {
      setProjectGenerating(true)
      try {
        // Compute next version first
        let ver = 1
        try {
          const res = await fetch(`/api/image-gen/project-images/${encodeURIComponent(selectedProject)}`)
          const data = await res.json()
          const gi = (data?.scenes || {})[selectedSceneNames[0]]
          const keys = Object.keys(gi?.versions || {}).sort((a: any, b: any) => Number(a) - Number(b))
          ver = keys.length > 0 ? Math.max(...keys.map(Number)) + 1 : 1
        } catch {}

        // For scene template: also add confirmed images of the SAME scene being generated
        let sceneRefs = [...confRefs]
        try {
          const confirmed = await fetchConfirmedImages(selectedProject)
          for (const sn of selectedSceneNames) {
            const imgs = confirmed.scenes[sn]
            if (imgs?.length) imgs.forEach((img: any) => sceneRefs.push(img.url))
          }
        } catch {}

        // Step 1: generate bird's-eye overview
        const birdResult = await projectImageGen({
          project_name: selectedProject,
          prompt: `${projectPrompt}\n\n场景全景鸟瞰图：从高空俯瞰整个场景的鸟瞰视角，展示场景的完整布局和全貌。`,
          negative_prompt: projectNegative,
          size: projectSize,
          n: 1,
          model: projectModel,
          character_names: selectedCharNames,
          scene_names: selectedSceneNames,
          reference_urls: sceneRefs,
          version: String(ver),
        })
        const bird = birdResult.images[0]
        const ref = bird?.local || bird?.url || ''

        // Step 2: generate front view using bird's-eye as reference (same version)
        const frontResult = await projectImageGen({
          project_name: selectedProject,
          prompt: `${projectPrompt}\n\n场景正视图：从正前方平视场景的正面视角。参考图中是同一个场景的鸟瞰图，请严格参考鸟瞰图中的布局、颜色和元素，生成一致的正面视角。`,
          negative_prompt: projectNegative,
          size: projectSize,
          n: 1,
          model: projectModel,
          character_names: selectedCharNames,
          scene_names: selectedSceneNames,
          reference_urls: ref ? [ref] : [],
          version: String(ver),
        })
        const front = frontResult.images[0]

        setProjectResults([bird, front])
        fetchGenerationHistory().then(h => setHistoryProject(h.images_project))
        fetchProjectImages(selectedProject).then(setGeneratedImages)
      } catch (e: any) {
        setProjectError(e.message || '生成失败')
        toast(e.message, 'error')
      }
      setProjectGenerating(false)
      return
    }
    setProjectGenerating(true)
    try {
      const templatePrompt = useCharTemplate
        ? `${projectPrompt}\n\n角色四视图：在一张图中排列四个视图——左上为面部特写，右上为全身正面，左下为全身侧面（侧身站立，展示服装轮廓），右下为全身背面。四个视图使用相同角色，保持外貌、服装、颜色完全一致。背景为纯色或渐变色。`
        : projectPrompt
      const result = await projectImageGen({
        project_name: selectedProject,
        prompt: templatePrompt,
        negative_prompt: projectNegative,
        size: projectSize,
        n: useCharTemplate ? 1 : projectCount,
        model: projectModel,
        character_names: selectedCharNames,
        scene_names: selectedSceneNames,
        reference_urls: confRefs,
      })
      setProjectResults(prev => [...result.images, ...prev])
      fetchGenerationHistory().then(h => setHistoryProject(h.images_project))
      fetchProjectImages(selectedProject).then(setGeneratedImages)
    } catch (e: any) {
      setProjectError(e.message || '生成失败，请检查 API Key 是否配置正确')
      toast(e.message, 'error')
    }
    setProjectGenerating(false)
  }

  const handleFreeGen = async () => {
    if (!freePrompt.trim()) return
    setFreeError('')
    setFreeGenerating(true)
    try {
      const result = await freeImageGen(freePrompt, freeNegative, freeSize, freeCount, freeModel)
      setFreeResults(prev => [...result.images, ...prev])
      fetchGenerationHistory().then(h => setHistoryFree(h.images_free))
    } catch (e: any) {
      setFreeError(e.message || '生成失败，请检查 API Key 是否配置正确')
      toast(e.message, 'error')
    }
    setFreeGenerating(false)
  }

  return (
    <div className="min-h-screen relative overflow-hidden">
      <div className="fixed inset-0 pointer-events-none">
        <div className="absolute -top-40 -left-40 w-96 h-96 rounded-full opacity-10"
          style={{ background: 'radial-gradient(circle, hsl(170, 70%, 55%), transparent 70%)' }} />
      </div>

      <div className="max-w-5xl mx-auto px-6 py-10 relative z-10">
        <button onClick={() => navigate('/')} className="flex items-center gap-1.5 text-muted-foreground hover:text-foreground mb-8 transition-colors">
          <ArrowLeft className="w-4 h-4" /> 返回首页
        </button>

        <h1 className="text-2xl font-bold mb-2"><span className="gradient-text">🖼️ 智能生图</span></h1>
        <p className="text-sm text-muted-foreground mb-6">自由创作 · 角色定妆照 · 场景概念图</p>

        <div className="flex gap-2 mb-8">
          <button onClick={() => setMode('free')} className={`px-5 py-2.5 rounded-xl text-sm font-medium transition-all ${mode === 'free' ? 'bg-primary/20 text-primary border-2 border-primary/50' : 'border-2 border-border text-muted-foreground hover:border-primary/30'}`}>
            ✏️ 自由创作
          </button>
          <button onClick={() => setMode('project')} className={`px-5 py-2.5 rounded-xl text-sm font-medium transition-all ${mode === 'project' ? 'bg-primary/20 text-primary border-2 border-primary/50' : 'border-2 border-border text-muted-foreground hover:border-primary/30'}`}>
            📂 项目模式
          </button>
        </div>

        {mode === 'free' ? (
          <>
            <div className="glass-card rounded-2xl p-6 mb-6">
              <label className="text-xs font-medium text-muted-foreground uppercase tracking-wider mb-2 block">描述画面</label>
              <textarea value={freePrompt} onChange={e => setFreePrompt(e.target.value)} placeholder="一只优雅的白猫坐在月光下的窗台上，周围是盛开的樱花，赛博朋克风格，4K..."
                className="w-full bg-muted border border-border rounded-xl px-4 py-3 h-28 resize-none text-sm mb-4" />
              <div className="grid grid-cols-3 gap-4 mb-4">
                <div>
                  <label className="text-xs text-muted-foreground block mb-1">模型</label>
                  <ModelSelector type="image" value={freeModel} onChange={setFreeModel} />
                </div>
                <div>
                  <label className="text-xs text-muted-foreground block mb-1">比例</label>
                  <select value={selectedRatio} onChange={e => { setSelectedRatio(e.target.value); const rs = ratioGroups[e.target.value]; if (rs && rs.length > 0) setFreeSize(rs[0]) }}
                    className="w-full bg-muted border border-border rounded-xl px-3 py-2.5 text-sm">
                    {Object.keys(ratioGroups).map(r => (<option key={r} value={r}>{r}</option>))}
                  </select>
                </div>
                <div>
                  <label className="text-xs text-muted-foreground block mb-1">尺寸</label>
                  <select value={freeSize} onChange={e => setFreeSize(e.target.value)} className="w-full bg-muted border border-border rounded-xl px-3 py-2.5 text-sm">
                    {(ratioGroups[selectedRatio] || resolutions).map(r => (<option key={r} value={r}>{r}</option>))}
                  </select>
                </div>
                <div>
                  <label className="text-xs text-muted-foreground block mb-1">数量</label>
                  <select value={freeCount} onChange={e => setFreeCount(Number(e.target.value))} className="w-full bg-muted border border-border rounded-xl px-3 py-2.5 text-sm">
                    <option value={1}>1 张</option>
                    <option value={2}>2 张</option>
                    <option value={4}>4 张</option>
                  </select>
                </div>
                <div>
                  <label className="text-xs text-muted-foreground block mb-1">负面提示</label>
                  <input value={freeNegative} onChange={e => setFreeNegative(e.target.value)} placeholder="如: 模糊"
                    className="w-full bg-muted border border-border rounded-xl px-3 py-2.5 text-sm" />
                </div>
              </div>
              <button onClick={handleFreeGen} disabled={freeGenerating || !freePrompt.trim()}
                className="btn-gradient flex items-center gap-2 px-6 py-3 rounded-xl text-sm font-medium disabled:opacity-50">
                {freeGenerating ? <Loader2 className="w-4 h-4 animate-spin" /> : <Sparkles className="w-4 h-4" />}
                {freeGenerating ? '生成中...' : '生成'}
              </button>
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
              <div className="glass-card rounded-2xl p-5">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="font-semibold text-sm">生成结果</h3>
                  <button onClick={() => setFreeResults([])} className="text-xs text-muted-foreground hover:text-red-400 flex items-center gap-1">
                    <Trash2 className="w-3 h-3" /> 清空
                  </button>
                </div>
                <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                  {freeResults.map((img, i) => (
                    <div key={i} className="bg-muted rounded-xl overflow-hidden group relative cursor-pointer" onClick={() => setPreviewSrc(img.local ? `/generated/${img.local.split('\\').pop() || img.local.split('/').pop()}` : img.url)}>
                      <img src={img.local ? `/generated/${img.local.split('\\').pop() || img.local.split('/').pop()}` : img.url} alt="" className="w-full h-56 object-contain bg-white" />
                      <div className="absolute inset-0 bg-black/0 group-hover:bg-black/40 transition-all flex items-center justify-center gap-2 opacity-0 group-hover:opacity-100 pointer-events-none" onClick={e => e.stopPropagation()}>
                        <a href={img.local ? `/generated/${img.local.split('\\').pop() || img.local.split('/').pop()}` : img.url} download={img.local?.split('\\').pop()?.split('/').pop() || 'image'} className="p-2 rounded-lg bg-white/20 hover:bg-white/30 text-white pointer-events-auto" title="下载"><Download className="w-4 h-4" /></a>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

          </>

        ) : (
          <>
            {/* Project selector */}
            <div className="glass-card rounded-2xl p-5 mb-6">
              <label className="text-xs font-medium text-muted-foreground uppercase tracking-wider mb-3 block">选择项目</label>
              <select value={selectedProject} onChange={e => { setSelectedProject(e.target.value); setSelectedCharNames([]); setSelectedSceneNames([]); setProjectPrompt(''); setProjectResults([]) }}
                className="w-full bg-muted border border-border rounded-xl px-4 py-3 text-sm">
                <option value="">-- 请选择项目 --</option>
                {projects.map(p => (<option key={p.name} value={p.name}>{p.name}</option>))}
              </select>
            </div>

            {selectedProject && (
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                {/* Left: character/scene selection + template toggles */}
                <div className="lg:col-span-1 space-y-4">
                  <div className="glass-card rounded-2xl p-4 border-2 border-primary/10">
                    <div className="flex items-center justify-between mb-3">
                      <h3 className="font-semibold text-xs">🧑 角色 ({characters.length})</h3>
                      {selectedCharNames.length > 0 && <span className="text-[9px] px-2 py-0.5 rounded-full bg-primary/20 text-primary font-medium">{selectedCharNames.length} 已选</span>}
                    </div>
                    {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : characters.length === 0 ? (
                      <p className="text-[10px] text-muted-foreground">暂无角色数据</p>
                    ) : (
                      <div className="space-y-2 max-h-64 overflow-y-auto">
                        {characters.map((c: any) => {
                          const sel = selectedCharNames.includes(c.name)
                          const gi = generatedImages.characters[c.name]
                          const confirmedImgs = gi?.images || []
                          const versions = gi?.versions || {}
                          const versionKeys = Object.keys(versions).sort()
                          return (
                            <div key={c._file} className="bg-muted/40 rounded-xl p-2 border border-border/30">
                              <div className={`flex items-center gap-1 px-2 py-1.5 rounded-lg text-[11px] transition-all ${
                                sel ? 'bg-primary/15 text-primary font-medium' : 'hover:bg-muted/60 text-muted-foreground'
                              }`}>
                                <button onClick={() => toggleChar(c.name)} className="flex items-center gap-2 flex-1 min-w-0">
                                  {sel ? <CheckSquare className="w-4 h-4 text-primary flex-shrink-0" /> : <Square className="w-4 h-4 text-muted-foreground/40 flex-shrink-0" />}
                                  <span className="flex-1 truncate">{c.name}</span>
                                  <span className={`text-[9px] px-1.5 py-0.5 rounded-full ${c.type === 'main' ? 'bg-primary/20 text-primary' : 'bg-muted text-muted-foreground'}`}>{c.type === 'main' ? '主角' : '配角'}</span>
                                </button>
                                {confirmedImgs.length > 0 && <span className="text-green-400 text-[9px] flex-shrink-0" title="已确认">✓</span>}
                              </div>
                              {versionKeys.length > 0 && (
                                <div className="flex flex-col gap-1 mt-1 px-1">
                                  <button onClick={() => toggleVersion(`char-${c.name}`)}
                                    className="text-[9px] text-muted-foreground hover:text-primary flex items-center gap-1 px-1 py-0.5 rounded">
                                    {expandedVersions[`char-${c.name}`] ? '▼' : '▶'} 已生成 {versionKeys.length} 个版本
                                  </button>
                                  {expandedVersions[`char-${c.name}`] && versionKeys.map(vk => {
                                    const v = versions[vk]
                                    return (
                                      <div key={vk} className={`rounded-lg border ${v.confirmed ? 'border-green-400/40 bg-green-400/5' : 'border-border/50 bg-muted/60'} p-1.5`}>
                                        <div className="flex items-center justify-between mb-1">
                                          <span className="text-[9px] font-medium text-muted-foreground">第{vk}次 {v.confirmed && <span className="text-green-400">✓已确认</span>}</span>
                                          <button onClick={async (e) => { e.stopPropagation(); setConfirmDelete({ message: '确认删除角色「' + c.name + '」第' + vk + '次生成的图片？', action: async () => { try { await deleteVersion(selectedProject, 'characters', c.name, vk); fetchProjectImages(selectedProject).then(setGeneratedImages) } catch (_) {} } }) }}
                                            className="text-[8px] text-red-400 hover:text-red-300 px-1 rounded hover:bg-red-500/10">删除</button>
                                        </div>
                                        <div className="flex gap-1 overflow-x-auto max-w-full">
                                          {v.images.map((img: any, j: number) => (
                                            <img key={j} src={img.url} alt=""
                                              className="w-9 h-9 rounded object-cover border border-border/40 cursor-pointer hover:border-primary/50 flex-shrink-0"
                                              onClick={() => setPreviewSrc(img.url)} title={img.name} />
                                          ))}
                                        </div>
                                        {!v.confirmed && (
                                          <button onClick={async (e) => { e.stopPropagation(); try { await confirmVersion(selectedProject, 'characters', c.name, vk); fetchProjectImages(selectedProject).then(setGeneratedImages) } catch {} }}
                                            className="mt-1 w-full text-[8px] py-0.5 rounded bg-primary/20 text-primary hover:bg-primary/30 transition-colors">确认此版</button>
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
                  <div className="glass-card rounded-2xl p-4 border-2 border-primary/10">
                    <div className="flex items-center justify-between mb-3">
                      <h3 className="font-semibold text-xs">🌆 场景 ({scenes.length})</h3>
                      {selectedSceneNames.length > 0 && <span className="text-[9px] px-2 py-0.5 rounded-full bg-primary/20 text-primary font-medium">{selectedSceneNames.length} 已选</span>}
                    </div>
                    {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : scenes.length === 0 ? (
                      <p className="text-[10px] text-muted-foreground">暂无场景数据</p>
                    ) : (
                      <div className="space-y-2 max-h-64 overflow-y-auto">
                        {scenes.map((s: any) => {
                          const sel = selectedSceneNames.includes(s.name)
                          const gi = generatedImages.scenes[s.name]
                          const confirmedImgs = gi?.images || []
                          const versions = gi?.versions || {}
                          const versionKeys = Object.keys(versions).sort()
                          return (
                            <div key={s._file} className="bg-muted/40 rounded-xl p-2 border border-border/30">
                              <div className={`flex items-center gap-1 px-2 py-1.5 rounded-lg text-[11px] transition-all ${
                                sel ? 'bg-primary/15 text-primary font-medium' : 'hover:bg-muted/60 text-muted-foreground'
                              }`}>
                                <button onClick={() => toggleScene(s.name)} className="flex items-center gap-2 flex-1 min-w-0">
                                  {sel ? <CheckSquare className="w-4 h-4 text-primary flex-shrink-0" /> : <Square className="w-4 h-4 text-muted-foreground/40 flex-shrink-0" />}
                                  <span className="flex-1 truncate">{s.name}</span>
                                </button>
                                {confirmedImgs.length > 0 && <span className="text-green-400 text-[9px] flex-shrink-0" title="已确认">✓</span>}
                              </div>
                              {versionKeys.length > 0 && (
                                <div className="flex flex-col gap-1 mt-1 px-1">
                                  <button onClick={() => toggleVersion(`scene-${s.name}`)}
                                    className="text-[9px] text-muted-foreground hover:text-primary flex items-center gap-1 px-1 py-0.5 rounded">
                                    {expandedVersions[`scene-${s.name}`] ? '▼' : '▶'} 已生成 {versionKeys.length} 个版本
                                  </button>
                                  {expandedVersions[`scene-${s.name}`] && versionKeys.map(vk => {
                                    const v = versions[vk]
                                    return (
                                      <div key={vk} className={`rounded-lg border ${v.confirmed ? 'border-green-400/40 bg-green-400/5' : 'border-border/50 bg-muted/60'} p-1.5`}>
                                        <div className="flex items-center justify-between mb-1">
                                          <span className="text-[9px] font-medium text-muted-foreground">第{vk}次 {v.confirmed && <span className="text-green-400">✓已确认</span>}</span>
                                          <button onClick={async (e) => { e.stopPropagation(); setConfirmDelete({ message: '确认删除场景「' + s.name + '」第' + vk + '次生成的图片？', action: async () => { try { await deleteVersion(selectedProject, 'scenes', s.name, vk); fetchProjectImages(selectedProject).then(setGeneratedImages) } catch (_) {} } }) }}
                                            className="text-[8px] text-red-400 hover:text-red-300 px-1 rounded hover:bg-red-500/10">删除</button>
                                        </div>
                                        <div className="flex gap-1 overflow-x-auto max-w-full">
                                          {v.images.map((img: any, j: number) => (
                                            <img key={j} src={img.url} alt=""
                                              className="w-9 h-9 rounded object-cover border border-border/40 cursor-pointer hover:border-primary/50 flex-shrink-0"
                                              onClick={() => setPreviewSrc(img.url)} title={img.name} />
                                          ))}
                                        </div>
                                        {!v.confirmed && (
                                          <button onClick={async (e) => { e.stopPropagation(); try { await confirmVersion(selectedProject, 'scenes', s.name, vk); fetchProjectImages(selectedProject).then(setGeneratedImages) } catch {} }}
                                            className="mt-1 w-full text-[8px] py-0.5 rounded bg-primary/20 text-primary hover:bg-primary/30 transition-colors">确认此版</button>
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
                </div>

                {/* Right: template + prompt + generate */}
                <div className="lg:col-span-2 space-y-6">
                  {/* Template toggles - moved above prompt */}
                  <div className="glass-card rounded-2xl p-4 border-2 border-accent/20">
                    <div className="flex items-center gap-2 mb-3">
                      <h3 className="font-semibold text-xs">🎨 生成模板</h3>
                      <span className="text-[9px] text-muted-foreground">鸟瞰图 + 参考生成正视图</span>
                    </div>
                    <div className="grid grid-cols-2 gap-4">
                      <label className={`flex items-center justify-between p-3 rounded-xl cursor-pointer transition-all ${useCharTemplate ? 'bg-primary/10 border border-primary/30' : 'bg-muted/50 border border-transparent'}`}>
                        <div>
                          <p className="text-[11px] font-medium">角色四视图</p>
                          <p className="text-[9px] text-muted-foreground">面部特写 + 全身正/侧/背</p>
                        </div>
                        <button onClick={() => { setUseCharTemplate(!useCharTemplate); if (!useCharTemplate) setUseSceneTemplate(false) }}
                          className={`relative w-9 h-5 rounded-full transition-all flex-shrink-0 ${useCharTemplate ? 'bg-primary' : 'bg-muted border border-border'}`}>
                          <div className={`absolute top-0.5 w-4 h-4 rounded-full bg-white shadow transition-all ${useCharTemplate ? 'left-4.5' : 'left-0.5'}`} />
                        </button>
                      </label>
                      <label className={`flex items-center justify-between p-3 rounded-xl cursor-pointer transition-all ${useSceneTemplate ? 'bg-primary/10 border border-primary/30' : 'bg-muted/50 border border-transparent'}`}>
                        <div>
                          <p className="text-[11px] font-medium">场景多角度</p>
                          <p className="text-[9px] text-muted-foreground">鸟瞰图 + 参考生成正视图</p>
                        </div>
                        <button onClick={() => { setUseSceneTemplate(!useSceneTemplate); if (!useSceneTemplate) setUseCharTemplate(false) }}
                          className={`relative w-9 h-5 rounded-full transition-all flex-shrink-0 ${useSceneTemplate ? 'bg-primary' : 'bg-muted border border-border'}`}>
                          <div className={`absolute top-0.5 w-4 h-4 rounded-full bg-white shadow transition-all ${useSceneTemplate ? 'left-4.5' : 'left-0.5'}`} />
                        </button>
                      </label>
                    </div>
                  </div>

                  <div className="glass-card rounded-2xl p-5">
                    <div className="flex items-center justify-between mb-2">
                      <label className="text-xs font-medium text-muted-foreground uppercase tracking-wider">提示词</label>
                      <div className="flex items-center gap-2">
                        {selectedCharNames.length > 0 && <span className="text-[9px] text-primary">勾选角色自动生成</span>}
                        <button onClick={() => setProjectPrompt('')} className="text-[10px] text-muted-foreground hover:text-red-400 px-2 py-0.5 rounded hover:bg-red-400/5 transition-all">清空</button>
                      </div>
                    </div>
                    <textarea value={projectPrompt} onChange={e => setProjectPrompt(e.target.value)}
                      placeholder={`在左侧勾选角色或场景，提示词将自动生成。\n也可以手动输入。`}
                      className="w-full bg-muted border border-border rounded-xl px-4 py-3 h-40 resize-none text-sm font-mono" />
                    <div className="grid grid-cols-3 gap-4 mt-4 mb-4">
                      <div>
                        <label className="text-xs text-muted-foreground block mb-1">模型</label>
                        <ModelSelector type="image" value={projectModel} onChange={setProjectModel} />
                      </div>
                      <div>
                        <label className="text-xs text-muted-foreground block mb-1">比例</label>
                        <select value={selectedRatio} onChange={e => { const rs = ratioGroups[e.target.value]; setSelectedRatio(e.target.value); if (rs?.length) setProjectSize(rs[0]) }}
                          className="w-full bg-muted border border-border rounded-xl px-3 py-2.5 text-sm">
                          {Object.keys(ratioGroups).map(r => (<option key={r} value={r}>{r}</option>))}
                        </select>
                      </div>
                      <div>
                        <label className="text-xs text-muted-foreground block mb-1">尺寸</label>
                        <select value={projectSize} onChange={e => setProjectSize(e.target.value)} className="w-full bg-muted border border-border rounded-xl px-3 py-2.5 text-sm">
                          {(ratioGroups[selectedRatio] || resolutions).map(r => (<option key={r} value={r}>{r}</option>))}
                        </select>
                      </div>
                      <div>
                        <label className="text-xs text-muted-foreground block mb-1">数量</label>
                        {useCharTemplate ? (
                          <div className="w-full bg-muted border border-border rounded-xl px-3 py-2.5 text-sm text-muted-foreground/60">固定1张（四视图拼合）</div>
                        ) : useSceneTemplate ? (
                          <div className="w-full bg-muted border border-border rounded-xl px-3 py-2.5 text-sm text-muted-foreground/60">固定1张（四角度拼合）</div>
                        ) : (
                          <select value={projectCount} onChange={e => setProjectCount(Number(e.target.value))} className="w-full bg-muted border border-border rounded-xl px-3 py-2.5 text-sm">
                            <option value={1}>1 张</option>
                          <option value={2}>2 张</option>
                          <option value={4}>4 张</option>
                        </select>
                        )}
                      </div>
                      <div>
                        <label className="text-xs text-muted-foreground block mb-1">负面提示</label>
                        <input value={projectNegative} onChange={e => setProjectNegative(e.target.value)} placeholder="如: 模糊" className="w-full bg-muted border border-border rounded-xl px-3 py-2.5 text-sm" />
                      </div>
                    </div>
                    <button onClick={handleGen} disabled={projectGenerating || !projectPrompt.trim()}
                      className="btn-gradient flex items-center gap-2 px-6 py-3 rounded-xl text-sm font-medium disabled:opacity-50">
                      {projectGenerating ? <Loader2 className="w-4 h-4 animate-spin" /> : <Sparkles className="w-4 h-4" />}
                      {projectGenerating ? '生成中...' : '生成'}
                    </button>
                    {projectError && (
                      <div className="mt-3 p-3 rounded-xl bg-red-400/10 border border-red-400/20 text-xs text-red-400 flex items-start gap-2">
                        <Info className="w-3.5 h-3.5 flex-shrink-0 mt-0.5" />
                        <div className="flex-1">
                          <span>{projectError}</span>
                          {projectError.toLowerCase().includes('api key') && (
                            <button onClick={() => navigate('/settings')} className="ml-2 underline hover:text-red-300">去设置</button>
                          )}
                        </div>
                      </div>
                    )}
                  </div>
                  {projectResults.length > 0 && (
                    <div className="glass-card rounded-2xl p-5">
                      <div className="flex items-center justify-between mb-4">
                        <h3 className="font-semibold text-sm">{useSceneTemplate ? '场景生成结果' : '生成结果'}</h3>
                        <button onClick={() => setProjectResults([])} className="text-xs text-muted-foreground hover:text-red-400 flex items-center gap-1">
                          <Trash2 className="w-3 h-3" /> 清空列表
                        </button>
                      </div>
                      {useSceneTemplate && projectResults.length === 2 ? (
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                          {[['🌍 全景鸟瞰图', '从高空俯瞰场景全貌'], ['🏛️ 正视图', '从正前方平视场景']].map(([label, tip], i) => {
                            const img = projectResults[i]
                            const src = img.local ? `/generated/${img.local.split('\\').pop() || img.local.split('/').pop()}` : img.url
                            return (
                              <div key={i} className="bg-muted rounded-xl overflow-hidden">
                                <div className="px-3 py-2 bg-muted/80 border-b border-border/30">
                                  <div className="text-[11px] font-medium">{label}</div>
                                  <div className="text-[8px] text-muted-foreground">{tip}</div>
                                </div>
                                <div className="group relative cursor-pointer" onClick={() => setPreviewSrc(src)}>
                                  <img src={src} alt="" className="w-full h-64 object-contain bg-white" />
                                  <div className="absolute inset-0 bg-black/0 group-hover:bg-black/40 transition-all flex items-center justify-center gap-2 opacity-0 group-hover:opacity-100 pointer-events-none" onClick={e => e.stopPropagation()}>
                                    <a href={src} download={`scene_${i}.png`} className="p-2 rounded-lg bg-white/20 hover:bg-white/30 text-white pointer-events-auto" title="下载"><Download className="w-4 h-4" /></a>
                                    <button onClick={async (e) => { e.stopPropagation(); setConfirmDelete({ message: '确认删除这张图片？', action: async () => { try { await deleteGeneratedFile(img.local || img.url); setProjectResults(prev => prev.filter((_, j) => j !== i)); } catch (_) {} } }) }}
                                      className="p-2 rounded-lg bg-red-500/20 hover:bg-red-500/30 text-white pointer-events-auto" title="删除"><Trash2 className="w-4 h-4" /></button>
                                  </div>
                                </div>
                              </div>
                            )
                          })}
                        </div>
                      ) : (
                      <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                          {projectResults.map((img, i) => {
                            const src = img.local ? `/generated/${img.local.split('\\').pop() || img.local.split('/').pop()}` : img.url
                            return (
                              <div key={i} className="bg-muted rounded-xl overflow-hidden group relative cursor-pointer" onClick={() => setPreviewSrc(src)}>
                                <img src={src} alt="" className="w-full h-56 object-contain bg-white" />
                                <div className="absolute inset-0 bg-black/0 group-hover:bg-black/40 transition-all flex items-center justify-center gap-2 opacity-0 group-hover:opacity-100 pointer-events-none" onClick={e => e.stopPropagation()}>
                                  <a href={src} download={img.local?.split('\\').pop()?.split('/').pop() || 'image'} className="p-2 rounded-lg bg-white/20 hover:bg-white/30 text-white pointer-events-auto" title="下载"><Download className="w-4 h-4" /></a>
                                  <button onClick={async (e) => { e.stopPropagation(); setConfirmDelete({ message: '确认删除这张图片？', action: async () => { try { await deleteGeneratedFile(img.local || img.url); setProjectResults(prev => prev.filter((_, j) => j !== i)); } catch (_) {} } }) }}
                                    className="p-2 rounded-lg bg-red-500/20 hover:bg-red-500/30 text-white pointer-events-auto" title="删除"><Trash2 className="w-4 h-4" /></button>
                                </div>
                              </div>
                            )
                          })}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              </div>
            )}
          </>
        )}

        {/* 智能历史 — 根据当前模式显示对应的历史 */}
        {mode === 'free' && historyFree.length > 0 && (
          <div className="glass-card rounded-2xl p-5 mt-6 opacity-70">
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-semibold text-sm">✏️ 自由创作历史</h3>
              {historyFree.length > 9 && (
                <button onClick={() => setShowAllFree(!showAllFree)} className="text-[10px] text-muted-foreground hover:text-primary transition-colors">
                  {showAllFree ? '收起' : `查看全部 (${historyFree.length})`}
                </button>
              )}
            </div>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
              {(showAllFree ? historyFree : historyFree.slice(0, 9)).map((img, i) => (
                <div key={i} className="bg-muted rounded-xl overflow-hidden group relative cursor-pointer" onClick={() => setPreviewSrc(img.url)}>
                  <img src={img.url} alt="" className="w-full h-40 object-contain bg-white" />
                  <div className="absolute inset-0 bg-black/0 group-hover:bg-black/40 transition-all flex items-center justify-center gap-2 opacity-0 group-hover:opacity-100 pointer-events-none" onClick={e => e.stopPropagation()}>
                    <a href={img.url} download={img.name} className="p-2 rounded-lg bg-white/20 hover:bg-white/30 text-white pointer-events-auto" title="下载"><Download className="w-4 h-4" /></a>
                    <button onClick={async (e) => { e.stopPropagation(); setConfirmDelete({ message: '确认删除这张图片？', action: async () => { try { await deleteGeneratedFile(img.url); setHistoryFree(prev => prev.filter((_, j) => j !== i)); } catch (_) {} } }) }}
                      className="p-2 rounded-lg bg-red-500/20 hover:bg-red-500/30 text-white pointer-events-auto" title="删除"><Trash2 className="w-4 h-4" /></button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
        {mode === 'project' && historyProject.length > 0 && (
          <div className="glass-card rounded-2xl p-5 mt-4 opacity-70">
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-semibold text-sm">📂 项目模式历史</h3>
              {historyProject.length > 9 && (
                <button onClick={() => setShowAllProject(!showAllProject)} className="text-[10px] text-muted-foreground hover:text-primary transition-colors">
                  {showAllProject ? '收起' : `查看全部 (${historyProject.length})`}
                </button>
              )}
            </div>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
              {(showAllProject ? historyProject : historyProject.slice(0, 9)).map((img, i) => (
                <div key={i} className="bg-muted rounded-xl overflow-hidden group relative cursor-pointer" onClick={() => setPreviewSrc(img.url)}>
                  <img src={img.url} alt="" className="w-full h-40 object-contain bg-white" />
                  <div className="absolute inset-0 bg-black/0 group-hover:bg-black/40 transition-all flex items-center justify-center gap-2 opacity-0 group-hover:opacity-100 pointer-events-none" onClick={e => e.stopPropagation()}>
                    <a href={img.url} download={img.name} className="p-2 rounded-lg bg-white/20 hover:bg-white/30 text-white pointer-events-auto" title="下载"><Download className="w-4 h-4" /></a>
                    <button onClick={async (e) => { e.stopPropagation(); setConfirmDelete({ message: '确认删除这张图片？', action: async () => { try { await deleteGeneratedFile(img.url); setHistoryProject(prev => prev.filter((_, j) => j !== i)); } catch (_) {} } }) }}
                      className="p-2 rounded-lg bg-red-500/20 hover:bg-red-500/30 text-white pointer-events-auto" title="删除"><Trash2 className="w-4 h-4" /></button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {previewSrc && <ImagePreview src={previewSrc} onClose={() => setPreviewSrc(null)} />}
        {confirmDelete && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50" onClick={() => setConfirmDelete(null)}>
            <div className="bg-background border border-border rounded-2xl p-6 max-w-sm w-full mx-4 shadow-2xl" onClick={e => e.stopPropagation()}>
              <p className="text-sm mb-6 text-center">{confirmDelete.message}</p>
              <div className="flex gap-3">
                <button onClick={() => setConfirmDelete(null)}
                  className="flex-1 py-2.5 rounded-xl border border-border text-sm text-muted-foreground hover:bg-muted transition-colors">取消</button>
                <button onClick={async () => { try { await confirmDelete.action() } catch {} setConfirmDelete(null) }}
                  className="flex-1 py-2.5 rounded-xl bg-red-500 text-white text-sm hover:bg-red-600 transition-colors">确定删除</button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
