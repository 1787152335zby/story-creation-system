import { useEffect, useState, useRef } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { Play, Check, Pencil, X, Loader2, Settings, Sparkles, RefreshCw, ArrowLeft, Zap } from 'lucide-react'
import { useWebSocket } from '../hooks/useWebSocket'
import { fetchProject, fetchPhaseContent, openProjectFolder, saveProjectTemplate } from '../lib/api'
import TemplateModal from '../components/TemplateModal'
import PhaseTimeline from '../components/PhaseTimeline'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

const PHASE_NAMES = ['故事大纲', '完整剧情', '完整剧本', '分镜脚本', '视觉提取', '提示词生成']
const PHASE_DIRS = ['01_故事大纲', '02_完整剧情', '03_完整剧本', '04_分镜脚本', '05_角色场景', '06_提示词']
const PHASE_ICONS = ['📋', '📖', '🎭', '🎬', '🔍', '💬']

export default function Workspace() {
  const { name } = useParams<{ name: string }>()
  const navigate = useNavigate()
  const [projectConfig, setProjectConfig] = useState<any>(null)
  const [feedbackText, setFeedbackText] = useState('')
  const [showFeedback, setShowFeedback] = useState(false)
  const [started, setStarted] = useState(false)
  const [pendingStart, setPendingStart] = useState(false)
  const [selectedPhase, setSelectedPhase] = useState(-1)
  const [selectedAct, setSelectedAct] = useState('')
  const [viewContent, setViewContent] = useState('')
  const [loadingPhase, setLoadingPhase] = useState(false)
  const [actFileList, setActFileList] = useState<string[]>([])
  const [expandedPhase, setExpandedPhase] = useState(-1)
  const [mixFeedback, setMixFeedback] = useState('')
  const [showMixInput, setShowMixInput] = useState(false)
  const [versionFeedback, setVersionFeedback] = useState('')
  const [showVersionFeedback, setShowVersionFeedback] = useState(false)
  const [redoInstruction, setRedoInstruction] = useState('')
  const [showRedoInput, setShowRedoInput] = useState(false)
  const [redoPhaseIndex, setRedoPhaseIndex] = useState(-1)
  const [suppressStream, setSuppressStream] = useState(false)
  const [pendingContinue, setPendingContinue] = useState(false)
  const [showTemplateModal, setShowTemplateModal] = useState(false)
  const [pendingRedo, setPendingRedo] = useState<{ index: number; instruction: string } | null>(null)
  const [continuing, setContinuing] = useState(false)
  const [editingContent, setEditingContent] = useState(false)
  const [editText, setEditText] = useState('')
  const [streamChars, setStreamChars] = useState(0)
  const [streamStartTime, setStreamStartTime] = useState(0)
  const [currentPhaseMaxChars, setCurrentPhaseMaxChars] = useState(0)
  const [elapsedSeconds, setElapsedSeconds] = useState(0)
  const [generating, setGenerating] = useState(false)
  const [confirmedPhases, setConfirmedPhases] = useState<number[]>([])
  const [confirmedPhaseId, setConfirmedPhaseId] = useState<number | null>(null)
  const streamHadContent = useRef(false)

  const { connect, send, approve, revise, reject, confirmPhase, proceedGeneration, selectVersion, disconnect, clearStream, connected, streamContent, currentPhase, phases, progress, awaitingApproval, awaitingVersion, awaitingProceed, contentWarnings, isComplete, streamDone, error } = useWebSocket()


  useEffect(() => {
    if (!name) return
    fetchProject(name).then(config => {
      setProjectConfig(config)
      const phs = config.phases || []
      if (phs.some((p: any) => p.done)) setStarted(true)
      if (typeof config.pending_approval === 'number' && config.pending_approval >= 0) {
        setStarted(true)
        connect(name)
        setPendingContinue(true)
      }
      if (typeof config.pending_version === 'number' && config.pending_version >= 0) {
        setStarted(true)
        connect(name)
        setPendingContinue(true)
      }
    })
  }, [name])

  useEffect(() => {
    if (!projectConfig || !phases.length) return
    let changed = false
    const updated = { ...projectConfig }
    updated.phases = [...(projectConfig.phases || [])]
    for (let i = 0; i < phases.length; i++) {
      if (phases[i]?.status === 'done' && updated.phases[i] && !updated.phases[i].done) {
        updated.phases[i] = { ...updated.phases[i], done: true }
        changed = true
      }
    }
    if (changed) setProjectConfig(updated)
  }, [phases])

  useEffect(() => {
    if (connected && (pendingStart || pendingContinue || pendingRedo) && projectConfig?.style_type) {
      const isContinue = pendingContinue
      const redo = pendingRedo
      if (pendingStart) setPendingStart(false)
      if (pendingContinue) setPendingContinue(false)
      if (pendingRedo) setPendingRedo(null)
      if (name) {
        const styleData = {
          story_type: projectConfig.style_type || '',
          genre: projectConfig.genre || '',
          writing_style: projectConfig.writing_style || '',
          visual_style: projectConfig.visual_style || '',
          art_style: projectConfig.art_style || '',
          screen_aspect: projectConfig.screen_aspect || '',
          script_style: projectConfig.script_style || '',
          duration_mode: projectConfig.duration_mode || '',
          episode_count: projectConfig.episode_count || '',
          episode_duration: projectConfig.episode_duration || '',
          custom_requirements: projectConfig.custom_requirements || '',
          visual_reference: projectConfig.visual_reference || '',
          action_reference: projectConfig.action_reference || '',
        }
        if (isContinue) {
          send({ action: 'continue', style: styleData })
        } else if (redo) {
          send({ action: 'redo_phase', phase_index: redo.index, feedback: redo.instruction, style: styleData })
        } else {
          send({ action: 'start', style: styleData })
        }
      }
    }
  }, [connected, pendingStart, pendingContinue, pendingRedo, name, projectConfig, send])

  useEffect(() => {
    if (continuing) {
      if (connected || currentPhase >= 0 || streamContent) {
        setContinuing(false)
      }
    }
  }, [continuing, connected, currentPhase, streamContent])

  useEffect(() => {
    if (!streamContent) { setStreamChars(0); return }
    setStreamChars(streamContent.length)
  }, [streamContent])

  useEffect(() => {
    if (currentPhase >= 0 && streamChars === 0) {
      setCurrentPhaseMaxChars(streamChars || 1)
    }
    if (streamChars > currentPhaseMaxChars) {
      setCurrentPhaseMaxChars(streamChars)
    }
  }, [currentPhase, streamChars])

  useEffect(() => {
    const hasContent = !!streamContent
    const hadContent = streamHadContent.current
    streamHadContent.current = hasContent

    if (awaitingVersion || awaitingApproval || isComplete) return
    if (!hasContent) { setElapsedSeconds(0); setStreamStartTime(0); return }
    if (!hadContent) setStreamStartTime(Date.now())
  }, [streamContent, awaitingVersion, awaitingApproval, isComplete])

  useEffect(() => {
    if (awaitingVersion || awaitingApproval || isComplete || !streamContent) return
    const timer = setInterval(() => {
      setStreamStartTime(t => {
        if (t > 0) setElapsedSeconds(Math.floor((Date.now() - t) / 1000))
        return t
      })
    }, 1000)
    return () => clearInterval(timer)
  }, [awaitingVersion, awaitingApproval, isComplete, !!streamContent])

  useEffect(() => {
    const isGenerating = connected && currentPhase >= 0 && !!streamContent
    setGenerating(isGenerating)
    if (isGenerating) {
      const handler = (e: BeforeUnloadEvent) => {
        e.preventDefault()
        e.returnValue = 'AI 正在生成内容，刷新将中断生成过程，确定要刷新吗？'
      }
      window.addEventListener('beforeunload', handler)
      return () => window.removeEventListener('beforeunload', handler)
    }
  }, [connected, currentPhase, streamContent])

  const handleStart = () => { if (!name) return; connect(name); setStarted(true); setPendingStart(true) }
  const handleContinue = () => {
    if (!name) return
    if (!connected) { connect(name); setPendingContinue(true); return }
    setContinuing(true)
    setViewContent('')
    setSelectedPhase(-1)
    setStarted(true)
    send({ action: 'continue', style: {
        story_type: projectConfig.style_type || '',
        genre: projectConfig.genre || '',
        writing_style: projectConfig.writing_style || '',
        visual_style: projectConfig.visual_style || '',
        art_style: projectConfig.art_style || '',
        screen_aspect: projectConfig.screen_aspect || '',
        script_style: projectConfig.script_style || '',
        duration_mode: projectConfig.duration_mode || '',
        episode_count: projectConfig.episode_count || '',
        episode_duration: projectConfig.episode_duration || '',
        custom_requirements: projectConfig.custom_requirements || '', visual_reference: projectConfig.visual_reference || '',
        action_reference: projectConfig.action_reference || '',
      }})
  }
  const handleApprove = () => { approve(currentPhase); setSelectedPhase(-1); setViewContent(''); setActFileList([]); setSuppressStream(false) }
  const handleConfirm = () => {
    confirmPhase(currentPhase)
    setConfirmedPhases(prev => [...prev, currentPhase])
    setConfirmedPhaseId(currentPhase)
    if (streamContent && !(selectedPhase >= 0 && viewContent)) {
      setViewContent(streamContent)
      setSelectedPhase(currentPhase)
    }
    setActFileList([])
    setSuppressStream(true)
  }
  const handleProceed = () => {
    proceedGeneration()
    setConfirmedPhaseId(null)
    setViewContent('')
    setSelectedPhase(-1)
    setSuppressStream(false)
  }
  const handleRevise = () => { if (!feedbackText.trim()) return; revise(currentPhase, feedbackText); setFeedbackText(''); setShowFeedback(false) }
  const handleReject = () => { reject(currentPhase, '不满意') }
  const handleVersionA = () => { selectVersion('1', versionFeedback); setVersionFeedback(''); setShowVersionFeedback(false) }
  const handleVersionB = () => { selectVersion('2', versionFeedback); setVersionFeedback(''); setShowVersionFeedback(false) }
  const handleVersionMix = () => { if (!mixFeedback.trim()) return; selectVersion('3', mixFeedback); setMixFeedback(''); setShowMixInput(false) }

  const handleRedoPhase = (index: number, instruction: string = '') => {
    if (!projectConfig?.style_type) return
    clearStream()
    setSuppressStream(false)
    setShowRedoInput(false)
    if (connected) {
      send({
        action: 'redo_phase',
        phase_index: index,
        feedback: instruction,
        style: {
          story_type: projectConfig.style_type || '',
          genre: projectConfig.genre || '',
          writing_style: projectConfig.writing_style || '',
          visual_style: projectConfig.visual_style || '',
          art_style: projectConfig.art_style || '',
          screen_aspect: projectConfig.screen_aspect || '',
          script_style: projectConfig.script_style || '',
          duration_mode: '1', episode_count: '', episode_duration: '',
          custom_requirements: '', visual_reference: projectConfig.visual_reference || '',
          action_reference: projectConfig.action_reference || '',
        },
      })
    } else {
      if (!name) return
      connect(name)
      setPendingRedo({ index, instruction })
    }
    setSelectedPhase(-1)
    setViewContent('')
    setActFileList([])
    setShowMixInput(false)
    if (index < 5) {
      projectConfig.phases[index].done = false
      setProjectConfig({ ...projectConfig })
    }
  }

  const handleEditContent = () => {
    setEditText(viewContent)
    setEditingContent(true)
  }

  const handleSaveEdit = () => {
    setViewContent(editText)
    setEditingContent(false)
  }

  const handleCancelEdit = () => {
    setEditingContent(false)
    setEditText('')
  }

  const formatTime = (s: number) => {
    if (s < 60) return `${s}秒`
    const m = Math.floor(s / 60)
    const sec = s % 60
    return `${m}分${sec > 0 ? sec + '秒' : ''}`
  }

  const calcRemaining = () => {
    if (awaitingApproval || awaitingVersion || isComplete) return null
    if (elapsedSeconds < 5 || streamChars < 50) return null
    const cps = streamChars / elapsedSeconds
    if (cps < 0.1) return null
    const avgTarget = streamChars > 2000 ? streamChars * 1.5 : 4000
    const remaining = Math.round((avgTarget - streamChars) / cps)
    if (remaining < 0) return null
    return remaining
  }

  const handleViewPhase = async (index: number) => {
    const phs = projectConfig?.phases || []
    if (!phs[index]?.done && !(phases[index]?.status === 'done')) return
    if (index === selectedPhase && !selectedAct) {
      setSelectedPhase(-1)
      setViewContent('')
      setActFileList([])
      setSelectedAct('')
      return
    }
    if (generating || streamContent) {
      disconnect()
      setGenerating(false)
    }
    setConfirmedPhaseId(null)
    setSuppressStream(true)
    setSelectedPhase(index); setActFileList([]); setSelectedAct(''); setViewContent(''); setLoadingPhase(true)
    try {
      const c = await fetchPhaseContent(projectConfig?.name, PHASE_DIRS[index])
      if (c.is_split && c.file_list && c.file_list.length > 1) { setActFileList(c.file_list); setExpandedPhase(index) }
      setViewContent(c.content || '内容正在生成中...')
    } catch { setViewContent('无法加载内容') }
    setLoadingPhase(false)
  }

  const handleViewAct = async (phaseIndex: number, actFileName: string) => {
    setSelectedAct(actFileName); setViewContent(''); setLoadingPhase(true)
    try {
      const actPath = actFileName ? `${PHASE_DIRS[phaseIndex]}/${actFileName}` : PHASE_DIRS[phaseIndex]
      const c = await fetchPhaseContent(projectConfig?.name, actPath)
      setViewContent(c.content || '')
    } catch { setViewContent('无法加载内容') }
    setLoadingPhase(false)
  }

  const allDone = (projectConfig?.phases || []).filter((p: any) => p.done).length >= 6
  const showStream = !suppressStream && connected && streamContent

  return (
    <div className="flex h-screen relative overflow-hidden">
      {/* Ambient bg */}
      <div className="fixed inset-0 pointer-events-none opacity-10">
        <div className="absolute top-0 left-1/4 w-72 h-72 rounded-full" style={{ background: 'radial-gradient(circle, hsl(var(--primary)), transparent 70%)' }} />
      </div>

      <PhaseTimeline
        name={name || ''}
        projectConfig={projectConfig}
        phases={phases}
        currentPhase={currentPhase}
        streamContent={streamContent}
        suppressStream={suppressStream}
        confirmedPhases={confirmedPhases}
        selectedPhase={selectedPhase}
        expandedPhase={expandedPhase}
        actFileList={actFileList}
        selectedAct={selectedAct}
        showStream={!suppressStream && connected && streamContent}
        connected={connected}
        onNavigate={navigate}
        onOpenFolder={() => openProjectFolder(name!)}
        onShowTemplateModal={() => setShowTemplateModal(true)}
        onViewPhase={handleViewPhase}
        onViewAct={handleViewAct}
        onSetExpandedPhase={setExpandedPhase}
        onRedo={(i) => { setRedoPhaseIndex(i); setRedoInstruction(''); setShowRedoInput(true) }}
      />

      {/* Main */}
      <main className="flex-1 flex flex-col overflow-hidden bg-background/50 relative z-10">
        {allDone && selectedPhase < 0 ? (
          <div className="flex-1 flex items-center justify-center animate-fade-in">
            <div className="text-center">
              <div className="w-20 h-20 mx-auto mb-4 rounded-3xl flex items-center justify-center animate-float"
                style={{ background: 'linear-gradient(135deg, hsl(170, 70%, 55%, 0.15), hsl(150, 60%, 50%, 0.1))' }}>
                <Sparkles className="w-8 h-8" style={{ color: 'hsl(170, 70%, 55%)' }} />
              </div>
              <h2 className="text-xl font-bold mb-1 text-green-400">完成所有任务！</h2>
              <p className="text-muted-foreground text-sm mb-6">提示词已生成完毕，可前往「智能生图」页面使用项目模式生成图片</p>
              <button onClick={() => navigate('/')} className="btn-gradient inline-flex items-center gap-2 px-6 py-3 rounded-xl font-medium">
                <ArrowLeft className="w-5 h-5" /> 返回首页
              </button>
            </div>
          </div>
        ) : !started ? (
          <div className="flex-1 flex items-center justify-center animate-fade-in">
            <div className="text-center">
              <div className="w-24 h-24 mx-auto mb-6 rounded-3xl flex items-center justify-center animate-float"
                style={{ background: 'linear-gradient(135deg, hsl(var(--primary) / 0.15), hsl(265, 87%, 60%, 0.1))' }}>
                <Zap className="w-10 h-10" style={{ color: 'hsl(var(--primary))' }} />
              </div>
              {projectConfig && (projectConfig.phases || []).some((p: any) => p.done) ? (
                <>
                  <h2 className="text-xl font-bold mb-2">继续创作</h2>
                  <p className="text-muted-foreground text-sm mb-6">内容已确认，可点击继续推进到下一步</p>
                  <button onClick={handleContinue} className="btn-gradient inline-flex items-center gap-2 px-8 py-3.5 rounded-2xl font-medium text-base">
                    <Play className="w-5 h-5" /> 继续创作
                  </button>
                </>
              ) : (
                <>
                  <h2 className="text-xl font-bold mb-2">准备开始创作</h2>
                  <p className="text-muted-foreground text-sm mb-6">AI 将引导你完成从大纲到提示词的每个阶段</p>
                  <button onClick={handleStart} className="btn-gradient inline-flex items-center gap-2 px-8 py-3.5 rounded-2xl font-medium text-base">
                    <Play className="w-5 h-5" /> 开始创作
                  </button>
                </>
              )}
            </div>
          </div>
        ) : error ? (
          <div className="flex-1 flex items-center justify-center">
            <div className="text-center max-w-md">
              <X className="w-12 h-12 mx-auto mb-3 text-red-400" />
              <p className="text-red-400 font-medium mb-2">{error}</p>
              {(error.toLowerCase().includes('api key') || error.toLowerCase().includes('api_key') || error.toLowerCase().includes('not configured') || error.toLowerCase().includes('auth')) ? (
                <button onClick={() => navigate('/settings')} className="btn-gradient inline-flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm font-medium mt-2">
                  <Settings className="w-4 h-4" /> 前往设置页配置 API Key
                </button>
              ) : (
                <button onClick={handleContinue} className="btn-gradient inline-flex items-center gap-1.5 px-5 py-2.5 rounded-xl text-sm font-medium mt-2">
                  <Play className="w-4 h-4" /> 重试
                </button>
              )}
            </div>
          </div>
        ) : showStream ? (
          <>
            <div className="border-b border-border/30 bg-card/40 backdrop-blur-sm px-8 py-3">
              <div className="max-w-3xl mx-auto flex items-center justify-between gap-4">
                <div className="flex items-center gap-2 text-sm">
                  <span>{PHASE_ICONS[currentPhase] || '📝'}</span>
                  <span className="font-medium">{PHASE_NAMES[currentPhase] || '生成中...'}</span>
                  <span className="text-muted-foreground text-xs ml-1">({Math.min(progress.current + 1, progress.total)}/{progress.total})</span>
                  <span className="text-xs text-muted-foreground ml-2">| {streamChars} 字</span>
                </div>
                <div className="flex-1 max-w-xs space-y-1">
                  <div className="w-full h-1.5 bg-muted rounded-full overflow-hidden">
                    <div className="h-full rounded-full transition-all duration-300 progress-glow"
                      style={{ width: `${Math.min(100, (streamChars / (currentPhaseMaxChars || 1)) * 100)}%`, background: 'linear-gradient(90deg, hsl(var(--primary)), hsl(265, 87%, 60%))' }} />
                  </div>
                  <div className="flex justify-between text-[10px] text-muted-foreground">
                    <span>已生成 {streamChars} 字</span>
                    <span>{formatTime(elapsedSeconds)} {(() => { const r = calcRemaining(); return r ? `| 预计剩余${formatTime(r)}` : '' })()}</span>
                  </div>
                </div>
                {connected && <div className="w-2 h-2 rounded-full bg-green-400 animate-pulse flex-shrink-0" title="已连接" />}
              </div>
            </div>
            <div className="flex-1 overflow-y-auto p-8" style={{ opacity: 1 }}>
              <div className="max-w-3xl mx-auto">
                {streamContent.length > 10 && (
                  <div className="mb-3 text-xs text-muted-foreground border-l-2 border-primary/30 pl-3 py-1">
                    AI 正在逐字生成内容... 已耗时 {formatTime(elapsedSeconds)}
                  </div>
                )}
                <div className="prose prose-invert max-w-none animate-fade-in">
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>{streamContent}</ReactMarkdown>
                  {streamContent && <span className="inline-block w-2 h-4 bg-primary animate-pulse ml-0.5" />}
                </div>
              </div>
            </div>
            {awaitingVersion && (
              <div className="border-t border-border/50 p-5 bg-card/80 backdrop-blur-sm animate-fade-in-up">
                <div className="max-w-3xl mx-auto">
                  <p className="text-sm font-medium mb-4">🎯 大纲已生成，请选择版本：</p>
                  {showMixInput ? (
                    <div className="space-y-3">
                      <textarea className="w-full bg-muted border border-border rounded-xl px-4 py-3 h-24 resize-none text-sm" placeholder="请描述你希望如何混合版本A和版本B..." value={mixFeedback} onChange={e => setMixFeedback(e.target.value)} autoFocus />
                      <div className="flex gap-2">
                        <button onClick={handleVersionMix} className="btn-gradient px-5 py-2 rounded-xl text-sm font-medium"><Sparkles className="w-4 h-4 inline mr-1" />提交混合</button>
                        <button onClick={() => setShowMixInput(false)} className="px-5 py-2 rounded-xl border border-border text-sm hover:bg-muted transition-colors">取消</button>
                      </div>
                    </div>
                  ) : (
                    <div className="space-y-3">
                      <textarea className="w-full bg-muted border border-border rounded-xl px-4 py-3 h-24 resize-none text-sm" placeholder="可选：输入修改要求，选中的版本将根据你的要求重新生成（如：增加第3个角色、把结局改成悲剧、加快节奏...）" value={versionFeedback} onChange={e => setVersionFeedback(e.target.value)} />
                      <div className="flex items-center gap-3">
                        <button onClick={handleVersionA} className="btn-gradient px-6 py-3 rounded-xl text-sm font-medium">版本 A</button>
                        <button onClick={handleVersionB} className="btn-gradient px-6 py-3 rounded-xl text-sm font-medium">版本 B</button>
                        <button onClick={() => setShowMixInput(true)} className="px-5 py-3 rounded-xl border-2 border-border text-sm font-medium hover:border-primary/50 hover:bg-primary/5 transition-all">混合 A + B</button>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            )}
            {awaitingApproval && !isComplete && (
              <div className="border-t border-border/50 p-5 bg-card/80 backdrop-blur-sm animate-fade-in-up">
                {showFeedback ? (
                  <div className="max-w-3xl mx-auto space-y-3">
                    <textarea className="w-full bg-muted border border-border rounded-xl px-4 py-3 h-28 resize-none text-sm" placeholder="请输入修改意见..." value={feedbackText} onChange={e => setFeedbackText(e.target.value)} autoFocus />
                    <div className="flex gap-2">
                      <button onClick={handleRevise} className="btn-gradient px-5 py-2 rounded-xl text-sm font-medium"><Pencil className="w-4 h-4 inline mr-1" />提交修改</button>
                      <button onClick={() => setShowFeedback(false)} className="px-5 py-2 rounded-xl border border-border text-sm hover:bg-muted transition-colors">取消</button>
                    </div>
                  </div>
                ) : (
                  <div className="max-w-3xl mx-auto flex items-center gap-2">
                    <button onClick={handleApprove} className="flex items-center gap-1.5 px-5 py-2.5 rounded-xl text-sm font-medium transition-all"
                      style={{ background: 'hsl(150, 60%, 50%)', color: 'white' }}>
                      <Check className="w-4 h-4" /> 通过并进行下一步
                    </button>
                    <button onClick={handleConfirm} className="flex items-center gap-1.5 px-5 py-2.5 rounded-xl text-sm font-medium transition-all border-2 border-primary/40 text-primary hover:bg-primary/5">
                      <Check className="w-4 h-4" /> 确认
                    </button>
                    <button onClick={() => setShowFeedback(true)} className="flex items-center gap-1.5 px-4 py-2.5 rounded-xl border border-border text-sm hover:bg-muted transition-all">
                      <Pencil className="w-4 h-4" /> 修改
                    </button>
                    <button onClick={handleReject} className="flex items-center gap-1.5 px-4 py-2.5 rounded-xl text-sm text-red-400 hover:bg-red-400/5 transition-all">
                      <X className="w-4 h-4" /> 退回
                    </button>
                  </div>
                )}
              </div>
            )}
            {awaitingProceed && (
              <div className="border-t border-border/50 p-5 bg-card/80 backdrop-blur-sm animate-fade-in-up">
                <div className="max-w-3xl mx-auto flex items-center justify-between">
                  <div className="flex items-center gap-2 text-sm">
                    <Check className="w-4 h-4 text-green-400" />
                    <span className="text-green-400 font-medium">已完成确认</span>
                    <span className="text-muted-foreground">— 准备好后可继续下一步</span>
                  </div>
                  <button onClick={handleProceed} className="btn-gradient inline-flex items-center gap-1.5 px-5 py-2.5 rounded-xl text-sm font-medium whitespace-nowrap"
                    style={{ background: 'linear-gradient(135deg, hsl(150, 60%, 50%), hsl(170, 60%, 45%))' }}>
                    <Play className="w-4 h-4" /> 继续进行下一步
                  </button>
                </div>
              </div>
            )}
            {showStream && streamDone && !awaitingApproval && !awaitingVersion && !isComplete && !awaitingProceed && (
              <div className="border-t border-border/50 p-4 bg-card/80 backdrop-blur-sm">
                <div className="max-w-3xl mx-auto flex items-center justify-between">
                  <p className="text-xs text-muted-foreground">内容已生成完毕</p>
                  <button onClick={() => { setViewContent(streamContent); setSelectedPhase(currentPhase); setSuppressStream(true) }}
                     className="px-4 py-2 rounded-xl border border-border text-xs hover:bg-muted transition-colors">
                    返回浏览
                  </button>
                </div>
              </div>
            )}
            {contentWarnings.length > 0 && (
              <div className="border-t border-border/50 p-4 bg-card/80 backdrop-blur-sm">
                <div className="max-w-3xl mx-auto">
                  {contentWarnings.map((w, i) => (
                    <div key={i} className="flex items-start gap-3 p-3 rounded-xl bg-amber-400/10 border border-amber-400/20 mb-2">
                      <span className="text-amber-400 text-sm flex-shrink-0">⚠️</span>
                      <div className="flex-1">
                        <p className="text-xs font-medium text-amber-400 mb-1">内容量提醒 — 第{w.phase_index + 1}阶段</p>
                        {w.warnings.map((msg, j) => (
                          <p key={j} className="text-xs text-amber-400/80">{msg}</p>
                        ))}
                        {w.stats?.max_scenes && (
                          <p className="text-[10px] text-muted-foreground mt-1">
                            检测到约{w.stats.scene_count}场（目标建议≤{w.stats.max_scenes}场）
                            · {w.stats.word_count}字（目标建议≤{w.stats.max_words}字）
                          </p>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </>
        ) : viewContent ? (
          <div className="flex-1 overflow-y-auto p-8 animate-fade-in">
            {/* 生成中的横幅提示 */}
            {streamContent && (
              <div className="mb-4 p-3 rounded-xl bg-primary/10 border border-primary/20 flex items-center justify-between">
                <div className="flex items-center gap-2 text-sm">
                  <span className="w-2 h-2 rounded-full bg-primary animate-pulse" />
                  <span className="text-primary font-medium">正在生成 {PHASE_NAMES[currentPhase] || '...'}</span>
                  <span className="text-muted-foreground">({Math.min(progress.current + 1, progress.total)}/{progress.total})</span>
                </div>
                <button onClick={() => setSuppressStream(false)} className="px-4 py-1.5 rounded-lg bg-primary/20 text-primary text-xs font-medium hover:bg-primary/30 transition-colors">
                  查看实时生成
                </button>
              </div>
            )}
            <div className="max-w-3xl mx-auto">
              {confirmedPhaseId !== null && (
                <div className="mb-4 p-3 rounded-xl bg-green-400/10 border border-green-400/20 flex items-center justify-between">
                  <div className="flex items-center gap-2 text-sm">
                    <Check className="w-4 h-4 text-green-400" />
                    <span className="text-green-400 font-medium">已确认，下一阶段正在生成中</span>
                  </div>
                  <button onClick={handleProceed} className="px-4 py-1.5 rounded-lg bg-green-400/20 text-green-400 text-xs font-medium hover:bg-green-400/30 transition-colors">
                    查看新内容
                  </button>
                </div>
              )}
              <div className="flex items-center justify-between mb-6">
                <h3 className="text-lg font-semibold flex items-center gap-2">
                  <span>{PHASE_ICONS[selectedPhase]}</span>
                  <span className="gradient-text">{PHASE_NAMES[selectedPhase]}</span>
                  {selectedAct && <span className="text-sm font-normal text-muted-foreground">— {selectedAct.replace(/^\d+_/, '').replace(/\.md$/, '').replace(/_/g, '')}</span>}
                  <span className="text-xs text-muted-foreground ml-2">({viewContent.length} 字)</span>
                </h3>
                <div className="flex items-center gap-2 flex-shrink-0">
                  {editingContent ? (
                    <>
                      <button onClick={handleSaveEdit} className="btn-gradient inline-flex items-center gap-1.5 px-4 py-2 rounded-xl text-xs font-medium whitespace-nowrap">
                        <Check className="w-3.5 h-3.5" /> 保存
                      </button>
                      <button onClick={handleCancelEdit} className="px-4 py-2 rounded-xl border border-border text-xs hover:bg-muted transition-colors">
                        <X className="w-3.5 h-3.5" /> 取消
                      </button>
                    </>
                  ) : (
                    <>
                      {streamContent ? (
                        <button onClick={() => setSuppressStream(false)} className="px-4 py-2 rounded-xl border border-border text-xs hover:bg-muted transition-colors">
                          ← 返回生成进度
                        </button>
                      ) : null}
                      <button onClick={handleEditContent} className="px-4 py-2 rounded-xl border border-border text-xs hover:bg-muted transition-colors">
                        <Pencil className="w-3.5 h-3.5 inline mr-1" /> 编辑
                      </button>
                      {!streamContent && !confirmedPhaseId && (
                        <button onClick={handleContinue} className="btn-gradient inline-flex items-center gap-1.5 px-4 py-2 rounded-xl text-xs font-medium whitespace-nowrap">
                          <Play className="w-3.5 h-3.5" /> 继续创作
                        </button>
                      )}
                      {confirmedPhaseId !== null && (
                        <button onClick={handleProceed} className="btn-gradient inline-flex items-center gap-1.5 px-4 py-2 rounded-xl text-xs font-medium whitespace-nowrap"
                          style={{ background: 'linear-gradient(135deg, hsl(150, 60%, 50%), hsl(170, 60%, 45%))' }}>
                          <Play className="w-3.5 h-3.5" /> 继续查看新内容
                        </button>
                      )}
                    </>
                  )}
                </div>
              </div>
              {editingContent ? (
                <textarea
                  className="w-full h-[70vh] bg-muted border border-border rounded-xl p-4 text-sm font-mono resize-none focus:outline-none focus:border-primary/50"
                  value={editText}
                  onChange={e => setEditText(e.target.value)}
                  autoFocus
                />
              ) : (
                <div className="prose prose-invert max-w-none">
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>{viewContent}</ReactMarkdown>
                </div>
              )}
            </div>
          </div>
        ) : connected && currentPhase >= 0 && !viewContent ? (
          <div className="flex-1 flex flex-col overflow-hidden">
            <div className="border-b border-border/30 bg-card/40 backdrop-blur-sm px-8 py-3">
              <div className="max-w-3xl mx-auto flex items-center justify-between gap-4">
                <div className="flex items-center gap-2 text-sm">
                  <span>{PHASE_ICONS[currentPhase] || '📝'}</span>
                  <span className="font-medium">{PHASE_NAMES[currentPhase] || '生成中...'}</span>
                  <span className="text-xs text-muted-foreground ml-2">| {streamContent.length} 字</span>
                </div>
                <div className="flex-1 max-w-xs space-y-1">
                  <div className="w-full h-1.5 bg-muted rounded-full overflow-hidden">
                    <div className="h-full rounded-full transition-all duration-300 progress-glow"
                      style={{ width: `${Math.min(100, (streamContent.length / (currentPhaseMaxChars || 1)) * 100)}%`, background: 'linear-gradient(90deg, hsl(252, 87%, 67%), hsl(265, 87%, 60%))' }} />
                  </div>
                  <div className="flex justify-between text-[10px] text-muted-foreground">
                     <span>已生成 {streamContent.length} 字</span>
                     <span>{formatTime(elapsedSeconds)} {(() => { const r = calcRemaining(); return r ? `| 预计剩余${formatTime(r)}` : '' })()}</span>
                   </div>
                 </div>
                 {connected && <div className="w-2 h-2 rounded-full bg-green-400 animate-pulse flex-shrink-0" title="已连接" />}
               </div>
             </div>
             <div className="flex-1 overflow-y-auto p-8">
               <div className="max-w-3xl mx-auto">
                 {!streamContent ? (
                   <div className="flex flex-col items-center justify-center gap-4 py-20">
                     <div className="w-10 h-10 border-2 border-primary border-t-transparent rounded-full animate-spin" />
                     <p className="text-muted-foreground text-sm">等待 AI 生成...</p>
                     <p className="text-xs text-amber-400/70 animate-pulse">请勿关闭网页，生成过程需一定时间</p>
                   </div>
                 ) : (
                   <>
                     <div className="mb-3 text-xs text-muted-foreground border-l-2 border-primary/30 pl-3 py-1">
                       AI 正在逐字生成内容... 已耗时 {formatTime(elapsedSeconds)}
                     </div>
                     <div className="prose prose-invert max-w-none">
                       <ReactMarkdown remarkPlugins={[remarkGfm]}>{streamContent}</ReactMarkdown>
                       <span className="inline-block w-2 h-4 bg-primary animate-pulse ml-0.5" />
                     </div>
                   </>
                 )}
               </div>
             </div>
           </div>
         ) : continuing ? (
           <div className="flex-1 flex flex-col overflow-hidden">
             <div className="border-b border-border/30 bg-card/40 backdrop-blur-sm px-8 py-3">
               <div className="max-w-3xl mx-auto flex items-center justify-between gap-4">
                 <div className="flex items-center gap-2 text-sm">
                   <span>{PHASE_ICONS[currentPhase] || '📝'}</span>
                   <span className="font-medium">{PHASE_NAMES[currentPhase] || '生成中...'}</span>
                   {streamContent ? <span className="text-xs text-muted-foreground ml-2">| {streamContent.length} 字</span> : null}
                 </div>
                 <div className="flex-1 max-w-xs">
                   {streamContent ? (
                     <div className="w-full h-1.5 bg-muted rounded-full overflow-hidden">
                       <div className="h-full rounded-full transition-all duration-300 progress-glow"
                         style={{ width: `${Math.min(100, (streamContent.length / (currentPhaseMaxChars || 1)) * 100)}%`, background: 'linear-gradient(90deg, hsl(252, 87%, 67%), hsl(265, 87%, 60%))' }} />
                       <div className="flex justify-between text-[10px] text-muted-foreground">
                         <span>已生成 {streamContent.length} 字</span>
                         <span>{formatTime(elapsedSeconds)} {(() => { const r = calcRemaining(); return r ? `| 预计剩余${formatTime(r)}` : '' })()}</span>
                       </div>
                     </div>
                   ) : null}
                 </div>
                 {connected && <div className="w-2 h-2 rounded-full bg-green-400 animate-pulse flex-shrink-0" title="已连接" />}
               </div>
             </div>
             <div className="flex-1 overflow-y-auto p-8">
               <div className="max-w-3xl mx-auto">
                 {!streamContent ? (
                   <div className="flex flex-col items-center justify-center gap-4 py-20">
                     <div className="w-10 h-10 border-2 border-primary border-t-transparent rounded-full animate-spin" />
                     <p className="text-muted-foreground text-sm">正在启动生成...</p>
                     <p className="text-xs text-amber-400/70 animate-pulse">请勿关闭网页，生成过程需一定时间</p>
                   </div>
                 ) : (
                   <>
                     <div className="mb-3 text-xs text-muted-foreground border-l-2 border-primary/30 pl-3 py-1">
                       AI 正在逐字生成内容... 已耗时 {formatTime(elapsedSeconds)}
                     </div>
                     <div className="prose prose-invert max-w-none">
                       <ReactMarkdown remarkPlugins={[remarkGfm]}>{streamContent}</ReactMarkdown>
                       <span className="inline-block w-2 h-4 bg-primary animate-pulse ml-0.5" />
                     </div>
                   </>
                 )}
               </div>
             </div>
           </div>
        ) : loadingPhase ? (
          <div className="flex-1 flex items-center justify-center"><div className="w-10 h-10 border-2 border-primary border-t-transparent rounded-full animate-spin" /></div>
        ) : connected && currentPhase >= 0 && streamContent ? (
          <div className="flex-1 flex flex-col items-center justify-center gap-4 animate-fade-in">
            <div className="w-10 h-10 border-2 border-primary border-t-transparent rounded-full animate-spin" />
            <p className="text-muted-foreground text-sm">实时生成中...</p>
            <button onClick={() => setSuppressStream(false)} className="text-xs text-primary hover:underline">查看实时内容</button>
          </div>
        ) : (
            <div className="flex-1 flex flex-col items-center justify-center gap-4 animate-fade-in">
             {(projectConfig?.phases || []).some((p: any) => p.done) ? (
               <>
                <p className="text-muted-foreground text-sm">有已完成的阶段内容，可以继续创作</p>
                {typeof projectConfig?.pending_approval === 'number' && projectConfig.pending_approval >= 0 ? (
                    <p className="text-xs text-amber-400/80 mb-2">有一个阶段等待你的审批</p>
                  ) : typeof projectConfig?.pending_version === 'number' && projectConfig.pending_version >= 0 ? (
                    <p className="text-xs text-amber-400/80 mb-2">大纲等待选择版本</p>
                  ) : null}
                <button onClick={handleContinue} className="btn-gradient inline-flex items-center gap-2 px-6 py-3 rounded-xl font-medium">
                  <Play className="w-5 h-5" /> 继续创作
                </button>
               </>
             ) : started ? (
              <>
                <div className="w-10 h-10 border-2 border-primary border-t-transparent rounded-full animate-spin" />
                <p className="text-muted-foreground text-sm">正在启动生成...</p>
                <p className="text-xs text-amber-400/70 animate-pulse">请勿关闭网页，生成过程需一定时间</p>
              </>
            ) : (
              <>
                <p className="text-muted-foreground text-sm">点击左侧已完成阶段开始浏览</p>
                <button onClick={handleContinue} className="btn-gradient inline-flex items-center gap-2 px-6 py-3 rounded-xl font-medium">
                  <Play className="w-5 h-5" /> 继续创作
                </button>
              </>
            )}
          </div>
        )}

        <TemplateModal
          show={showTemplateModal}
          defaultName={name || ''}
          onClose={() => setShowTemplateModal(false)}
          onSave={async (templateName) => {
            await saveProjectTemplate(name!, templateName)
          }}
        />

        {showRedoInput && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm" onClick={() => setShowRedoInput(false)}>
            <div className="glass-card rounded-2xl p-6 w-full max-w-lg mx-4 animate-fade-in-up" onClick={e => e.stopPropagation()}>
              <h3 className="font-bold text-lg mb-1">🔄 重新生成 {PHASE_NAMES[redoPhaseIndex]}</h3>
              <p className="text-sm text-muted-foreground mb-4">可选填修改意见，留空则按原风格重新生成</p>
              <textarea className="w-full bg-muted border border-border rounded-xl px-4 py-3 h-28 resize-none text-sm mb-4"
                placeholder="例如：动作描写再详细一些 / 场景布局写清楚 / 节奏放慢一点..."
                value={redoInstruction} onChange={e => setRedoInstruction(e.target.value)} autoFocus />
              <div className="flex justify-end gap-3">
                <button onClick={() => setShowRedoInput(false)} className="px-5 py-2.5 rounded-xl border border-border text-sm hover:bg-muted transition-colors">取消</button>
                <button onClick={() => handleRedoPhase(redoPhaseIndex, redoInstruction)} className="btn-gradient px-6 py-2.5 rounded-xl text-sm font-medium">
                  <RefreshCw className="w-4 h-4 inline mr-1" />确认重新生成
                </button>
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  )
}

