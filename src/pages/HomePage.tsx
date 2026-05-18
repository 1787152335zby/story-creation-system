import { useEffect, useState, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import { Plus, Settings, Film, FolderOpen, Trash2, AlertTriangle, Image, Video, BookText, Sparkles, Search } from 'lucide-react'
import { fetchProjects, deleteProject, openProjectFolder, fetchSettings, fetchTemplates, deleteTemplate } from '../lib/api'
import { useToast } from '../components/Toast'
import type { ProjectInfo, Template } from '../lib/types'

const PHASE_NAMES = ['故事大纲', '完整剧情', '完整剧本', '分镜脚本', '提示词']

export default function HomePage() {
  const navigate = useNavigate()
  const { toast } = useToast()
  const [projects, setProjects] = useState<ProjectInfo[]>([])
  const [loading, setLoading] = useState(true)
  const [deleteTarget, setDeleteTarget] = useState<string | null>(null)
  const [deleteTemplateTarget, setDeleteTemplateTarget] = useState<string | null>(null)
  const [showSetupPrompt, setShowSetupPrompt] = useState(false)
  const [templates, setTemplates] = useState<Template[]>([])
  const [showAllProjects, setShowAllProjects] = useState(false)
  const [showAllTemplates, setShowAllTemplates] = useState(false)
  const [searchText, setSearchText] = useState('')
  const [statusFilter, setStatusFilter] = useState<'all' | 'progress' | 'done'>('all')

  const filteredProjects = useMemo(() => {
    let list = projects
    if (searchText.trim()) {
      const q = searchText.trim().toLowerCase()
      list = list.filter((p: ProjectInfo) => p.name?.toLowerCase().includes(q))
    }
    if (statusFilter === 'progress') {
      list = list.filter((p: ProjectInfo) => {
        const done = (p.phases || []).filter((ph: any) => ph.done).length
        const total = p.total_phases || p.phases?.length || 5
        return done > 0 && done < total
      })
    } else if (statusFilter === 'done') {
      list = list.filter((p: ProjectInfo) => {
        const done = (p.phases || []).filter((ph: any) => ph.done).length
        const total = p.total_phases || p.phases?.length || 5
        return done >= total
      })
    }
    return list
  }, [projects, searchText, statusFilter])

  const load = async () => {
    try { setProjects(await fetchProjects()) } catch (e) { toast('加载项目失败: ' + (e as any).message, 'error') }
    finally { setLoading(false) }
  }

  const loadTemplates = async () => {
    try { setTemplates(await fetchTemplates()) } catch (e) { toast('加载模板失败', 'error') }
  }

  useEffect(() => {
    load()
    loadTemplates()
    if (localStorage.getItem('setup_dismissed') === 'true') return
    fetchSettings().then(data => {
      const hasKey = data.deepseek_api_key || data.openai_api_key || data.claude_api_key
      setShowSetupPrompt(!hasKey)
    }).catch(() => {})
  }, [])

  const dismissSetup = () => {
    setShowSetupPrompt(false)
    localStorage.setItem('setup_dismissed', 'true')
  }

  const handleDelete = async (name: string) => {
    setDeleteTarget(name)
  }

  const confirmDelete = async () => {
    if (!deleteTarget) return
    await deleteProject(deleteTarget)
    setDeleteTarget(null)
    toast('已删除项目', 'success')
    load()
  }

  const entries = [
    { icon: Plus, label: '新建项目', desc: '从故事想法开始，AI 全自动完成大纲到提示词', color: 'hsl(252, 87%, 67%)', path: '/new' },
    { icon: Image, label: '智能生图', desc: '角色定妆照 · 场景概念图 · 四视图 · 四角度环绕', color: 'hsl(170, 70%, 55%)', path: '/image-gen' },
    { icon: Video, label: '视频生成', desc: '图生视频 · 多片段拼接 · 完整短片输出', color: 'hsl(350, 80%, 60%)', path: '/video-gen' },
    { icon: BookText, label: '剧本目录', desc: '浏览已有项目 · 继续创作 · 管理剧本文件', color: 'hsl(40, 90%, 55%)', path: null },
  ]

  return (
    <div className="min-h-screen relative overflow-hidden">
      <div className="fixed inset-0 pointer-events-none overflow-hidden">
        <div className="absolute -top-40 -right-40 w-96 h-96 rounded-full opacity-20"
          style={{ background: 'radial-gradient(circle, hsl(var(--primary)), transparent 70%)' }} />
        <div className="absolute -bottom-40 -left-40 w-96 h-96 rounded-full opacity-10"
          style={{ background: 'radial-gradient(circle, hsl(var(--accent)), transparent 70%)' }} />
      </div>

      <div className="max-w-6xl mx-auto px-6 py-10 relative z-10">
        <header className="flex items-center justify-between mb-10 animate-fade-in">
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 rounded-2xl flex items-center justify-center animate-pulse-glow"
              style={{ background: 'linear-gradient(135deg, hsl(var(--primary)), hsl(265, 87%, 60%))' }}>
              <Film className="w-6 h-6 text-white" />
            </div>
            <div>
              <h1 className="text-2xl font-bold">
                <span className="gradient-text">多智能体故事创作系统</span>
              </h1>
              <p className="text-xs text-muted-foreground mt-0.5">AI 驱动的全流程创作平台</p>
            </div>
          </div>
          <button onClick={() => navigate('/settings')} className="relative p-3 rounded-xl hover:bg-muted transition-all hover:scale-105 group" title="设置">
            <Settings className="w-5 h-5 text-muted-foreground group-hover:text-foreground transition-colors" />
          </button>
        </header>

        {showSetupPrompt && (
          <div className="mb-8 p-5 rounded-2xl border-2 border-amber-400/30 bg-amber-400/5 animate-fade-in-up flex items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <AlertTriangle className="w-6 h-6 text-amber-400 flex-shrink-0" />
              <div>
                <p className="text-sm font-medium text-amber-300">配置 AI 模型以开始创作</p>
                <p className="text-xs text-muted-foreground mt-0.5">首次使用需要设置 API Key，AI 才能为你生成内容</p>
              </div>
            </div>
            <div className="flex items-center gap-2 flex-shrink-0">
              <button onClick={() => navigate('/settings')} className="btn-gradient px-5 py-2.5 rounded-xl text-sm font-medium whitespace-nowrap">
                <Settings className="w-4 h-4 inline mr-1" />去设置
              </button>
              <button onClick={dismissSetup} className="px-4 py-2.5 rounded-xl border border-border text-sm hover:bg-muted transition-colors whitespace-nowrap">
                稍后
              </button>
            </div>
          </div>
        )}

        {/* Entry cards */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-12">
          {entries.map((entry, idx) => (
            <div
              key={entry.label}
              onClick={() => entry.path && navigate(entry.path)}
              className={`glass-card rounded-2xl p-6 animate-fade-in-up transition-all duration-300 ${
                entry.path ? 'card-hover cursor-pointer' : ''
              } ${!entry.path ? 'ring-2 ring-primary/20' : ''}`}
              style={{ animationDelay: `${idx * 0.08}s`, opacity: 0 }}
            >
              <div className="w-10 h-10 rounded-xl flex items-center justify-center mb-4"
                style={{ background: `${entry.color}20`, color: entry.color }}>
                <entry.icon className="w-5 h-5" />
              </div>
              <h3 className="font-semibold text-sm mb-1">{entry.label}</h3>
              <p className="text-xs text-muted-foreground leading-relaxed">{entry.desc}</p>
            </div>
          ))}
        </div>

        {/* Project list = 剧本目录 */}
        <div className="animate-fade-in-up" style={{ animationDelay: '0.35s', opacity: 0 }}>
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-bold flex items-center gap-2">
              <BookText className="w-5 h-5 text-muted-foreground" />
              <span>剧本目录</span>
              {!loading && <span className="text-xs text-muted-foreground font-normal">({filteredProjects.length}/{projects.length} 个项目)</span>}
            </h2>
            {!loading && (
              <button onClick={() => navigate('/new')} className="btn-gradient inline-flex items-center gap-1.5 px-4 py-2 rounded-xl text-xs font-medium">
                <Plus className="w-3.5 h-3.5" /> 新建
              </button>
            )}
          </div>

          <div className="flex items-center gap-2 mb-5">
            <div className="relative flex-1 max-w-xs">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-muted-foreground" />
              <input value={searchText} onChange={e => { setSearchText(e.target.value); setShowAllProjects(true) }}
                placeholder="搜索项目名称..."
                className="w-full bg-muted border border-border rounded-xl pl-9 pr-3 py-2 text-xs placeholder:text-muted-foreground/50 focus:outline-none focus:border-primary/50 transition-colors" />
            </div>
            <div className="flex items-center gap-1 bg-muted/50 rounded-xl p-0.5 border border-border/50">
              {[
                { key: 'all', label: '全部' },
                { key: 'progress', label: '进行中' },
                { key: 'done', label: '已完成' },
              ].map(f => (
                <button key={f.key} onClick={() => setStatusFilter(f.key as any)}
                  className={`px-3 py-1.5 rounded-lg text-[10px] font-medium transition-all ${
                    statusFilter === f.key ? 'bg-primary/20 text-primary' : 'text-muted-foreground hover:text-foreground'
                  }`}>
                  {f.label}
                </button>
              ))}
            </div>
          </div>

          {loading ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {[1,2,3,4,5,6].map(i => (
                <div key={i} className="glass-card rounded-2xl p-5">
                  <div className="skeleton h-4 w-3/4 mb-3" />
                  <div className="skeleton h-3 w-1/2 mb-3" />
                  <div className="flex gap-1 mb-3">
                    {[1,2,3,4,5].map(j => <div key={j} className="skeleton h-5 w-12 rounded-full" />)}
                  </div>
                  <div className="skeleton h-1.5 w-full rounded-full mb-2" />
                  <div className="skeleton h-3 w-1/4" />
                </div>
              ))}
            </div>
          ) : filteredProjects.length === 0 ? (
            <div className="glass-card rounded-2xl p-12 text-center">
              <div className="empty-icon"><BookText className="w-5 h-5 text-muted-foreground" /></div>
              {searchText || statusFilter !== 'all' ? (
                <div>
                  <p className="font-medium text-sm mb-1">没有找到匹配的项目</p>
                  <p className="text-muted-foreground text-xs">试试其他关键词或筛选条件</p>
                </div>
              ) : (
                <div>
                  <p className="font-medium text-sm mb-1">开始你的第一个项目吧</p>
                  <p className="text-muted-foreground text-xs">点击右上角「新建项目」，AI 会帮你完成从大纲到提示词的全部创作</p>
                  <button onClick={() => navigate('/new')} className="btn-gradient px-5 py-2.5 rounded-xl text-sm font-medium mt-5 inline-flex items-center gap-1.5">
                    <Plus className="w-4 h-4" /> 新建项目
                  </button>
                </div>
              )}
            </div>
          ) : (
            <>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {(showAllProjects ? filteredProjects : filteredProjects.slice(0, 6)).map((p, idx) => {
                const done = (p.phases || []).filter((ph: any) => ph.done).length
                const total = p.total_phases || p.phases?.length || 5
                const pct = total > 0 ? (done / total) * 100 : 0
                return (
                  <div key={p.name} onClick={() => navigate(`/project/${encodeURIComponent(p.name)}`)}
                    className="glass-card rounded-2xl p-5 cursor-pointer group card-glow">
                    <div className="flex items-start justify-between mb-3">
                      <div className="flex-1 min-w-0">
                        <h3 className="font-semibold text-sm truncate group-hover:text-primary transition-colors">{p.name}</h3>
                        <p className="text-xs text-muted-foreground mt-0.5">{p.genre || '未分类'} · {p.updated_at?.slice(0, 10)}</p>
                      </div>
                      <div className="flex items-center gap-0.5 opacity-0 group-hover:opacity-100 transition-all">
                        <button onClick={(e) => { e.stopPropagation(); openProjectFolder(p.name) }} className="p-1.5 rounded-lg hover:bg-muted text-muted-foreground" title="打开文件夹">
                          <FolderOpen className="w-3.5 h-3.5" />
                        </button>
                        <button onClick={(e) => { e.stopPropagation(); handleDelete(p.name) }} className="p-1.5 rounded-lg hover:bg-red-500/10 text-muted-foreground hover:text-red-400" title="删除">
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    </div>
                    <div className="flex flex-wrap gap-1 mb-3">
                      {PHASE_NAMES.map((pn, i) => (
                        <span key={i} className={`badge ${
                          (p.phases || [])[i]?.done ? 'badge-primary' : 'badge-muted'
                        }`}>{pn}</span>
                      ))}
                    </div>
                    <div className="w-full h-1.5 bg-muted rounded-full overflow-hidden">
                      <div className="h-full rounded-full transition-all duration-700 progress-glow" style={{
                        width: `${pct}%`,
                        background: pct === 100 ? 'linear-gradient(90deg, hsl(var(--accent)), hsl(150, 60%, 50%))' : 'linear-gradient(90deg, hsl(var(--primary)), hsl(265, 87%, 60%))',
                      }} />
                    </div>
                    <div className="flex justify-between mt-1.5 text-[10px] text-muted-foreground">
                      <span>{done}/{total} 阶段</span>
                      <span>{pct === 100 ? '已完成' : `${Math.round(pct)}%`}</span>
                    </div>
                  </div>
                )
              })}
              </div>
              {filteredProjects.length > 6 && (
                <div className="mt-4 text-center">
                  <button onClick={() => setShowAllProjects(!showAllProjects)}
                    className="inline-flex items-center gap-1.5 px-5 py-2 rounded-xl border border-border text-xs text-muted-foreground hover:text-foreground hover:border-primary/30 transition-all">
                    {showAllProjects ? '收起' : `查看全部 (${filteredProjects.length} 个)`}
                  </button>
                </div>
              )}
            </>
          )}
        </div>

        {/* Templates section */}
        {templates.length > 0 && (
          <div className="mt-10 animate-fade-in-up" style={{ animationDelay: '0.45s', opacity: 0 }}>
            <div className="flex items-center justify-between mb-5">
              <h2 className="text-lg font-bold flex items-center gap-2">
                <Sparkles className="w-5 h-5 text-muted-foreground" />
                <span>创作模板</span>
                <span className="text-xs text-muted-foreground font-normal">({templates.length} 个)</span>
              </h2>
            </div>
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
              {(showAllTemplates ? templates : templates.slice(0, 8)).map((t: Template) => (
                <div key={t.name} className="glass-card rounded-xl p-4 group hover:ring-2 hover:ring-primary/30 transition-all">
                  <div className="flex items-start justify-between mb-2">
                    <div className="flex-1 min-w-0">
                      <h3 className="font-medium text-sm truncate">{t.name}</h3>
                      <p className="text-[10px] text-muted-foreground mt-0.5">{t.genre || '未分类'}</p>
                    </div>
                    <button onClick={(e) => {
                      e.stopPropagation()
                      setDeleteTemplateTarget(t.name)
                    }} className="p-1 rounded-lg hover:bg-red-500/10 text-muted-foreground hover:text-red-400 opacity-0 group-hover:opacity-100 transition-all">
                      <Trash2 className="w-3 h-3" />
                    </button>
                  </div>
                  <button onClick={() => navigate('/new')}
                    className="w-full mt-2 py-1.5 rounded-lg border border-border text-[10px] hover:bg-muted transition-colors">
                    使用此模板
                  </button>
                </div>
              ))}
            </div>
            {templates.length > 8 && (
              <div className="mt-4 text-center">
                <button onClick={() => setShowAllTemplates(!showAllTemplates)}
                  className="inline-flex items-center gap-1.5 px-5 py-2 rounded-xl border border-border text-xs text-muted-foreground hover:text-foreground hover:border-primary/30 transition-all">
                  {showAllTemplates ? '收起' : `查看全部 (${templates.length} 个)`}
                </button>
              </div>
            )}
          </div>
        )}

      </div>

      {/* Delete template confirm modal */}
      {deleteTemplateTarget && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm" onClick={() => setDeleteTemplateTarget(null)}>
          <div className="glass-card rounded-2xl p-6 w-full max-w-sm mx-4" onClick={e => e.stopPropagation()}>
            <div className="flex items-center gap-3 mb-4">
              <div className="w-10 h-10 rounded-xl bg-red-500/10 flex items-center justify-center">
                <Trash2 className="w-5 h-5 text-red-400" />
              </div>
              <div>
                <h3 className="font-semibold">删除模板</h3>
                <p className="text-sm text-muted-foreground">此操作不可撤销</p>
              </div>
            </div>
            <p className="text-sm mb-4">确定删除模板「{deleteTemplateTarget}」？</p>
            <div className="flex gap-2 justify-end">
              <button onClick={() => setDeleteTemplateTarget(null)} className="px-4 py-2 rounded-xl border border-border text-sm hover:bg-muted transition-colors">取消</button>
              <button onClick={async () => {
                await deleteTemplate(deleteTemplateTarget)
                setDeleteTemplateTarget(null)
                loadTemplates()
              }} className="px-4 py-2 rounded-xl bg-red-500 text-white text-sm hover:bg-red-600 transition-colors">确认删除</button>
            </div>
          </div>
        </div>
      )}

      {/* Delete confirm modal */}
      {deleteTarget && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm" onClick={() => setDeleteTarget(null)}>
          <div className="glass-card rounded-2xl p-6 w-full max-w-sm mx-4" onClick={e => e.stopPropagation()}>
            <div className="flex items-center gap-3 mb-4">
              <div className="w-10 h-10 rounded-xl bg-red-500/10 flex items-center justify-center">
                <Trash2 className="w-5 h-5 text-red-400" />
              </div>
              <div>
                <h3 className="font-semibold">删除项目</h3>
                <p className="text-sm text-muted-foreground">此操作不可撤销</p>
              </div>
            </div>
            <p className="text-sm mb-4">确定删除「{deleteTarget}」及其所有文件？</p>
            <div className="flex gap-2 justify-end">
              <button onClick={() => setDeleteTarget(null)} className="px-4 py-2 rounded-xl border border-border text-sm hover:bg-muted transition-colors">取消</button>
              <button onClick={confirmDelete} className="px-4 py-2 rounded-xl bg-red-500 text-white text-sm hover:bg-red-600 transition-colors">确认删除</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
