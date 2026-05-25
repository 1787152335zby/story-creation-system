import { useEffect, useState, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import { Sparkles, ArrowRight, Search, Plus, Loader2, Pencil, Check, X, FolderOpen, Trash2 } from 'lucide-react'
import ConfirmModal from '../components/ConfirmModal'
import { fetchProjects, deleteProject, openProjectFolder, renameProject, fetchProjectImages, fetchVideoClips } from '../lib/api'
import { useToast } from '../components/Toast'
import type { ProjectInfo } from '../lib/types'
import { getPhaseNames } from '../lib/constants'

export default function HomePage() {
  const navigate = useNavigate()
  const { toast } = useToast()
  const [projects, setProjects] = useState<ProjectInfo[]>([])
  const [loading, setLoading] = useState(true)
  const [deleteTarget, setDeleteTarget] = useState<string | null>(null)
  const [searchText, setSearchText] = useState('')
  const [renaming, setRenaming] = useState<string | null>(null)
  const [renameInput, setRenameInput] = useState('')

  const filteredProjects = useMemo(() => {
    if (!searchText.trim()) return projects
    const q = searchText.trim().toLowerCase()
    return projects.filter(p => p.name?.toLowerCase().includes(q))
  }, [projects, searchText])

  const load = async () => {
    try { setProjects(await fetchProjects()) } catch (e) { toast('加载失败', 'error') }
    finally { setLoading(false) }
  }

  useEffect(() => { load() }, [])

  useEffect(() => {
    if (!projects.some(p => p.running)) return
    const timer = setInterval(() => { fetchProjects().then(setProjects).catch(() => {}) }, 3000)
    return () => clearInterval(timer)
  }, [projects])

  const handleRename = async (old: string) => {
    if (!renameInput.trim() || renameInput.trim() === old) { setRenaming(null); return }
    try { await renameProject(old, renameInput.trim()); toast('已重命名', 'success'); setRenaming(null); load() }
    catch (e: any) { toast(e.message || '失败', 'error') }
  }

  const doneCount = projects.filter(p => {
    const names = getPhaseNames(p.style_type)
    return (p.phases || []).slice(0, names.length).filter((ph: any) => ph.done).length >= names.length
  }).length

  return (
    <div className="px-6 py-16 max-w-4xl mx-auto">
      {/* Hero */}
      <div className="text-center mb-20 animate-fade-in-up">
        <h1 className="text-[clamp(36px,7vw,64px)] font-black tracking-[-0.04em] leading-none mb-4"
          style={{
            background: 'linear-gradient(180deg, rgba(255,255,255,0.95) 0%, rgba(255,255,255,0.55) 100%)',
            WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent', backgroundClip: 'text',
          }}>
          从灵感到银幕
        </h1>
        <p className="text-sm text-white/15 tracking-wider">AI-Powered Story Creation</p>
      </div>

      {/* Glass panels */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-20 animate-fade-in-up delay-100">
        {[
          { label: '开始创作', desc: '输入想法，AI 全流程自动创作', path: '/new', primary: true },
          { label: '智能生图', desc: '角色 · 场景 · 道具', path: '/image-gen' },
          { label: '视频生成', desc: '图生视频 · 拼接成片', path: '/video-gen' },
          { label: '创作历史', desc: '浏览已生成内容', path: '/history' },
        ].map(item => (
          <button key={item.label} onClick={() => navigate(item.path)}
            className={`group relative p-6 rounded-2xl border text-left transition-all duration-300
              glass-surface-visible border-white/[0.08]
              ${item.primary ? 'premium-card' : 'glow-border'} shimmer-hover`}>
            <div className={`relative ${item.primary ? 'card-inner' : 'z-[1]'}`}>
              <div className="text-[13px] font-semibold text-white/85 mb-1.5">{item.label}</div>
              <div className="text-[11px] leading-relaxed text-white/25">{item.desc}</div>
            </div>
          </button>
        ))}
      </div>

      {/* Projects */}
      <div className="animate-fade-in-up delay-200">
        <div className="flex items-end justify-between mb-8">
          <div>
            <div className="text-[10px] text-white/10 tracking-[0.15em] uppercase mb-2">Projects</div>
            <div className="flex items-center gap-3">
              <h2 className="text-lg font-semibold text-white/40">项目列表</h2>
              <span className="text-xs text-white/10">{filteredProjects.length}/{projects.length}</span>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <div className="relative w-40">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-3 h-3 text-white/10" />
              <input value={searchText} onChange={e => setSearchText(e.target.value)}
                placeholder="搜索..."
                className="w-full bg-transparent border-b border-white/[0.03] pb-2 pt-1 pl-8 pr-2 text-xs text-white/40 placeholder:text-white/06 focus:outline-none focus:border-white/[0.1] transition-all" />
            </div>
            <button onClick={() => navigate('/new')}
              className="flex items-center gap-1.5 px-4 py-2 rounded-xl border border-white/[0.06] text-[11px] text-white/25 hover:text-white/50 hover:border-white/[0.12] transition-all">
              <Plus className="w-3 h-3" /> 新建
            </button>
          </div>
        </div>

        {loading ? (
          <div className="space-y-0">
            {[1,2,3,4].map(i => (
              <div key={i} className="py-5 border-b border-white/[0.02]">
                <div className="skeleton h-4 w-48" />
              </div>
            ))}
          </div>
        ) : filteredProjects.length === 0 ? (
          <div className="py-24 text-center">
            <p className="text-white/10 text-sm mb-2">还没有项目</p>
            <p className="text-white/06 text-xs mb-8">输入一个故事想法，开始你的第一次创作</p>
            <button onClick={() => navigate('/new')}
              className="inline-flex items-center gap-2 px-6 py-3 rounded-2xl bg-white text-black text-sm font-semibold hover:bg-white/90 transition-all">
              <Sparkles className="w-4 h-4" /> 开始创作
            </button>
          </div>
        ) : (
          <div className="space-y-2">
            {filteredProjects.slice(0, 10).map(p => {
              const names = getPhaseNames(p.style_type)
              const done = (p.phases || []).slice(0, names.length).filter((ph: any) => ph.done).length
              const total = names.length
              const pct = total > 0 ? (done / total) * 100 : 0
              return (
                <div key={p.name}
                  className={`group relative flex items-center gap-4 px-5 py-4 rounded-2xl border cursor-pointer transition-all duration-300 ${
                    done >= total 
                      ? 'glass-surface-visible glow-border selected border-green-400/20' 
                      : 'glass-surface-visible border border-white/[0.08] glow-border hover:bg-white/[0.12] hover:border-white/[0.14]'
                  }`}
                  style={done >= total ? {
                    background: 'rgba(52,211,153,0.08)',
                    border: '1px solid rgba(52,211,153,0.25)'
                  } : {}}
                  onClick={() => { if (renaming !== p.name) navigate(`/project/${encodeURIComponent(p.name)}`) }}>
                  {/* Status dot */}
                  <div className={`w-2.5 h-2.5 rounded-full flex-shrink-0 ${
                    p.running ? 'bg-green-400/80 animate-pulse' :
                    done >= total ? 'bg-green-400/90 shadow-[0_0_8px_rgba(52,211,153,0.6)]' :
                    p.pending_approval ? 'bg-amber-400/60' :
                    done > 0 ? 'bg-indigo-400/40' : 'bg-white/10'
                  }`} />

                  {/* Name */}
                  <div className="flex-1 min-w-0">
                    {renaming === p.name ? (
                      <div className="flex items-center gap-1" onClick={e => e.stopPropagation()}>
                        <input className="bg-white/[0.03] border border-white/[0.06] rounded-lg px-2 py-1 text-sm font-medium text-white/70 focus:outline-none focus:border-white/20 w-56"
                          value={renameInput} onChange={e => setRenameInput(e.target.value)} autoFocus
                          onKeyDown={e => { if (e.key === 'Enter') handleRename(p.name); if (e.key === 'Escape') setRenaming(null) }} />
                        <button onClick={() => handleRename(p.name)} className="p-1 rounded hover:bg-green-500/10 text-green-400"><Check className="w-3 h-3" /></button>
                        <button onClick={() => setRenaming(null)} className="p-1 rounded hover:bg-white/[0.03] text-white/15"><X className="w-3 h-3" /></button>
                      </div>
                    ) : (
                      <h3 className="text-sm font-medium truncate transition-colors" style={{ 
                      color: done >= total ? 'rgba(255,255,255,0.95)' : 'rgba(255,255,255,0.70)'
                    }}>{p.name}</h3>
                    )}
                    <div className="flex items-center gap-3 mt-0.5">
                      <span className="text-[10px] text-white/20">{p.genre || '未分类'}</span>
                      <span className="text-[10px] text-white/15">{p.updated_at?.slice(0, 10)}</span>
                      <span className="text-[10px] text-white/15">{done}/{total}</span>
                    </div>
                  </div>

                  {/* Progress */}
                  <div className="w-24 h-0.5 rounded-full overflow-hidden flex-shrink-0 hidden sm:block"
                    style={{ background: done >= total ? 'rgba(52,211,153,0.15)' : 'rgba(255,255,255,0.03)' }}>
                    <div className="h-full rounded-full transition-all duration-700"
                      style={{ 
                        width: `${pct}%`, 
                        background: pct === 100 
                          ? 'linear-gradient(90deg, rgba(52,211,153,0.6), rgba(52,211,153,0.9))' 
                          : 'rgba(255,255,255,0.1)',
                        boxShadow: pct === 100 ? '0 0 8px rgba(52,211,153,0.5)' : 'none'
                      }} />
                  </div>

                  {/* Status badge */}
                  <span className={`text-[10px] px-2 py-0.5 rounded-full flex-shrink-0 hidden sm:inline-block ${
                    p.running ? 'text-green-400/80 bg-green-500/[0.08]' :
                    done >= total ? 'text-green-400/90 bg-green-500/[0.10]' :
                    p.pending_approval ? 'text-amber-400/80 bg-amber-500/[0.08]' :
                    done > 0 ? 'text-indigo-400/80 bg-indigo-500/[0.08]' : 'text-white/10 bg-white/[0.02]'
                  }`}
                  style={done >= total ? { boxShadow: '0 0 8px rgba(52,211,153,0.3)' } : {}}>
                    {p.running ? '生成中' : done >= total ? '✓ 已完成' : p.pending_approval ? '待审核' : done > 0 ? '创作中' : '新建'}
                  </span>

                  {/* Actions */}
                  <div className="flex items-center gap-0.5 opacity-0 group-hover:opacity-100 transition-all flex-shrink-0">
                    <button onClick={e => { e.stopPropagation(); setRenaming(p.name); setRenameInput(p.name) }}
                      className="p-1.5 rounded-lg hover:bg-white/[0.03] text-white/10" title="重命名"><Pencil className="w-3 h-3" /></button>
                    <button onClick={e => { e.stopPropagation(); openProjectFolder(p.name) }}
                      className="p-1.5 rounded-lg hover:bg-white/[0.03] text-white/10" title="打开文件夹"><FolderOpen className="w-3 h-3" /></button>
                    <button onClick={e => { e.stopPropagation(); setDeleteTarget(p.name) }}
                      className="p-1.5 rounded-lg hover:bg-red-500/[0.06] text-white/10 hover:text-red-400/60" title="删除"><Trash2 className="w-3 h-3" /></button>
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </div>

      {deleteTarget && (
        <ConfirmModal title="删除项目" message={`确定删除「${deleteTarget}」及其所有文件？`}
          onConfirm={async () => { await deleteProject(deleteTarget); setDeleteTarget(null); toast('已删除', 'success'); load() }}
          onCancel={() => setDeleteTarget(null)} />
      )}
    </div>
  )
}
