import { ArrowLeft, Eye, ChevronDown, FolderOpen, Sparkles, RefreshCw } from 'lucide-react'
import type { ChunkInfo } from '../hooks/useWebSocket'

const PHASE_NAMES = ['故事大纲', '完整剧情', '完整剧本', '分镜脚本', '视觉提取', '提示词生成']
const PHASE_ICONS = ['📋', '📖', '🎭', '🎬', '🔍', '💬']

interface PhaseData {
  done: boolean
}

interface Props {
  name: string
  projectConfig: { genre?: string; phases?: PhaseData[] } | null
  phases: { status?: string }[]
  currentPhase: number
  streamContent: string
  suppressStream: boolean
  confirmedPhases: number[]
  selectedPhase: number
  expandedPhase: number
  actFileList: string[]
  selectedAct: string
  showStream: boolean
  connected: boolean
  autoApprove: boolean
  chunksCompleted: Record<number, ChunkInfo[]>
  onNavigate: (path: string) => void
  onOpenFolder: () => void
  onShowTemplateModal: () => void
  onViewPhase: (index: number) => void
  onViewAct: (phaseIndex: number, act: string) => void
  onSetExpandedPhase: (index: number) => void
  onRedo: (index: number) => void
  onAutoApproveChange: (value: boolean) => void
}

