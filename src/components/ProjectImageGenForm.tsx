import { useState, useEffect, useMemo, useRef, useCallback } from 'react'
import { ChevronDown, ChevronRight, Sparkles, X, Lock, Unlock, Loader2, Image, Trash2, Search, Plus, History, ImageIcon } from 'lucide-react'
import CollapsibleSection from './CollapsibleSection'
import { CharacterInfo, SceneInfo, PropInfo, EntityImagesMap, ReferenceUrlsByType, FreeRefImage } from '../lib/types'
import { fetchProjectAssetLibrary, fetchImageDemands, projectDemandBatchGen, fetchGenerationHistory, fetchPropsSummary, fetchPropPrompt } from '../lib/api'
import ModelSelector from './ModelSelector'
import ReferenceImageUploader from './ReferenceImageUploader'

interface HistoryEntry {
  name: string
  url: string
  [key: string]: unknown
}

interface ProjectImageGenFormProps {
  selectedProject: string
  projects: { name: string; [key: string]: unknown }[]
  characters: CharacterInfo[]
  scenes: SceneInfo[]
  propsList: PropInfo[]
  selectedChar: string | null
  selectedScene: string | null
  projectPrompt: string
  projectNegative: string
  projectSize: string
  projectCount: number
  projectGenerating: boolean
  projectError: string
  useCharTemplate: boolean
  useSceneTemplate: boolean
  promptLocked: boolean
  onPromptLockToggle: () => void
  refTypeEnabled: Record<string, boolean>
  onRefTypeToggle: (type: string) => void
  generatedImages: EntityImagesMap
  projectResults: { url: string; local: string }[]
  historyProject: { name: string; url: string; [key: string]: unknown }[]
  expandedVersions: Record<string, boolean>
  showAllProject: boolean
  previewSrc: string | null
  resolutions: string[]
  ratioGroups: Record<string, string[]>
  selectedRatio: string
  projectModel: string
  currentTaskId: string | null
  onCancel: () => void
  loading: boolean
  autoRefUrls: string[]
  manualRefUrls: string[]
  presets: any[]
  selectedPreset: any | null
  onPresetSelect: (preset: any | null) => void
  onProjectChange: (v: string) => void
  onCharSelect: (name: string | null) => void
  onSceneSelect: (name: string | null) => void
  onManualRefUrlsChange: (urls: string[]) => void
  onPromptChange: (v: string) => void
  onNegativeChange: (v: string) => void
  onSizeChange: (v: string) => void
  onCountChange: (v: number) => void
  onRatioChange: (v: string) => void
  onModelChange: (v: string) => void
  onCharTemplateChange: (v: boolean) => void
  onSceneTemplateChange: (v: boolean) => void
  onGenerate: () => void
  onToggleShowAll: () => void
  onClearResults: () => void
  onToggleVersion: (key: string) => void
  onConfirmVersion: (project: string, type: string, name: string, version: string) => void
  onDeleteVersion: (project: string, type: string, name: string, version: string) => void
  onPreview: (src: string | null) => void
  onConfirmDelete: (data: { message: string; action: () => void } | null) => void
  onRemix?: (entry: HistoryEntry) => void
  autoRefUrlsByType: ReferenceUrlsByType
  manualRefUrlsByType: ReferenceUrlsByType
  refMetaByType?: Record<string, Record<string, { label: string }>>
  onManualRefUrlsByTypeChange: (v: ReferenceUrlsByType) => void
  selectedProp: string | null
  onPropSelect: (characterName: string, propName: string) => void
  onDemandPropSelect: (propName: string, propPrompt: string) => void
  confirmDelete: { message: string; action: () => void } | null
  setShowAllProject: (v: boolean) => void
  setExpandedVersions: (fn: (prev: Record<string, boolean>) => Record<string, boolean>) => void
  setProjectError: (v: string) => void
  setProjectGenerating: (v: boolean) => void
  setProjectResults: (results: { url: string; local: string }[]) => void
  setHistoryProject: (history: any[]) => void
  setAutoRefUrlsByType: (v: ReferenceUrlsByType) => void
  setAutoRefUrls: (urls: string[]) => void
  setGeneratedImages: (images: EntityImagesMap) => void
  fetchProjectImages: (project: string) => Promise<EntityImagesMap>
  setProjectPrompt: (v: string) => void
  useSceneBackgroundRef?: boolean
  setUseSceneBackgroundRef?: (v: boolean) => void
  onFreeGen?: (prompt: string) => void
  setSelectedChar?: (v: string | null) => void
  setSelectedScene?: (v: string | null) => void
  onPropPromptFetch?: (result: { prompt: string; character_name: string }) => void
  freeGenerating?: boolean
  freeError?: string
  freePrompt?: string
  setFreePrompt?: (v: string) => void
  setFreeGenerating?: (v: boolean) => void
  setFreeError?: (v: string) => void
  modelCap?: { max_ref_images: number; supports_img2img: boolean }
}

