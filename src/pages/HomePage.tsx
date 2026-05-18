import { useEffect, useState, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import { Plus, Settings, Film, FolderOpen, Trash2, AlertTriangle, Image, Video, BookText, Sparkles, Search, Loader2 } from 'lucide-react'
import { fetchProjects, deleteProject, openProjectFolder, fetchSettings, fetchTemplates, deleteTemplate, fetchProjectImages, fetchVideoClips } from '../lib/api'
import { useToast } from '../components/Toast'
import type { ProjectInfo, Template } from '../lib/types'

const PHASE_NAMES = ['故事大纲', '完整剧情', '完整剧本', '分镜设计', '视觉提取', '提示词生成']

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
  const [activeProjectTab, setActiveProjectTab] = useState<Record<string, 'text' | 'images' | 'videos'>>({})
  const [cachedImages, setCachedImages] = useState<Record<string, any>>({})
  const [cachedClips, setCachedClips] = useState<Record<string, any>>({})
  const [loadingTab, setLoadingTab] = useState<Record<string, boolean>>({})

  const filteredProjects = useMemo(() => {
    let list = projects
    if (searchText.trim()) {
      const q = searchText.trim().toLowerCase()
      list = list.filter((p: ProjectInfo) => p.name?.toLowerCase().includes(q))
    }
    if (statusFilter === 'progress') {
      list = list.filter((p: ProjectInfo) => {
        const done = (p.phases || []).slice(0, PHASE_NAMES.length).filter((ph: any) => ph.done).length
        return done > 0 && done < PHASE_NAMES.length
      })
    } else if (statusFilter === 'done') {
      list = list.filter((p: ProjectInfo) => {
        const done = (p.phases || []).slice(0, PHASE_NAMES.length).filter((ph: any) => ph.done).length
        return done >= PHASE_NAMES.length
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

  const doneProjects = projects.filter(p => {
    const d = (p.phases || []).slice(0, PHASE_NAMES.length).filter((ph: any) => ph.done).length
    return d >= PHASE_NAMES.length
  }).length

  return (
    <div className="min-h-screen relative overflow-hidden">

      <div className="max-w-6xl mx-auto px-6 py-10 relative z-10">
        {/* Header */}
        <header className="flex items-center justify-between mb-8 animate-fade-in">
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
          <div className="flex items-center gap-3">
            <button onClick={() => navigate('/settings')} className="relative p-3 rounded-xl hover:bg-white/5 transition-all hover:scale-105 group" title="设置">
              <Settings className="w-5 h-5 text-white/50 group-hover:text-white/80 transition-colors" />
            </button>
          </div>
        </header>

        {/* Setup prompt */}
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

        {/* === Hero Section === */}
        <div className="relative overflow-hidden rounded-2xl p-8 mb-8 animate-fade-in-up"
          style={{
            background: 'linear-gradient(135deg, hsl(var(--primary) / 0.08), hsl(var(--accent) / 0.05))',
            border: '1px solid hsl(var(--primary) / 0.12)',
          }}>
          <div className="absolute -top-24 -right-24 w-64 h-64 rounded-full opacity-30 pointer-events-none"
            style={{ background: 'radial-gradient(circle, hsl(var(--primary) / 0.2), transparent 70%)' }} />
          <div className="relative">
            <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-[11px] font-medium mb-4"
              style={{ background: 'hsl(var(--primary) / 0.12)', color: 'hsl(var(--primary))', border: '1px solid hsl(var(--primary) / 0.2)' }}>
              <Sparkles className="w-3 h-3" /> AI 驱动全流程
            </span>
            <h2 className="text-2xl sm:text-3xl font-bold mb-3">从灵感到银幕</h2>
            <p className="text-sm text-muted-foreground max-w-lg leading-relaxed mb-6">
              输入一句话故事想法，AI 全自动完成大纲、剧情、剧本、分镜到提示词。让创作回归创意本身。
            </p>
            <button onClick={() => navigate('/new')}
              className="inline-flex items-center gap-2 px-6 py-3 rounded-xl text-sm font-semibold text-white transition-all hover:scale-105 active:scale-95"
              style={{ background: 'linear-gradient(135deg, hsl(var(--primary)), hsl(265, 87%, 60%))' }}>
              <Sparkles className="w-4 h-4" /> 开始创作
            </button>
            {!loading && (
              <div className="flex gap-8 mt-6 pt-5 border-t border-border/40">
                <div>
                  <div className="text-lg font-bold" style={{ color: 'hsl(var(--primary))' }}>{projects.length}</div>
                  <div className="text-[10px] text-muted-foreground">已完成项目</div>
                </div>
                <div>
                  <div className="text-lg font-bold" style={{ color: 'hsl(var(--primary))' }}>{doneProjects}</div>
                  <div className="text-[10px] text-muted-foreground">创作环节</div>
                </div>
                <div>
                  <div className="text-lg font-bold" style={{ color: 'hsl(var(--primary))' }}>∞</div>
                  <div className="text-[10px] text-muted-foreground">AI 模型支持</div>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* === Tool Cards === */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-10">
          {entries.map((entry, idx) => (
            <div
              key={entry.label}
              onClick={() => entry.path && navigate(entry.path)}
              className={`glass-card rounded-2xl p-6 animate-fade-in-up transition-all duration-300 ${
                entry.path ? 'card-hover cursor-pointer hover:-translate-y-1' : ''
              } ${!entry.path ? 'ring-2 ring-primary/20' : ''}`}
              style={{ animationDelay: `${idx * 0.08}s`, opacity: 0 }}
            >
              <div className="w-11 h-11 rounded-xl flex items-center justify-center mb-4 transition-transform group-hover:scale-110"
                style={{ background: `${entry.color}20`, color: entry.color }}>
                <entry.icon className="w-5 h-5" />
              </div>
              <h3 className="font-semibold text-sm mb-1">{entry.label}</h3>
              <p className="text-xs text-muted-foreground leading-relaxed">{entry.desc}</p>
            </div>
          ))}
        </div>

        {/* === Project List === */}
        <div className="animate-fade-in-up" style={{ animationDelay: '0.35s', opacity: 0 }}>
          <div className="flex items-center justify-between mb-5">
            <div className="flex items-center gap-2">
              <h2 className="text-base font-bold">📂 最近项目</h2>
              {!loading && <span className="text-[10px] text-muted-foreground">({filteredProjects.length}/{projects.length})</span>}
            </div>
            <div className="flex items-center gap-2">
              <div className="relative max-w-[180px]">
                <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3 h-3 text-muted-foreground" />
                <input value={searchText} onChange={e => { setSearchText(e.target.value); setShowAllProjects(true) }}
                  placeholder="搜索项目..."
                  className="w-full bg-muted border border-border rounded-lg pl-7 pr-2.5 py-1.5 text-[11px] placeholder:text-muted-foreground/50 focus:outline-none focus:border-primary/50 transition-colors" />
              </div>
              <div className="flex items-center gap-1 bg-muted/50 rounded-lg p-0.5 border border-border/50">
                {[
                  { key: 'all', label: '全部' },
                  { key: 'progress', label: '进行中' },
                  { key: 'done', label: '已完成' },
                ].map(f => (
                  <button key={f.key} onClick={() => setStatusFilter(f.key as any)}
                    className={`px-2.5 py-1 rounded text-[10px] font-medium transition-all ${
                      statusFilter === f.key ? 'bg-primary/20 text-primary' : 'text-muted-foreground hover:text-foreground'
                    }`}>
                    {f.label}
                  </button>
                ))}
              </div>
              {!loading && (
                <button onClick={() => navigate('/new')} className="btn-gradient inline-flex items-center gap-1 px-3 py-1.5 rounded-lg text-[11px] font-medium flex-shrink-0">
                  <Plus className="w-3 h-3" /> 新建
                </button>
              )}
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
              <BookText className="w-10 h-10 mx-auto mb-3 text-muted-foreground/40" />
              {searchText || statusFilter !== 'all' ? (
                <div>
                  <p className="font-medium text-sm mb-1">没有找到匹配的项目</p>
                  <p className="text-muted-foreground text-xs">试试其他关键词或筛选条件</p>
                </div>
              ) : (
                <div>
                  <p className="font-medium text-sm mb-1">开始你的第一个项目吧</p>
                  <p className="text-muted-foreground text-xs">点击下方按钮，AI 会帮你完成从大纲到提示词的全部创作</p>
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
                const phases = (p.phases || []).slice(0, PHASE_NAMES.length)
                const done = phases.filter((ph: any) => ph.done).length
                const total = PHASE_NAMES.length
                const pct = total > 0 ? (done / total) * 100 : 0
                const tab = activeProjectTab[p.name] || 'text'
                const imgs = cachedImages[p.name]
                const clips = cachedClips[p.name]
                const loading = loadingTab[p.name]
                const handleTab = (t: 'text' | 'images' | 'videos', e: React.MouseEvent) => {
                  e.stopPropagation()
                  setActiveProjectTab(prev => ({ ...prev, [p.name]: t }))
                  if (t === 'images' && !imgs && !loading) {
                    setLoadingTab(prev => ({ ...prev, [p.name]: true }))
                    fetchProjectImages(p.name).then(data => {
                      setCachedImages(prev => ({ ...prev, [p.name]: data }))
                    }).catch(() => {}).finally(() => {
                      setLoadingTab(prev => ({ ...prev, [p.name]: false }))
                    })
                  }
                  if (t === 'videos' && !clips && !loading) {
                    setLoadingTab(prev => ({ ...prev, [p.name]: true }))
                    fetchVideoClips(p.name).then(data => {
                      setCachedClips(prev => ({ ...prev, [p.name]: data }))
                    }).catch(() => {}).finally(() => {
                      setLoadingTab(prev => ({ ...prev, [p.name]: false }))
                    })
                  }
                }
                return (
                  <div key={p.name}
                    className="glass-card rounded-2xl overflow-hidden group card-glow transition-all duration-200">
                    {/* Tab buttons */}
                    <div className="flex border-b border-border/40">
                      {[
                        { key: 'text' as const, icon: '📝', label: '文本' },
                        { key: 'images' as const, icon: '🎨', label: '生图' },
                        { key: 'videos' as const, icon: '🎬', label: '视频' },
                      ].map(t => (
                        <button key={t.key} onClick={(e) => handleTab(t.key, e)}
                          className={`flex-1 text-[10px] py-2.5 font-medium transition-all ${
                            tab === t.key
                              ? 'bg-primary/10 text-primary border-b-2 border-primary'
                              : 'text-muted-foreground hover:text-foreground hover:bg-muted/30'
                          }`}>
                          {t.icon} {t.label}
                        </button>
                      ))}
                    </div>

                    {tab === 'text' && (
                      <div className="p-4 cursor-pointer" onClick={() => navigate(`/project/${encodeURIComponent(p.name)}`)}>
                        <div className="flex items-start justify-between mb-2">
                          <div className="flex-1 min-w-0">
                            <h3 className="font-semibold text-sm truncate group-hover:text-primary transition-colors">{p.name}</h3>
                            <p className="text-[11px] text-muted-foreground mt-0.5">{p.genre || '未分类'} · {p.updated_at?.slice(0, 10)}</p>
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
                    )}

                    {tab === 'images' && (
                      <div className="p-4">
                        <div className="flex items-start justify-between mb-3">
                          <h3 className="font-semibold text-sm truncate">{p.name}</h3>
                          <div className="flex items-center gap-0.5">
                            <button onClick={(e) => { e.stopPropagation(); openProjectFolder(p.name, '05_角色场景') }} className="p-1.5 rounded-lg hover:bg-muted text-muted-foreground" title="打开图片文件夹">
                              <FolderOpen className="w-3.5 h-3.5" />
                            </button>
                            <button onClick={(e) => { e.stopPropagation(); handleDelete(p.name) }} className="p-1.5 rounded-lg hover:bg-red-500/10 text-muted-foreground hover:text-red-400" title="删除">
                              <Trash2 className="w-3.5 h-3.5" />
                            </button>
                          </div>
                        </div>
                        {loading ? (
                          <div className="flex items-center justify-center py-8">
                            <Loader2 className="w-5 h-5 animate-spin text-muted-foreground" />
                          </div>
                        ) : imgs ? (
                          <>
                            {Object.keys(imgs.characters).length > 0 && (
                              <div className="mb-2">
                                <p className="text-[10px] text-muted-foreground mb-1.5 font-medium">角色</p>
                                <div className="flex flex-wrap gap-2">
                                  {Object.entries(imgs.characters).map(([name, data]: [string, any]) => {
                                    const entities = Array.isArray(data) ? data : (data.images || [])
                                    return entities.length > 0 ? (
                                      <div key={name} className="text-center">
                                        <img key={name} src={entities[0].url} alt={name}
                                          className="w-12 h-12 rounded-lg object-cover border border-border/40 cursor-pointer"
                                          onClick={() => navigate(`/project/${encodeURIComponent(p.name)}`)} />
                                        <p className="text-[8px] text-muted-foreground mt-0.5 truncate max-w-[48px]">{name}</p>
                                      </div>
                                    ) : null
                                  })}
                                </div>
                              </div>
                            )}
                            {Object.keys(imgs.scenes).length > 0 && (
                              <div>
                                <p className="text-[10px] text-muted-foreground mb-1.5 font-medium">场景</p>
                                <div className="flex flex-wrap gap-2">
                                  {Object.entries(imgs.scenes).map(([name, data]: [string, any]) => {
                                    const entities = Array.isArray(data) ? data : (data.images || [])
                                    return entities.length > 0 ? (
                                      <div key={name} className="text-center">
                                        <img key={name} src={entities[0].url} alt={name}
                                          className="w-12 h-12 rounded-lg object-cover border border-border/40 cursor-pointer"
                                          onClick={() => navigate(`/project/${encodeURIComponent(p.name)}`)} />
                                        <p className="text-[8px] text-muted-foreground mt-0.5 truncate max-w-[48px]">{name}</p>
                                      </div>
                                    ) : null
                                  })}
                                </div>
                              </div>
                            )}
                            {(Object.keys(imgs.characters).length === 0 && Object.keys(imgs.scenes).length === 0) && (
                              <p className="text-xs text-muted-foreground text-center py-6">暂无生成图片</p>
                            )}
                          </>
                        ) : (
                          <p className="text-xs text-muted-foreground text-center py-6">点击加载图片数据</p>
                        )}
                      </div>
                    )}

                    {tab === 'videos' && (
                      <div className="p-4">
                        <div className="flex items-start justify-between mb-3">
                          <h3 className="font-semibold text-sm truncate">{p.name}</h3>
                          <div className="flex items-center gap-0.5">
                            <button onClick={(e) => { e.stopPropagation(); openProjectFolder(p.name, '08_视频') }} className="p-1.5 rounded-lg hover:bg-muted text-muted-foreground" title="打开视频文件夹">
                              <FolderOpen className="w-3.5 h-3.5" />
                            </button>
                            <button onClick={(e) => { e.stopPropagation(); handleDelete(p.name) }} className="p-1.5 rounded-lg hover:bg-red-500/10 text-muted-foreground hover:text-red-400" title="删除">
                              <Trash2 className="w-3.5 h-3.5" />
                            </button>
                          </div>
                        </div>
                        {loading ? (
                          <div className="flex items-center justify-center py-8">
                            <Loader2 className="w-5 h-5 animate-spin text-muted-foreground" />
                          </div>
                        ) : clips ? (
                          <div className="space-y-1.5">
                            {clips.final && (
                              <div className="flex items-center gap-2 p-2 rounded-lg bg-green-400/5 border border-green-400/20">
                                <span className="text-[9px] text-green-400 font-medium">最终</span>
                                <span className="text-xs truncate flex-1">{clips.final.name}</span>
                                <button onClick={() => navigate(`/video-gen`)} className="text-[9px] text-primary hover:underline">查看</button>
                              </div>
                            )}
                            {clips.clips?.length > 0 ? clips.clips.slice(0, 4).map((clip: any, i: number) => (
                              <div key={i} className="flex items-center gap-2 p-2 rounded-lg bg-muted/30">
                                <span className="text-[10px] text-muted-foreground w-4">{i + 1}</span>
                                <span className="text-xs truncate flex-1">{clip.name}</span>
                              </div>
                            )) : (
                              <p className="text-xs text-muted-foreground text-center py-6">暂无视频片段</p>
                            )}
                          </div>
                        ) : (
                          <p className="text-xs text-muted-foreground text-center py-6">点击加载视频数据</p>
                        )}
                      </div>
                    )}
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
              <h2 className="text-base font-bold flex items-center gap-2">
                <Sparkles className="w-4 h-4 text-muted-foreground" />
                <span>创作模板</span>
                <span className="text-[10px] text-muted-foreground font-normal">({templates.length} 个)</span>
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

      {/* Delete project confirm modal */}
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
