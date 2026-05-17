import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ArrowLeft, Sparkles, Loader2, Download, Trash2, Info, CheckSquare, Square } from 'lucide-react'
import { fetchProjects, fetchCharacters, fetchScenes, freeImageGen, fetchImageResolutions, runVisualExtract, confirmVisualExtract, generateSelectionPrompt, fetchActiveConfig, fetchGenerationHistory, projectImageGen, fetchProjectImages } from '../lib/api'
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
  const [freeSize, setFreeSize] = useState('1024x1024')
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
  const [extracting, setExtracting] = useState(false)
  const [extractLog, setExtractLog] = useState('')

  const [selectedCharNames, setSelectedCharNames] = useState<string[]>([])
  const [selectedSceneNames, setSelectedSceneNames] = useState<string[]>([])
  const [projectPrompt, setProjectPrompt] = useState('')
  const [projectNegative, setProjectNegative] = useState('')
  const [projectSize, setProjectSize] = useState('1024x1024')
  const [projectCount, setProjectCount] = useState(1)
  const [projectGenerating, setProjectGenerating] = useState(false)
  const [projectResults, setProjectResults] = useState<{ url: string; local: string }[]>([])
  const [extractedOnce, setExtractedOnce] = useState(false)
  const [useCharTemplate, setUseCharTemplate] = useState(false)
  const [useSceneTemplate, setUseSceneTemplate] = useState(false)
  const [freeError, setFreeError] = useState('')
  const [projectError, setProjectError] = useState('')
  const [historyFree, setHistoryFree] = useState<{ name: string; url: string }[]>([])
  const [historyProject, setHistoryProject] = useState<{ name: string; url: string }[]>([])
  const [showAllFree, setShowAllFree] = useState(false)
  const [showAllProject, setShowAllProject] = useState(false)
  const [previewSrc, setPreviewSrc] = useState<string | null>(null)

  useEffect(() => {
    fetchProjects().then(setProjects)
    fetchImageResolutions().then(r => {
      setResolutions(r.resolutions)
      setRatioGroups(r.groups)
      const ratios = Object.keys(r.groups)
      if (ratios.length > 0) setSelectedRatio(ratios[0])
    })
    fetchGenerationHistory().then(h => { setHistoryFree(h.images_free); setHistoryProject(h.images_project) })
    fetchActiveConfig('image').then(cfg => {
      if (cfg?.model) { setFreeModel(cfg.model); setProjectModel(cfg.model) }
    })
  }, [])

  // 模型切换时更新分辨率列表
  useEffect(() => {
    if (mode === 'free') {
      fetchImageResolutions(freeModel || undefined).then(r => {
        setResolutions(r.resolutions)
        setRatioGroups(r.groups)
        const ratios = Object.keys(r.groups)
        const first = ratios[0] || ''
        setSelectedRatio(first)
        if (freeSize && !(r.resolutions.includes(freeSize))) setFreeSize(r.resolutions[0] || '1024x1024')
      })
    }
  }, [freeModel, mode])

  useEffect(() => {
    if (mode === 'project') {
      fetchImageResolutions(projectModel || undefined).then(r => {
        setResolutions(r.resolutions)
        setRatioGroups(r.groups)
        const ratios = Object.keys(r.groups)
        const first = ratios[0] || ''
        setSelectedRatio(first)
        if (projectSize && !(r.resolutions.includes(projectSize))) setProjectSize(r.resolutions[0] || '1024x1024')
      })
    }
  }, [projectModel, mode])

  useEffect(() => {
    if (!selectedProject) { setCharacters([]); setScenes([]); return }
    setLoading(true)
    Promise.all([
      fetchCharacters(selectedProject).then(setCharacters),
      fetchScenes(selectedProject).then(setScenes),
    ]).finally(() => setLoading(false))
  }, [selectedProject])

  const handleExtract = async () => {
    if (!selectedProject) return
    setExtracting(true)
    setExtractLog('⏳ 正在提取角色/场景（可能需要30秒到2分钟）...')
    try {
      const start = Date.now()
      await runVisualExtract(selectedProject)
      const [chars, scenes] = await Promise.all([
        fetchCharacters(selectedProject),
        fetchScenes(selectedProject),
      ])
      setCharacters(chars)
      setScenes(scenes)
      setExtractedOnce(true)
      setExtractLog(`✅ 提取完成：${chars.length} 个角色，${scenes.length} 个场景（用时 ${Math.round((Date.now() - start) / 1000)} 秒）`)
    } catch (e: any) {
      setExtractLog(`❌ 提取失败：${e.message}`)
      toast(e.message, 'error')
    }
    setExtracting(false)
  }

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
    setProjectGenerating(true)
    try {
      const result = await projectImageGen({
        project_name: selectedProject,
        prompt: projectPrompt,
        negative_prompt: projectNegative,
        size: projectSize,
        n: projectCount,
        model: projectModel,
        character_names: selectedCharNames,
        scene_names: selectedSceneNames,
      })
      setProjectResults(prev => [...result.images, ...prev])
      fetchGenerationHistory().then(h => setHistoryProject(h.images_project))
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
            {/* Project selector + extract */}
            <div className="glass-card rounded-2xl p-5 mb-6">
              <div className="flex items-end gap-4">
                <div className="flex-1">
                  <label className="text-xs font-medium text-muted-foreground uppercase tracking-wider mb-2 block">选择项目</label>
                  <select value={selectedProject} onChange={e => { setSelectedProject(e.target.value); setSelectedCharNames([]); setSelectedSceneNames([]); setProjectPrompt(''); setProjectResults([]) }}
                    className="w-full bg-muted border border-border rounded-xl px-4 py-3 text-sm">
                    <option value="">-- 请选择项目 --</option>
                    {projects.map(p => (<option key={p.name} value={p.name}>{p.name}</option>))}
                  </select>
                </div>
                <button onClick={handleExtract} disabled={!selectedProject || extracting}
                  className="flex items-center gap-1.5 px-4 py-3 rounded-xl border-2 border-border text-sm font-medium hover:border-primary/30 disabled:opacity-50 transition-all whitespace-nowrap">
                  {extracting ? <Loader2 className="w-4 h-4 animate-spin" /> : <Sparkles className="w-4 h-4" />}
                  {extracting ? '提取中...' : '🔄 视觉提取'}
                </button>
                {extractedOnce && characters.length > 0 && !extracting && (
                  <button onClick={async () => { await confirmVisualExtract(selectedProject); alert('✅ 已确认') }}
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
                      <p className="text-[10px] text-muted-foreground">点击「视觉提取」</p>
                    ) : (
                      <div className="space-y-1 max-h-48 overflow-y-auto">
                        {characters.map((c: any) => {
                          const sel = selectedCharNames.includes(c.name)
                          return (
                            <button key={c._file} onClick={() => toggleChar(c.name)}
                              className={`w-full flex items-center gap-2.5 px-3 py-2.5 rounded-lg text-[11px] text-left transition-all ${
                                sel ? 'bg-primary/20 text-primary font-medium border border-primary/30' : 'hover:bg-muted/80 text-muted-foreground border border-transparent'
                              }`}>
                              {sel ? <CheckSquare className="w-4 h-4 text-primary flex-shrink-0" /> : <Square className="w-4 h-4 text-muted-foreground/40 flex-shrink-0" />}
                              <span className="flex-1 truncate">{c.name}</span>
                              <span className={`text-[9px] px-1.5 py-0.5 rounded-full ${c.type === 'main' ? 'bg-primary/20 text-primary' : 'bg-muted text-muted-foreground'}`}>{c.type === 'main' ? '主角' : '配角'}</span>
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
                          return (
                            <button key={s._file} onClick={() => toggleScene(s.name)}
                              className={`w-full flex items-center gap-2.5 px-3 py-2.5 rounded-lg text-[11px] text-left transition-all ${
                                sel ? 'bg-primary/20 text-primary font-medium border border-primary/30' : 'hover:bg-muted/80 text-muted-foreground border border-transparent'
                              }`}>
                              {sel ? <CheckSquare className="w-4 h-4 text-primary flex-shrink-0" /> : <Square className="w-4 h-4 text-muted-foreground/40 flex-shrink-0" />}
                              <span className="flex-1 truncate">{s.name}</span>
                            </button>
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
                      <span className="text-[9px] text-muted-foreground">勾选后按模板布局生成多张图</span>
                    </div>
                    <div className="grid grid-cols-2 gap-4">
                      <label className={`flex items-center justify-between p-3 rounded-xl cursor-pointer transition-all ${useCharTemplate ? 'bg-primary/10 border border-primary/30' : 'bg-muted/50 border border-transparent'}`}>
                        <div>
                          <p className="text-[11px] font-medium">角色四视图</p>
                          <p className="text-[9px] text-muted-foreground">面部特写 + 全身正/侧/背</p>
                        </div>
                        <button onClick={() => setUseCharTemplate(!useCharTemplate)}
                          className={`relative w-9 h-5 rounded-full transition-all flex-shrink-0 ${useCharTemplate ? 'bg-primary' : 'bg-muted border border-border'}`}>
                          <div className={`absolute top-0.5 w-4 h-4 rounded-full bg-white shadow transition-all ${useCharTemplate ? 'left-4.5' : 'left-0.5'}`} />
                        </button>
                      </label>
                      <label className={`flex items-center justify-between p-3 rounded-xl cursor-pointer transition-all ${useSceneTemplate ? 'bg-primary/10 border border-primary/30' : 'bg-muted/50 border border-transparent'}`}>
                        <div>
                          <p className="text-[11px] font-medium">场景多角度</p>
                          <p className="text-[9px] text-muted-foreground">正视图 + 左45° + 右45° + 鸟瞰</p>
                        </div>
                        <button onClick={() => setUseSceneTemplate(!useSceneTemplate)}
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
                        <select value={projectCount} onChange={e => setProjectCount(Number(e.target.value))} className="w-full bg-muted border border-border rounded-xl px-3 py-2.5 text-sm">
                          <option value={1}>1 张</option>
                          <option value={2}>2 张</option>
                          <option value={4}>4 张</option>
                        </select>
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
                        <h3 className="font-semibold text-sm">生成结果</h3>
                        <button onClick={() => setProjectResults([])} className="text-xs text-muted-foreground hover:text-red-400 flex items-center gap-1">
                          <Trash2 className="w-3 h-3" /> 清空
                        </button>
                      </div>
                      <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                        {projectResults.map((img, i) => (
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
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {previewSrc && <ImagePreview src={previewSrc} onClose={() => setPreviewSrc(null)} />}
      </div>
    </div>
  )
}