const ProjectImageGenForm: React.FC<ProjectImageGenFormProps> = (props) => {
  const {
    selectedProject,
    projects,
    characters,
    scenes,
    propsList,
    selectedChar,
    selectedScene,
    projectPrompt,
    projectNegative,
    projectSize,
    projectCount,
    projectGenerating,
    projectError,
    useCharTemplate,
    useSceneTemplate,
    promptLocked,
    onPromptLockToggle,
    refTypeEnabled,
    onRefTypeToggle,
    generatedImages,
    projectResults,
    historyProject,
    expandedVersions,
    showAllProject,
    previewSrc,
    resolutions,
    ratioGroups,
    selectedRatio,
    projectModel,
    currentTaskId,
    onCancel,
    loading,
    autoRefUrls,
    manualRefUrls,
    presets,
    selectedPreset,
    onPresetSelect,
    onProjectChange,
    onCharSelect,
    onSceneSelect,
    onManualRefUrlsChange,
    onPromptChange,
    onNegativeChange,
    onSizeChange,
    onCountChange,
    onRatioChange,
    onModelChange,
    onCharTemplateChange,
    onSceneTemplateChange,
    onGenerate,
    onToggleShowAll,
    onClearResults,
    onToggleVersion,
    onConfirmVersion,
    onDeleteVersion,
    onPreview,
    onConfirmDelete,
    onRemix,
    autoRefUrlsByType,
    manualRefUrlsByType,
    refMetaByType,
    onManualRefUrlsByTypeChange,
    selectedProp,
    onPropSelect,
    onDemandPropSelect,
    confirmDelete,
    setShowAllProject,
    setExpandedVersions,
    setProjectError,
    setProjectGenerating,
    setProjectResults,
    setHistoryProject,
    setAutoRefUrlsByType,
    setAutoRefUrls,
    setGeneratedImages,
    fetchProjectImages,
    setProjectPrompt,
    useSceneBackgroundRef,
    setUseSceneBackgroundRef,
    onFreeGen,
    setSelectedChar,
    setSelectedScene,
    onPropPromptFetch,
    freeGenerating,
    freeError,
    freePrompt,
    setFreePrompt,
    setFreeGenerating,
    setFreeError,
    modelCap,
  } = props

  const [expandedChars, setExpandedChars] = useState<Record<string, boolean>>({})
  const [expandedScenes, setExpandedScenes] = useState<Record<string, boolean>>({})
  const [generatingStatus, setGeneratingStatus] = useState('')
  const [promptEdited, setPromptEdited] = useState(false)
  const [historySearch, setHistorySearch] = useState('')
  const [propsSummary, setPropsSummary] = useState<any[]>([])
  const [generalRefUrls, setGeneralRefUrls] = useState<string[]>([])
  const [generalRefEnabled, setGeneralRefEnabled] = useState(false)
  const [imageDemands, setImageDemands] = useState<any>(null)
  const [demandAnalyzing, setDemandAnalyzing] = useState(false)
  const [expandedDemandChars, setExpandedDemandChars] = useState<Record<string, boolean>>({})
  const promptRef = useRef<HTMLTextAreaElement>(null)
  const [projectRefImages, setProjectRefImages] = useState<any[]>([])
  const fileInputRef3 = useRef<HTMLInputElement>(null)
  const [showRefHistory, setShowRefHistory] = useState(false)
  const [showRefPicker, setShowRefPicker] = useState(false)
  const refPickerRef = useRef<HTMLDivElement>(null)
  const [refHistoryImages, setRefHistoryImages] = useState<{ name: string; url: string }[]>([])
  const [refHistoryLoading, setRefHistoryLoading] = useState(false)

  const charTree = useMemo(() => {
    const chars = (characters || []) as CharacterInfo[]
    const bases = chars.filter(c => c && c.is_base)
    return bases.map(base => ({
      ...base,
      children: chars.filter(c => c && c.character_base === base.name && c.name !== base.name)
    }))
  }, [characters])

  const sceneTree = useMemo(() => {
    const scns = (scenes || []) as SceneInfo[]
    const bases = scns.filter(c => c && c.is_base)
    return bases.map(base => ({
      ...base,
      children: scns.filter(c => c && c.scene_base === base.name && c.name !== base.name)
    }))
  }, [scenes])

  useEffect(() => {
    if (!selectedProject) return
    fetchImageDemands(selectedProject).then(data => {
      if (data && !data._normalized) {
        data.characters = (data.characters || []).map((c: any) => ({
          ...c,
          shots: (c.shot_indices || []).map((si: number, idx: number) => ({
            shot_id: si,
            episode: c.episodes ? c.episodes[Math.min(idx, (c.episodes.length - 1) || 0)] : '',
          }))
        }))
        data.scenes = (data.scenes || []).map((s: any) => ({
          ...s,
          shots: (s.shot_indices || []).map((si: number, idx: number) => ({
            shot_id: si,
            episode: s.episodes ? s.episodes[Math.min(idx, (s.episodes.length - 1) || 0)] : '',
          }))
        }))
        if (data.character_groups) {
          data.character_groups = data.character_groups.map((g: any) => ({
            ...g,
            members: (g.members || []).map((m: any) => ({
              ...m,
              shots: m.shots,
            }))
          }))
        }
        data._normalized = true
        if (data.character_groups) {
          data.character_groups = data.character_groups.filter((g: any) => {
            const gn = g.name || ''
            if (/^(无[（(]|屏幕|画面|声音|声源|文字|字幕|回执|水渍|残骸|碎片|照片|镜头|系统)/.test(gn)) return false
            if (gn.includes('→') || gn.includes('→')) return false
            return true
          })
        }
        if (data.scene_groups) {
          data.scene_groups = data.scene_groups.filter((g: any) => {
            const gn = g.name || ''
            if (/^(无[（(]|记忆-林川回忆|画面|声音|声源|文字|回执)/.test(gn)) return false
            return true
          })
        }
        if (data.scenes) {
          data.scenes = data.scenes.filter((s: any) => {
            const sn = s.name || ''
            if (/^(无[（(]|记忆-林川回忆|画面|声音|声源|文字|回执)/.test(sn)) return false
            return true
          })
        }
      }
      setImageDemands(data)
    }).catch(() => {})
  }, [selectedProject])

  useEffect(() => {
    if (!selectedProject) return
    fetchPropsSummary(selectedProject).then(d => setPropsSummary(d?.props || [])).catch(() => {})
    fetchProjectAssetLibrary(selectedProject).then(lib => {
      const refs: string[] = []
      Object.values(lib.characters || {}).forEach((c: any) => {
        if (c.images && c.images.length > 0) refs.push(...c.images)
      })
      setGeneralRefUrls(refs)
    }).catch(() => {})
  }, [selectedProject])

  useEffect(() => {
    const el = promptRef.current
    if (el) {
      el.style.height = 'auto'
      el.style.height = el.scrollHeight + 'px'
    }
  }, [projectPrompt])

  const handleReanalyze = async () => {
    setDemandAnalyzing(true)
    try {
      const res = await fetch(`${import.meta.env.VITE_API_BASE || '/api'}/projects/${encodeURIComponent(selectedProject)}/re-analyze-demands`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: '{}' })
      if (res.ok) {
        const data = await fetchImageDemands(selectedProject)
        if (data) {
          data._normalized = false
          setImageDemands(null)
          setTimeout(() => setImageDemands(data), 100)
        }
      }
    } catch {} finally { setDemandAnalyzing(false) }
  }

  const handleCharTemplateGen = async () => {
    if (!selectedChar || !projectPrompt.trim()) return
    setProjectGenerating(true)
    try {
      let ver = 1
      try {
        const data: any = await fetchProjectImages(selectedProject)
        const gi = (data?.characters || {})[selectedChar || '']
        const keys = Object.keys(gi?.versions || {}).sort((a: string, b: string) => Number(a) - Number(b))
        ver = keys.length > 0 ? Math.max(...keys.map(Number)) + 1 : 1
      } catch {}
      const templatePrompt = `${projectPrompt}\n\n【构图要求】画面左侧为角色面部特写（仅限头部和颈部，不出现服装），画面右侧为全身三视图横向排列（正面全身/侧面全身/背面全身）。三视图中的服装必须与上述角色设定的服装完全一致（颜色、款式、细节不可改变）。背景为纯色或浅渐变。`
      await genWithBaseImages({
        project_name: selectedProject,
        prompt: templatePrompt,
        negative_prompt: projectNegative,
        size: projectSize,
        n: 1,
        model: projectModel,
        character_names: [selectedChar],
        scene_names: [],
        reference_urls: [...autoRefUrls, ...manualRefUrls, ...generalRefUrls],
        reference_urls_by_type: manualRefUrlsByType || ({} as ReferenceUrlsByType),
      })
      fetchGenerationHistory().then(h => setHistoryProject(h?.images_project || []))
      fetchProjectImages(selectedProject).then(setGeneratedImages)
    } catch {} finally { setProjectGenerating(false) }
  }

  const handleSceneTemplateGen = async () => {
    if (!selectedScene || !projectPrompt.trim()) return
    setProjectGenerating(true)
    try {
      let ver = 1
      try {
        const data: any = await fetchProjectImages(selectedProject)
        const gi = (data?.scenes || {})[selectedScene || '']
        const keys = Object.keys(gi?.versions || {}).sort((a: string, b: string) => Number(a) - Number(b))
        ver = keys.length > 0 ? Math.max(...keys.map(Number)) + 1 : 1
      } catch {}
      await genWithBaseImages({
        project_name: selectedProject,
        prompt: projectPrompt,
        negative_prompt: (projectNegative ? projectNegative + ', ' : '') + '不要出现人物, no people, no characters',
        size: projectSize,
        n: 1,
        model: projectModel,
        character_names: [],
        scene_names: [selectedScene],
        reference_urls: [...autoRefUrls, ...manualRefUrls, ...generalRefUrls],
        reference_urls_by_type: manualRefUrlsByType || ({} as ReferenceUrlsByType),
      })
      fetchGenerationHistory().then(h => setHistoryProject(h?.images_project || []))
      fetchProjectImages(selectedProject).then(setGeneratedImages)
    } catch {} finally { setProjectGenerating(false) }
  }

  const genWithBaseImages = async (params: Record<string, unknown>) => {
    const refUrls: string[] = [...(params.reference_urls as string[] || [])]
    if (projectRefImages.length > 0) {
      const base64Images = await Promise.all(projectRefImages.map(async (img: any) => {
        if (img.file) {
          return new Promise<string>((resolve) => {
            const reader = new FileReader()
            reader.onload = () => resolve(reader.result as string)
            reader.readAsDataURL(img.file)
          })
        }
        const resp = await fetch(img.url)
        const blob = await resp.blob()
        return new Promise<string>((resolve) => {
          const reader = new FileReader()
          reader.onload = () => resolve(reader.result as string)
          reader.readAsDataURL(blob)
        })
      }))
      refUrls.unshift(...base64Images)
    }
    return projectDemandBatchGen({ ...params, reference_urls: refUrls } as any)
  }

  const handleGen = async () => {
    if (!projectPrompt.trim()) return
    setProjectGenerating(true)
    try {
      await genWithBaseImages({
        project_name: selectedProject,
        prompt: projectPrompt,
        negative_prompt: projectNegative,
        size: projectSize,
        n: 1,
        model: projectModel,
        character_names: selectedChar ? [selectedChar] : [],
        scene_names: selectedScene ? [selectedScene] : [],
        reference_urls: [...autoRefUrls, ...manualRefUrls, ...generalRefUrls],
        reference_urls_by_type: manualRefUrlsByType || ({} as ReferenceUrlsByType),
      })
      fetchGenerationHistory().then(h => setHistoryProject(h?.images_project || []))
      fetchProjectImages(selectedProject).then(setGeneratedImages)
    } catch {} finally { setProjectGenerating(false) }
  }

  return (
    <div>
      <div className="mb-4">
        <select value={selectedProject} onChange={e => onProjectChange(e.target.value)}
          className="w-full premium-select rounded-xl px-4 py-3 text-sm">
          <option value="">-- 选择项目 --</option>
          {projects.map(p => <option key={p.name} value={p.name}>{p.name}</option>)}
        </select>
      </div>

      {selectedProject && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-1 space-y-4">
            {imageDemands && (
              <div className="premium-subpanel p-4 premium-glow-bottom">
                <CollapsibleSection title={`📋 生图需求清单${imageDemands.fallback ? ' (降级模式)' : ''}`} defaultOpen={true} actions={<button onClick={e => { e.stopPropagation(); handleReanalyze() }} disabled={demandAnalyzing} className="ml-2 text-[9px] px-1.5 py-0.5 rounded border border-primary/20 text-primary/60 hover:bg-primary/10 disabled:opacity-40">{demandAnalyzing ? '分析中...' : '🔄 分析需求'}</button>}>
                  <div className="space-y-1 max-h-80 overflow-y-auto">
                    <CollapsibleSection title={`🧑 角色 (${(imageDemands.character_groups || []).length}组, ${(imageDemands.characters || []).length}个)`} defaultOpen={false}>
                      <div className="space-y-0.5 ml-2">
                        {(imageDemands.character_groups || []).length > 0 ? (
                          (imageDemands.character_groups || []).map((group: any) => {
                            const expanded = expandedDemandChars[`demand_${group.name}`]
                            const members = group.members || []
                            return (
                              <div key={group.name}>
                                <div onClick={() => setExpandedDemandChars(prev => ({ ...prev, [`demand_${group.name}`]: !prev[`demand_${group.name}`] }))}
                                  className="flex items-center gap-1 px-2 py-0.5 rounded cursor-pointer text-[10px] hover:bg-muted text-muted-foreground transition-all">
                                  {expanded ? <ChevronDown className="w-2.5 h-2.5" /> : <ChevronRight className="w-2.5 h-2.5" />}
                                  <span className="truncate">{group.name}</span>
                                  <span className="text-[8px] bg-primary/10 text-primary/70 px-1 py-0 rounded-full ml-auto">{group.total_shots}镜</span>
                                </div>
                                {expanded && members.map((member: any) => {
                                  const isConfirmed = imageDemands._confirmed && imageDemands._confirmed[member.name]
                                  const isVariant = !member.is_base
                                  return (
                                    <div key={member.name} className={`ml-4 flex items-center gap-1 px-2 py-0.5 rounded text-[9px] ${isConfirmed ? 'bg-green-500/5' : ''} ${isVariant && !isConfirmed ? 'text-muted-foreground/40' : 'text-muted-foreground/70'}`}>
                                      {member.is_base ? '👤' : '🔄'}
                                      <span>{member.variant_name || member.name}</span>
                                      <span className="ml-auto text-[8px] text-primary/50">{member.shots}镜</span>
                                      {isConfirmed && <span className="text-green-400 text-[8px]">✓</span>}
                                      {isVariant && !isConfirmed && <span className="text-amber-400 text-[8px]">⚠</span>}
                                    </div>
                                  )
                                })}
                              </div>
                            )
                          })
                        ) : (
                          (imageDemands.characters || []).map((char: any) => (
                            <div key={char.name} className="flex items-center gap-1 px-2 py-0.5 text-[10px] text-muted-foreground/70">
                              <span className="truncate">{char.name}</span>
                              <span className="text-[8px] text-primary/50 ml-auto">{(char.shots || []).length}镜</span>
                            </div>
                          ))
                        )}
                      </div>
                    </CollapsibleSection>

                    <CollapsibleSection title={`🏔️ 场景 (${(imageDemands.scene_groups || []).length}组, ${((imageDemands.scene_groups || []).reduce((sum: number, g: any) => sum + (g.members || []).length, 0))}个)`} defaultOpen={false}>
                      <div className="space-y-0.5 ml-2">
                        {(imageDemands.scene_groups || []).map((group: any) => {
                          const expanded = expandedDemandChars[`demand_scene_${group.name}`]
                          const members = group.members || []
                          return (
                            <div key={`sg_${group.name}`}>
                              <div onClick={() => setExpandedDemandChars(prev => ({ ...prev, [`demand_scene_${group.name}`]: !prev[`demand_scene_${group.name}`] }))}
                                className="flex items-center gap-1 px-2 py-0.5 rounded cursor-pointer text-[10px] hover:bg-muted text-muted-foreground transition-all">
                                {expanded ? <ChevronDown className="w-2.5 h-2.5" /> : <ChevronRight className="w-2.5 h-2.5" />}
                                <span className="truncate">{group.name}</span>
                                <span className="text-[8px] bg-primary/10 text-primary/70 px-1 py-0 rounded-full ml-auto">{group.total_shots}镜</span>
                              </div>
                              {expanded && members.map((member: any) => {
                                const isConfirmed = imageDemands._confirmed && imageDemands._confirmed[member.name]
                                const isVariant = !member.is_base
                                return (
                                  <div key={member.name} className={`ml-4 flex items-center gap-1 px-2 py-0.5 rounded text-[9px] ${isConfirmed ? 'bg-green-500/5' : ''} ${isVariant && !isConfirmed ? 'text-muted-foreground/40' : 'text-muted-foreground/70'}`}>
                                    {member.is_base ? '🏔️' : '🔍'}
                                    <span>{member.variant_name || member.name}</span>
                                    <span className="ml-auto text-[8px] text-primary/50">{member.shots}镜</span>
                                  </div>
                                )
                              })}
                            </div>
                          )
                        })}
                      </div>
                    </CollapsibleSection>

                    {((imageDemands.cross_scene_props || []).length + (imageDemands.scene_props || []).length) > 0 && (
                      <CollapsibleSection title={`🔧 道具 (${(imageDemands.cross_scene_props || []).length + (imageDemands.scene_props || []).length}个)`} defaultOpen={false}>
                        <div className="space-y-0.5 ml-2">
                          {(imageDemands.cross_scene_props || []).length > 0 && (
                            <div className="mb-1">
                              <div className="text-[9px] text-muted-foreground/50 px-1">跨场景 · {(imageDemands.cross_scene_props || []).length}个</div>
                              {(imageDemands.cross_scene_props || []).map((prop: any) => {
                                const isConfirmed = imageDemands._confirmed && imageDemands._confirmed[prop.name]
                                return (
                                  <div key={`cross_${prop.name}`}
                                    className={`flex items-center gap-1 px-2 py-0.5 rounded text-[10px] text-muted-foreground/70 ${isConfirmed ? 'bg-green-500/5' : ''}`}>
                                    {isConfirmed && <span className="text-green-400 text-[9px]">✓</span>}
                                    <span className="truncate">{prop.name}</span>
                                  </div>
                                )
                              })}
                            </div>
                          )}
                          {(imageDemands.scene_props || []).length > 0 && (
                            <div>
                              <div className="text-[9px] text-muted-foreground/50 px-1">场景 · {(imageDemands.scene_props || []).length}个</div>
                              {(imageDemands.scene_props || []).map((prop: any) => {
                                const isConfirmed = imageDemands._confirmed && imageDemands._confirmed[prop.name]
                                return (
                                  <div key={`scene_${prop.name}`}
                                    className={`flex items-center gap-1 px-2 py-0.5 rounded text-[10px] text-muted-foreground/70 ${isConfirmed ? 'bg-green-500/5' : ''}`}>
                                    {isConfirmed && <span className="text-green-400 text-[9px]">✓</span>}
                                    <span className="truncate">{prop.name}</span>
                                  </div>
                                )
                              })}
                            </div>
                          )}
                        </div>
                      </CollapsibleSection>
                    )}

                    {(imageDemands.characters || []).length === 0 && (imageDemands.scene_groups || []).length === 0 && ((imageDemands.cross_scene_props || []).length + (imageDemands.scene_props || []).length) === 0 && (
                      <p className="text-[10px] text-muted-foreground py-4 text-center">清单为空，请先运行生图需求管线</p>
                    )}
                  </div>
                </CollapsibleSection>
              </div>
            )}

            <div className="premium-subpanel p-4 premium-glow-bottom">
              <CollapsibleSection title={`🧑 ${(imageDemands?.character_groups || []).length} 个角色`}>
                {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : (imageDemands?.character_groups || []).length === 0 ? (
                  <p className="text-[10px] text-muted-foreground">暂无角色数据</p>
                ) : (
                  <div className="space-y-2 max-h-64 overflow-y-auto">
                    {(imageDemands?.character_groups || []).map((group: any) => {
                      const members = group.members || []
                      const baseMember = members.find((m: any) => m.is_base) || members[0]
                      const baseName = baseMember?.name || group.name
                      const isSelected = selectedChar === baseName || members.some((m: any) => selectedChar === m.name)
                      const charPropsMap = imageDemands?.char_props || {}
                      const groupProps: any[] = []
                      for (const [owner, items] of Object.entries(charPropsMap)) {
                        if (owner === group.name || owner.startsWith(group.name + '（') || owner.startsWith(group.name + '(') || owner === group.name.replace(/^系统/, '').replace(/【】/, '')) {
                          groupProps.push(...(items as any[]))
                        }
                      }
                      const hasChildren = members.length > 1 || groupProps.length > 0
                      const expanded = expandedChars[group.name]
                      const gi: any = (generatedImages as any).characters?.[group.name]
                      const confirmedImgs = gi?.images || []
                      const versions = gi?.versions || {}
                      const versionKeys = Object.keys(versions).sort()
                      return (
                        <div key={group.name}>
                          <div onClick={() => {
                            if (hasChildren) {
                              setExpandedChars(prev => ({ ...prev, [group.name]: !prev[group.name] }))
                            } else {
                              onCharSelect(baseName)
                            }
                          }}
                            className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg cursor-pointer text-[11px] transition-all ${
                              isSelected ? 'bg-primary/15 text-primary font-medium' : 'hover:bg-muted text-muted-foreground'
                            }`}>
                            {hasChildren && (
                              expanded ? <ChevronDown className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />
                            )}
                            {confirmedImgs.length > 0 && <span className="w-1.5 h-1.5 rounded-full bg-green-500 flex-shrink-0" />}
                            <span className="truncate">{group.name}</span>
                            {versionKeys.length > 0 && <span className="text-[9px] text-muted-foreground/50 flex-shrink-0">v{versionKeys.length}</span>}
                          </div>
                          {expanded && hasChildren && (
                            <div onClick={(e) => { e.stopPropagation(); onCharSelect(baseName) }}
                              className={`flex items-center gap-1.5 ml-4 px-2.5 py-1.5 rounded-lg cursor-pointer text-[11px] transition-all ${
                                selectedChar === baseName ? 'bg-primary/15 text-primary font-medium' : 'hover:bg-muted text-muted-foreground/80'
                              }`}>
                              <ImageIcon className="w-3 h-3 opacity-50" />
                              <span className="truncate">基础形象</span>
                            </div>
                          )}
                          {expanded && hasChildren && members.filter((m: any) => !m.is_base).map((member: any) => (
                            <div key={member.name} onClick={() => { onCharSelect(member.name) }}
                              className={`flex items-center gap-1.5 ml-4 px-2.5 py-1.5 rounded-lg cursor-pointer text-[11px] transition-all ${
                                selectedChar === member.name ? 'bg-primary/15 text-primary font-medium' : 'hover:bg-muted text-muted-foreground/80'
                              }`}>
                              <ChevronRight className="w-2.5 h-2.5 opacity-50" />
                              <span className="truncate">{member.variant_name || member.name}</span>
                            </div>
                          ))}
                          {expanded && groupProps.length > 0 && (
                            <div className="ml-4 mt-1 border-t border-border/20 pt-0.5">
                              <div className="text-[9px] text-muted-foreground/50 px-2.5 py-0.5">🎒 随身道具</div>
                              {groupProps.map((prop: any) => {
                                const propKey = `${group.name}/${prop.name}`
                                const isPropSelected = selectedProp === propKey
                                return (
                                  <div key={prop.name} onClick={(e) => { e.stopPropagation(); onPropSelect(group.name, prop.name) }}
                                    className={`flex items-center gap-1.5 ml-2 px-2.5 py-0.5 rounded cursor-pointer text-[10px] transition-all ${
                                      isPropSelected ? 'bg-primary/15 text-primary font-medium' : 'hover:bg-muted text-muted-foreground/60'
                                    }`}>
                                    <span className="truncate">{prop.name}</span>
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
              </CollapsibleSection>
              {(imageDemands?.character_groups || []).length > 0 && (
                <div className="space-y-1 mt-2">
                  <button onClick={async () => {
                    const groups = imageDemands?.character_groups || []
                    const bases = groups.length > 0
                      ? groups.flatMap((g: any) => (g.members || []).filter((m: any) => m.is_base))
                      : []
                    const names = bases.length > 0 ? bases.map((m: any) => m.name) : charTree.map(c => c.name)
                    if (names.length === 0) return
                    setProjectGenerating(true)
                    let idx = 0
                    for (const name of names) {
                      idx++
                      setGeneratingStatus(`基础形象 ${idx}/${names.length}: ${name}`)
                      try {
                        await genWithBaseImages({
                          project_name: selectedProject,
                          prompt: projectPrompt,
                          negative_prompt: projectNegative,
                          size: projectSize,
                          n: 1,
                          model: projectModel,
                          character_names: [name],
                          scene_names: [],
                          reference_urls: [...autoRefUrls, ...manualRefUrls, ...generalRefUrls],
                          reference_urls_by_type: manualRefUrlsByType || ({} as ReferenceUrlsByType),
                        })
                      } catch {}
                    }
                    fetchGenerationHistory().then(h => setHistoryProject(h?.images_project || []))
                    fetchProjectImages(selectedProject).then(setGeneratedImages)
                    setProjectGenerating(false)
                    setGeneratingStatus('')
                  }} disabled={projectGenerating}
                    className="w-full px-3 py-2 rounded-lg text-[10px] border border-primary/20 text-primary/70 hover:bg-primary/10 hover:text-primary transition-colors disabled:opacity-40">
                    ⚡ 第一步：生成所有基础形象 ({(() => {
                      const groups = imageDemands?.character_groups || []
                      const bases = groups.flatMap((g: any) => (g.members || []).filter((m: any) => m.is_base))
                      return bases.length || charTree.length
                    })()}个)
                  </button>
                  <button onClick={async () => {
                    const groups = imageDemands?.character_groups || []
                    const variants = groups.flatMap((g: any) => (g.members || []).filter((m: any) => !m.is_base))
                    const names = variants.map((m: any) => m.name)
                    if (names.length === 0) return
                    setProjectGenerating(true)
                    let idx = 0
                    for (const name of names) {
                      idx++
                      setGeneratingStatus(`变体 ${idx}/${names.length}: ${name}`)
                      const group = groups.find((g: any) => (g.members || []).some((m: any) => m.name === name))
                      const baseName = group?.name || ''
                      const baseImages = baseName ? ((generatedImages as any).characters?.[baseName]?.images || []) : []
                      const baseRefUrls = baseImages.map((img: any) => img.url)
                      try {
                        await genWithBaseImages({
                          project_name: selectedProject,
                          prompt: projectPrompt,
                          negative_prompt: projectNegative,
                          size: projectSize,
                          n: 1,
                          model: projectModel,
                          character_names: [name],
                          scene_names: [],
                          reference_urls: [...autoRefUrls, ...manualRefUrls, ...generalRefUrls, ...baseRefUrls],
                          reference_urls_by_type: manualRefUrlsByType || ({} as ReferenceUrlsByType),
                        })
                      } catch {}
                    }
                    fetchGenerationHistory().then(h => setHistoryProject(h?.images_project || []))
                    fetchProjectImages(selectedProject).then(setGeneratedImages)
                    setProjectGenerating(false)
                    setGeneratingStatus('')
                  }} disabled={projectGenerating || (() => {
                    const groups = imageDemands?.character_groups || []
                    const bases = groups.flatMap((g: any) => (g.members || []).filter((m: any) => m.is_base))
                    return bases.some((m: any) => !(imageDemands?._confirmed && imageDemands._confirmed[m.name]))
                  })()}
                    className="w-full px-3 py-2 rounded-lg text-[10px] border border-border/30 text-muted-foreground/50 hover:bg-muted/20 transition-colors disabled:opacity-30 disabled:cursor-not-allowed">
                    ⚡ 第二步：生成所有变体 ({(() => {
                      const groups = imageDemands?.character_groups || []
                      const variants = groups.flatMap((g: any) => (g.members || []).filter((m: any) => !m.is_base))
                      return variants.length
                    })()}个)
                  </button>
                </div>
              )}
            </div>

            {(selectedChar || selectedScene) && (() => {
              const entityName = selectedChar || selectedScene || ''
              const entityType = selectedChar ? 'characters' : 'scenes'
              const gi: any = (generatedImages as any)[entityType]?.[entityName] || {}
              const confirmedImgs = gi?.images || []
              const versions: Record<string, any> = gi?.versions || {}
              const versionKeys = Object.keys(versions).sort()

              if (versionKeys.length === 0 && confirmedImgs.length === 0) return null

              return (
                <div className="premium-subpanel p-4 premium-glow-bottom">
                  <p className="text-[10px] font-medium mb-3" style={{ color: 'rgba(167, 139, 250, 0.7)' }}>
                    {selectedChar ? '🧑' : '🏔️'} {entityName} · 版本管理
                  </p>
                  {confirmedImgs.length > 0 && (
                    <div className="mb-3">
                      <div className="flex items-center gap-1.5 mb-2">
                        <span className="w-1.5 h-1.5 rounded-full bg-green-500" />
                        <span className="text-[10px] text-green-400 font-medium">已确认版本</span>
                      </div>
                      <div className="flex flex-wrap gap-1.5">
                        {confirmedImgs.slice(0, 4).map((img: any, idx: number) => (
                          <img key={idx} src={img.url} alt="" onClick={() => onPreview(img.url)}
                            className="w-12 h-12 rounded-lg object-cover border border-green-500/30 cursor-pointer hover:border-green-400 transition-colors img-hover" />
                        ))}
                      </div>
                    </div>
                  )}
                  {versionKeys.length > 0 && (
                    <div className="space-y-2 max-h-48 overflow-y-auto">
                      {versionKeys.map(v => {
                        const vData = versions[v] || {}
                        const vImgs = vData.images || vData || []
                        const imgList = Array.isArray(vImgs) ? vImgs : []
                        const key = `${entityType}-${entityName}-${v}`
                        const expand = expandedVersions[key]
                        return (
                          <div key={v} className={`bg-muted/30 rounded-lg p-2 border ${vData.confirmed ? 'border-green-500/40 bg-green-500/5' : 'border-border/20'}`}>
                            <div className="flex items-center justify-between">
                              <button onClick={() => onToggleVersion(key)}
                                className="flex items-center gap-1 text-[10px] text-muted-foreground hover:text-foreground transition-colors">
                                {expand ? <ChevronDown className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />}
                                v{v} · {imgList.length}张
                                {vData.confirmed && <span className="text-green-400">✓ 已确认</span>}
                              </button>
                              <div className="flex items-center gap-1">
                                {!vData.confirmed && (
                                  <button onClick={() => onConfirmVersion(selectedProject, entityType, entityName, v)}
                                    className="text-[9px] px-1.5 py-0.5 rounded bg-green-500/20 text-green-400 hover:bg-green-500/30 transition-colors">
                                    确认
                                  </button>
                                )}
                                <button onClick={() => onDeleteVersion(selectedProject, entityType, entityName, v)}
                                  className="text-[9px] px-1 py-0.5 rounded hover:bg-red-500/20 text-red-400 transition-colors">
                                  <Trash2 className="w-3 h-3" />
                                </button>
                              </div>
                            </div>
                            {expand && (
                              <div className="flex flex-wrap gap-1.5 mt-2">
                                {imgList.map((img: any, i: number) => (
                                  <img key={i} src={img.url || img} alt="" onClick={() => onPreview(img.url || img)}
                                    className="w-10 h-10 rounded object-cover cursor-pointer hover:ring-1 ring-primary transition-all img-hover" />
                                ))}
                              </div>
                            )}
                          </div>
                        )
                      })}
                    </div>
                  )}
                </div>
              )
            })()}

            <div className="premium-subpanel p-4 premium-glow-bottom">
              <CollapsibleSection title={`🏔️ ${(imageDemands?.scene_groups || []).length} 个场景`}>
                {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : (imageDemands?.scene_groups || []).length === 0 ? (
                  <p className="text-[10px] text-muted-foreground">暂无场景数据</p>
                ) : (
                  <div className="space-y-2 max-h-64 overflow-y-auto">
                    {(imageDemands?.scene_groups || []).map((group: any) => {
                      const members = group.members || []
                      const baseMember = members.find((m: any) => m.is_base) || members[0]
                      const baseName = baseMember?.name || group.name
                      const isSelected = selectedScene === baseName || members.some((m: any) => selectedScene === m.name)
                      const hasChildren = members.length > 1
                      const expanded = expandedScenes[group.name]
                      const gi: any = (generatedImages as any).scenes?.[group.name]
                      const confirmedImgs = gi?.images || []
                      const versions = gi?.versions || {}
                      const versionKeys = Object.keys(versions).sort()
                      return (
                        <div key={group.name}>
                          <div onClick={() => { onSceneSelect(baseName) }}
                            className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg cursor-pointer text-[11px] transition-all ${
                              isSelected ? 'bg-primary/15 text-primary font-medium' : 'hover:bg-muted text-muted-foreground'
                            }`}>
                            {hasChildren && (
                              <button onClick={(e) => { e.stopPropagation(); setExpandedScenes(prev => ({ ...prev, [group.name]: !prev[group.name] })) }}
                                className="p-0.5 hover:text-foreground">
                                {expanded ? <ChevronDown className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />}
                              </button>
                            )}
                            {confirmedImgs.length > 0 && <span className="w-1.5 h-1.5 rounded-full bg-green-500 flex-shrink-0" />}
                            <span className="truncate">{group.name}</span>
                            {versionKeys.length > 0 && <span className="text-[9px] text-muted-foreground/50 flex-shrink-0">v{versionKeys.length}</span>}
                          </div>
                          {expanded && hasChildren && members.filter((m: any) => !m.is_base).map((member: any) => (
                            <div key={member.name} onClick={() => { onSceneSelect(member.name) }}
                              className={`flex items-center gap-1.5 ml-4 px-2.5 py-1.5 rounded-lg cursor-pointer text-[11px] transition-all ${
                                selectedScene === member.name ? 'bg-primary/15 text-primary font-medium' : 'hover:bg-muted text-muted-foreground/80'
                              }`}>
                              <ChevronRight className="w-2.5 h-2.5 opacity-50" />
                              <span className="truncate">{member.variant_name || member.name}</span>
                            </div>
                          ))}
                        </div>
                      )
                    })}
                  </div>
                )}
              </CollapsibleSection>
              {(imageDemands?.scene_groups || []).length > 0 && (
                <button onClick={async () => {
                  const demandGroups = imageDemands?.scene_groups || []
                  const names = demandGroups.flatMap((g: any) => (g.members || []).filter((m: any) => m.is_base).map((m: any) => m.name))
                  if (names.length === 0) return
                  setProjectGenerating(true)
                  let idx = 0
                  for (const name of names) {
                    idx++
                    setGeneratingStatus(`场景概念图 ${idx}/${names.length}: ${name}`)
                    try {
                      await genWithBaseImages({
                        project_name: selectedProject,
                        prompt: projectPrompt,
                        negative_prompt: (projectNegative ? projectNegative + ', ' : '') + '不要出现人物, no people, no characters',
                        size: projectSize,
                        n: 1,
                        model: projectModel,
                        character_names: [],
                        scene_names: [name],
                        reference_urls: [...autoRefUrls, ...manualRefUrls, ...generalRefUrls],
                        reference_urls_by_type: manualRefUrlsByType || ({} as ReferenceUrlsByType),
                      })
                    } catch {}
                  }
                  fetchGenerationHistory().then(h => setHistoryProject(h?.images_project || []))
                  fetchProjectImages(selectedProject).then(setGeneratedImages)
                  setProjectGenerating(false)
                  setGeneratingStatus('')
                }} disabled={projectGenerating}
                  className="w-full mt-2 px-3 py-2 rounded-lg text-[10px] border border-primary/20 text-primary/70 hover:bg-primary/10 hover:text-primary transition-colors disabled:opacity-40">
                  ⚡ 一键生成所有场景概念图 ({(imageDemands?.scene_groups || []).length}组)
                </button>
              )}
            </div>

            {((imageDemands?.cross_scene_props || []).length + (imageDemands?.scene_props || []).length) > 0 && (
              <div className="premium-subpanel p-4 premium-glow-bottom">
                {(imageDemands?.cross_scene_props || []).length > 0 && (
                  <>
                    <CollapsibleSection title={`🔧 跨场景道具 (${(imageDemands?.cross_scene_props || []).length}个)`} defaultOpen={false}>
                      <div className="space-y-1 ml-2 max-h-32 overflow-y-auto">
                        {(imageDemands?.cross_scene_props || []).map((prop: any) => (
                          <div key={prop.name} onClick={(e) => { e.stopPropagation(); onDemandPropSelect(prop.name, prop.prompt || '') }}
                            className={`flex items-center gap-1.5 px-2.5 py-0.5 rounded cursor-pointer text-[10px] transition-all ${
                              selectedProp === prop.name ? 'bg-primary/15 text-primary font-medium' : 'hover:bg-muted text-muted-foreground/60'
                            }`}>
                            <span className="truncate">{prop.name}</span>
                            <span className="text-[8px] text-muted-foreground/40 ml-auto flex-shrink-0">{prop.scene_count || 0}景</span>
                          </div>
                        ))}
                      </div>
                    </CollapsibleSection>
                    <button onClick={async () => {
                      const props = imageDemands?.cross_scene_props || []
                      if (props.length === 0) return
                      setProjectGenerating(true)
                      let idx = 0
                      for (const prop of props) {
                        idx++
                        setGeneratingStatus(`跨场景道具 ${idx}/${props.length}: ${prop.name}`)
                        try {
                          await genWithBaseImages({
                            project_name: selectedProject,
                            prompt: prop.prompt || projectPrompt,
                            negative_prompt: projectNegative,
                            size: projectSize,
                            n: 1,
                            model: projectModel,
                            character_names: [],
                            scene_names: [],
                            prop_names: [prop.name],
                            reference_urls: [...autoRefUrls, ...manualRefUrls, ...generalRefUrls],
                            reference_urls_by_type: manualRefUrlsByType || ({} as ReferenceUrlsByType),
                          })
                        } catch {}
                      }
                      fetchGenerationHistory().then(h => setHistoryProject(h?.images_project || []))
                      fetchProjectImages(selectedProject).then(setGeneratedImages)
                      setProjectGenerating(false)
                      setGeneratingStatus('')
                    }} disabled={projectGenerating}
                      className="w-full mt-2 px-3 py-2 rounded-lg text-[10px] border border-primary/20 text-primary/70 hover:bg-primary/10 hover:text-primary transition-colors disabled:opacity-40">
                      ⚡ 一键生成跨场景道具 ({(imageDemands?.cross_scene_props || []).length}个)
                    </button>
                  </>
                )}
                {(imageDemands?.scene_props || []).length > 0 && (
                  <>
                    <div className={(imageDemands?.cross_scene_props || []).length > 0 ? 'mt-3 pt-3 border-t border-border/20' : ''} />
                    <CollapsibleSection title={`🏗️ 场景道具 (${(imageDemands?.scene_props || []).length}个) · 可选`} defaultOpen={false}>
                      <div className="space-y-1 ml-2 max-h-40 overflow-y-auto">
                        {(imageDemands?.scene_props || []).map((prop: any) => (
                          <div key={prop.name} onClick={(e) => { e.stopPropagation(); onDemandPropSelect(prop.name, prop.prompt || '') }}
                            className={`flex items-center gap-1.5 px-2.5 py-0.5 rounded cursor-pointer text-[10px] transition-all ${
                              selectedProp === prop.name ? 'bg-primary/15 text-primary font-medium' : 'hover:bg-muted text-muted-foreground/60'
                            }`}>
                            <span className="truncate">{prop.name}</span>
                            <span className="text-[8px] text-muted-foreground/40 ml-auto flex-shrink-0">{prop.scene_count || 0}景</span>
                          </div>
                        ))}
                      </div>
                    </CollapsibleSection>
                    <button onClick={async () => {
                      const props = imageDemands?.scene_props || []
                      if (props.length === 0) return
                      setProjectGenerating(true)
                      let idx = 0
                      for (const prop of props) {
                        idx++
                        setGeneratingStatus(`场景道具 ${idx}/${props.length}: ${prop.name}`)
                        try {
                          await genWithBaseImages({
                            project_name: selectedProject,
                            prompt: prop.prompt || projectPrompt,
                            negative_prompt: projectNegative,
                            size: projectSize,
                            n: 1,
                            model: projectModel,
                            character_names: [],
                            scene_names: [],
                            prop_names: [prop.name],
                            reference_urls: [...autoRefUrls, ...manualRefUrls, ...generalRefUrls],
                            reference_urls_by_type: manualRefUrlsByType || ({} as ReferenceUrlsByType),
                          })
                        } catch {}
                      }
                      fetchGenerationHistory().then(h => setHistoryProject(h?.images_project || []))
                      fetchProjectImages(selectedProject).then(setGeneratedImages)
                      setProjectGenerating(false)
                      setGeneratingStatus('')
                    }} disabled={projectGenerating}
                      className="w-full mt-2 px-3 py-2 rounded-lg text-[10px] border border-primary/20 text-primary/70 hover:bg-primary/10 hover:text-primary transition-colors disabled:opacity-40">
                      ⚡ 一键生成场景道具 ({(imageDemands?.scene_props || []).length}个)
                    </button>
                  </>
                )}
              </div>
            )}
          </div>

          <div className="lg:col-span-2 space-y-4">
            <div className="premium-panel p-5">
              <div className="premium-header" style={{ marginBottom: '0.75rem' }}>
                <label className="premium-label" style={{ marginBottom: 0 }}>提示词</label>
                <div className="flex items-center gap-1">
                  <button onClick={() => setShowRefPicker(!showRefPicker)}
                    className="p-2 rounded-lg border transition-all flex-shrink-0 border-white/10 text-white/50 hover:border-primary/30"
                    title="@引用参考图">@</button>
                  <button onClick={onPromptLockToggle}
                    className={`p-2 rounded-lg border transition-all flex-shrink-0 ${promptLocked ? 'bg-amber-500/10 border-amber-500/30 text-amber-400' : 'border-white/10 text-white/50 hover:border-primary/30'}`}
                    title={promptLocked ? '提示词已锁定，切换角色不会覆盖' : '点击锁定提示词'}>
                    {promptLocked ? <Lock className="w-3.5 h-3.5" /> : <Unlock className="w-3.5 h-3.5" />}
                  </button>
                </div>
              </div>
              {showRefPicker && (
                <div ref={refPickerRef} className="mb-3 p-3 rounded-xl" style={{ background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.08)' }}>
                  <div className="text-[10px] text-muted-foreground mb-2 flex items-center justify-between">
                    <span>@引用参考图 — 点击插入提示词</span>
                    <button onClick={() => setShowRefPicker(false)} className="text-xs text-muted-foreground hover:text-white">✕</button>
                  </div>
                  {projectRefImages.length > 0 && (
                    <div className="mb-2">
                      <div className="text-[9px] text-muted-foreground/50 mb-1">🖼️ 底图</div>
                      <div className="flex flex-wrap gap-1">
                        {projectRefImages.map((img: any, idx: number) => (
                          <span key={img.id} onClick={() => {
                            const ta = promptRef.current; if (ta) { const pos = ta.selectionStart; const text = ta.value; ta.value = text.slice(0, pos) + `@底图${idx+1} ` + text.slice(pos); ta.focus(); ta.setSelectionRange(pos + 4, pos + 4); onPromptChange(ta.value) } setShowRefPicker(false)
                          }} className="inline-block px-1.5 py-0.5 rounded text-[9px] cursor-pointer" style={{ background: 'rgba(16,185,129,0.15)', color: '#10b981' }}>@底图{idx+1}</span>
                        ))}
                      </div>
                    </div>
                  )}
                  {(['character','scene','prop','style'] as const).map(type => {
                    const urls = (manualRefUrlsByType as any)[type] || [] as string[]
                    if (urls.length === 0) return null
                    const labels: Record<string,string> = { character:'👤 角色', scene:'🏠 场景', prop:'🔧 道具', style:'🎨 画风' }
                    const metaMap = (refMetaByType || {})[type] || {}
                    return (
                      <div key={type} className="mb-1">
                        <div className="text-[9px] text-muted-foreground/50 mb-1">{labels[type]}</div>
                        <div className="flex flex-wrap gap-1">
                          {urls.map((url: string, idx: number) => {
                            const meta = metaMap[url]
                            const display = meta ? `@${meta.label}` : `@${labels[type]}${idx+1}`
                            return (
                              <span key={`${type}_${idx}`} onClick={() => {
                                const ta = promptRef.current; if (ta) { const pos = ta.selectionStart; const text = ta.value; const tag = meta ? ` @${meta.label} ` : ` @${labels[type]} `; ta.value = text.slice(0, pos) + tag + text.slice(pos); ta.focus(); ta.setSelectionRange(pos + tag.length, pos + tag.length); onPromptChange(ta.value) } setShowRefPicker(false)
                              }} className="inline-block px-1.5 py-0.5 rounded text-[9px] cursor-pointer" style={{ background: meta ? 'rgba(16,185,129,0.2)' : 'rgba(139,92,246,0.15)', color: meta ? '#10b981' : '#a78bfa' }}>{display}</span>
                            )
                          })}
                        </div>
                      </div>
                    )
                  })}
                </div>
              )}
              <textarea ref={promptRef} value={projectPrompt} onChange={e => { onPromptChange(e.target.value); const t = e.target; t.style.height = 'auto'; t.style.height = t.scrollHeight + 'px' }}
                placeholder={selectedChar || selectedScene ? '已自动生成提示词，可在此微调' : '请从左侧选择角色或场景'}
                className="flex-1 w-full premium-input rounded-xl px-4 py-3 min-h-[6rem] resize-none text-sm overflow-hidden mb-3" />

              {modelCap?.supports_img2img !== false && (
              <div className="premium-section-refmode mb-4">
                <div className="refmode-label">
                  <span>🖼️ 参考图生图 — 底图上传</span>
                  <span className="refmode-badge">模式1</span>
                </div>
                <p className="refmode-desc">上传原始底图，可同时上传多张。提示词中用 @图1/@图2 引用</p>

                <div className="refmode-grid">
                  {projectRefImages.map((img: any, idx: number) => (
                    <div key={img.id} className="refmode-thumb" style={{ borderColor: idx === 0 ? '#10b981' : undefined }}>
                      <img src={img.url} alt="" style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
                      <div style={{ position: 'absolute', top: '4px', left: '4px', fontSize: '9px', background: '#10b981', color: 'black', padding: '1px 6px', borderRadius: '4px', fontWeight: 700 }}>{img.label}</div>
                      <button
                        onClick={() => setProjectRefImages((prev: any[]) => prev.filter((r: any) => r.id !== img.id).map((r: any, i: number) => ({ ...r, label: `图${i + 1}` })))}
                        style={{ position: 'absolute', top: '4px', right: '4px', width: '16px', height: '16px', borderRadius: '50%', background: 'rgba(0,0,0,0.6)', display: 'flex', alignItems: 'center', justifyContent: 'center', cursor: 'pointer', border: 'none', color: 'white', fontSize: '8px' }}>
                        ✕
                      </button>
                      <button onClick={() => {
                        const ta = promptRef.current
                        if (ta) {
                          const pos = ta.selectionStart
                          const text = ta.value
                          ta.value = text.slice(0, pos) + `@底图${idx+1} ` + text.slice(pos)
                          ta.focus()
                          ta.setSelectionRange(pos + 5, pos + 5)
                          onPromptChange(ta.value)
                        }
                      }} className="text-[9px] text-primary/70 hover:text-primary" style={{ position: 'absolute', bottom: '4px', right: '4px' }}>@</button>
                    </div>
                  ))}
                  <div
                    onClick={() => fileInputRef3.current?.click()}
                    onDrop={(e: any) => {
                      e.preventDefault()
                      const files = Array.from(e.dataTransfer.files)
                      files.forEach((file: any) => {
                        const url = URL.createObjectURL(file)
                        setProjectRefImages((prev: any[]) => [...prev, { id: crypto.randomUUID(), url, label: `图${prev.length + 1}`, file }])
                      })
                    }}
                    onDragOver={(e: any) => e.preventDefault()}
                    className="refmode-add">
                    <div style={{ fontSize: '22px', color: 'rgba(16,185,129,0.5)' }}>+</div>
                    <div style={{ fontSize: '9px', color: 'rgba(16,185,129,0.5)' }}>拖入上传</div>
                  </div>
                  <input ref={fileInputRef3} type="file" accept="image/*" multiple
                    style={{ display: 'none' }}
                    onChange={(e: any) => {
                      const files = Array.from(e.target.files || [])
                      files.forEach((file: any) => {
                        const url = URL.createObjectURL(file)
                        setProjectRefImages((prev: any[]) => [...prev, { id: crypto.randomUUID(), url, label: `图${prev.length + 1}`, file }])
                      })
                      e.target.value = ''
                    }} />
                </div>

                {projectRefImages.length > 0 && (
                  <div className="refmode-at-bar">
                    <span style={{ color: 'rgba(255,255,255,0.35)' }}>@引用：点击插入提示词</span>
                    {projectRefImages.map((img: any, idx: number) => (
                      <span key={img.id}
                        onClick={() => {
                          const ta = promptRef.current
                          if (ta) {
                            const pos = ta.selectionStart
                            const text = ta.value
                            ta.value = text.slice(0, pos) + `@底图${idx+1} ` + text.slice(pos)
                            ta.focus()
                            ta.setSelectionRange(pos + 5, pos + 5)
                            onPromptChange(ta.value)
                          }
                        }}
                        style={{ display: 'inline-block', background: 'rgba(16,185,129,0.15)', color: '#10b981', padding: '2px 8px', borderRadius: '4px', cursor: 'pointer', fontWeight: 600, userSelect: 'none' }}>
                        @底图{idx+1}
                      </span>
                    ))}
                  </div>
                )}

                <button onClick={async () => {
                  setShowRefHistory(true)
                  setRefHistoryLoading(true)
                  try {
                    const h = await fetchGenerationHistory()
                    const all = [...(h.images_free || []), ...(h.images_project || [])]
                    setRefHistoryImages(all)
                  } catch {
                  } finally {
                    setRefHistoryLoading(false)
                  }
                }} type="button"
                  className="mt-2 flex items-center gap-1.5 text-[10px] text-muted-foreground hover:text-primary transition-colors">
                  <History className="w-3 h-3" /> 从历史作品选择
                </button>
              </div>
              )}

              {showRefHistory && (
                <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm" onClick={() => setShowRefHistory(false)}>
                  <div className="bg-background border border-border rounded-2xl p-5 max-w-lg w-full mx-4 max-h-[80vh] flex flex-col shadow-2xl" onClick={e => e.stopPropagation()}>
                    <div className="flex items-center justify-between mb-3">
                      <h3 className="font-semibold text-sm flex items-center gap-1.5">
                        <ImageIcon className="w-4 h-4" />
                        选择历史作品 → 加入底图
                      </h3>
                      <button onClick={() => setShowRefHistory(false)} className="text-muted-foreground hover:text-foreground text-xs">✕</button>
                    </div>
                    {refHistoryLoading ? (
                      <div className="flex items-center justify-center py-10">
                        <Loader2 className="w-5 h-5 animate-spin text-muted-foreground" />
                      </div>
                    ) : refHistoryImages.length === 0 ? (
                      <p className="text-xs text-muted-foreground text-center py-10">暂无历史作品</p>
                    ) : (
                      <div className="grid grid-cols-3 sm:grid-cols-4 gap-2 overflow-y-auto max-h-64">
                        {refHistoryImages.map((img) => (
                          <div key={img.url} className="group relative cursor-pointer rounded-lg overflow-hidden border border-border/30 hover:border-green-500/50 transition-colors"
                            onClick={() => {
                              if (!projectRefImages.some(r => r.url === img.url)) {
                                setProjectRefImages(prev => [...prev, { id: crypto.randomUUID(), url: img.url, label: `图${prev.length + 1}` }])
                              }
                              setShowRefHistory(false)
                            }}>
                            <img src={img.url} alt="" className="w-full h-20 object-cover bg-muted" />
                            <div className="absolute inset-0 bg-black/0 group-hover:bg-green-500/20 transition-all flex items-center justify-center opacity-0 group-hover:opacity-100">
                              <span className="text-[10px] text-white bg-black/60 px-2 py-0.5 rounded-full">选择</span>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              )}

              <div className="grid grid-cols-2 gap-3 mb-3">
                <div>
                  <label className="premium-label" style={{ fontSize: '0.625rem' }}>模型</label>
                  <ModelSelector type="image" value={projectModel} onChange={onModelChange} />
                </div>
                <div>
                  <label className="premium-label" style={{ fontSize: '0.625rem' }}>比例</label>
                  <select value={selectedRatio} onChange={e => { onRatioChange(e.target.value); const rs = ratioGroups[e.target.value]; if (rs && rs.length > 0) onSizeChange(rs[0]) }}
                    className="w-full premium-select rounded-xl px-3 py-2.5 text-[11px]">
                    {Object.keys(ratioGroups).map(r => (<option key={r} value={r}>{r}</option>))}
                  </select>
                </div>
              </div>

              {presets.length > 0 && (
                <div className="mb-4">
                  <label className="premium-label" style={{ fontSize: '0.625rem' }}>🎨 风格预设</label>
                  <div className="premium-btn-group">
                    <button onClick={() => onPresetSelect(null)}
                      className={!selectedPreset ? 'active' : ''}>
                      无
                    </button>
                    {presets.map((p: any) => (
                      <button key={p.id} onClick={() => onPresetSelect(p)}
                        className={selectedPreset?.id === p.id ? 'active' : ''}>
                        {p.name}
                      </button>
                    ))}
                  </div>
                </div>
              )}

              <ReferenceImageUploader
                autoUrls={autoRefUrls} manualUrls={manualRefUrls}
                autoUrlsByType={autoRefUrlsByType} manualUrlsByType={manualRefUrlsByType}
                onManualChange={onManualRefUrlsChange}
                onManualByTypeChange={onManualRefUrlsByTypeChange}
                refTypeEnabled={refTypeEnabled} onRefTypeToggle={onRefTypeToggle}
                generalRefUrls={generalRefUrls} generalRefEnabled={generalRefEnabled}
                onGeneralRefToggle={setGeneralRefEnabled}
              />

              {projectGenerating ? (
                <div className="space-y-2 mt-4">
                  <div className="flex items-center gap-2 text-sm text-muted-foreground">
                    <Loader2 className="w-4 h-4 animate-spin" />
                    <span>{generatingStatus || '生成中...'}</span>
                  </div>
                  {currentTaskId && (
                    <button onClick={onCancel}
                      className="flex items-center gap-1.5 px-4 py-3 rounded-xl border border-red-400/30 text-red-400 text-sm hover:bg-red-500/10 transition-colors">
                      <X className="w-4 h-4" /> 取消
                    </button>
                  )}
                </div>
              ) : (
                <div className="flex flex-wrap gap-2 mt-4">
                  <button onClick={useCharTemplate ? handleCharTemplateGen : useSceneTemplate ? handleSceneTemplateGen : handleGen}
                    disabled={!projectPrompt.trim() || (!selectedChar && !selectedScene)}
                    className={`flex items-center gap-2 px-6 py-3 rounded-xl text-sm font-medium disabled:opacity-50 transition-all ${
                      useCharTemplate || useSceneTemplate
                        ? 'border-2 border-primary/30 text-primary hover:bg-primary/10'
                        : 'btn-gradient'
                    }`}>
                    <Sparkles className="w-4 h-4" /> {useCharTemplate || useSceneTemplate ? '生成模板' : '生成'}
                  </button>
                  {selectedChar && (
                    <button onClick={() => { onCharTemplateChange(!useCharTemplate); if (useSceneTemplate) onSceneTemplateChange(false) }}
                      className={`flex items-center gap-1.5 px-4 py-3 rounded-xl border-2 text-sm transition-all ${
                        useCharTemplate ? 'bg-primary/20 text-primary border-primary/40' : 'border-border text-muted-foreground hover:border-primary/30'
                      }`}
                      title="启用后生成角色定妆照（左侧面部特写 + 右侧正面/侧面/背面三视图）">
                      <Sparkles className="w-4 h-4" /> 角色定妆照
                      {useCharTemplate && <span className="text-[9px] bg-primary/30 px-1.5 py-0.5 rounded">ON</span>}
                    </button>
                  )}
                  {selectedScene && (
                    <button onClick={() => { onSceneTemplateChange(!useSceneTemplate); if (useCharTemplate) onCharTemplateChange(false) }}
                      className={`flex items-center gap-1.5 px-4 py-3 rounded-xl border-2 text-sm transition-all ${
                        useSceneTemplate ? 'bg-primary/20 text-primary border-primary/40' : 'border-border text-muted-foreground hover:border-primary/30'
                      }`}
                      title="启用后自动添加'不要出现人物'约束">
                      <Sparkles className="w-4 h-4" /> 场景概念图
                      {useSceneTemplate && <span className="text-[9px] bg-primary/30 px-1.5 py-0.5 rounded">ON</span>}
                    </button>
                  )}
                </div>
              )}
            </div>

            {projectResults.length > 0 && (
              <div className="premium-subpanel p-4">
                <div className="flex items-center justify-between mb-3">
                  <span className="text-[10px]" style={{ color: 'rgba(167, 139, 250, 0.7)' }}>生成结果 ({projectResults.length})</span>
                  <button onClick={onClearResults} className="text-[9px] text-red-400 hover:text-red-300 transition-colors">清除</button>
                </div>
                <div className="flex flex-wrap gap-2">
                  {projectResults.map((r, i) => (
                    <img key={i} src={r.url} alt="" onClick={() => onPreview(r.url)}
                      className="w-16 h-16 rounded-lg object-cover cursor-pointer hover:ring-1 ring-primary transition-all img-hover" />
                  ))}
                </div>
              </div>
            )}

            <div className="premium-subpanel p-4">
              <div className="flex items-center justify-between mb-2">
                <span className="text-[10px]" style={{ color: 'rgba(167, 139, 250, 0.7)' }}>历史记录</span>
                <button onClick={onToggleShowAll} className="text-[9px] text-primary/70 hover:text-primary transition-colors">
                  {showAllProject ? '仅本项目' : '全部项目'}
                </button>
              </div>
              <div className="relative mb-2">
                <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3 h-3" style={{ color: 'rgba(255,255,255,0.3)' }} />
                <input value={historySearch} onChange={e => setHistorySearch(e.target.value)}
                  placeholder="搜索..." className="w-full premium-input rounded-lg pl-7 pr-3 py-1.5 text-[10px]" />
              </div>
              <div className="flex flex-wrap gap-1.5 max-h-48 overflow-y-auto">
                {historyProject.filter(e => !historySearch || e.name.includes(historySearch)).map((entry, i) => (
                  <div key={i} className="relative group">
                    <img src={entry.url} alt={entry.name} onClick={() => onPreview(entry.url)}
                      className="w-12 h-12 rounded-lg object-cover cursor-pointer hover:ring-1 ring-primary transition-all img-hover" />
                    <span className="absolute bottom-0 left-0 right-0 text-[7px] text-center truncate px-0.5 bg-black/60 rounded-b-lg">{entry.name}</span>
                    {onRemix && (
                      <button onClick={() => onRemix(entry)}
                        className="absolute -top-1 -right-1 w-4 h-4 rounded-full bg-primary/80 text-[8px] flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity">
                        <Plus className="w-2.5 h-2.5" />
                      </button>
                    )}
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default ProjectImageGenForm
