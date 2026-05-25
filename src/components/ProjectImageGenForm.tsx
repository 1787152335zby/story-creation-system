import { useState, useEffect, useMemo, useRef } from 'react'
import { ChevronDown, ChevronRight, Sparkles, X, Lock, Unlock, Loader2, Image, Trash2, Search, Plus } from 'lucide-react'
import CollapsibleSection from './CollapsibleSection'
import { CharacterInfo, SceneInfo, PropInfo, EntityImagesMap, ReferenceUrlsByType } from '../lib/types'
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
      await projectDemandBatchGen({
        project_name: selectedProject,
        prompt: templatePrompt,
        negative_prompt: projectNegative,
        size: projectSize,
        n: 1,
        model: projectModel,
        character_names: [selectedChar],
        scene_names: [],
        reference_urls: [...autoRefUrls, ...manualRefUrls, ...generalRefUrls],
        reference_urls_by_type: autoRefUrlsByType || ({} as ReferenceUrlsByType),
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
      await projectDemandBatchGen({
        project_name: selectedProject,
        prompt: projectPrompt,
        negative_prompt: (projectNegative ? projectNegative + ', ' : '') + '不要出现人物, no people, no characters',
        size: projectSize,
        n: 1,
        model: projectModel,
        character_names: [],
        scene_names: [selectedScene],
        reference_urls: [...autoRefUrls, ...manualRefUrls, ...generalRefUrls],
        reference_urls_by_type: autoRefUrlsByType || ({} as ReferenceUrlsByType),
      })
      fetchGenerationHistory().then(h => setHistoryProject(h?.images_project || []))
      fetchProjectImages(selectedProject).then(setGeneratedImages)
    } catch {} finally { setProjectGenerating(false) }
  }

  const handleGen = async () => {
    if (!projectPrompt.trim()) return
    setProjectGenerating(true)
    try {
      await projectDemandBatchGen({
        project_name: selectedProject,
        prompt: projectPrompt,
        negative_prompt: projectNegative,
        size: projectSize,
        n: 1,
        model: projectModel,
        character_names: selectedChar ? [selectedChar] : [],
        scene_names: selectedScene ? [selectedScene] : [],
        reference_urls: [...autoRefUrls, ...manualRefUrls, ...generalRefUrls],
        reference_urls_by_type: autoRefUrlsByType || ({} as ReferenceUrlsByType),
      })
      fetchGenerationHistory().then(h => setHistoryProject(h?.images_project || []))
      fetchProjectImages(selectedProject).then(setGeneratedImages)
    } catch {} finally { setProjectGenerating(false) }
  }

  return (
    <div>
      <div className="mb-4">
        <select value={selectedProject} onChange={e => onProjectChange(e.target.value)}
          className="w-full bg-muted border border-border rounded-xl px-4 py-3 text-sm">
          <option value="">-- 选择项目 --</option>
          {projects.map(p => <option key={p.name} value={p.name}>{p.name}</option>)}
        </select>
      </div>

      {selectedProject && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-1 space-y-4">
            {imageDemands && (
              <div className="glass-card card-glow rounded-2xl p-4 border-2 border-primary/10">
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

                    <CollapsibleSection title={`🔧 道具 (${(imageDemands.key_props || []).length}个)`} defaultOpen={false}>
                      <div className="space-y-0.5 ml-2">
                        {(imageDemands.key_props || []).map((prop: any) => {
                          const isConfirmed = imageDemands._confirmed && imageDemands._confirmed[prop.name]
                          return (
                            <div key={`kp_${prop.name}`}
                              className={`flex items-center gap-1 px-2 py-0.5 rounded text-[10px] text-muted-foreground/70 ${isConfirmed ? 'bg-green-500/5' : ''}`}>
                              {isConfirmed && <span className="text-green-400 text-[9px]">✓</span>}
                              <span className="truncate">{prop.name}</span>
                            </div>
                          )
                        })}
                      </div>
                    </CollapsibleSection>

                    {(imageDemands.characters || []).length === 0 && (imageDemands.scene_groups || []).length === 0 && ((imageDemands.key_props || []).length === 0) && (
                      <p className="text-[10px] text-muted-foreground py-4 text-center">清单为空，请先运行生图需求管线</p>
                    )}
                  </div>
                </CollapsibleSection>
              </div>
            )}

            <div className="glass-card card-glow rounded-2xl p-4 border-2 border-primary/10">
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
                          <div onClick={() => { onCharSelect(baseName) }}
                            className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg cursor-pointer text-[11px] transition-all ${
                              isSelected ? 'bg-primary/15 text-primary font-medium' : 'hover:bg-muted text-muted-foreground'
                            }`}>
                            {hasChildren && (
                              <button onClick={(e) => { e.stopPropagation(); setExpandedChars(prev => ({ ...prev, [group.name]: !prev[group.name] })) }}
                                className="p-0.5 hover:text-foreground">
                                {expanded ? <ChevronDown className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />}
                              </button>
                            )}
                            {confirmedImgs.length > 0 && <span className="w-1.5 h-1.5 rounded-full bg-green-500 flex-shrink-0" />}
                            <span className="truncate">{group.name}</span>
                            {versionKeys.length > 0 && <span className="text-[9px] text-muted-foreground/50 flex-shrink-0">v{versionKeys.length}</span>}
                          </div>
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
                        await projectDemandBatchGen({
                          project_name: selectedProject,
                          prompt: projectPrompt,
                          negative_prompt: projectNegative,
                          size: projectSize,
                          n: 1,
                          model: projectModel,
                          character_names: [name],
                          scene_names: [],
                          reference_urls: [...autoRefUrls, ...manualRefUrls, ...generalRefUrls],
                          reference_urls_by_type: autoRefUrlsByType || ({} as ReferenceUrlsByType),
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
                        await projectDemandBatchGen({
                          project_name: selectedProject,
                          prompt: projectPrompt,
                          negative_prompt: projectNegative,
                          size: projectSize,
                          n: 1,
                          model: projectModel,
                          character_names: [name],
                          scene_names: [],
                          reference_urls: [...autoRefUrls, ...manualRefUrls, ...generalRefUrls, ...baseRefUrls],
                          reference_urls_by_type: autoRefUrlsByType || ({} as ReferenceUrlsByType),
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
                <div className="glass-card card-glow rounded-2xl p-4 border-2 border-primary/10">
                  <p className="text-[10px] font-medium text-muted-foreground mb-3">
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

            <div className="glass-card card-glow rounded-2xl p-4 border-2 border-primary/10">
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
                      const scenePropsMap = imageDemands?.scene_props || {}
                      const groupSceneProps: any[] = []
                      for (const [sk, items] of Object.entries(scenePropsMap)) {
                        if (sk && (group.name === sk || group.name.startsWith(sk + '·') || group.name.startsWith(sk + '（') || group.name.startsWith(sk + '(') || sk === group.name.substring(0, sk.length))) {
                          groupSceneProps.push(...(items as any[]))
                        }
                      }
                      const hasChildren = members.length > 1 || groupSceneProps.length > 0
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
                          {expanded && groupSceneProps.length > 0 && (
                            <div className="ml-4 mt-1 border-t border-border/20 pt-0.5">
                              <div className="text-[9px] text-muted-foreground/50 px-2.5 py-0.5">🏗️ 场景道具</div>
                              {groupSceneProps.map((prop: any) => (
                                <div key={prop.name} onClick={(e) => { e.stopPropagation(); onDemandPropSelect(prop.name, prop.prompt || '') }}
                                  className={`flex items-center gap-1.5 ml-2 px-2.5 py-0.5 rounded cursor-pointer text-[10px] transition-all ${
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
                      await projectDemandBatchGen({
                        project_name: selectedProject,
                        prompt: projectPrompt,
                        negative_prompt: (projectNegative ? projectNegative + ', ' : '') + '不要出现人物, no people, no characters',
                        size: projectSize,
                        n: 1,
                        model: projectModel,
                        character_names: [],
                        scene_names: [name],
                        reference_urls: [...autoRefUrls, ...manualRefUrls, ...generalRefUrls],
                        reference_urls_by_type: autoRefUrlsByType || ({} as ReferenceUrlsByType),
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

            <div className="glass-card card-glow rounded-2xl p-4 border-2 border-primary/10">
              <CollapsibleSection title={`🔧 道具 (${(imageDemands?.key_props || []).length}个)`}>
                {(imageDemands?.key_props || []).length === 0 ? (
                  <p className="text-[10px] text-muted-foreground">暂无关键道具数据，请先运行生图需求管线</p>
                ) : (
                  <div className="space-y-1 max-h-48 overflow-y-auto">
                    {(imageDemands?.key_props || []).map((prop: any) => {
                      const isConfirmed = imageDemands?._confirmed && imageDemands._confirmed[prop.name]
                      return (
                        <div key={prop.name}
                          onClick={() => onDemandPropSelect(prop.name, prop.prompt || '')}
                          className={`flex items-center gap-2 px-2.5 py-1.5 rounded-lg cursor-pointer text-[11px] transition-all ${
                            selectedProp === prop.name ? 'bg-primary/15 text-primary font-medium' : 'hover:bg-muted text-muted-foreground'
                          } ${isConfirmed ? 'bg-green-500/5' : ''}`}>
                          {isConfirmed && <span className="w-1.5 h-1.5 rounded-full bg-green-500 flex-shrink-0" />}
                          <span className="truncate">{prop.name}</span>
                        </div>
                      )
                    })}
                  </div>
                )}
              </CollapsibleSection>
              {(imageDemands?.key_props || []).length > 0 && (
                <button onClick={async () => {
                  const props = imageDemands?.key_props || []
                  if (props.length === 0) return
                  setProjectGenerating(true)
                  let idx = 0
                  for (const prop of props) {
                    idx++
                    setGeneratingStatus(`道具 ${idx}/${props.length}: ${prop.name}`)
                    try {
                      await projectDemandBatchGen({
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
                        reference_urls_by_type: autoRefUrlsByType || ({} as ReferenceUrlsByType),
                      })
                    } catch {}
                  }
                  fetchGenerationHistory().then(h => setHistoryProject(h?.images_project || []))
                  fetchProjectImages(selectedProject).then(setGeneratedImages)
                  setProjectGenerating(false)
                  setGeneratingStatus('')
                }} disabled={projectGenerating}
                  className="w-full mt-2 px-3 py-2 rounded-lg text-[10px] border border-primary/20 text-primary/70 hover:bg-primary/10 hover:text-primary transition-colors disabled:opacity-40">
                  ⚡ 一键生成所有关键道具 ({(imageDemands?.key_props || []).length}个)
                </button>
              )}
            </div>
          </div>

          <div className="lg:col-span-2 space-y-4">
            <div className="glass-card card-glow rounded-2xl p-5">
              <div className="flex items-start gap-2 mb-3">
                <textarea ref={promptRef} value={projectPrompt} onChange={e => { onPromptChange(e.target.value); const t = e.target; t.style.height = 'auto'; t.style.height = t.scrollHeight + 'px' }}
                  placeholder={selectedChar || selectedScene ? '已自动生成提示词，可在此微调' : '请从左侧选择角色或场景'}
                  className="flex-1 w-full bg-muted border border-border rounded-xl px-4 py-3 min-h-[6rem] resize-none text-sm overflow-hidden" />
                <button onClick={onPromptLockToggle}
                  className={`p-2 rounded-lg border transition-all flex-shrink-0 mt-0.5 ${promptLocked ? 'bg-amber-500/10 border-amber-500/30 text-amber-400' : 'border-border/50 text-muted-foreground hover:border-primary/30'}`}
                  title={promptLocked ? '提示词已锁定，切换角色不会覆盖' : '点击锁定提示词'}>
                  {promptLocked ? <Lock className="w-3.5 h-3.5" /> : <Unlock className="w-3.5 h-3.5" />}
                </button>
              </div>

              <div className="grid grid-cols-2 gap-3 mb-3">
                <div>
                  <label className="text-[10px] text-muted-foreground block mb-1">模型</label>
                  <ModelSelector type="image" value={projectModel} onChange={onModelChange} />
                </div>
                <div>
                  <label className="text-[10px] text-muted-foreground block mb-1">比例</label>
                  <select value={selectedRatio} onChange={e => { onRatioChange(e.target.value); const rs = ratioGroups[e.target.value]; if (rs && rs.length > 0) onSizeChange(rs[0]) }}
                    className="w-full bg-muted border border-border rounded-xl px-3 py-2.5 text-[11px]">
                    {Object.keys(ratioGroups).map(r => (<option key={r} value={r}>{r}</option>))}
                  </select>
                </div>
              </div>

              <input value={projectNegative} onChange={e => onNegativeChange(e.target.value)}
                placeholder="负面提示（可选）"
                className="w-full bg-muted border border-border rounded-xl px-3 py-2.5 text-sm mb-3" />

              {presets.length > 0 && (
                <div className="mb-4">
                  <label className="text-[10px] font-medium text-muted-foreground block mb-1.5">🎨 风格预设</label>
                  <div className="flex flex-wrap gap-1.5">
                    <button onClick={() => onPresetSelect(null)}
                      className={`px-3 py-1.5 rounded-lg text-[10px] border transition-all ${
                        !selectedPreset ? 'bg-primary/20 text-primary border-primary/40' : 'bg-muted text-muted-foreground border-border/50 hover:border-primary/30'
                      }`}>
                      无
                    </button>
                    {presets.map((p: any) => (
                      <button key={p.id} onClick={() => onPresetSelect(p)}
                        className={`px-3 py-1.5 rounded-lg text-[10px] border transition-all ${
                          selectedPreset?.id === p.id ? 'bg-primary/20 text-primary border-primary/40' : 'bg-muted text-muted-foreground border-border/50 hover:border-primary/30'
                        }`}>
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
              <div className="glass-card card-glow rounded-2xl p-4">
                <div className="flex items-center justify-between mb-3">
                  <span className="text-[10px] text-muted-foreground">生成结果 ({projectResults.length})</span>
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

            <div className="glass-card card-glow rounded-2xl p-4">
              <div className="flex items-center justify-between mb-2">
                <span className="text-[10px] text-muted-foreground">历史记录</span>
                <button onClick={onToggleShowAll} className="text-[9px] text-primary/70 hover:text-primary transition-colors">
                  {showAllProject ? '仅本项目' : '全部项目'}
                </button>
              </div>
              <div className="relative mb-2">
                <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3 h-3 text-muted-foreground/50" />
                <input value={historySearch} onChange={e => setHistorySearch(e.target.value)}
                  placeholder="搜索..." className="w-full bg-muted border border-border rounded-lg pl-7 pr-3 py-1.5 text-[10px]" />
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
