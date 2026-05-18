import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ArrowLeft, Sparkles, Loader2, Download, Trash2 } from 'lucide-react'
import { fetchProjects, fetchCharacters, fetchScenes, freeImageGen, fetchImageResolutions, fetchActiveConfig, fetchGenerationHistory, deleteGeneratedFile, fetchProjectImages, confirmVersion, deleteVersion } from '../lib/api'
import FreeImageGenForm from '../components/FreeImageGenForm'
import ProjectImageGenForm from '../components/ProjectImageGenForm'
import ImagePreview from '../components/ImagePreview'

import { useToast } from '../components/Toast'
import type { ProjectInfo, EntityImagesMap, GenerationHistory } from '../lib/types'

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
  const [projects, setProjects] = useState<ProjectInfo[]>([])
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
          <FreeImageGenForm
            freePrompt={freePrompt}
            freeNegative={freeNegative}
            freeSize={freeSize}
            freeCount={freeCount}
            freeGenerating={freeGenerating}
            freeError={freeError}
            freeResults={freeResults}
            resolutions={resolutions}
            ratioGroups={ratioGroups}
            selectedRatio={selectedRatio}
            freeModel={freeModel}
            onPromptChange={setFreePrompt}
            onNegativeChange={setFreeNegative}
            onSizeChange={setFreeSize}
            onCountChange={setFreeCount}
            onRatioChange={setSelectedRatio}
            onModelChange={setFreeModel}
            onGenerate={handleFreeGen}
            onClearResults={() => setFreeResults([])}
          />

        ) : (
          <ProjectImageGenForm
            projects={projects}
            selectedProject={selectedProject}
            characters={characters}
            scenes={scenes}
            selectedCharNames={selectedCharNames}
            selectedSceneNames={selectedSceneNames}
            projectPrompt={projectPrompt}
            projectNegative={projectNegative}
            projectSize={projectSize}
            projectCount={projectCount}
            projectGenerating={projectGenerating}
            projectError={projectError}
            useCharTemplate={useCharTemplate}
            useSceneTemplate={useSceneTemplate}
            generatedImages={generatedImages}
            projectResults={projectResults}
            historyProject={historyProject}
            expandedVersions={expandedVersions}
            showAllProject={showAllProject}
            previewSrc={previewSrc}
            resolutions={resolutions}
            ratioGroups={ratioGroups}
            selectedRatio={selectedRatio}
            projectModel={projectModel}
            loading={loading}
            onProjectChange={(v) => { setSelectedProject(v); setSelectedCharNames([]); setSelectedSceneNames([]); setProjectPrompt('') }}
            onCharToggle={toggleChar}
            onSceneToggle={toggleScene}
            onPromptChange={setProjectPrompt}
            onNegativeChange={setProjectNegative}
            onSizeChange={setProjectSize}
            onCountChange={setProjectCount}
            onRatioChange={setSelectedRatio}
            onModelChange={setProjectModel}
            onCharTemplateChange={setUseCharTemplate}
            onSceneTemplateChange={setUseSceneTemplate}
            onToggleShowAll={() => setShowAllProject(!showAllProject)}
            onClearResults={() => setProjectResults([])}
            onToggleVersion={(key) => setExpandedVersions(prev => ({ ...prev, [key]: !prev[key] }))}
            onConfirmVersion={confirmVersion}
            onDeleteVersion={deleteVersion}
            onPreview={setPreviewSrc}
            onConfirmDelete={setConfirmDelete}
            confirmDelete={confirmDelete}
            setShowAllProject={setShowAllProject}
            setExpandedVersions={setExpandedVersions}
            setProjectNegative={setProjectNegative}
            setProjectResults={setProjectResults}
            setHistoryProject={setHistoryProject}
            setProjectError={setProjectError}
            setProjectGenerating={setProjectGenerating}
            setGeneratedImages={setGeneratedImages}
          />
        )}

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