export default function PhaseTimeline({
  name, projectConfig, phases, currentPhase, streamContent, suppressStream,
  confirmedPhases, selectedPhase, expandedPhase, actFileList, selectedAct, showStream,
  connected, autoApprove, chunksCompleted, onNavigate, onOpenFolder, onShowTemplateModal,
  onViewPhase, onViewAct, onSetExpandedPhase, onRedo, onAutoApproveChange,
}: Props) {
  const phaseStatus = (index: number) => {
    if (index === currentPhase && streamContent && !suppressStream) return 'active'
    if (projectConfig?.phases?.[index]?.done || phases[index]?.status === 'done') return 'done'
    if (confirmedPhases.includes(index)) return 'done'
    return 'pending'
  }

  const activePhaseCount = PHASE_NAMES.length
  const donePhaseCount = (projectConfig?.phases || []).filter((p: any) => p.done).length

  return (
    <aside className="w-64 border-r border-border bg-card/80 backdrop-blur-sm flex flex-col relative z-10">
      <div className="p-5 border-b border-border/50">
        <button onClick={() => onNavigate('/')} className="flex items-center gap-1.5 text-muted-foreground hover:text-foreground text-sm mb-3 transition-colors">
          <ArrowLeft className="w-4 h-4" /> 返回首页
        </button>
        <div className="flex items-center justify-between">
          <h2 className="font-bold truncate">{name}</h2>
          <div className="flex items-center gap-1">
            <button onClick={onShowTemplateModal}
              className="flex items-center gap-1 px-2 py-1.5 rounded-lg border border-border hover:bg-muted text-[10px] text-muted-foreground hover:text-foreground transition-all" title="将当前项目的风格配置保存为模板">
              <Sparkles className="w-3 h-3" /> 存为模板
            </button>
            <button onClick={onOpenFolder} className="p-1.5 rounded-lg hover:bg-muted text-muted-foreground hover:text-foreground transition-all" title="打开文件夹">
              <FolderOpen className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
        {projectConfig?.genre && <p className="text-xs text-muted-foreground mt-1">{projectConfig.genre}</p>}
      </div>

      <div className="flex-1 p-3 space-y-0.5 overflow-y-auto">
        {PHASE_NAMES.map((pname, i) => {
          const s = phaseStatus(i)
          const isSelected = selectedPhase === i && !showStream
          const canView = s === 'done'
          const hasActs = isSelected && actFileList.length > 1
          return (
            <div key={i} className="animate-fade-in-up" style={{ animationDelay: `${i * 0.06}s`, opacity: 0 }}>
              <button
                onClick={() => { if (canView) { onViewPhase(i); onSetExpandedPhase(expandedPhase === i ? -1 : i) } }}
                disabled={!canView}
                className={`group w-full flex items-center gap-2.5 px-3 py-2.5 rounded-xl text-sm text-left transition-all duration-200 ${
                  isSelected ? 'bg-primary/15 text-primary font-medium'
                  : s === 'active' ? 'bg-primary/5 text-primary animate-shimmer'
                  : s === 'done' ? 'text-green-400 hover:bg-green-400/5 cursor-pointer'
                  : 'text-muted-foreground cursor-default'
                }`}
              >
                <span className="text-sm flex-shrink-0">{PHASE_ICONS[i]}</span>
                <span className="flex-1">{pname}</span>
                {s === 'active' && <div className="w-1.5 h-1.5 rounded-full bg-primary animate-ping flex-shrink-0" />}
                {s === 'done' && <div className="w-1.5 h-1.5 rounded-full bg-green-400 flex-shrink-0" />}
                {s !== 'active' && s !== 'done' && chunksCompleted[i]?.length > 0 && (
                  <div className="w-1.5 h-1.5 rounded-full bg-green-400 flex-shrink-0" />
                )}
                {canView && (isSelected && hasActs ? <ChevronDown className="w-3.5 h-3.5 opacity-60 flex-shrink-0" /> : <Eye className="w-3.5 h-3.5 opacity-0 group-hover:opacity-50 flex-shrink-0 transition-opacity" />)}
                {s === 'done' && (
                  <button
                    onClick={(e) => { e.stopPropagation(); onRedo(i) }}
                    className="p-1 rounded-md hover:bg-orange-400/10 text-muted-foreground hover:text-orange-400 opacity-0 group-hover:opacity-100 flex-shrink-0 transition-all"
                    title="重新生成"
                  >
                    <RefreshCw className="w-3 h-3" />
                  </button>
                )}
              </button>

              {isSelected && hasActs && actFileList.length > 1 && (
                <div className="ml-8 mt-0.5 mb-1 space-y-0.5 border-l-2 border-primary/20 pl-3 animate-fade-in">
                  <button onClick={() => onViewAct(i, '')} className={`w-full text-left text-xs px-2.5 py-1.5 rounded-lg transition-all ${selectedAct === '' ? 'text-primary bg-primary/10 font-medium' : 'text-muted-foreground hover:text-foreground hover:bg-muted'}`}>
                    完整内容
                  </button>
                  {actFileList.map((act) => (
                    <button key={act} onClick={(e) => { e.stopPropagation(); onViewAct(i, act) }}
                      className={`w-full text-left text-xs px-2.5 py-1.5 rounded-lg transition-all ${selectedAct === act ? 'text-primary bg-primary/10 font-medium' : 'text-muted-foreground hover:text-foreground hover:bg-muted'}`}>
                      {act.replace(/^\d+_/, '').replace(/\.md$/, '').replace(/_/g, '')}
                    </button>
                  ))}
                </div>
              )}
              {/* 分集进度展示 */}
              {chunksCompleted[i]?.length > 0 && i !== selectedPhase && i === currentPhase && (
                <div className="ml-8 mt-1 mb-1 space-y-0.5 border-l-2 border-primary/20 pl-3">
                  {Array.from({ length: chunksCompleted[i][0]?.total || 1 }, (_, idx) => {
                    const done = chunksCompleted[i].find(c => c.index === idx)
                    return (
                      <div key={idx} className="flex items-center gap-1.5 text-xs px-2.5 py-1 rounded-lg text-muted-foreground">
                        <button
                          onClick={() => { if (done) { onViewAct(i, ''); onSetExpandedPhase(i) } }}
                          className={`w-full text-left truncate transition-all ${done ? 'hover:text-green-400 cursor-pointer' : 'cursor-default'}`}
                        >
                          {done ? (
                            <span className="text-green-400">✅ 第{idx + 1}集</span>
                          ) : (
                            <span className="text-muted-foreground">⏳ 第{idx + 1}集</span>
                          )}
                        </button>
                      </div>
                    )
                  })}
                </div>
              )}
            </div>
          )
        })}
      </div>

      <div className="p-4 border-t border-border/50 space-y-3">
        <label className="flex items-center justify-between gap-2 cursor-pointer">
          <span className="text-xs text-muted-foreground">自动审核（逐阶段）</span>
          <div className="relative inline-flex items-center cursor-pointer">
            <input type="checkbox" className="sr-only peer" checked={autoApprove}
              onChange={(e) => onAutoApproveChange(e.target.checked)} />
            <div className="w-8 h-4 bg-muted rounded-full peer peer-checked:bg-green-500/60 peer-checked:after:translate-x-4 after:content-[''] after:absolute after:top-0.5 after:start-0.5 after:bg-white after:rounded-full after:h-3 after:w-3 after:transition-all" />
          </div>
        </label>
        <div>
          <div className="flex justify-between text-xs text-muted-foreground mb-1.5">
            <span>总进度</span>
            <span>{donePhaseCount}/{activePhaseCount}</span>
          </div>
          <div className="w-full h-1.5 bg-muted rounded-full overflow-hidden">
            <div className="h-full rounded-full transition-all duration-500 progress-glow"
              style={{ width: `${(donePhaseCount / activePhaseCount) * 100}%`, background: 'linear-gradient(90deg, hsl(var(--primary)), hsl(265, 87%, 60%))' }} />
          </div>
        </div>
      </div>
    </aside>
  )
}
