import { useState } from 'react'
import { Play, Check, X, Loader2, Pencil, RefreshCw, Sparkles } from 'lucide-react'

export interface Shot {
  index: number
  act: string
  scene: string
  prompt: string
  status: 'pending' | 'generating' | 'done' | 'failed'
  videoUrl?: string
  error?: string
}

interface Props {
  shots: Shot[]
  onGenerateAll: () => void
  onGenerateOne: (index: number) => void
  onRegenerate: (index: number) => void
  onEditPrompt: (index: number, newPrompt: string) => void
  onExport: (index: number) => void
  onConcat: () => void
}

export default function ShotListView({
  shots, onGenerateAll, onGenerateOne, onRegenerate,
  onEditPrompt, onExport, onConcat,
}: Props) {
  const [editingIndex, setEditingIndex] = useState<number | null>(null)
  const [editText, setEditText] = useState('')

  const groups: Record<string, Shot[]> = {}
  for (const s of shots) {
    if (!groups[s.act]) groups[s.act] = []
    groups[s.act].push(s)
  }

  const doneCount = shots.filter(s => s.status === 'done').length
  const failCount = shots.filter(s => s.status === 'failed').length
  const genCount = shots.filter(s => s.status === 'generating').length

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="glass-card rounded-2xl p-5">
        <div className="flex items-center gap-3">
          <button onClick={onGenerateAll} disabled={genCount > 0}
            className="btn-gradient flex items-center gap-1.5 px-5 py-2.5 rounded-xl text-sm font-medium disabled:opacity-50">
            {genCount > 0 ? <Loader2 className="w-4 h-4 animate-spin" /> : <Sparkles className="w-4 h-4" />}
            {genCount > 0 ? `生成中 (${genCount})` : '批量生成全部'}
          </button>
          <button onClick={onConcat} className="px-5 py-2.5 rounded-xl border border-border text-sm hover:bg-muted transition-colors">
            拼接成片
          </button>
          <span className="text-xs text-muted-foreground ml-auto">
            已完成 {doneCount}/{shots.length}
            {failCount > 0 && <span className="text-red-400 ml-2">失败 {failCount}</span>}
            {genCount > 0 && <span className="text-primary ml-2">生成中 {genCount}</span>}
          </span>
        </div>
      </div>

      {Object.entries(groups).map(([act, actShots]) => (
        <div key={act} className="glass-card rounded-2xl p-4">
          <h3 className="text-sm font-semibold mb-3 flex items-center gap-2">
            <span>{act}</span>
            <span className="text-[10px] text-muted-foreground font-normal">
              ({actShots.filter(s => s.status === 'done').length}/{actShots.length})
            </span>
          </h3>
          <div className="space-y-2">
            {actShots.map(shot => (
              <div key={shot.index}
                className={`p-3 rounded-xl border transition-all ${getStatusBorder(shot.status)}`}>
                <div className="flex items-start justify-between gap-3">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-xs font-medium text-muted-foreground">镜头{shot.index}</span>
                      {renderStatusBadge(shot.status)}
                    </div>
                    {editingIndex === shot.index ? (
                      <textarea className="w-full bg-muted border border-border rounded-lg px-3 py-2 text-xs h-20 resize-none focus:outline-none focus:border-primary/50"
                        value={editText} onChange={e => setEditText(e.target.value)} autoFocus />
                    ) : (
                      <p className="text-xs text-muted-foreground line-clamp-2">{shot.prompt}</p>
                    )}
                    {shot.error && <p className="text-xs text-red-400 mt-1">❌ {shot.error}</p>}
                  </div>
                  <div className="flex items-center gap-1 flex-shrink-0">
                    {shot.status === 'done' && shot.videoUrl && (
                      <video src={shot.videoUrl} className="w-16 h-12 object-cover rounded-lg" preload="metadata" />
                    )}
                    {editingIndex === shot.index ? (
                      <>
                        <button onClick={() => { onEditPrompt(shot.index, editText); setEditingIndex(null) }}
                          className="p-1.5 rounded-lg bg-primary/20 text-primary text-xs font-medium">保存</button>
                        <button onClick={() => setEditingIndex(null)}
                          className="p-1.5 rounded-lg border border-border text-xs">取消</button>
                      </>
                    ) : (
                      <>
                        {shot.status === 'pending' && (
                          <button onClick={() => onGenerateOne(shot.index)}
                            className="p-1.5 rounded-lg border border-border hover:bg-muted transition-colors" title="生成">
                            <Play className="w-3 h-3" />
                          </button>
                        )}
                        {shot.status === 'done' && (
                          <button onClick={() => onRegenerate(shot.index)}
                            className="p-1.5 rounded-lg border border-border hover:bg-muted transition-colors" title="重新生成">
                            <RefreshCw className="w-3 h-3" />
                          </button>
                        )}
                        {shot.status === 'failed' && (
                          <button onClick={() => onGenerateOne(shot.index)}
                            className="p-1.5 rounded-lg border border-red-400/30 text-red-400 hover:bg-red-400/5 transition-colors" title="重试">
                            <RefreshCw className="w-3 h-3" />
                          </button>
                        )}
                        <button onClick={() => { setEditingIndex(shot.index); setEditText(shot.prompt) }}
                          className="p-1.5 rounded-lg border border-border hover:bg-muted transition-colors" title="编辑提示词">
                          <Pencil className="w-3 h-3" />
                        </button>
                      </>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  )
}

function getStatusBorder(status: string): string {
  switch (status) {
    case 'done': return 'border-green-400/30 bg-green-400/5'
    case 'generating': return 'border-primary/30 bg-primary/5 animate-pulse'
    case 'failed': return 'border-red-400/30 bg-red-400/5'
    default: return 'border-border'
  }
}

function renderStatusBadge(status: string) {
  switch (status) {
    case 'done': return <span className="text-[10px] px-1.5 py-0.5 rounded bg-green-400/10 text-green-400 font-medium">✅ 已生成</span>
    case 'generating': return <span className="text-[10px] px-1.5 py-0.5 rounded bg-primary/10 text-primary font-medium"><Loader2 className="w-2.5 h-2.5 inline animate-spin" /> 生成中</span>
    case 'failed': return <span className="text-[10px] px-1.5 py-0.5 rounded bg-red-400/10 text-red-400 font-medium">❌ 失败</span>
    default: return <span className="text-[10px] px-1.5 py-0.5 rounded bg-muted text-muted-foreground">待生成</span>
  }
}
