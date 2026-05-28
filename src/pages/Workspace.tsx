import { useEffect, useState, useRef } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { Play, Check, Pencil, X, Loader2, Settings, Sparkles, RefreshCw, ArrowLeft, Zap, ChevronRight } from 'lucide-react'
import Starfield from '../components/Starfield'
import { useWebSocket } from '../hooks/useWebSocket'
import { fetchProject, fetchPhaseContent, savePhaseContent, openProjectFolder, saveProjectTemplate, updateProjectConfig } from '../lib/api'
import TemplateModal from '../components/TemplateModal'
import PhaseTimeline from '../components/PhaseTimeline'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { getPhaseNames, PHASE_DIRS, PHASE_ICONS } from '../lib/constants'

const MAIN_FILES: Record<string, string> = {
  '01_故事大纲': '故事大纲.md',
  '02_完整剧情': '完整剧情.md',
  '03_完整剧本': '完整剧本.md',
  '04_角色场景': '角色场景.md',
  '05_分镜脚本': '分镜脚本.md',
  '06_生图需求': '分析报告.md',
}

export default function Workspace() {
  const { name } = useParams<{ name: string }>()
  const navigate = useNavigate()
  const [projectConfig, setProjectConfig] = useState<any>(null)
  const [feedbackText, setFeedbackText] = useState('')
  const [showFeedback, setShowFeedback] = useState(false)
  const [episodeFeedbackText, setEpisodeFeedbackText] = useState('')
  const [showEpisodeFeedback, setShowEpisodeFeedback] = useState(false)
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
  const [streamDraft, setStreamDraft] = useState('')
  const [editingStream, setEditingStream] = useState(false)
  const [editingEpisode, setEditingEpisode] = useState(false)
  const [streamChars, setStreamChars] = useState(0)
  const [streamStartTime, setStreamStartTime] = useState(0)
  const [currentPhaseMaxChars, setCurrentPhaseMaxChars] = useState(0)
  const [elapsedSeconds, setElapsedSeconds] = useState(0)
  const [generating, setGenerating] = useState(false)
  const [autoApprove, setAutoApprove] = useState(false)
  const [projectRunning, setProjectRunning] = useState(false)
  const [confirmedPhases, setConfirmedPhases] = useState<number[]>([])
  const [confirmedPhaseId, setConfirmedPhaseId] = useState<number | null>(null)
  const streamHadContent = useRef(false)

  const { connect, send, approve, revise, reject, confirmPhase, proceedGeneration, selectVersion, disconnect, clearStream, connected, streamContent, currentPhase, phases, progress, awaitingApproval, awaitingVersion, awaitingProceed, contentWarnings, isComplete, streamDone, chunksCompleted, error, episodeConfirm, episodeApprove, episodeRevise, awaitingEpisodeApproval, currentEpisode, confirmedPhaseIndex, clearConfirmedPhase, pausedPhaseIndex } = useWebSocket()


  useEffect(() => {
    if (streamDone && streamContent) {
      setStreamDraft(streamContent)
    } else if (!streamDone) {
      setStreamDraft('')
      setEditingStream(false)
      setEditingEpisode(false)
    }
  }, [streamDone, streamContent])

  // 自动审核模式下，自动通过审批 & 自动选择版本A
  useEffect(() => {
    if (autoApprove && awaitingVersion) {
      selectVersion('1', '')
    }
  }, [autoApprove, awaitingVersion])

  useEffect(() => {
    if (autoApprove && awaitingApproval) {
      approve('')
    }
  }, [autoApprove, awaitingApproval])

  useEffect(() => {
    if (!name) return
    fetchProject(name).then(config => {
      setProjectConfig(config)
      setAutoApprove(config.auto_approve === true)
      const phs = config.phases || []
      if (phs.some((p: any) => p.done)) setStarted(true)
      if (config.running) {
        // 后台任务正在运行，连接 WS 看实时进度
        setStarted(true)
        setProjectRunning(true)
        setSuppressStream(false)
        connect(name)
      } else if (typeof config.pending_approval === 'number' && config.pending_approval >= 0) {
        setStarted(true)
        connect(name)
        setPendingContinue(true)
      } else if (typeof config.pending_version === 'number' && config.pending_version >= 0) {
        setStarted(true)
        connect(name)
        setPendingContinue(true)
      } else if (config.pending_episode && typeof config.pending_episode.phase_index === 'number') {
        setStarted(true)
        connect(name)
        setPendingContinue(true)
      } else if (typeof config._version_selected === 'string') {
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
          setPendingContinue(false)
        } else if (redo) {
          send({ action: 'redo_phase', phase_index: redo.index, feedback: redo.instruction, style: styleData })
          setPendingRedo(null)
        } else {
          send({ action: 'start', style: styleData })
          setPendingStart(false)
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
  const handleResumeGeneration = () => {
    if (!name) return
    if (!connected) { connect(name); setPendingContinue(true); return }
    setSuppressStream(false)
    setViewContent('')
    setSelectedPhase(-1)
    setContinuing(true)
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
  const handleApprove = async () => {
    // 如果用户在审核中编辑了内容，先保存
    if (streamDraft && streamDraft !== streamContent) {
      const dir = PHASE_DIRS[currentPhase]
      const savePath = `${dir}/${MAIN_FILES[dir] || '产出.md'}`
      await savePhaseContent(name!, savePath, streamDraft)
    }
    approve(currentPhase)
    setSelectedPhase(-1)
    setViewContent('')
    setActFileList([])
    setSuppressStream(false)
    setStreamDraft('')
  }
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
  const handleVersionA = () => { selectVersion('1', versionFeedback); setVersionFeedback(''); setShowVersionFeedback(false) }
  const handleVersionB = () => { selectVersion('2', versionFeedback); setVersionFeedback(''); setShowVersionFeedback(false) }
  const handleVersionMix = () => { if (!mixFeedback.trim()) return; selectVersion('3', mixFeedback); setMixFeedback(''); setShowMixInput(false) }

  const handleRedoPhase = (index: number, instruction: string = '') => {
    if (!projectConfig?.style_type) return
    clearStream()
    setSuppressStream(false)
    setShowRedoInput(false)
    setConfirmedPhaseId(null)
    setConfirmedPhases(prev => prev.filter(i => i < index))
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
          duration_mode: projectConfig.duration_mode || '', episode_count: projectConfig.episode_count || '', episode_duration: projectConfig.episode_duration || '',
          custom_requirements: projectConfig.custom_requirements || '', visual_reference: projectConfig.visual_reference || '',
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
    if (index < projectConfig.phases.length) {
      // 将当前阶段及所有下游阶段标记为未完成
      for (let i = index; i < projectConfig.phases.length; i++) {
        projectConfig.phases[i].done = false
      }
      setProjectConfig({ ...projectConfig })
    }
  }

  const handleEditContent = () => {
    setEditText(viewContent)
    setEditingContent(true)
  }

  const handleSaveEdit = async () => {
    const dir = PHASE_DIRS[selectedPhase]
    let savePath: string
    if (selectedAct) {
      savePath = selectedAct.includes('/') ? selectedAct : `${dir}/${selectedAct}`
    } else {
      savePath = `${dir}/${MAIN_FILES[dir] || '产出.md'}`
    }
    const ok = await savePhaseContent(name!, savePath, editText)
    if (ok) {
      setViewContent(editText)
    }
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
    setSuppressStream(true)
    setSelectedPhase(index); setActFileList([]); setSelectedAct(''); setViewContent(''); setLoadingPhase(true)
    try {
      const c = await fetchPhaseContent(projectConfig?.name, PHASE_DIRS[index])
      if (c.is_split && c.file_list && c.file_list.length > 1) { setActFileList(c.file_list); setExpandedPhase(index) }
      setViewContent(c.content || '（暂无内容，请先生成该项目）')
    } catch { setViewContent('无法加载内容') }
    setLoadingPhase(false)
  }

  const handleViewAct = async (phaseIndex: number, actFileName: string) => {
    setSelectedAct(actFileName); setViewContent(''); setLoadingPhase(true)
    try {
      const actPath = actFileName && actFileName.includes('/')
        ? `${PHASE_DIRS[phaseIndex]}/${actFileName}`
        : (actFileName ? `${PHASE_DIRS[phaseIndex]}/${actFileName}` : PHASE_DIRS[phaseIndex])
      const c = await fetchPhaseContent(projectConfig?.name, actPath)
      setViewContent(c.content || '')
    } catch { setViewContent('无法加载内容') }
    setLoadingPhase(false)
  }

  const phaseNames = getPhaseNames(projectConfig?.style_type)
  const allDone = (projectConfig?.phases || []).filter((p: any) => p.done).length >= phaseNames.length
  const showStream = !suppressStream && connected && (streamContent || projectRunning)

  return (
    <div className="flex h-screen relative overflow-hidden">
      <Starfield />

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
        autoApprove={autoApprove}
        chunksCompleted={chunksCompleted}
        onNavigate={navigate}
        onOpenFolder={() => openProjectFolder(name!)}
        onShowTemplateModal={() => setShowTemplateModal(true)}
        onViewPhase={handleViewPhase}
        onViewAct={handleViewAct}
        onSetExpandedPhase={setExpandedPhase}
        onRedo={(i) => { setRedoPhaseIndex(i); setRedoInstruction(''); setShowRedoInput(true) }}
        onAutoApproveChange={(v) => {
          setAutoApprove(v)
          if (name) updateProjectConfig(name, { auto_approve: v })
          send({ action: 'set_auto_approve', value: v })
        }}
      />

      {/* Main */}
      <main className="flex-1 flex flex-col overflow-hidden relative z-10 premium-panel premium-panel-rich" style={{ borderRadius: 0, borderLeft: '1px solid rgba(255,255,255,0.06)' }}>
        {/* Decorative layers matching homepage cards */}
        <div className="wp-border" />
        <div className="wp-sweep" />
        <div className="wp-bottom-glow" />
        {allDone && selectedPhase < 0 && !awaitingApproval && !awaitingEpisodeApproval && !awaitingProceed ? (
          <div className="flex-1 flex items-center justify-center" style={{ animation: 'celebrate-fade-in 0.6s ease forwards' }}>
            <div className="text-center">
              <div className="w-20 h-20 mx-auto mb-4 rounded-3xl flex items-center justify-center" style={{ animation: 'celebrate-float 3s ease-in-out infinite', background: 'linear-gradient(135deg, rgba(74,222,128,0.20), rgba(52,211,153,0.15))' }}>
                <Sparkles className="w-8 h-8" style={{ color: 'rgba(74,222,128,0.90)' }} />
              </div>
              <h2 className="text-xl font-bold mb-1" style={{
                background: 'linear-gradient(135deg, rgba(74,222,128,0.95), rgba(52,211,153,0.85))',
                WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent', backgroundClip: 'text',
              }}>完成所有任务！</h2>
              <p className="text-sm mb-6" style={{ color: 'rgba(255,255,255,0.55)' }}>{projectConfig?.style_type === '4' ? '小说创作已完成' : '提示词已生成完毕，可前往智能生图页面使用项目模式生成图片'}</p>
              <div className="flex items-center justify-center gap-3 flex-wrap">
                <button onClick={() => navigate('/home')} className="inline-flex items-center gap-2 px-6 py-3 rounded-xl font-medium transition-all"
                  style={{ background: 'linear-gradient(135deg, hsl(var(--primary)), hsl(265, 87%, 60%))', color: '#000' }}>
                  <ArrowLeft className="w-5 h-5" /> 返回首页
                </button>
                {projectConfig?.style_type && projectConfig.style_type !== '4' && (
                  <>
                    <button onClick={() => { if (name) { localStorage.setItem('lastProject', name); navigate('/image-gen') } }}
                      className="inline-flex items-center gap-2 px-6 py-3 rounded-xl border text-sm transition-all"
                      style={{ borderColor: 'rgba(255,255,255,0.22)', color: 'rgba(255,255,255,0.75)' }}
                      onMouseOver={(e) => { e.currentTarget.style.background = 'rgba(255,255,255,0.08)'; e.currentTarget.style.borderColor = 'rgba(255,255,255,0.30)' }}
                      onMouseOut={(e) => { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.borderColor = 'rgba(255,255,255,0.22)' }}
                    >
                      🎨 去生图
                    </button>
                    <button onClick={() => { if (name) { localStorage.setItem('lastProject', name); navigate('/video-gen') } }}
                      className="inline-flex items-center gap-2 px-6 py-3 rounded-xl border text-sm transition-all"
                      style={{ borderColor: 'rgba(255,255,255,0.22)', color: 'rgba(255,255,255,0.75)' }}
                      onMouseOver={(e) => { e.currentTarget.style.background = 'rgba(255,255,255,0.08)'; e.currentTarget.style.borderColor = 'rgba(255,255,255,0.30)' }}
                      onMouseOut={(e) => { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.borderColor = 'rgba(255,255,255,0.22)' }}
                    >
                      🎬 去视频
                    </button>
                  </>
                )}
                {projectConfig?.style_type === '4' && (
                  <a href={`/api/projects/${encodeURIComponent(name!)}/export-novel`} target="_blank" rel="noopener noreferrer"
                    className="inline-flex items-center gap-2 px-6 py-3 rounded-xl border text-sm transition-all"
                    style={{ borderColor: 'rgba(255,255,255,0.22)', color: 'rgba(255,255,255,0.75)' }}
                    onMouseOver={(e) => { e.currentTarget.style.background = 'rgba(255,255,255,0.08)'; e.currentTarget.style.borderColor = 'rgba(255,255,255,0.30)' }}
                    onMouseOut={(e) => { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.borderColor = 'rgba(255,255,255,0.22)' }}
                  >
                    📥 导出 Markdown
                  </a>
                )}
                {currentPhase >= 0 && PHASE_DIRS[currentPhase] && (
                  <a href={`/api/projects/${encodeURIComponent(name!)}/${PHASE_DIRS[currentPhase]}/export-docx`} target="_blank" rel="noopener noreferrer"
                    className="inline-flex items-center gap-2 px-6 py-3 rounded-xl text-sm font-medium transition-all"
                    style={{ background: 'rgba(59,130,246,0.15)', border: '1px solid rgba(59,130,246,0.30)', color: 'rgba(147,197,253,0.90)' }}
                    onMouseOver={(e) => { e.currentTarget.style.background = 'rgba(59,130,246,0.25)'; e.currentTarget.style.borderColor = 'rgba(59,130,246,0.45)' }}
                    onMouseOut={(e) => { e.currentTarget.style.background = 'rgba(59,130,246,0.15)'; e.currentTarget.style.borderColor = 'rgba(59,130,246,0.30)' }}
                  >
                    📄 导出 Word
                  </a>
                )}
              </div>
            </div>
          </div>
        ) : !started ? (
          <div className="flex-1 flex items-center justify-center animate-fade-in">
            <div className="text-center">
              <div className="w-24 h-24 mx-auto mb-6 rounded-3xl flex items-center justify-center animate-float"
                style={{ background: 'linear-gradient(135deg, rgba(255,255,255,0.15), rgba(200,150,255,0.10))' }}>
                <Zap className="w-10 h-10" style={{ color: 'rgba(255,255,255,0.90)' }} />
              </div>
              {projectConfig && (projectConfig.phases || []).some((p: any) => p.done) ? (
                <>
                  <h2 className="text-xl font-bold mb-2" style={{ color: 'rgba(255,255,255,0.90)' }}>继续创作</h2>
                  <p className="text-sm mb-6" style={{ color: 'rgba(255,255,255,0.55)' }}>内容已确认，可点击继续推进到下一步</p>
                  <button onClick={handleContinue} className="inline-flex items-center gap-2 px-8 py-3.5 rounded-2xl font-medium text-base transition-all"
                    style={{ background: 'linear-gradient(135deg, hsl(var(--primary)), hsl(265, 87%, 60%))', color: '#000' }}>
                    <Play className="w-5 h-5" /> 继续创作
                  </button>
                </>
              ) : (
                <>
                  <h2 className="text-xl font-bold mb-2" style={{ color: 'rgba(255,255,255,0.90)' }}>准备开始创作</h2>
                  <p className="text-sm mb-6" style={{ color: 'rgba(255,255,255,0.55)' }}>AI 将引导你完成从大纲到提示词的每个阶段</p>
                  <button onClick={handleStart} className="inline-flex items-center gap-2 px-8 py-3.5 rounded-2xl font-medium text-base transition-all"
                    style={{ background: 'linear-gradient(135deg, hsl(var(--primary)), hsl(265, 87%, 60%))', color: '#000' }}>
                    <Play className="w-5 h-5" /> 开始创作
                  </button>
                </>
              )}
            </div>
          </div>
        ) : error ? (
          <div className="flex-1 flex items-center justify-center">
            <div className="text-center max-w-md">
              <X className="w-12 h-12 mx-auto mb-3" style={{ color: 'rgba(248,113,113,0.90)' }} />
              <p className="font-medium mb-2" style={{ color: 'rgba(248,113,113,0.90)' }}>{error}</p>
              {(error.toLowerCase().includes('api key') || error.toLowerCase().includes('api_key') || error.toLowerCase().includes('not configured') || error.toLowerCase().includes('auth')) ? (
                <button onClick={() => navigate('/settings')} className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm font-medium mt-2 transition-all"
                  style={{ background: 'linear-gradient(135deg, hsl(var(--primary)), hsl(265, 87%, 60%))', color: '#000' }}>
                  <Settings className="w-4 h-4" /> 前往设置页配置 API Key
                </button>
              ) : (
                <button onClick={handleContinue} className="inline-flex items-center gap-1.5 px-5 py-2.5 rounded-xl text-sm font-medium mt-2 transition-all"
                  style={{ background: 'linear-gradient(135deg, hsl(var(--primary)), hsl(265, 87%, 60%))', color: '#000' }}>
                  <Play className="w-4 h-4" /> 重试
                </button>
              )}
            </div>
          </div>
        ) : showStream ? (
          <>
            <div className="px-8 py-3" style={{ borderBottom: '1px solid rgba(255,255,255,0.12)', background: 'rgba(255,255,255,0.06)', backdropFilter: 'blur(12px)', WebkitBackdropFilter: 'blur(12px)' }}>
              <div className="max-w-5xl mx-auto flex items-center justify-between gap-4">
                <div className="flex items-center gap-2 text-sm" style={{ color: 'rgba(255,255,255,0.80)' }}>
                  <span>{PHASE_ICONS[currentPhase] || '📝'}</span>
                  <span className="font-medium">{getPhaseNames(projectConfig?.style_type)[currentPhase] || '生成中...'}</span>
                  <span className="text-xs ml-1" style={{ color: 'rgba(255,255,255,0.50)' }}>({Math.min(progress.current + 1, progress.total)}/{progress.total})</span>
                  <span className="text-xs ml-2" style={{ color: 'rgba(255,255,255,0.50)' }}>| {streamChars} 字</span>
                </div>
                <div className="flex-1 max-w-xs space-y-1">
                  <div className="w-full h-1.5 rounded-full overflow-hidden" style={{ background: 'rgba(255,255,255,0.08)' }}>
                    <div className="h-full rounded-full transition-all duration-300"
                      style={{ width: `${Math.min(100, (streamChars / (currentPhaseMaxChars || 1)) * 100)}%`, background: 'linear-gradient(90deg, hsl(var(--primary)), hsl(265, 87%, 60%))', boxShadow: '0 0 12px rgba(255,255,255,0.25)' }} />
                  </div>
                  <div className="flex justify-between text-[10px]" style={{ color: 'rgba(255,255,255,0.50)' }}>
                    <span>已生成 {streamChars} 字</span>
                    <span>{formatTime(elapsedSeconds)} {(() => { const r = calcRemaining(); return r ? `| 预计剩余${formatTime(r)}` : '' })()}</span>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  {connected && <div className="w-2 h-2 rounded-full flex-shrink-0 animate-pulse" style={{ background: 'rgba(74,222,128,0.90)' }} title="已连接" />}
                </div>
              </div>
            </div>
            <div className="flex-1 overflow-y-auto p-10" style={{ opacity: 1 }}>
              <div className="max-w-5xl mx-auto premium-inset p-6">
                {streamContent.length > 10 && !streamDone && (
                  <div className="mb-3 text-xs pl-3 py-1" style={{ color: 'rgba(255,255,255,0.55)', borderLeft: '2px solid rgba(255,255,255,0.25)' }}>
                    AI 正在逐字生成内容... 已耗时 {formatTime(elapsedSeconds)}
                  </div>
                )}
                {(streamDone && awaitingApproval && editingStream) || (streamDone && awaitingEpisodeApproval && editingEpisode) ? (
                  <textarea
                    className="w-full h-[65vh] rounded-xl p-4 text-sm font-mono resize-none focus:outline-none"
                    style={{ background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.18)', color: 'rgba(255,255,255,0.85)' }}
                    value={streamDraft}
                    onChange={e => setStreamDraft(e.target.value)}
                    autoFocus
                  />
                ) : (
                  <div className="prose prose-invert max-w-none animate-fade-in" style={{ color: 'rgba(255,255,255,0.85)' }}>
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>{streamContent}</ReactMarkdown>
                    {streamContent && <span className="inline-block w-2 h-4 ml-0.5 animate-pulse" style={{ background: 'hsl(var(--primary))' }} />}
                  </div>
                )}
              </div>
            </div>
             {awaitingVersion && (
              <div className="p-5 animate-fade-in-up" style={{ borderTop: '1px solid rgba(139,92,246,0.15)', background: 'rgba(255,255,255,0.06)', backdropFilter: 'blur(12px)', WebkitBackdropFilter: 'blur(12px)' }}>
                <div className="max-w-5xl mx-auto">
                  <p className="text-sm font-medium mb-4" style={{ color: 'rgba(255,255,255,0.85)' }}>🎯 方向卡已生成，请选择版本：</p>
                  {showMixInput ? (
                    <div className="space-y-3">
                      <textarea className="w-full rounded-xl px-4 py-3 h-24 resize-none text-sm"
                        style={{ background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.18)', color: 'rgba(255,255,255,0.85)' }}
                        placeholder="请描述你希望如何混合版本A和版本B..." value={mixFeedback} onChange={e => setMixFeedback(e.target.value)} autoFocus />
                      <div className="flex gap-2">
                        <button onClick={handleVersionMix} className="inline-flex items-center gap-1 px-5 py-2 rounded-xl text-sm font-medium transition-all"
                          style={{ background: 'linear-gradient(135deg, hsl(var(--primary)), hsl(265, 87%, 60%))', color: '#000' }}>
                          <Sparkles className="w-4 h-4" />提交混合
                        </button>
                        <button onClick={() => setShowMixInput(false)} className="px-5 py-2 rounded-xl border text-sm transition-all"
                          style={{ borderColor: 'rgba(255,255,255,0.22)', color: 'rgba(255,255,255,0.75)' }}
                          onMouseOver={(e) => { e.currentTarget.style.background = 'rgba(255,255,255,0.08)'; e.currentTarget.style.borderColor = 'rgba(255,255,255,0.30)' }}
                          onMouseOut={(e) => { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.borderColor = 'rgba(255,255,255,0.22)' }}
                        >取消</button>
                      </div>
                    </div>
                  ) : (
                    <div className="space-y-3">
                      <textarea className="w-full rounded-xl px-4 py-3 h-24 resize-none text-sm"
                        style={{ background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.18)', color: 'rgba(255,255,255,0.85)' }}
                        placeholder="可选：输入修改要求，选中的版本将根据你的要求重新生成（如：增加第3个角色、把结局改成悲剧、加快节奏...）" value={versionFeedback} onChange={e => setVersionFeedback(e.target.value)} />
                      <div className="flex items-center gap-3">
                        <button onClick={handleVersionA} className="px-6 py-3 rounded-xl text-sm font-medium transition-all"
                          style={{ background: 'linear-gradient(135deg, hsl(var(--primary)), hsl(265, 87%, 60%))', color: '#000' }}>版本 A</button>
                        <button onClick={handleVersionB} className="px-6 py-3 rounded-xl text-sm font-medium transition-all"
                          style={{ background: 'linear-gradient(135deg, hsl(var(--primary)), hsl(265, 87%, 60%))', color: '#000' }}>版本 B</button>
                        <button onClick={() => setShowMixInput(true)} className="px-5 py-3 rounded-xl border-2 text-sm font-medium transition-all"
                          style={{ borderColor: 'rgba(255,255,255,0.22)', color: 'rgba(255,255,255,0.75)' }}
                          onMouseOver={(e) => { e.currentTarget.style.background = 'rgba(255,255,255,0.08)'; e.currentTarget.style.borderColor = 'rgba(255,255,255,0.35)' }}
                          onMouseOut={(e) => { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.borderColor = 'rgba(255,255,255,0.22)' }}
                        >混合 A + B</button>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            )}
            {awaitingApproval && !isComplete && (
              <div className="p-5 animate-fade-in-up" style={{ borderTop: '1px solid rgba(139,92,246,0.15)', background: 'rgba(255,255,255,0.06)', backdropFilter: 'blur(12px)', WebkitBackdropFilter: 'blur(12px)' }}>
                {showFeedback ? (
                  <div className="max-w-5xl mx-auto space-y-3">
                    <textarea className="w-full bg-muted border border-border rounded-xl px-4 py-3 h-28 resize-none text-sm" placeholder="请输入修改意见..." value={feedbackText} onChange={e => setFeedbackText(e.target.value)} autoFocus />
                    <div className="flex gap-2">
                      <button onClick={handleRevise} className="btn-gradient px-5 py-2 rounded-xl text-sm font-medium"><Pencil className="w-4 h-4 inline mr-1" />提交修改</button>
                      <button onClick={() => setShowFeedback(false)} className="px-5 py-2 rounded-xl border border-border text-sm hover:bg-muted transition-colors">取消</button>
                    </div>
                  </div>
                ) : (
                  <div className="max-w-5xl mx-auto flex items-center gap-2">
                    <button onClick={handleApprove} className="flex items-center gap-1.5 px-5 py-2.5 rounded-xl text-sm font-medium transition-all"
                      style={{ background: 'linear-gradient(135deg, rgba(74,222,128,0.25), rgba(52,211,153,0.2))', color: 'rgba(74,222,128,0.95)', border: '1px solid rgba(74,222,128,0.3)' }}>
                      <Check className="w-4 h-4" /> 通过
                    </button>
                    <button onClick={() => setShowFeedback(true)} className="flex items-center gap-1.5 px-4 py-2.5 rounded-xl text-sm transition-all"
                      style={{ border: '1px solid rgba(255,255,255,0.10)', color: 'rgba(255,255,255,0.7)' }}
                      onMouseOver={(e) => { e.currentTarget.style.background = 'rgba(255,255,255,0.06)' }}
                      onMouseOut={(e) => { e.currentTarget.style.background = 'transparent' }}>
                      <Pencil className="w-4 h-4" /> 修改
                    </button>
                    <button onClick={async () => {
                      if (!editingStream) {
                        setStreamDraft(streamContent)
                        setEditingStream(true)
                      } else {
                        if (streamDraft && streamDraft !== streamContent && name) {
                          const dir = PHASE_DIRS[currentPhase]
                          const savePath = `${dir}/${MAIN_FILES[dir] || '产出.md'}`
                          await savePhaseContent(name, savePath, streamDraft)
                        }
                        setEditingStream(false)
                      }
                    }} className="flex items-center gap-1.5 px-4 py-2.5 rounded-xl text-sm transition-all"
                      style={{ color: 'rgba(255,255,255,0.5)' }}
                      onMouseOver={(e) => { e.currentTarget.style.color = 'rgba(255,255,255,0.8)' }}
                      onMouseOut={(e) => { e.currentTarget.style.color = 'rgba(255,255,255,0.5)' }}>
                      <Pencil className="w-4 h-4" /> {editingStream ? '完成编辑' : '编辑'}
                    </button>
                  </div>
                )}
              </div>
            )}
            {awaitingApproval && !awaitingEpisodeApproval && (
              <div className="p-5 animate-fade-in-up" style={{ borderTop: '1px solid rgba(139,92,246,0.15)', background: 'rgba(255,255,255,0.06)', backdropFilter: 'blur(12px)', WebkitBackdropFilter: 'blur(12px)' }}>
                <div className="max-w-5xl mx-auto flex items-center gap-2">
                  <button onClick={handleApprove} className="flex items-center gap-1.5 px-5 py-2.5 rounded-xl text-sm font-medium transition-all"
                    style={{ background: 'linear-gradient(135deg, rgba(74,222,128,0.25), rgba(52,211,153,0.2))', color: 'rgba(74,222,128,0.95)', border: '1px solid rgba(74,222,128,0.3)' }}>
                    <Check className="w-4 h-4" /> 通过
                  </button>
                  <button onClick={() => setShowFeedback(true)} className="flex items-center gap-1.5 px-4 py-2.5 rounded-xl text-sm transition-all"
                    style={{ border: '1px solid rgba(255,255,255,0.10)', color: 'rgba(255,255,255,0.7)' }}
                    onMouseOver={(e) => { e.currentTarget.style.background = 'rgba(255,255,255,0.06)' }}
                    onMouseOut={(e) => { e.currentTarget.style.background = 'transparent' }}>
                    <Pencil className="w-4 h-4" /> 修改
                  </button>
                </div>
              </div>
            )}
            {awaitingProceed && (
              <div className="p-5 animate-fade-in-up" style={{ borderTop: '1px solid rgba(139,92,246,0.15)', background: 'rgba(255,255,255,0.06)', backdropFilter: 'blur(12px)', WebkitBackdropFilter: 'blur(12px)' }}>
                <div className="max-w-5xl mx-auto flex items-center justify-between">
                  <div className="flex items-center gap-2 text-sm">
                    <Check className="w-4 h-4 text-green-400" />
                    <span className="text-green-400 font-medium">已完成确认</span>
                    <span className="text-muted-foreground">— 准备好后可继续下一步</span>
                  </div>
                  <button onClick={handleProceed} className="flex items-center gap-1.5 px-5 py-2.5 rounded-xl text-sm font-medium transition-all whitespace-nowrap"
                    style={{ background: 'linear-gradient(135deg, rgba(74,222,128,0.25), rgba(52,211,153,0.2))', color: 'rgba(74,222,128,0.95)', border: '1px solid rgba(74,222,128,0.3)' }}>
                    <Play className="w-4 h-4" /> 继续进行下一步
                  </button>
                </div>
              </div>
            )}
            {showStream && streamDone && !awaitingApproval && !awaitingVersion && !isComplete && !awaitingProceed && !awaitingEpisodeApproval && pausedPhaseIndex === null && (
              <div className="border-t border-border/50 p-4 bg-card/80 backdrop-blur-sm">
                <div className="max-w-5xl mx-auto flex items-center justify-between">
                  <p className="text-xs text-muted-foreground">内容已生成完毕</p>
                  <button onClick={() => { setViewContent(streamContent); setSelectedPhase(currentPhase); setSuppressStream(true) }}
                     className="px-4 py-2 rounded-xl text-xs transition-all"
                     style={{ border: '1px solid rgba(255,255,255,0.10)', color: 'rgba(255,255,255,0.7)' }}
                     onMouseOver={(e) => { e.currentTarget.style.background = 'rgba(255,255,255,0.06)' }}
                     onMouseOut={(e) => { e.currentTarget.style.background = 'transparent' }}>
                    查看内容
                  </button>
                </div>
              </div>
            )}
            {awaitingEpisodeApproval && currentEpisode && (
              <div className="p-5 animate-fade-in-up" style={{ borderTop: '1px solid rgba(139,92,246,0.15)', background: 'rgba(255,255,255,0.06)', backdropFilter: 'blur(12px)', WebkitBackdropFilter: 'blur(12px)', borderColor: 'hsl(35, 80%, 50%, 0.3)' }}>
                {showEpisodeFeedback ? (
                  <div className="max-w-5xl mx-auto space-y-3">
                    <div className="flex items-center gap-2 text-sm text-amber-400 mb-1">
                      <span className="font-medium">修改第 {currentEpisode.chunk_index + 1} 集</span>
                      <span className="text-muted-foreground">— 输入修改意见后将重新生成</span>
                    </div>
                    <textarea className="w-full bg-muted border border-border rounded-xl px-4 py-3 h-28 resize-none text-sm" placeholder="请输入修改意见..." value={episodeFeedbackText} onChange={e => setEpisodeFeedbackText(e.target.value)} autoFocus />
                    <div className="flex gap-2">
                      <button onClick={() => { episodeRevise(episodeFeedbackText); setShowEpisodeFeedback(false); setEpisodeFeedbackText('') }} className="btn-gradient px-5 py-2 rounded-xl text-sm font-medium">
                        <Pencil className="w-4 h-4 inline mr-1" /> 提交修改
                      </button>
                      <button onClick={() => setShowEpisodeFeedback(false)} className="px-5 py-2 rounded-xl text-sm transition-all"
                        style={{ border: '1px solid rgba(255,255,255,0.10)', color: 'rgba(255,255,255,0.7)' }}
                        onMouseOver={(e) => { e.currentTarget.style.background = 'rgba(255,255,255,0.06)' }}
                        onMouseOut={(e) => { e.currentTarget.style.background = 'transparent' }}>取消</button>
                    </div>
                  </div>
                ) : (
                  <div className="max-w-5xl mx-auto">
                    <div className="flex items-center gap-2 text-sm text-amber-400 mb-3">
                      <span className="w-1.5 h-1.5 rounded-full bg-amber-400 animate-pulse" />
                      <span className="font-medium">第 {currentEpisode.chunk_index + 1}/{currentEpisode.total_chunks} 集已生成</span>
                      <span className="text-muted-foreground">— 请选择下一步操作</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <button onClick={() => episodeConfirm(currentEpisode?.phase_index)} className="flex items-center gap-1.5 px-5 py-2.5 rounded-xl text-sm font-medium transition-all border-2 border-primary/40 text-primary hover:bg-primary/5">
                        <Check className="w-4 h-4" />{currentEpisode.chunk_index + 1 < currentEpisode.total_chunks ? ' 完成' : ' 完成并暂停'}
                      </button>
                      <button onClick={episodeApprove} className="flex items-center gap-1.5 px-5 py-2.5 rounded-xl text-sm font-medium transition-all btn-gradient">
                        <ChevronRight className="w-4 h-4" />{currentEpisode.chunk_index + 1 < currentEpisode.total_chunks ? ' 继续下一集' : ' 完成本阶段'}
                      </button>
                      <button onClick={() => setShowEpisodeFeedback(true)} className="flex items-center gap-1.5 px-4 py-2.5 rounded-xl text-sm transition-all"
                        style={{ border: '1px solid rgba(255,255,255,0.10)', color: 'rgba(255,255,255,0.7)' }}
                        onMouseOver={(e) => { e.currentTarget.style.background = 'rgba(255,255,255,0.06)' }}
                        onMouseOut={(e) => { e.currentTarget.style.background = 'transparent' }}>
                        <Pencil className="w-4 h-4" /> 修改
                      </button>
                      <button onClick={async () => {
                        if (!editingEpisode) {
                          setStreamDraft(streamContent)
                          setEditingEpisode(true)
                        } else {
                          if (streamDraft && streamDraft !== streamContent && name && currentEpisode) {
                            const dir = PHASE_DIRS[currentEpisode.phase_index]
                            const filePath = currentEpisode.chunk_name || ''
                            const savePath = filePath.includes('/') ? filePath : `${dir}/${filePath}`
                            await savePhaseContent(name, savePath, streamDraft)
                          }
                          setEditingEpisode(false)
                        }
                      }} className="flex items-center gap-1.5 px-4 py-2.5 rounded-xl text-sm transition-all"
                        style={{ color: 'rgba(255,255,255,0.5)' }}
                        onMouseOver={(e) => { e.currentTarget.style.color = 'rgba(255,255,255,0.8)' }}
                        onMouseOut={(e) => { e.currentTarget.style.color = 'rgba(255,255,255,0.5)' }}>
                        <Pencil className="w-4 h-4" /> {editingEpisode ? '完成编辑' : '编辑'}
                      </button>
                    </div>
                  </div>
                )}
              </div>
            )}
            {contentWarnings.length > 0 && (
              <div className="border-t border-border/50 p-4 bg-card/80 backdrop-blur-sm">
                <div className="max-w-5xl mx-auto">
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
            {pausedPhaseIndex !== null && !awaitingEpisodeApproval && !awaitingApproval && (
              <div className="p-5 animate-fade-in-up" style={{ borderTop: '1px solid rgba(139,92,246,0.15)', background: 'rgba(255,255,255,0.06)', backdropFilter: 'blur(12px)', WebkitBackdropFilter: 'blur(12px)', borderColor: 'hsl(45, 80%, 50%, 0.3)' }}>
                  <div className="max-w-5xl mx-auto flex items-center justify-between">
                  <div className="flex items-center gap-2 text-sm">
                    <Check className="w-4 h-4 text-amber-400" />
                    <span className="text-amber-400 font-medium">第 {chunksCompleted[currentPhase]?.length || 1} 集已保存</span>
                    <span className="text-muted-foreground">— 可继续生成下一集</span>
                  </div>
                  <button onClick={handleProceed} className="flex items-center gap-1.5 px-5 py-2.5 rounded-xl text-sm font-medium transition-all whitespace-nowrap"
                    style={{ background: 'linear-gradient(135deg, rgba(74,222,128,0.25), rgba(52,211,153,0.2))', color: 'rgba(74,222,128,0.95)', border: '1px solid rgba(74,222,128,0.3)' }}>
                    <Play className="w-4 h-4" /> 继续生成下一集
                  </button>
                </div>
              </div>
            )}
            {confirmedPhaseIndex !== null && !awaitingEpisodeApproval && (
              <div className="p-5 animate-fade-in-up" style={{ borderTop: '1px solid rgba(139,92,246,0.15)', background: 'rgba(255,255,255,0.06)', backdropFilter: 'blur(12px)', WebkitBackdropFilter: 'blur(12px)' }}>
                <div className="max-w-5xl mx-auto flex items-center justify-between">
                  <div className="flex items-center gap-2 text-sm">
                    <Check className="w-4 h-4 text-green-400" />
                    <span className="text-green-400 font-medium">阶段已确认，内容已保存</span>
                  </div>
                  <button onClick={() => { clearConfirmedPhase(); handleContinue() }} className="flex items-center gap-1.5 px-5 py-2.5 rounded-xl text-sm font-medium transition-all whitespace-nowrap"
                    style={{ background: 'linear-gradient(135deg, rgba(74,222,128,0.25), rgba(52,211,153,0.2))', color: 'rgba(74,222,128,0.95)', border: '1px solid rgba(74,222,128,0.3)' }}>
                    <Play className="w-4 h-4" /> 继续创作
                  </button>
                </div>
              </div>
            )}
          </>
        ) : viewContent ? (
          <><div className="flex-1 overflow-y-auto p-10 animate-fade-in">
            {/* 暂停中 - 继续生成下一集横幅 */}
            {pausedPhaseIndex !== null && (
              <div className="mb-4 p-4 rounded-xl bg-amber-400/10 border border-amber-400/20 flex items-center justify-between">
                <div className="flex items-center gap-2 text-sm">
                  <span className="w-2 h-2 rounded-full bg-amber-400 animate-pulse" />
                  <span className="text-amber-400 font-medium">
                    第 {chunksCompleted[currentPhase]?.length || 1}/{chunksCompleted[currentPhase]?.[0]?.total || 1} 集已保存 — 可继续生成下一集
                  </span>
                </div>
                <button onClick={handleResumeGeneration} className="btn-gradient inline-flex items-center gap-1.5 px-5 py-2.5 rounded-xl text-sm font-medium whitespace-nowrap"
                  style={{ background: 'linear-gradient(135deg, hsl(150, 60%, 50%), hsl(170, 60%, 45%))' }}>
                  <Play className="w-4 h-4" /> 继续生成下一集
                </button>
              </div>
            )}
            {/* 生成中的横幅提示 */}
            {streamContent && !confirmedPhaseId && pausedPhaseIndex === null && (
              <div className="mb-4 p-3 rounded-xl bg-primary/10 border border-primary/20 flex items-center justify-between">
                <div className="flex items-center gap-2 text-sm">
                  <span className="w-2 h-2 rounded-full bg-primary animate-pulse" />
                  <span className="text-primary font-medium">正在生成 {getPhaseNames(projectConfig?.style_type)[currentPhase] || '...'}</span>
                  <span className="text-muted-foreground">({Math.min(progress.current + 1, progress.total)}/{progress.total})</span>
                </div>
                <button onClick={() => setSuppressStream(false)} className="px-4 py-1.5 rounded-lg bg-primary/20 text-primary text-xs font-medium hover:bg-primary/30 transition-colors">
                  查看实时生成
                </button>
              </div>
            )}
            <div className="max-w-5xl mx-auto premium-inset p-6">
              {confirmedPhaseId !== null && (
                <div className="mb-4 p-3 rounded-xl bg-green-400/10 border border-green-400/20 flex items-center justify-between">
                  <div className="flex items-center gap-2 text-sm">
                    <Check className="w-4 h-4 text-green-400" />
                    <span className="text-green-400 font-medium">已确认，内容已保存</span>
                  </div>
                  <button onClick={handleContinue} className="px-4 py-1.5 rounded-lg bg-green-400/20 text-green-400 text-xs font-medium hover:bg-green-400/30 transition-colors">
                    继续创作
                  </button>
                </div>
              )}
              <div className="flex items-center justify-between mb-6">
                <h3 className="text-lg font-semibold flex items-center gap-2">
                  <span>{PHASE_ICONS[selectedPhase]}</span>
                  <span className="gradient-text">{getPhaseNames(projectConfig?.style_type)[selectedPhase]}</span>
                  {selectedAct && <span className="text-sm font-normal text-muted-foreground">— {selectedAct.replace(/^\d+_/, '').replace(/\.md$/, '').replace(/_/g, '')}</span>}
                  <span className="text-xs text-muted-foreground ml-2">({viewContent.length} 字)</span>
                </h3>
                <div className="flex items-center gap-2 flex-shrink-0">
                  {(awaitingEpisodeApproval || pausedPhaseIndex !== null) && (
                    <button onClick={() => { setSelectedPhase(-1); setViewContent(''); setActFileList([]); setSuppressStream(false) }} className="px-4 py-2 rounded-xl text-xs transition-all"
                      style={{ border: '1px solid rgba(255,255,255,0.10)', color: 'rgba(255,255,255,0.7)' }}
                      onMouseOver={(e) => { e.currentTarget.style.background = 'rgba(255,255,255,0.06)' }}
                      onMouseOut={(e) => { e.currentTarget.style.background = 'transparent' }}>
                      <ChevronRight className="w-3.5 h-3.5 inline mr-1" /> 回到当前阶段
                    </button>
                  )}
                  {editingContent ? (
                    <>
                      <button onClick={handleSaveEdit} className="btn-gradient inline-flex items-center gap-1.5 px-4 py-2 rounded-xl text-xs font-medium whitespace-nowrap">
                        <Check className="w-3.5 h-3.5" /> 保存
                      </button>
                      <button onClick={handleCancelEdit} className="px-4 py-2 rounded-xl text-xs transition-all"
                        style={{ border: '1px solid rgba(255,255,255,0.10)', color: 'rgba(255,255,255,0.7)' }}
                        onMouseOver={(e) => { e.currentTarget.style.background = 'rgba(255,255,255,0.06)' }}
                        onMouseOut={(e) => { e.currentTarget.style.background = 'transparent' }}>
                        <X className="w-3.5 h-3.5" /> 取消
                      </button>
                    </>
                  ) : (
                    <>
                      <button onClick={handleEditContent} className="px-4 py-2 rounded-xl text-xs transition-all"
                        style={{ color: 'rgba(255,255,255,0.5)' }}
                        onMouseOver={(e) => { e.currentTarget.style.color = 'rgba(255,255,255,0.8)' }}
                        onMouseOut={(e) => { e.currentTarget.style.color = 'rgba(255,255,255,0.5)' }}>
                        <Pencil className="w-3.5 h-3.5 inline mr-1" /> 编辑
                      </button>
                      {!streamContent && !confirmedPhaseId && (
                        <button onClick={handleContinue} className="btn-gradient inline-flex items-center gap-1.5 px-4 py-2 rounded-xl text-xs font-medium whitespace-nowrap">
                          <Play className="w-3.5 h-3.5" /> 继续创作
                        </button>
                      )}
                    </>
                  )}
                  <a href={`/api/projects/${encodeURIComponent(name!)}/${PHASE_DIRS[selectedPhase]}/export-docx`} target="_blank" rel="noopener noreferrer"
                    className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg text-[11px] font-medium transition-all flex-shrink-0"
                    style={{ background: 'rgba(59,130,246,0.12)', border: '1px solid rgba(59,130,246,0.25)', color: 'rgba(147,197,253,0.85)' }}
                    onMouseOver={(e) => { e.currentTarget.style.background = 'rgba(59,130,246,0.22)'; e.currentTarget.style.borderColor = 'rgba(59,130,246,0.40)' }}
                    onMouseOut={(e) => { e.currentTarget.style.background = 'rgba(59,130,246,0.12)'; e.currentTarget.style.borderColor = 'rgba(59,130,246,0.25)' }}
                  >
                    📄 导出 Word
                  </a>
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
            {awaitingEpisodeApproval && currentEpisode && (
              <div className="p-5 animate-fade-in-up" style={{ borderTop: '1px solid rgba(139,92,246,0.15)', background: 'rgba(255,255,255,0.06)', backdropFilter: 'blur(12px)', WebkitBackdropFilter: 'blur(12px)', borderColor: 'hsl(35, 80%, 50%, 0.3)' }}>
                {showEpisodeFeedback ? (
                  <div className="max-w-5xl mx-auto space-y-3">
                    <div className="flex items-center gap-2 text-sm text-amber-400 mb-1">
                      <span className="font-medium">修改第 {currentEpisode.chunk_index + 1} 集</span>
                      <span className="text-muted-foreground">— 输入修改意见后将重新生成</span>
                    </div>
                    <textarea className="w-full bg-muted border border-border rounded-xl px-4 py-3 h-28 resize-none text-sm" placeholder="请输入修改意见..." value={episodeFeedbackText} onChange={e => setEpisodeFeedbackText(e.target.value)} autoFocus />
                    <div className="flex gap-2">
                      <button onClick={() => { episodeRevise(episodeFeedbackText); setShowEpisodeFeedback(false); setEpisodeFeedbackText('') }} className="btn-gradient px-5 py-2 rounded-xl text-sm font-medium">
                        <Pencil className="w-4 h-4 inline mr-1" /> 提交修改
                      </button>
                      <button onClick={() => setShowEpisodeFeedback(false)} className="px-5 py-2 rounded-xl text-sm transition-all"
                        style={{ border: '1px solid rgba(255,255,255,0.10)', color: 'rgba(255,255,255,0.7)' }}
                        onMouseOver={(e) => { e.currentTarget.style.background = 'rgba(255,255,255,0.06)' }}
                        onMouseOut={(e) => { e.currentTarget.style.background = 'transparent' }}>取消</button>
                    </div>
                  </div>
                ) : (
                  <div className="max-w-5xl mx-auto">
                    <div className="flex items-center gap-2 text-sm text-amber-400 mb-3">
                      <span className="w-1.5 h-1.5 rounded-full bg-amber-400 animate-pulse" />
                      <span className="font-medium">第 {currentEpisode.chunk_index + 1}/{currentEpisode.total_chunks} 集已生成</span>
                      <span className="text-muted-foreground">— 请选择下一步操作</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <button onClick={() => episodeConfirm(currentEpisode?.phase_index)} className="flex items-center gap-1.5 px-5 py-2.5 rounded-xl text-sm font-medium transition-all border-2 border-primary/40 text-primary hover:bg-primary/5">
                        <Check className="w-4 h-4" /> 完成
                      </button>
                      {currentEpisode.chunk_index + 1 < currentEpisode.total_chunks && (
                        <button onClick={episodeApprove} className="flex items-center gap-1.5 px-5 py-2.5 rounded-xl text-sm font-medium transition-all btn-gradient">
                          <ChevronRight className="w-4 h-4" /> 继续下一集
                        </button>
                      )}
                      <button onClick={() => setShowEpisodeFeedback(true)} className="flex items-center gap-1.5 px-4 py-2.5 rounded-xl text-sm transition-all"
                        style={{ border: '1px solid rgba(255,255,255,0.10)', color: 'rgba(255,255,255,0.7)' }}
                        onMouseOver={(e) => { e.currentTarget.style.background = 'rgba(255,255,255,0.06)' }}
                        onMouseOut={(e) => { e.currentTarget.style.background = 'transparent' }}>
                        <Pencil className="w-4 h-4" /> 修改
                      </button>
                    </div>
                  </div>
                )}
              </div>
            )}
            {awaitingProceed && (
              <div className="p-5 animate-fade-in-up" style={{ borderTop: '1px solid rgba(139,92,246,0.15)', background: 'rgba(255,255,255,0.06)', backdropFilter: 'blur(12px)', WebkitBackdropFilter: 'blur(12px)' }}>
                <div className="max-w-5xl mx-auto flex items-center justify-between">
                  <div className="flex items-center gap-2 text-sm">
                    <Check className="w-4 h-4 text-green-400" />
                    <span className="text-green-400 font-medium">已完成确认</span>
                    <span className="text-muted-foreground">— 准备好后可继续下一步</span>
                  </div>
                  <button onClick={handleProceed} className="flex items-center gap-1.5 px-5 py-2.5 rounded-xl text-sm font-medium transition-all whitespace-nowrap"
                    style={{ background: 'linear-gradient(135deg, rgba(74,222,128,0.25), rgba(52,211,153,0.2))', color: 'rgba(74,222,128,0.95)', border: '1px solid rgba(74,222,128,0.3)' }}>
                    <Play className="w-4 h-4" /> 继续进行下一步
                  </button>
                </div>
              </div>
            )}
           </>
         ) : connected && currentPhase >= 0 && !viewContent ? (
           <><div className="flex-1 flex flex-col overflow-hidden">
              <div className="border-b border-border/30 bg-card/40 backdrop-blur-sm px-8 py-3">
              <div className="max-w-5xl mx-auto flex items-center justify-between gap-4">
                <div className="flex items-center gap-2 text-sm">
                  <span>{PHASE_ICONS[currentPhase] || '📝'}</span>
                  <span className="font-medium">{getPhaseNames(projectConfig?.style_type)[currentPhase] || '生成中...'}</span>
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
             <div className="flex-1 overflow-y-auto p-10">
               <div className="max-w-5xl mx-auto premium-inset p-6">
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
            {awaitingVersion && (
              <div className="p-5 animate-fade-in-up" style={{ borderTop: '1px solid rgba(139,92,246,0.15)', background: 'rgba(255,255,255,0.06)', backdropFilter: 'blur(12px)', WebkitBackdropFilter: 'blur(12px)' }}>
                <div className="max-w-5xl mx-auto">
                  <p className="text-sm font-medium mb-4">🎯 方向卡已生成，请选择版本：</p>
                  {showMixInput ? (
                    <div className="space-y-3">
                      <textarea className="w-full rounded-xl px-4 py-3 h-24 resize-none text-sm" style={{ background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.18)', color: 'rgba(255,255,255,0.85)' }} placeholder="请描述你希望如何混合版本A和版本B..." value={mixFeedback} onChange={e => setMixFeedback(e.target.value)} autoFocus />
                      <div className="flex gap-2">
                        <button onClick={handleVersionMix} className="btn-gradient px-5 py-2 rounded-xl text-sm font-medium"><Sparkles className="w-4 h-4 inline mr-1" />提交混合</button>
                        <button onClick={() => setShowMixInput(false)} className="px-5 py-2 rounded-xl text-sm transition-all"
                          style={{ border: '1px solid rgba(255,255,255,0.10)', color: 'rgba(255,255,255,0.7)' }}
                          onMouseOver={(e) => { e.currentTarget.style.background = 'rgba(255,255,255,0.06)' }}
                          onMouseOut={(e) => { e.currentTarget.style.background = 'transparent' }}>取消</button>
                      </div>
                    </div>
                  ) : (
                    <div className="space-y-3">
                      <textarea className="w-full rounded-xl px-4 py-3 h-24 resize-none text-sm" style={{ background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.18)', color: 'rgba(255,255,255,0.85)' }} placeholder="可选：输入修改要求，选中的版本将根据你的要求重新生成（如：增加第3个角色、把结局改成悲剧、加快节奏...）" value={versionFeedback} onChange={e => setVersionFeedback(e.target.value)} />
                      <div className="flex items-center gap-3">
                        <button onClick={handleVersionA} className="btn-gradient px-6 py-3 rounded-xl text-sm font-medium">版本 A</button>
                        <button onClick={handleVersionB} className="btn-gradient px-6 py-3 rounded-xl text-sm font-medium">版本 B</button>
                        <button onClick={() => setShowMixInput(true)} className="px-5 py-3 rounded-xl border-2 text-sm font-medium transition-all"
                          style={{ borderColor: 'rgba(255,255,255,0.10)', color: 'rgba(255,255,255,0.7)' }}
                          onMouseOver={(e) => { e.currentTarget.style.borderColor = 'rgba(255,255,255,0.25)'; e.currentTarget.style.background = 'rgba(255,255,255,0.06)' }}
                          onMouseOut={(e) => { e.currentTarget.style.borderColor = 'rgba(255,255,255,0.10)'; e.currentTarget.style.background = 'transparent' }}>混合 A + B</button>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            )}
            {awaitingApproval && !isComplete && (
              <div className="p-5 animate-fade-in-up" style={{ borderTop: '1px solid rgba(139,92,246,0.15)', background: 'rgba(255,255,255,0.06)', backdropFilter: 'blur(12px)', WebkitBackdropFilter: 'blur(12px)' }}>
                {showFeedback ? (
                  <div className="max-w-5xl mx-auto space-y-3">
                    <textarea className="w-full bg-muted border border-border rounded-xl px-4 py-3 h-28 resize-none text-sm" placeholder="请输入修改意见..." value={feedbackText} onChange={e => setFeedbackText(e.target.value)} autoFocus />
                    <div className="flex gap-2">
                      <button onClick={handleRevise} className="btn-gradient px-5 py-2 rounded-xl text-sm font-medium"><Pencil className="w-4 h-4 inline mr-1" />提交修改</button>
                      <button onClick={() => setShowFeedback(false)} className="px-5 py-2 rounded-xl text-sm transition-all"
                        style={{ border: '1px solid rgba(255,255,255,0.10)', color: 'rgba(255,255,255,0.7)' }}
                        onMouseOver={(e) => { e.currentTarget.style.background = 'rgba(255,255,255,0.06)' }}
                        onMouseOut={(e) => { e.currentTarget.style.background = 'transparent' }}>取消</button>
                    </div>
                  </div>
                ) : (
                  <div className="max-w-5xl mx-auto flex items-center gap-2">
                    <button onClick={handleApprove} className="flex items-center gap-1.5 px-5 py-2.5 rounded-xl text-sm font-medium transition-all"
                      style={{ background: 'linear-gradient(135deg, rgba(74,222,128,0.25), rgba(52,211,153,0.2))', color: 'rgba(74,222,128,0.95)', border: '1px solid rgba(74,222,128,0.3)' }}>
                      <Check className="w-4 h-4" /> 通过
                    </button>
                    <button onClick={() => setShowFeedback(true)} className="flex items-center gap-1.5 px-4 py-2.5 rounded-xl text-sm transition-all"
                      style={{ border: '1px solid rgba(255,255,255,0.10)', color: 'rgba(255,255,255,0.7)' }}
                      onMouseOver={(e) => { e.currentTarget.style.background = 'rgba(255,255,255,0.06)' }}
                      onMouseOut={(e) => { e.currentTarget.style.background = 'transparent' }}>
                      <Pencil className="w-4 h-4" /> 修改
                    </button>
                    <button onClick={async () => {
                      if (!editingStream) {
                        setStreamDraft(streamContent)
                        setEditingStream(true)
                      } else {
                        if (streamDraft && streamDraft !== streamContent && name) {
                          const dir = PHASE_DIRS[currentPhase]
                          const savePath = `${dir}/${MAIN_FILES[dir] || '产出.md'}`
                          await savePhaseContent(name, savePath, streamDraft)
                        }
                        setEditingStream(false)
                      }
                    }} className="flex items-center gap-1.5 px-4 py-2.5 rounded-xl text-sm transition-all"
                      style={{ color: 'rgba(255,255,255,0.5)' }}
                      onMouseOver={(e) => { e.currentTarget.style.color = 'rgba(255,255,255,0.8)' }}
                      onMouseOut={(e) => { e.currentTarget.style.color = 'rgba(255,255,255,0.5)' }}>
                      <Pencil className="w-4 h-4" /> {editingStream ? '完成编辑' : '编辑'}
                    </button>
                  </div>
                )}
              </div>
            )}
            {awaitingProceed && (
              <div className="p-5 animate-fade-in-up" style={{ borderTop: '1px solid rgba(139,92,246,0.15)', background: 'rgba(255,255,255,0.06)', backdropFilter: 'blur(12px)', WebkitBackdropFilter: 'blur(12px)' }}>
                <div className="max-w-5xl mx-auto flex items-center justify-between">
                  <div className="flex items-center gap-2 text-sm">
                    <Check className="w-4 h-4 text-green-400" />
                    <span className="text-green-400 font-medium">已完成确认</span>
                    <span className="text-muted-foreground">— 准备好后可继续下一步</span>
                  </div>
                  <button onClick={handleProceed} className="flex items-center gap-1.5 px-5 py-2.5 rounded-xl text-sm font-medium transition-all whitespace-nowrap"
                    style={{ background: 'linear-gradient(135deg, rgba(74,222,128,0.25), rgba(52,211,153,0.2))', color: 'rgba(74,222,128,0.95)', border: '1px solid rgba(74,222,128,0.3)' }}>
                    <Play className="w-4 h-4" /> 继续进行下一步
                  </button>
                </div>
              </div>
            )}
            {awaitingEpisodeApproval && currentEpisode && (
              <div className="p-5 animate-fade-in-up" style={{ borderTop: '1px solid rgba(139,92,246,0.15)', background: 'rgba(255,255,255,0.06)', backdropFilter: 'blur(12px)', WebkitBackdropFilter: 'blur(12px)', borderColor: 'hsl(35, 80%, 50%, 0.3)' }}>
                {showEpisodeFeedback ? (
                  <div className="max-w-5xl mx-auto space-y-3">
                    <div className="flex items-center gap-2 text-sm text-amber-400 mb-1">
                      <span className="font-medium">修改第 {currentEpisode.chunk_index + 1} 集</span>
                      <span className="text-muted-foreground">— 输入修改意见后将重新生成</span>
                    </div>
                    <textarea className="w-full bg-muted border border-border rounded-xl px-4 py-3 h-28 resize-none text-sm" placeholder="请输入修改意见..." value={episodeFeedbackText} onChange={e => setEpisodeFeedbackText(e.target.value)} autoFocus />
                    <div className="flex gap-2">
                      <button onClick={() => { episodeRevise(episodeFeedbackText); setShowEpisodeFeedback(false); setEpisodeFeedbackText('') }} className="btn-gradient px-5 py-2 rounded-xl text-sm font-medium">
                        <Pencil className="w-4 h-4 inline mr-1" /> 提交修改
                      </button>
                      <button onClick={() => setShowEpisodeFeedback(false)} className="px-5 py-2 rounded-xl text-sm transition-all"
                        style={{ border: '1px solid rgba(255,255,255,0.10)', color: 'rgba(255,255,255,0.7)' }}
                        onMouseOver={(e) => { e.currentTarget.style.background = 'rgba(255,255,255,0.06)' }}
                        onMouseOut={(e) => { e.currentTarget.style.background = 'transparent' }}>取消</button>
                    </div>
                  </div>
                ) : (
                  <div className="max-w-5xl mx-auto">
                    <div className="flex items-center gap-2 text-sm text-amber-400 mb-3">
                      <span className="w-1.5 h-1.5 rounded-full bg-amber-400 animate-pulse" />
                      <span className="font-medium">第 {currentEpisode.chunk_index + 1}/{currentEpisode.total_chunks} 集已生成</span>
                      <span className="text-muted-foreground">— 请选择下一步操作</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <button onClick={() => episodeConfirm(currentEpisode?.phase_index)} className="flex items-center gap-1.5 px-5 py-2.5 rounded-xl text-sm font-medium transition-all border-2 border-primary/40 text-primary hover:bg-primary/5">
                        <Check className="w-4 h-4" /> 完成
                      </button>
                      <button onClick={() => setShowEpisodeFeedback(true)} className="flex items-center gap-1.5 px-4 py-2.5 rounded-xl text-sm transition-all"
                        style={{ border: '1px solid rgba(255,255,255,0.10)', color: 'rgba(255,255,255,0.7)' }}
                        onMouseOver={(e) => { e.currentTarget.style.background = 'rgba(255,255,255,0.06)' }}
                        onMouseOut={(e) => { e.currentTarget.style.background = 'transparent' }}>
                        <Pencil className="w-4 h-4" /> 修改
                      </button>
                    </div>
                  </div>
                )}
              </div>
            )}
            {contentWarnings.length > 0 && (
              <div className="border-t border-border/50 p-4 bg-card/80 backdrop-blur-sm">
                <div className="max-w-5xl mx-auto">
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
           </div>
           </>
         ) : continuing ? (
           <div className="flex-1 flex flex-col overflow-hidden">
             <div className="border-b border-border/30 bg-card/40 backdrop-blur-sm px-8 py-3">
               <div className="max-w-5xl mx-auto flex items-center justify-between gap-4">
                 <div className="flex items-center gap-2 text-sm">
                   <span>{PHASE_ICONS[currentPhase] || '📝'}</span>
                   <span className="font-medium">{getPhaseNames(projectConfig?.style_type)[currentPhase] || '生成中...'}</span>
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
             <div className="flex-1 overflow-y-auto p-10">
               <div className="max-w-5xl mx-auto premium-inset p-6">
                 {!streamContent ? (
                   <div className="flex flex-col items-center justify-center gap-4 py-20">
                     <div className="w-10 h-10 border-2 border-primary border-t-transparent rounded-full animate-spin" />
                     <p className="text-muted-foreground text-sm">{projectRunning ? '后台任务正在运行，等待数据...' : '正在启动生成...'}</p>
                     <p className="text-xs text-amber-400/70 animate-pulse">{projectRunning ? '数据到达后将自动显示' : '请勿关闭网页，生成过程需一定时间'}</p>
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
              <h3 className="font-bold text-lg mb-1">🔄 重新生成 {getPhaseNames(projectConfig?.style_type)[redoPhaseIndex]}</h3>
              <p className="text-sm text-muted-foreground mb-4">可选填修改意见，留空则按原风格重新生成</p>
              <textarea className="w-full bg-muted border border-border rounded-xl px-4 py-3 h-28 resize-none text-sm mb-4"
                placeholder="例如：动作描写再详细一些 / 场景布局写清楚 / 节奏放慢一点..."
                value={redoInstruction} onChange={e => setRedoInstruction(e.target.value)} autoFocus />
              <div className="flex justify-end gap-3">
                <button onClick={() => setShowRedoInput(false)} className="px-5 py-2.5 rounded-xl text-sm transition-all"
                  style={{ border: '1px solid rgba(255,255,255,0.10)', color: 'rgba(255,255,255,0.7)' }}
                  onMouseOver={(e) => { e.currentTarget.style.background = 'rgba(255,255,255,0.06)' }}
                  onMouseOut={(e) => { e.currentTarget.style.background = 'transparent' }}>取消</button>
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

