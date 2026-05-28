import { useEffect, useState } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { ArrowLeft, Sparkles, Loader2, Download, Trash2 } from 'lucide-react'
import { fetchProjects, fetchCharacters, fetchScenes, fetchProps, freeImageGen, fetchImageResolutions, fetchActiveConfig, fetchGenerationHistory, fetchGenerationHistoryItem, deleteGeneratedFile, fetchProjectImages, confirmVersion, deleteVersion, uploadReferenceImage, generateSelectionPrompt, fetchConfirmedImages, fetchImagePresets, fetchCharacterPrompt, fetchCharacterConfirmedImages, fetchScenePrompt, fetchSceneConfirmedImages, fetchPropPrompt, getModelCapability } from '../lib/api'
import FreeImageGenForm from '../components/FreeImageGenForm'
import ProjectImageGenForm from '../components/ProjectImageGenForm'
import ImagePreview from '../components/ImagePreview'

import { useToast } from '../components/Toast'
import Starfield from '../components/Starfield'
import type { ProjectInfo, EntityImagesMap, GenerationHistory, HistoryEntry, CharacterInfo, SceneInfo, PropInfo, EntityImage, ReferenceUrlsByType, FreeRefImage } from '../lib/types'

export default function ImageGenPage() {
  const navigate = useNavigate()
  const location = useLocation()
  const { toast } = useToast()
  const [mode, setMode] = useState<'free' | 'project'>('free')

  // Free mode
  const [freePrompt, setFreePrompt] = useState('')
  const [freeNegative, setFreeNegative] = useState('')
  const [freeSize, setFreeSize] = useState('')
  const [freeCount, setFreeCount] = useState(1)
  const [freeGenerating, setFreeGenerating] = useState(false)
  const [freeResults, setFreeResults] = useState<{ url: string; local: string }[]>([])
  // Free mode resolutions
  const [freeResolutions, setFreeResolutions] = useState<string[]>([])
  const [freeRatioGroups, setFreeRatioGroups] = useState<Record<string, string[]>>({})
  const [freeSelectedRatio, setFreeSelectedRatio] = useState('')
  const [freeModel, setFreeModel] = useState('')
  const [presets, setPresets] = useState<any[]>([])
  const [selectedPreset, setSelectedPreset] = useState<any | null>(null)
  const [projSelectedPreset, setProjSelectedPreset] = useState<any | null>(null)
  const [currentTaskId, setCurrentTaskId] = useState<string | null>(null)
  // Project mode resolutions
  const [projResolutions, setProjResolutions] = useState<string[]>([])
  const [projRatioGroups, setProjRatioGroups] = useState<Record<string, string[]>>({})
  const [projSelectedRatio, setProjSelectedRatio] = useState('')
  const [projectModel, setProjectModel] = useState('')

  // Project mode
  const [projects, setProjects] = useState<ProjectInfo[]>([])
  const [selectedProject, setSelectedProject] = useState<string>('')
  const [characters, setCharacters] = useState<CharacterInfo[]>([])
  const [scenes, setScenes] = useState<SceneInfo[]>([])
  const [props, setProps] = useState<PropInfo[]>([])
  const [extracting, setExtracting] = useState(false)
  const [extractLog, setExtractLog] = useState('')
  const [loading, setLoading] = useState(false)
  const [generatedImages, setGeneratedImages] = useState<EntityImagesMap>({ characters: {}, scenes: {}, props: {} })
  const [previewSrc, setPreviewSrc] = useState<string | null>(null)

  const [selectedChar, setSelectedChar] = useState<string | null>(null)
  const [selectedScene, setSelectedScene] = useState<string | null>(null)
  const [autoRefUrls, setAutoRefUrls] = useState<string[]>([])
  const [manualRefUrls, setManualRefUrls] = useState<string[]>([])
  const [projectPrompt, setProjectPrompt] = useState('')
  const [projectNegative, setProjectNegative] = useState('')
  const [projectSize, setProjectSize] = useState('')
  const [projectCount, setProjectCount] = useState(1)
  const [projectGenerating, setProjectGenerating] = useState(false)
  const [projectResults, setProjectResults] = useState<{ url: string; local: string; seed?: number }[]>([])
  const [lastSeed, setLastSeed] = useState<number | null>(null)
  const [useCharTemplate, setUseCharTemplate] = useState(false)
  const [useSceneTemplate, setUseSceneTemplate] = useState(false)
  const [freeError, setFreeError] = useState('')
  const [projectError, setProjectError] = useState('')
  const [freeRefUrls, setFreeRefUrls] = useState<string[]>([])
  const [freeRefUrlsByType, setFreeRefUrlsByType] = useState<ReferenceUrlsByType>({ style: [], character: [], scene: [], prop: [] })
  const [historyFree, setHistoryFree] = useState<HistoryEntry[]>([])
  const [historyProject, setHistoryProject] = useState<HistoryEntry[]>([])
  const [showAllFree, setShowAllFree] = useState(false)
  const [showAllProject, setShowAllProject] = useState(false)
  const [expandedVersions, setExpandedVersions] = useState<Record<string, boolean>>({})
  const [confirmDelete, setConfirmDelete] = useState<{ message: string; action: () => void } | null>(null)
  const [autoRefUrlsByType, setAutoRefUrlsByType] = useState<ReferenceUrlsByType>({ style: [], character: [], scene: [], prop: [] })
  const [manualRefUrlsByType, setManualRefUrlsByType] = useState<ReferenceUrlsByType>({ style: [], character: [], scene: [], prop: [] })
  const [selectedProp, setSelectedProp] = useState<string | null>(null)
  const [promptLocked, setPromptLocked] = useState(false)
  const [freeCap, setFreeCap] = useState({ max_ref_images: 1, supports_img2img: true })
  const [projectCap, setProjectCap] = useState({ max_ref_images: 1, supports_img2img: true })
  const [refTypeEnabled, setRefTypeEnabled] = useState<Record<string, boolean>>({ style: true, character: true, scene: true, prop: true })
  const [baseRefImages, setBaseRefImages] = useState<FreeRefImage[]>([])
  const [refMetaByType, setRefMetaByType] = useState<Record<string, Record<string, { label: string }>>>({})

  useEffect(() => {
    fetchProjects().then(setProjects)
    fetchImagePresets().then(setPresets)
    fetchGenerationHistory().then(h => { setHistoryFree(h?.images_free || []); setHistoryProject(h?.images_project || []) })
    fetchActiveConfig('image').then(cfg => {
      const model = cfg?.model || ''
      setFreeModel(model)
      setProjectModel(model)
      setFreeCap(getModelCapability(model))
      setProjectCap(getModelCapability(model))
      fetchImageResolutions(model || undefined).then(r => {
        setFreeResolutions(r.resolutions)
        setFreeRatioGroups(r.groups || {})
        setProjResolutions(r.resolutions)
        setProjRatioGroups(r.groups || {})
        const prefer = '16:9'
        const firstGroup = (r.groups && r.groups[prefer]) ? prefer : (Object.keys(r.groups || {})[0] || '')
        const firstSize = r.groups?.[firstGroup]?.[0] || r.resolutions?.[0] || ''
        setFreeSelectedRatio(firstGroup || '')
        setFreeSize(firstSize)
        setProjSelectedRatio(firstGroup || '')
        setProjectSize(firstSize)
      })
    })

    // 从 URL 参数恢复项目名
    const params = new URLSearchParams(location.search)
    const projectFromUrl = params.get('project')
    if (projectFromUrl) {
      fetchProjects().then(list => {
        if (list.some(p => p.name === projectFromUrl)) {
          handleProjectSwitch(projectFromUrl)
          setMode('project')
        }
      })
    } else {
      const savedProject = localStorage.getItem('lastProject')
      if (savedProject) {
        fetchProjects().then(list => {
          if (list.some(p => p.name === savedProject)) {
            handleProjectSwitch(savedProject)
            setMode('project')
          }
        })
      }
    }
  }, [])

  const handleProjectSwitch = async (name: string) => {
    setSelectedProject(name)
    localStorage.setItem('lastProject', name)
    setSelectedChar(null)
    setSelectedScene(null)
    setAutoRefUrls([])
    setManualRefUrls([])
    setProjectPrompt('')
    setAutoRefUrlsByType({ style: [], character: [], scene: [], prop: [] })
    setManualRefUrlsByType({ style: [], character: [], scene: [], prop: [] })
    setSelectedProp(null)
    setLoading(true)
    try {
      const [chars, scns, prps] = await Promise.all([
        fetchCharacters(name),
        fetchScenes(name),
        fetchProps(name),
      ])
      setCharacters(chars)
      setScenes(scns)
      setProps(prps)
    } catch {}
    try {
      const imgs = await fetchProjectImages(name)
      setGeneratedImages(imgs)
    } catch {}
    fetchGenerationHistory().then(h => setHistoryProject(h?.images_project || []))
    setLoading(false)
  }

  const handleExtract = async () => {
    setExtracting(true)
    setExtractLog('⏳ 正在提取角色/场景/道具...')
    try {
      const start = Date.now()
      const res = await fetch(`/api/projects/${encodeURIComponent(selectedProject)}/re-extract-visual`, { method: 'POST' })
      if (!res.ok) throw new Error('提取失败')
      const data = await res.json()
      const [chars, scns, prps] = await Promise.all([
        fetchCharacters(selectedProject),
        fetchScenes(selectedProject),
        fetchProps(selectedProject),
      ])
      setCharacters(chars)
      setScenes(scns)
      setProps(prps)
      setExtractLog(`✅ 提取完成：${data.characters} 个角色，${data.scenes} 个场景（用时 ${Math.round((Date.now() - start) / 1000)} 秒）`)
    } catch (e: any) {
      setExtractLog(`❌ 提取失败：${e.message}`)
    }
    setExtracting(false)
  }

  const handleCharSelect = async (name: string | null) => {
    if (name === selectedChar) { setSelectedChar(null); setProjectPrompt(''); setAutoRefUrls([]); setPromptLocked(false); return }
    setSelectedChar(name)
    setSelectedScene(null)
    if (!name) return
    if (promptLocked) return
    let finalPrompt = ''
    try {
      const result = await fetchCharacterPrompt(selectedProject, name)
      finalPrompt = result.prompt || ''
      if (result.style_decl) {
        finalPrompt = `${result.style_decl.trim()}\n\n${finalPrompt}`
      }
      setProjectPrompt(finalPrompt)

      const isVariant = name.includes('_')
      if (isVariant && result.base_character) {
        const baseImages = await fetchCharacterConfirmedImages(selectedProject, result.base_character)
        let charRefs: string[] = []
        if (baseImages.images.length > 0) {
          charRefs = baseImages.images.map(img => img.url)
        }
        if (result.cross_ref) {
          try {
            const crImages = await fetchCharacterConfirmedImages(selectedProject, result.cross_ref)
            if (crImages.images.length > 0) {
              charRefs = [...charRefs, ...crImages.images.map(img => img.url)]
            }
          } catch {}
        }
        setAutoRefUrls(charRefs)
         setManualRefUrlsByType(prev => {
           const existing = new Set(prev.character || [])
           const merged = [...prev.character, ...charRefs.filter(u => !existing.has(u))]
           return { ...prev, character: merged }
         })
         setRefMetaByType(prev => {
           const meta = { ...(prev.character || {}) }
           const label = result.base_character || name.split('_')[0]
           for (const u of charRefs) { if (!meta[u]) meta[u] = { label } }
           return { ...prev, character: meta }
         })
      } else {
        const selfImages = await fetchCharacterConfirmedImages(selectedProject, name)
        if (selfImages.images.length > 0) {
          const urls = selfImages.images.map(img => img.url)
          setAutoRefUrls(urls)
          setManualRefUrlsByType(prev => {
             const existing = new Set(prev.character || [])
             const merged = [...prev.character, ...urls.filter(u => !existing.has(u))]
             return { ...prev, character: merged }
           })
           setRefMetaByType(prev => {
             const meta = { ...(prev.character || {}) }
             for (const u of urls) { if (!meta[u]) meta[u] = { label: name } }
             return { ...prev, character: meta }
           })
        } else {
          setAutoRefUrls([])
        }
      }
    } catch (e) {
      if (!finalPrompt || finalPrompt === '') {
        setProjectPrompt('')
      }
      setAutoRefUrls([])
    }
    setUseCharTemplate(false)
  }

  const handleSceneSelect = async (name: string | null) => {
    if (name === selectedScene) { setSelectedScene(null); setProjectPrompt(''); setAutoRefUrls([]); setPromptLocked(false); return }
    setSelectedScene(name)
    setSelectedChar(null)
    if (!name) return
    if (promptLocked) return
    let finalPrompt = ''
    try {
      const result = await fetchScenePrompt(selectedProject, name)
      finalPrompt = result.prompt || ''
      if (result.style_decl) {
        finalPrompt = `${result.style_decl.trim()}\n\n${finalPrompt}`
      }
      setProjectPrompt(finalPrompt)

      if (result.base_scene) {
        const baseImages = await fetchSceneConfirmedImages(selectedProject, result.base_scene)
        if (baseImages.images.length > 0) {
          setAutoRefUrls(baseImages.images.map(img => img.url))
        }
      } else {
        const selfImages = await fetchSceneConfirmedImages(selectedProject, name)
        if (selfImages.images.length > 0) {
          setAutoRefUrls(selfImages.images.map(img => img.url))
        } else {
          setAutoRefUrls([])
        }
      }
    } catch (e) {
      if (!finalPrompt || finalPrompt === '') {
        setProjectPrompt('')
      }
      setAutoRefUrls([])
    }
    setUseSceneTemplate(false)
  }

  const handlePropSelect = async (charName: string, propName: string) => {
    const propKey = `${charName}/${propName}`
    if (propKey === selectedProp) { setSelectedProp(null); setProjectPrompt(''); return }
    setSelectedProp(propKey)
    setSelectedChar(null)
    setSelectedScene(null)
    try {
      const result = await fetchPropPrompt(selectedProject, charName, propName)
      const styleDecl = result.style_decl || ''
      const finalPrompt = styleDecl ? `${styleDecl.trim()}\n\n${result.prompt}` : result.prompt
      setProjectPrompt(finalPrompt || '')
    } catch {
      setProjectPrompt('')
    }
  }

  const handleDemandPropSelect = (propName: string, propPrompt: string) => {
    if (propName === selectedProp) { setSelectedProp(null); setProjectPrompt(''); return }
    setSelectedProp(propName)
    setSelectedChar(null)
    setSelectedScene(null)
    setProjectPrompt(propPrompt || '')
  }

  const handleFreeGen = async () => {
    if (!freePrompt.trim()) return
    setFreeError('')
    setFreeGenerating(true)
    try {
      let finalPrompt = freePrompt
      const finalParams: Record<string, unknown> = {}
      if (selectedPreset) {
        if (selectedPreset.prompt_suffix) {
          const styleKeywords = ['cg', '3d', '写实', '动画', '水墨', '像素', '卡通', '二次元', '油画', '素描', '手绘', '赛博', '国风', '复古', '极简']
          const promptLower = freePrompt.toLowerCase()
          const userStyle = styleKeywords.find(k => promptLower.includes(k))
          const suffixStyle = styleKeywords.find(k => selectedPreset.prompt_suffix.includes(k))
          if (userStyle && suffixStyle && userStyle !== suffixStyle) {
            toast(`提示词已指定「${userStyle}」风格，预设「${suffixStyle}」未自动追加 | 如需启用请手动调整`, 'warning')
          } else {
            finalPrompt = `${freePrompt}，${selectedPreset.prompt_suffix}`
          }
        }
        if (selectedPreset.style_params) {
          Object.assign(finalParams, selectedPreset.style_params)
        }
      }
      // 把底图转成 base64 data URI 放入 reference_urls
      const allRefUrls = [...freeRefUrls]
      if (baseRefImages.length > 0) {
        const base64Images = await Promise.all(baseRefImages.map(async (img) => {
          if (img.file) {
            return new Promise<string>((resolve) => {
              const reader = new FileReader()
              reader.onload = () => resolve(reader.result as string)
              reader.readAsDataURL(img.file!)
            })
          }
          // 从 blob URL 获取
          const resp = await fetch(img.url)
          const blob = await resp.blob()
          return new Promise<string>((resolve) => {
            const reader = new FileReader()
            reader.onload = () => resolve(reader.result as string)
            reader.readAsDataURL(blob)
          })
        }))
        allRefUrls.unshift(...base64Images)
      }
      const result = await freeImageGen(finalPrompt, freeNegative, freeSize, freeCount, freeModel, allRefUrls, freeRefUrlsByType, finalParams)
      if (result.task_id) setCurrentTaskId(result.task_id)
      setFreeResults(prev => [...result.images, ...prev])
      fetchGenerationHistory().then(h => setHistoryFree(h.images_free))
    } catch (e: unknown) {
      setFreeError(e instanceof Error ? e.message || '生成失败，请检查 API Key 是否配置正确' : '生成失败，请检查 API Key 是否配置正确')
      toast(e instanceof Error ? e.message : '生成失败', 'error')
    }
    setFreeGenerating(false)
    setCurrentTaskId(null)
  }

  const handleCancelGen = async () => {
    if (!currentTaskId) return
    try {
      await fetch('/api/image-gen/cancel', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ task_id: currentTaskId }),
      })
    } catch {}
    setCurrentTaskId(null)
    setFreeGenerating(false)
    setProjectGenerating(false)
  }

  const handleRemix = (entry: HistoryEntry) => {
    setMode('free')
    if (entry.prompt) setFreePrompt(entry.prompt)
    if (entry.negative_prompt) setFreeNegative(entry.negative_prompt)
    if (entry.model) { setFreeModel(entry.model); setFreeCap(getModelCapability(entry.model)) }
    if (entry.size) { setFreeSize(entry.size); }
    if (entry.count) setFreeCount(Number(entry.count))
    if (entry.reference_urls && entry.reference_urls.length > 0) {
      setFreeRefUrls(entry.reference_urls)
    }
    if (entry.reference_urls_by_type) {
      setFreeRefUrlsByType(entry.reference_urls_by_type)
    }
    toast('已加载历史参数（提示词 + 参考图）', 'success')
  }

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
          🖼️ 智能生图
        </h1>
        <p className="text-xs text-white/15 tracking-wider mb-4">自由创作 · 角色定妆照 · 场景概念图</p>

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
              <div className="text-[10px]" style={{ color: mode === 'free' ? 'rgba(167,139,250,0.6)' : 'rgba(255,255,255,0.2)' }}>输入提示词，AI 自由生成图片</div>
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
              <div className="text-[10px]" style={{ color: mode === 'project' ? 'rgba(167,139,250,0.6)' : 'rgba(255,255,255,0.2)' }}>为项目中的角色/场景/道具生图</div>
            </div>
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
            resolutions={freeResolutions}
            ratioGroups={freeRatioGroups}
            selectedRatio={freeSelectedRatio}
            freeModel={freeModel}
            referenceUrls={freeRefUrls}
            referenceUrlsByType={freeRefUrlsByType}
            onReferenceUrlsByTypeChange={setFreeRefUrlsByType}
            onFreeRefImagesChange={setBaseRefImages}
            presets={presets}
            selectedPreset={selectedPreset}
            currentTaskId={currentTaskId}
            onCancel={handleCancelGen}
            onReferenceUrlsChange={setFreeRefUrls}
            onPromptChange={setFreePrompt}
            onNegativeChange={setFreeNegative}
            onSizeChange={setFreeSize}
            onCountChange={setFreeCount}
            onRatioChange={setFreeSelectedRatio}
            onModelChange={(model) => { setFreeModel(model); setFreeCap(getModelCapability(model)) }}
            onPresetSelect={setSelectedPreset}
            onGenerate={handleFreeGen}
            onClearResults={() => setFreeResults([])}
            onPreview={setPreviewSrc}
            modelCap={freeCap}
          />

        ) : (
          <>
          {selectedProject && characters.length === 0 && scenes.length === 0 && (
            <div className="flex items-center gap-3 mb-4">
              <button onClick={handleExtract} disabled={extracting}
                className="flex items-center gap-1.5 px-4 py-3 rounded-xl border-2 border-white/[0.15] text-sm font-medium hover:bg-white/[0.04] disabled:opacity-50 transition-all whitespace-nowrap">
                {extracting ? <Loader2 className="w-4 h-4 animate-spin" /> : <Sparkles className="w-4 h-4" />}
                {extracting ? '提取中...' : '🔄 视觉提取'}
              </button>
              {extractLog && (
                <p className={`text-xs ${extractLog.includes('✅') ? 'text-green-400' : extractLog.includes('❌') ? 'text-red-400' : 'text-white/55'}`}>
                  {extractLog}
                </p>
              )}
            </div>
          )}
          <ProjectImageGenForm
            projects={projects}
            selectedProject={selectedProject}
            characters={characters}
            scenes={scenes}
            propsList={props}
            selectedChar={selectedChar}
            selectedScene={selectedScene}
            autoRefUrls={autoRefUrls}
            manualRefUrls={manualRefUrls}
            onManualRefUrlsChange={setManualRefUrls}
            autoRefUrlsByType={autoRefUrlsByType}
            manualRefUrlsByType={manualRefUrlsByType}
            refMetaByType={refMetaByType}
            onManualRefUrlsByTypeChange={setManualRefUrlsByType}
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
            resolutions={projResolutions}
            ratioGroups={projRatioGroups}
            selectedRatio={projSelectedRatio}
            projectModel={projectModel}
            presets={presets}
            selectedPreset={projSelectedPreset}
            onPresetSelect={setProjSelectedPreset}
            currentTaskId={currentTaskId}
            onCancel={handleCancelGen}
            loading={loading}
            onProjectChange={(v) => { handleProjectSwitch(v) }}
            onCharSelect={handleCharSelect}
            onSceneSelect={handleSceneSelect}
            selectedProp={selectedProp}
            onPropSelect={handlePropSelect}
            onDemandPropSelect={handleDemandPropSelect}
            onModelChange={(model) => { setProjectModel(model); setProjectCap(getModelCapability(model)) }}
            onPromptChange={setProjectPrompt}
            onNegativeChange={setProjectNegative}
            onSizeChange={setProjectSize}
            onCountChange={setProjectCount}
            onRatioChange={setProjSelectedRatio}
            onCharTemplateChange={setUseCharTemplate}
            onSceneTemplateChange={setUseSceneTemplate}
            promptLocked={promptLocked}
            onPromptLockToggle={() => setPromptLocked(!promptLocked)}
            refTypeEnabled={refTypeEnabled}
            onRefTypeToggle={(type) => setRefTypeEnabled(prev => ({ ...prev, [type]: !prev[type] }))}
            onToggleShowAll={() => setShowAllProject(!showAllProject)}
            onClearResults={() => setProjectResults([])}
            onToggleVersion={(key) => setExpandedVersions(prev => ({ ...prev, [key]: !prev[key] }))}
            onConfirmVersion={async (project, type, name, version) => {
              await confirmVersion(project, type, name, version)
              const imgs = await fetchProjectImages(project)
              setGeneratedImages(imgs)
            }}
            onDeleteVersion={async (project, type, name, version) => {
              try { await deleteVersion(project, type, name, version) } catch {}
              const imgs = await fetchProjectImages(project)
              setGeneratedImages(imgs)
            }}
            onPreview={setPreviewSrc}
            onConfirmDelete={setConfirmDelete}
            onRemix={handleRemix}
            confirmDelete={confirmDelete}
            setShowAllProject={setShowAllProject}
            setExpandedVersions={setExpandedVersions}
            setProjectNegative={setProjectNegative}
            setProjectResults={setProjectResults}
            setHistoryProject={setHistoryProject}
            setProjectError={setProjectError}
            setProjectGenerating={setProjectGenerating}
            setGeneratedImages={setGeneratedImages}
            fetchProjectImages={fetchProjectImages}
            modelCap={projectCap}
          />
          </>
        )}

        {mode === 'free' && historyFree.length > 0 && (
          <div className="rounded-2xl p-5 mt-6 card-glow premium-panel premium-glow-bottom">
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-semibold text-sm">✏️ 自由创作历史</h3>
              {historyFree.length > 9 && (
                <button onClick={() => setShowAllFree(!showAllFree)} className="text-[10px] text-white/55 hover:text-white transition-colors">
                  {showAllFree ? '收起' : `查看全部 (${historyFree.length})`}
                </button>
              )}
            </div>
            <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-4 gap-3">
              {(showAllFree ? historyFree : historyFree.slice(0, 9)).map((img, i) => (
                <div key={img.url} className="premium-grid-item group">
                  <img src={img.url} alt="" className="w-full h-36 object-contain bg-white img-hover"
                    onClick={() => setPreviewSrc(img.url)} />
                  <div className="px-2.5 py-2 space-y-1">
                    <p className="text-[10px] text-white/55 leading-tight truncate">
                      {img.prompt ? img.prompt.slice(0, 40) + (img.prompt.length > 40 ? '...' : '') : '无 prompt'}
                    </p>
                    <div className="flex items-center justify-between gap-1">
                      <span className="text-[10px] text-white/35">{img.model || '-'} · {img.size || '-'}</span>
                      {img.reference_urls && img.reference_urls.length > 0 && (
                        <span className="text-[10px] text-amber-400/70">📎 {img.reference_urls.length}</span>
                      )}
                    </div>
                  </div>
                  <div className="absolute top-2 right-2 flex gap-1 opacity-0 group-hover:opacity-100 transition-all">
                    <button onClick={(e) => { e.stopPropagation(); handleRemix(img) }}
                      className="p-1.5 rounded-lg bg-white/[0.12] hover:bg-white/[0.18] text-white text-[10px] pointer-events-auto" title="画同款">
                      画同款
                    </button>
                    <a href={img.url} download={img.name} className="p-1.5 rounded-lg bg-white/20 hover:bg-white/30 text-white pointer-events-auto" title="下载"
                      onClick={e => e.stopPropagation()}>
                      <Download className="w-3 h-3" />
                    </a>
                    <button onClick={async (e) => { e.stopPropagation(); setConfirmDelete({ message: '确认删除这张图片？', action: async () => { try { await deleteGeneratedFile(img.url); setHistoryFree(prev => prev.filter((_, j) => j !== i)); } catch {} } }) }}
                      className="p-1.5 rounded-lg bg-red-500/20 hover:bg-red-500/30 text-white pointer-events-auto" title="删除">
                      <Trash2 className="w-3 h-3" />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {previewSrc && (
          <ImagePreview src={previewSrc} onClose={() => setPreviewSrc(null)}
            images={[
              ...freeResults.map(r => r.local ? `/generated/${r.local.split('\\').pop() || r.local.split('/').pop()}` : r.url),
              ...projectResults.map(r => r.local ? `/generated/${r.local.split('\\').pop() || r.local.split('/').pop()}` : r.url),
              ...historyFree.map(r => r.url),
              ...historyProject.map(r => r.url),
            ]}
            onNavigate={(i) => {
              const all = [
                ...freeResults.map(r => r.local ? `/generated/${r.local.split('\\').pop() || r.local.split('/').pop()}` : r.url),
                ...projectResults.map(r => r.local ? `/generated/${r.local.split('\\').pop() || r.local.split('/').pop()}` : r.url),
                ...historyFree.map(r => r.url),
                ...historyProject.map(r => r.url),
              ]
              if (all[i]) setPreviewSrc(all[i])
            }}
          />
        )}
        {confirmDelete && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm" onClick={() => setConfirmDelete(null)}>
            <div className="bg-[#01010a] border border-white/[0.10] rounded-2xl p-6 max-w-sm w-full mx-4 shadow-2xl card-glow premium-panel" onClick={e => e.stopPropagation()}>
              <p className="text-sm mb-6 text-center">{confirmDelete.message}</p>
              <div className="flex gap-3">
                <button onClick={() => setConfirmDelete(null)}
                  className="flex-1 py-2.5 rounded-xl border border-white/[0.10] text-sm text-white/55 hover:bg-white/[0.04] transition-colors">取消</button>
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