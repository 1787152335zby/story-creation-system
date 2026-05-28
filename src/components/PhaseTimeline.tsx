import { ArrowLeft, Eye, ChevronDown, FolderOpen, Sparkles, RefreshCw, Pencil } from 'lucide-react'
import type { ChunkInfo } from '../hooks/useWebSocket'
import { renameProject } from '../lib/api'
import { getPhaseNames, PHASE_ICONS } from '../lib/constants'

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

  const activePhaseCount = getPhaseNames(projectConfig?.style_type).length
  const donePhaseCount = (projectConfig?.phases || []).filter((p: any) => p.done).length

  return (
    <aside className="w-64 border-r flex flex-col relative z-10 premium-subpanel premium-panel-rich" style={{ borderColor: 'rgba(255,255,255,0.18)', background: 'rgba(255,255,255,0.08)', backdropFilter: 'blur(24px)', WebkitBackdropFilter: 'blur(24px)' }}>
      {/* Decorative layers matching homepage cards */}
      <div className="wp-border" style={{ borderRadius: 0 }} />
      <div className="wp-bottom-glow" />
      <div className="p-5" style={{ borderBottom: '1px solid rgba(255,255,255,0.15)' }}>
        <button onClick={() => onNavigate('/home')} className="flex items-center gap-1.5 text-sm mb-3 transition-colors" style={{ color: 'rgba(255,255,255,0.60)' }}>
          <ArrowLeft className="w-4 h-4" /> 返回首页
        </button>
        <div className="flex items-center justify-between">
          <h2 className="font-bold truncate" style={{ color: 'rgba(255,255,255,0.90)' }}>{name}</h2>
          <div className="flex items-center gap-1">
            <button onClick={() => {
              const newName = prompt('输入新项目名称：', name)
              if (newName && newName.trim() && newName.trim() !== name) {
                renameProject(name, newName.trim()).then(() => window.location.reload())
              }
            }} className="p-1.5 rounded-lg transition-all" style={{ background: 'transparent', color: 'rgba(255,255,255,0.50)' }}
              onMouseOver={(e) => { e.currentTarget.style.background = 'rgba(255,255,255,0.07)'; e.currentTarget.style.color = 'rgba(255,255,255,0.80)' }}
              onMouseOut={(e) => { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.color = 'rgba(255,255,255,0.50)' }}
              title="重命名项目">
              <Pencil className="w-3.5 h-3.5" />
            </button>
            <button onClick={onShowTemplateModal}
              className="flex items-center gap-1 px-2 py-1.5 rounded-lg border transition-all text-[10px]"
              style={{ borderColor: 'rgba(255,255,255,0.18)', color: 'rgba(255,255,255,0.50)' }}
              onMouseOver={(e) => { e.currentTarget.style.background = 'rgba(255,255,255,0.07)'; e.currentTarget.style.color = 'rgba(255,255,255,0.80)' }}
              onMouseOut={(e) => { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.color = 'rgba(255,255,255,0.50)' }}
              title="将当前项目的风格配置保存为模板">
              <Sparkles className="w-3 h-3" /> 存为模板
            </button>
            <button onClick={onOpenFolder} className="p-1.5 rounded-lg transition-all" style={{ color: 'rgba(255,255,255,0.50)' }}
              onMouseOver={(e) => { e.currentTarget.style.background = 'rgba(255,255,255,0.07)'; e.currentTarget.style.color = 'rgba(255,255,255,0.80)' }}
              onMouseOut={(e) => { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.color = 'rgba(255,255,255,0.50)' }}
              title="打开文件夹">
              <FolderOpen className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
        {projectConfig?.genre && <p className="text-xs mt-1" style={{ color: 'rgba(255,255,255,0.45)' }}>{projectConfig.genre}</p>}
      </div>

      <div className="flex-1 p-3 space-y-0.5 overflow-y-auto">
        {getPhaseNames(projectConfig?.style_type).map((pname, i) => {
          const s = phaseStatus(i)
          const isSelected = selectedPhase === i && !showStream
          const canView = s === 'done'
          const hasActs = isSelected && actFileList.length > 1
          return (
            <div key={i} className="animate-fade-in-up" style={{ animationDelay: `${i * 0.06}s`, opacity: 0 }}>
              <button
                onClick={() => { if (canView) { onViewPhase(i); onSetExpandedPhase(expandedPhase === i ? -1 : i) } }}
                disabled={!canView}
                className={`group w-full flex items-center gap-2.5 px-3 py-2.5 rounded-xl text-sm text-left transition-all duration-200`}
                style={{
                  background: isSelected ? 'rgba(167,139,250,0.10)' : s === 'active' ? 'rgba(255,255,255,0.08)' : 'transparent',
                  borderLeft: s === 'done' ? '2px solid rgba(74,222,128,0.4)' : s === 'active' ? '2px solid rgba(167,139,250,0.6)' : '2px solid transparent',
                  color: isSelected ? 'rgba(255,255,255,0.95)' : s === 'active' ? 'rgba(255,255,255,0.85)' : s === 'done' ? 'rgba(255,255,255,0.75)' : 'rgba(255,255,255,0.40)',
                  fontWeight: isSelected || s === 'active' ? 500 : 400,
                  cursor: canView ? 'pointer' : 'default'
                }}
                onMouseOver={(e) => {
                  if (s === 'done' && !isSelected) {
                    e.currentTarget.style.background = 'rgba(255,255,255,0.07)';
                  }
                }}
                onMouseOut={(e) => {
                  if (!isSelected && s !== 'active') {
                    e.currentTarget.style.background = 'transparent';
                  }
                }}
              >
                <span className="text-sm flex-shrink-0">{PHASE_ICONS[i]}</span>
                <span className="flex-1">{pname}</span>
                {s === 'active' && <div className="w-1.5 h-1.5 rounded-full flex-shrink-0 animate-ping" style={{ background: 'linear-gradient(135deg, hsl(var(--primary)), hsl(265, 87%, 60%))' }} />}
                {s === 'done' && <div className="w-1.5 h-1.5 rounded-full bg-green-400 flex-shrink-0" />}
                {s !== 'active' && s !== 'done' && chunksCompleted[i]?.length > 0 && (
                  <div className="w-1.5 h-1.5 rounded-full bg-green-400 flex-shrink-0" />
                )}
                {canView && (isSelected && hasActs ? <ChevronDown className="w-3.5 h-3.5 opacity-60 flex-shrink-0" /> : <Eye className="w-3.5 h-3.5 opacity-0 group-hover:opacity-60 flex-shrink-0 transition-opacity" />)}
                {s === 'done' && (
                  <button
                    onClick={(e) => { e.stopPropagation(); onRedo(i) }}
                    className="p-1 rounded-md text-muted-foreground hover:text-orange-400 opacity-0 group-hover:opacity-100 flex-shrink-0 transition-all"
                    style={{ color: 'rgba(255,255,255,0.40)' }}
                    onMouseOver={(e) => { e.currentTarget.style.background = 'rgba(255,165,0,0.10)'; e.currentTarget.style.color = 'rgba(255,165,0,0.80)' }}
                    onMouseOut={(e) => { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.color = 'rgba(255,255,255,0.40)' }}
                    title="重新生成"
                  >
                    <RefreshCw className="w-3 h-3" />
                  </button>
                )}
              </button>

              {isSelected && hasActs && actFileList.length > 1 && (
                <div className="ml-8 mt-0.5 mb-1 space-y-0.5 pl-3 animate-fade-in" style={{ borderLeft: '2px solid rgba(255,255,255,0.25)' }}>
                  <button onClick={() => onViewAct(i, '')} className="w-full text-left text-xs px-2.5 py-1.5 rounded-lg transition-all"
                    style={{
                      background: selectedAct === '' ? 'rgba(255,255,255,0.12)' : 'transparent',
                      color: selectedAct === '' ? 'rgba(255,255,255,0.90)' : 'rgba(255,255,255,0.50)',
                      fontWeight: selectedAct === '' ? 500 : 400
                    }}
                    onMouseOver={(e) => {
                      if (selectedAct !== '') {
                        e.currentTarget.style.background = 'rgba(255,255,255,0.07)';
                        e.currentTarget.style.color = 'rgba(255,255,255,0.80)';
                      }
                    }}
                    onMouseOut={(e) => {
                      if (selectedAct !== '') {
                        e.currentTarget.style.background = 'transparent';
                        e.currentTarget.style.color = 'rgba(255,255,255,0.50)';
                      }
                    }}
                  >
                    📄 完整内容
                  </button>
                  {actFileList.map((act) => (
                    <button key={act} onClick={(e) => { e.stopPropagation(); onViewAct(i, act) }}
                      className="w-full text-left text-xs px-2.5 py-1.5 rounded-lg transition-all"
                      style={{
                        background: selectedAct === act ? 'rgba(255,255,255,0.12)' : 'transparent',
                        color: selectedAct === act ? 'rgba(255,255,255,0.90)' : 'rgba(255,255,255,0.50)',
                        fontWeight: selectedAct === act ? 500 : 400
                      }}
                      onMouseOver={(e) => {
                        if (selectedAct !== act) {
                          e.currentTarget.style.background = 'rgba(255,255,255,0.07)';
                          e.currentTarget.style.color = 'rgba(255,255,255,0.80)';
                        }
                      }}
                      onMouseOut={(e) => {
                        if (selectedAct !== act) {
                          e.currentTarget.style.background = 'transparent';
                          e.currentTarget.style.color = 'rgba(255,255,255,0.50)';
                        }
                      }}
                    >
                      {act.includes('/') ? `✅ ${act.split('/')[0]}` : act.includes('第') ? `✅ ${act.replace(/\.md$/, '').replace(/.*_第/, '第')}` : act.replace(/^\d+_/, '').replace(/\.md$/, '').replace(/_/g, '')}
                    </button>
                  ))}
                </div>
              )}
            </div>
          )
        })}
      </div>

      <div className="p-4 space-y-3" style={{ borderTop: '1px solid rgba(255,255,255,0.15)' }}>
        <label className="flex items-center justify-between gap-2 cursor-pointer">
          <span className="text-xs" style={{ color: 'rgba(255,255,255,0.50)' }}>自动审核</span>
          <div className="relative inline-flex items-center cursor-pointer">
            <input type="checkbox" className="sr-only peer" checked={autoApprove}
              onChange={(e) => onAutoApproveChange(e.target.checked)} />
            <div className="w-8 h-4 rounded-full peer peer-checked:after:translate-x-4 after:content-[''] after:absolute after:top-0.5 after:start-0.5 after:bg-white after:rounded-full after:h-3 after:w-3 after:transition-all"
              style={{ background: autoApprove ? 'rgba(74,222,128,0.60)' : 'rgba(255,255,255,0.08)' }}
            />
          </div>
        </label>
        <div>
          <div className="flex justify-between text-xs mb-1.5" style={{ color: 'rgba(255,255,255,0.50)' }}>
            <span>总进度</span>
            <span>{donePhaseCount}/{activePhaseCount}</span>
          </div>
          <div className="w-full h-1.5 rounded-full overflow-hidden" style={{ background: 'rgba(255,255,255,0.08)' }}>
            <div className="h-full rounded-full transition-all duration-500"
              style={{ width: `${(donePhaseCount / activePhaseCount) * 100}%`, background: 'linear-gradient(90deg, hsl(var(--primary)), hsl(265, 87%, 60%))', boxShadow: '0 0 12px rgba(255,255,255,0.25)' }} />
          </div>
        </div>
      </div>
    </aside>
  )
}
