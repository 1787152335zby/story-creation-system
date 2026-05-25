import { useState, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { ArrowLeft, ArrowRight, Check, Sparkles, Wand2, X } from 'lucide-react'
import { createProject, StyleConfig, generateRandomIdea, fetchSettings, fetchAvailableModels, fetchTemplates } from '../lib/api'
import { useToast } from '../components/Toast'
import Starfield from '../components/Starfield'

const STORY_TYPES: Record<string, string> = { '1': '短剧', '2': '电影', '3': '电视剧', '4': '小说/网文', '5': '舞台剧/话剧', '6': '广播剧/有声书' }
const GENRE_TAGS = [
  '科幻', '奇幻', '悬疑', '古装', '现代', '都市', '爱情', '动作',
  '冒险', '武侠', '仙侠', '历史', '战争', '犯罪', '谍战', '警匪',
  '喜剧', '末世', '恐怖', '灵异', '家庭', '伦理', '校园', '青春',
  '职场', '音乐', '传记',
]
const WRITING_STYLES: Record<string, string> = { '1': '精炼实用', '2': '文学质感', '3': '对白优先', '4': '画面感强', '5': '自动适配' }
const VISUAL_STYLES: Record<string, string> = { '1': '好莱坞大片风', '2': '竖屏短剧风', '3': '文艺/独立风', '4': '日韩生活风', '5': '电视剧风', '6': '自动适配' }
const RENDER_STYLES: Record<string, string> = { '1': '写实/真人', '2': '2D 动画', '3': '3D CG', '4': '卡通/风格化', '5': '水墨/国风', '6': '像素/复古', '7': '自动适配' }
const SCREEN_ASPECTS: Record<string, string> = { '1': '9:16 竖屏', '2': '16:9 横屏', '3': '自适应' }
const SCRIPT_STYLES: Record<string, string> = { '1': '视觉化写作', '2': '对白驱动型', '3': '文学剧本型', '4': '自动适配' }
const SCRIPT_FORMATS: Record<string, string> = { '1': '系统格式', '2': '市场格式' }
const MOOD_TAGS = [
  '悬疑紧张', '轻松治愈', '热血激昂', '阴冷压抑', '温暖感人',
  '幽默诙谐', '黑暗深沉', '文艺清新', '史诗宏大', '诡异迷幻',
  '简约克制', '华丽张扬',
]

export default function NewProjectWizard() {
  const navigate = useNavigate()
  const { toast } = useToast()
  const [step, setStep] = useState(0)
  const [style, setStyle] = useState<StyleConfig>({ story_type: '', genre: '', writing_style: '', visual_style: '', art_style: '', screen_aspect: '', script_style: '', script_format: '', duration_mode: '1', episode_count: '', episode_duration: '', custom_requirements: '', visual_reference: '', action_reference: '', mood: '' })
  const [storyIdea, setStoryIdea] = useState('')
  const [projectName, setProjectName] = useState('')
  const [loading, setLoading] = useState(false)
  const [randomLoading, setRandomLoading] = useState(false)
  const [selectedTemplateName, setSelectedTemplateName] = useState('')
  const randomAbortRef = useRef<AbortController | null>(null)
  const steps = ['故事类型', '风格偏好', '时长设置', '故事描述', '模型选择']
  const [selectedGenres, setSelectedGenres] = useState<string[]>([])
  const [selectedMoods, setSelectedMoods] = useState<string[]>([])
  const [customActive, setCustomActive] = useState<Record<string, boolean>>({})
  const [customTexts, setCustomTexts] = useState<Record<string, string>>({})
  const [llmModels, setLlmModels] = useState<{ value: string; label: string }[]>([])
  const [selectedModel, setSelectedModel] = useState('')
  const [templates, setTemplates] = useState<any[]>([])
  const [showStagger, setShowStagger] = useState(false)
  const staggerRef = useRef(false)

  useEffect(() => {
    fetchAvailableModels().then(data => {
      const groups = data.llm_groups || []
      const source = data.active_llm_source
      let filtered = groups
      if (source && groups.length > 0) {
        const backendId = source.backend || source.name || ''
        const found = groups.find((g: any) => {
          const gid = (g.id || '').toLowerCase()
          return gid === backendId.toLowerCase() || gid.includes(backendId.toLowerCase())
        })
        if (found) filtered = [found]
      }
      const models = filtered.flatMap((g: any) => (g.models || []).map((m: any) => ({ value: m.value || m.model_id || m.id, label: m.label || m.name || m.value || m.model_id || m.id })))
      setLlmModels(models)
      if (models.length > 0) setSelectedModel(models[0].value)
    }).catch(err => {
      console.error('获取模型失败:', err)
    })
    fetchTemplates().then(setTemplates).catch(() => {})
    setTimeout(() => { staggerRef.current = true; setShowStagger(true) }, 80)
  }, [])

  const toggleGenre = (tag: string) => {
    const next = selectedGenres.includes(tag)
      ? selectedGenres.filter(g => g !== tag)
      : [...selectedGenres, tag]
    setSelectedGenres(next)
    setStyle({ ...style, genre: next.join(',') })
  }

  const toggleMood = (tag: string) => {
    const next = selectedMoods.includes(tag)
      ? selectedMoods.filter(m => m !== tag)
      : [...selectedMoods, tag]
    setSelectedMoods(next)
    setStyle({ ...style, mood: next.join(',') })
  }

  const handleCreate = async () => {
    setLoading(true)
    const settings = await fetchSettings().catch(() => null)
    const hasKey = settings?.deepseek_api_key || settings?.openai_api_key || settings?.claude_api_key || settings?.seedance_api_key || (settings?.aggregated_api_key && !settings.aggregated_api_key.includes('****'))
    if (!hasKey) {
      toast('请先在设置页面配置 API Key', 'error')
      navigate('/settings')
      setLoading(false)
      return
    }
    const dl = style.duration_mode === '1' ? '自动（由Agent推荐）' : (style.episode_count && style.episode_duration ? `${style.episode_count}集 × ${style.episode_duration}/集` : style.episode_duration || style.episode_count || '')
    try { const r = await createProject({ name: projectName || 'untitled', story_idea: storyIdea, style, duration_line: dl, model: selectedModel, template_name: selectedTemplateName }); navigate(`/project/${encodeURIComponent(r.name)}`) }
    catch (e) { toast('创建失败: ' + String(e), 'error') }
    finally { setLoading(false) }
  }

  const handleRandomIdea = async () => {
    if (!style.story_type) { toast('请先选择故事类型和题材风格', 'info'); return }
    if (randomAbortRef.current) randomAbortRef.current.abort()
    const controller = new AbortController()
    randomAbortRef.current = controller
    const prevIdea = storyIdea
    setRandomLoading(true)
    try {
      const idea = await generateRandomIdea(style, controller.signal)
      setStoryIdea(idea)
    } catch (e: any) {
      if (e?.name === 'AbortError') return
      setStoryIdea(prevIdea)
      toast('随机生成失败: ' + String(e), 'error')
    } finally {
      setRandomLoading(false)
    }
  }

  const applyTemplate = (t: any) => {
    setStyle({
      ...style, story_type: t.story_type || style.story_type,
      writing_style: t.writing_style || style.writing_style,
      visual_style: t.visual_style || style.visual_style,
      art_style: t.art_style || style.art_style,
      screen_aspect: t.screen_aspect || style.screen_aspect,
      script_style: t.script_style || style.script_style,
      script_format: t.script_format || style.script_format,
      duration_mode: t.duration_mode || style.duration_mode,
      episode_count: t.episode_count || style.episode_count,
      episode_duration: t.episode_duration || style.episode_duration,
      genre: t.genre || style.genre,
    })
    if (t.genre) setSelectedGenres(t.genre.split(','))
    setSelectedTemplateName(t.name)
    toast('已应用模板「' + t.name + '」', 'success')
  }

  const tagStyle = (active: boolean) => ({
    border: active ? '1px solid rgba(255,255,255,0.15)' : '1px solid rgba(255,255,255,0.06)',
    background: active ? 'rgba(255,255,255,0.08)' : 'rgba(255,255,255,0.02)',
    color: active ? 'rgba(255,255,255,0.85)' : 'rgba(255,255,255,0.45)',
  })

  return (
    <div className="min-h-screen relative overflow-hidden">
      <Starfield />
      <div className="px-6 py-10 max-w-3xl mx-auto relative z-10">

        <button onClick={() => navigate('/home')} className="flex items-center gap-1.5 text-white/40 hover:text-white/70 mb-8 transition-all text-xs">
          <ArrowLeft className="w-3.5 h-3.5" /> 返回
        </button>

        <div className="text-center mb-10 animate-fade-in-up">
          <h1 className="text-[clamp(28px,5vw,42px)] font-black tracking-[-0.04em] leading-none mb-2"
            style={{
              background: 'linear-gradient(180deg, rgba(255,255,255,0.95) 0%, rgba(255,255,255,0.55) 100%)',
              WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent', backgroundClip: 'text',
            }}>
            开始创作
          </h1>
          <p className="text-xs text-white/15 tracking-wider">从一句话想法开始</p>
        </div>

        <div className="flex items-center justify-center gap-2 mb-10">
          {steps.map((s, i) => (
            <div key={i} className="flex items-center gap-2">
              <div className="flex items-center gap-2">
                <div style={{
                  width: 28, height: 28, borderRadius: 10,
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  background: i <= step ? 'rgba(255,255,255,0.08)' : 'rgba(255,255,255,0.03)',
                  border: `1px solid ${i <= step ? 'rgba(255,255,255,0.12)' : 'rgba(255,255,255,0.05)'}`,
                  transition: 'all 0.3s',
                }}>
                  {i < step ? (
                    <Check className="w-3.5 h-3.5 text-white/60" />
                  ) : (
                    <span style={{ fontSize: 11, fontWeight: 600, color: i <= step ? 'rgba(255,255,255,0.85)' : 'rgba(255,255,255,0.45)' }}>{i + 1}</span>
                  )}
                </div>
                <span className="hidden sm:inline text-[11px]" style={{ color: i <= step ? 'rgba(255,255,255,0.6)' : 'rgba(255,255,255,0.35)', fontWeight: i <= step ? 500 : 400 }}>{s}</span>
              </div>
              {i < steps.length - 1 && (
                <div style={{ width: 20, height: 1, background: i < step ? 'rgba(255,255,255,0.2)' : 'rgba(255,255,255,0.1)' }} />
              )}
            </div>
          ))}
        </div>

        <div className="rounded-2xl overflow-hidden animate-fade-in-up delay-100">
          <div className="px-6 py-6" key={step}
            style={{
              background: 'rgba(255,255,255,0.12)',
              backdropFilter: 'blur(24px)',
              WebkitBackdropFilter: 'blur(24px)',
              border: '1px solid rgba(255,255,255,0.22)',
            }}>
            <h2 className="text-sm font-semibold text-white/80 mb-6 flex items-center gap-2">
              <Wand2 className="w-4 h-4 text-white/40" />
              {steps[step]}
            </h2>

            {step === 0 && (
              <div>
                <div className="mb-6">
                  <label className="text-[11px] text-white/30 mb-3 block">从模板创建</label>
                  {templates.length > 0 ? (
                    <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
                      {templates.map((t: any) => (
                        <button key={t.name} onClick={() => applyTemplate(t)}
                          className={`p-3 rounded-xl text-left transition-all duration-200 text-xs glow-border shimmer-hover relative overflow-hidden ${selectedTemplateName === t.name ? 'selected' : ''}`}
                          style={{
                            background: selectedTemplateName === t.name ? 'rgba(255,255,255,0.16)' : 'rgba(255,255,255,0.07)',
                            border: `1px solid ${selectedTemplateName === t.name ? 'rgba(255,255,255,0.30)' : 'rgba(255,255,255,0.15)'}`,
                          }}>
                          <div className="relative z-[1]">
                            <span className="font-medium text-white/80 block mb-0.5">{t.name}</span>
                            <span className="text-[9px] text-white/35">{STORY_TYPES[t.story_type] || ''} · {t.genre || ''}</span>
                          </div>
                        </button>
                      ))}
                    </div>
                  ) : (
                    <div className="text-center p-6 rounded-xl" style={{ background: 'rgba(255,255,255,0.08)', border: '1px solid rgba(255,255,255,0.08)' }}>
                      <Sparkles className="w-4 h-4 mx-auto mb-1 text-white/20" />
                      <p className="text-[10px] text-white/25">还没有模板，在项目工作区可保存当前项目的风格为模板</p>
                    </div>
                  )}
                  <div className="my-4 flex items-center gap-3">
                    <div className="flex-1 h-px" style={{ background: 'rgba(255,255,255,0.07)' }} />
                    <span className="text-[10px] text-white/15">或手动配置</span>
                    <div className="flex-1 h-px" style={{ background: 'rgba(255,255,255,0.07)' }} />
                  </div>
                </div>
                <div className="mb-5">
                  <p className="text-[11px] text-white/30 mb-3">选择故事类型</p>
                  <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
                    {Object.entries(STORY_TYPES).map(([k, v]) => (
                      <button key={k} onClick={() => setStyle({ ...style, story_type: k })}
                        className={`p-3 rounded-xl text-sm transition-all duration-200 text-left glow-border shimmer-hover relative overflow-hidden ${style.story_type === k ? 'selected' : ''}`}
                        style={{
                          background: style.story_type === k ? 'rgba(255,255,255,0.16)' : 'rgba(255,255,255,0.07)',
                          border: `1px solid ${style.story_type === k ? 'rgba(255,255,255,0.30)' : 'rgba(255,255,255,0.16)'}`,
                          color: style.story_type === k ? 'rgba(255,255,255,0.90)' : 'rgba(255,255,255,0.60)',
                        }}>
                        <div className="relative z-[1]">
                          <div className="font-medium text-sm">{v}</div>
                        </div>
                      </button>
                    ))}
                  </div>
                </div>
                <div>
                  <p className="text-[11px] text-white/30 mb-3">选择题材风格 <span className="text-[9px] text-white/15">（可多选）</span></p>
                  {selectedGenres.length > 0 && (
                    <div className="flex flex-wrap gap-1.5 mb-3">
                      {selectedGenres.map(g => (
                        <span key={g} className="inline-flex items-center gap-1 px-2 py-0.5 rounded-lg text-[10px] font-medium"
                          style={{ background: 'rgba(255,255,255,0.16)', color: 'rgba(255,255,255,0.7)', border: '1px solid rgba(255,255,255,0.28)' }}>
                          {g}
                          <button onClick={() => toggleGenre(g)} className="hover:opacity-70"><X className="w-2.5 h-2.5" /></button>
                        </span>
                      ))}
                    </div>
                  )}
                  <div className="flex flex-wrap gap-1.5">
                    {GENRE_TAGS.map(g => (
                      <button key={g} onClick={() => toggleGenre(g)}
                        className={`px-3 py-1.5 rounded-lg text-[11px] transition-all duration-200 glow-border shimmer-hover relative overflow-hidden ${selectedGenres.includes(g) ? 'selected' : ''}`}
                        style={selectedGenres.includes(g) ? {
                          border: '1px solid rgba(255,255,255,0.30)',
                          background: 'rgba(255,255,255,0.16)',
                          color: 'rgba(255,255,255,0.95)'
                        } : {
                          border: '1px solid rgba(255,255,255,0.16)',
                          background: 'rgba(255,255,255,0.07)',
                          color: 'rgba(255,255,255,0.75)'
                        }}>
                        <div className="relative z-[1]">
                          {selectedGenres.includes(g) && <Check className="w-2.5 h-2.5 inline mr-1" />}
                          {g}
                        </div>
                      </button>
                    ))}
                  </div>
                </div>
              </div>
            )}

            {step === 1 && (
              <div className="space-y-6">
                {[
                  ['文笔风格', WRITING_STYLES, 'writing_style'],
                  ['视觉/叙事风格', VISUAL_STYLES, 'visual_style'],
                  ['渲染画风', RENDER_STYLES, 'art_style'],
                  ['剧本写作风格', SCRIPT_STYLES, 'script_style'],
                  ['剧本格式', SCRIPT_FORMATS, 'script_format'],
                  ['画面比例', SCREEN_ASPECTS, 'screen_aspect'],
                ].map(([label, options, field]) => (
                  <div key={field}>
                    <p className="text-[11px] text-white/30 mb-3">{label}</p>
                    <div className="flex flex-wrap gap-1.5">
                      {Object.entries(options as Record<string, string>).map(([k, v]) => {
                        const active = !customActive[field] && (style as any)[field] === k
                        return (
                          <button key={k} onClick={() => {
                            setStyle({ ...style, [field]: k })
                            setCustomActive(a => ({ ...a, [field]: false }))
                          }} className={`px-3 py-1.5 rounded-lg text-[11px] transition-all duration-200 glow-border shimmer-hover relative overflow-hidden ${active ? 'selected' : ''}`}
                          style={active ? {
                            border: '1px solid rgba(255,255,255,0.30)',
                            background: 'rgba(255,255,255,0.16)',
                            color: 'rgba(255,255,255,0.95)'
                          } : {
                            border: '1px solid rgba(255,255,255,0.16)',
                            background: 'rgba(255,255,255,0.07)',
                            color: 'rgba(255,255,255,0.75)'
                          }}>
                            <div className="relative z-[1]">
                              {v}
                            </div>
                          </button>
                        )
                      })}
                      <button onClick={() => {
                        setCustomActive(a => ({ ...a, [field]: true }))
                        setStyle({ ...style, [field]: customTexts[field] || '' })
                      }} className={`px-3 py-1.5 rounded-lg text-[11px] transition-all duration-200 border border-dashed glow-border shimmer-hover relative overflow-hidden ${customActive[field] ? 'selected' : ''}`}
                      style={customActive[field] ? {
                        border: '1px dashed rgba(255,255,255,0.30)',
                        background: 'rgba(255,255,255,0.16)',
                        color: 'rgba(255,255,255,0.95)'
                      } : {
                        border: '1px dashed rgba(255,255,255,0.16)',
                        background: 'rgba(255,255,255,0.07)',
                        color: 'rgba(255,255,255,0.75)'
                      }}>
                        <div className="relative z-[1]">
                          + 自定义
                        </div>
                      </button>
                    </div>
                    {customActive[field] && (
                      <input autoFocus className="w-full mt-2 rounded-xl px-4 py-2.5 text-xs outline-none"
                        style={{ background: 'rgba(255,255,255,0.08)', border: '1px solid rgba(255,255,255,0.22)', color: 'rgba(255,255,255,0.82)' }}
                        placeholder="请输入自定义风格..."
                        value={customTexts[field] || ''}
                        onChange={e => {
                          const v = e.target.value
                          setCustomTexts(t => ({ ...t, [field]: v }))
                          setStyle({ ...style, [field]: v || '' })
                        }} />
                    )}
                  </div>
                ))}
                <div>
                  <p className="text-[11px] text-white/30 mb-3">情绪氛围 <span className="text-[9px] text-white/15">（可多选）</span></p>
                  {selectedMoods.length > 0 && (
                    <div className="flex flex-wrap gap-1.5 mb-3">
                      {selectedMoods.map(m => (
                        <span key={m} className="inline-flex items-center gap-1 px-2 py-0.5 rounded-lg text-[10px] font-medium"
                          style={{ background: 'rgba(255,255,255,0.16)', color: 'rgba(255,255,255,0.7)', border: '1px solid rgba(255,255,255,0.28)' }}>
                          {m}
                          <button onClick={() => toggleMood(m)} className="hover:opacity-70"><X className="w-2.5 h-2.5" /></button>
                        </span>
                      ))}
                    </div>
                  )}
                  <div className="flex flex-wrap gap-1.5">
                    {MOOD_TAGS.map(m => (
                      <button key={m} onClick={() => toggleMood(m)}
                        className={`px-3 py-1.5 rounded-lg text-[11px] transition-all duration-200 glow-border shimmer-hover relative overflow-hidden ${selectedMoods.includes(m) ? 'selected' : ''}`}
                        style={selectedMoods.includes(m) ? {
                          border: '1px solid rgba(255,255,255,0.30)',
                          background: 'rgba(255,255,255,0.16)',
                          color: 'rgba(255,255,255,0.95)'
                        } : {
                          border: '1px solid rgba(255,255,255,0.16)',
                          background: 'rgba(255,255,255,0.07)',
                          color: 'rgba(255,255,255,0.75)'
                        }}>
                        <div className="relative z-[1]">
                          {selectedMoods.includes(m) && <Check className="w-2.5 h-2.5 inline mr-1" />}
                          {m}
                        </div>
                      </button>
                    ))}
                  </div>
                </div>
              </div>
            )}

            {step === 2 && (
              <div>
                <div className="flex gap-2 mb-6">
                  <button onClick={() => setStyle({ ...style, duration_mode: '1' })}
                    className={`flex-1 py-2.5 px-4 rounded-xl text-[11px] font-medium transition-all duration-200 glow-border shimmer-hover relative overflow-hidden ${style.duration_mode === '1' ? 'selected' : ''}`}
                    style={style.duration_mode === '1' ? {
                      border: '1px solid rgba(255,255,255,0.30)',
                      background: 'rgba(255,255,255,0.16)',
                      color: 'rgba(255,255,255,0.95)'
                    } : {
                      border: '1px solid rgba(255,255,255,0.16)',
                      background: 'rgba(255,255,255,0.07)',
                      color: 'rgba(255,255,255,0.75)'
                    }}>
                    <div className="relative z-[1]">
                      自动时长
                    </div>
                  </button>
                  <button onClick={() => setStyle({ ...style, duration_mode: '2' })}
                    className={`flex-1 py-2.5 px-4 rounded-xl text-[11px] font-medium transition-all duration-200 glow-border shimmer-hover relative overflow-hidden ${style.duration_mode === '2' ? 'selected' : ''}`}
                    style={style.duration_mode === '2' ? {
                      border: '1px solid rgba(255,255,255,0.30)',
                      background: 'rgba(255,255,255,0.16)',
                      color: 'rgba(255,255,255,0.95)'
                    } : {
                      border: '1px solid rgba(255,255,255,0.16)',
                      background: 'rgba(255,255,255,0.07)',
                      color: 'rgba(255,255,255,0.75)'
                    }}>
                    <div className="relative z-[1]">
                      自定义时长
                    </div>
                  </button>
                </div>
                {style.duration_mode === '2' && (
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="text-[10px] text-white/30 block mb-2">集数/章节数</label>
                      <input className="w-full rounded-xl px-4 py-2.5 text-xs outline-none"
                        style={{ background: 'rgba(255,255,255,0.08)', border: '1px solid rgba(255,255,255,0.22)', color: 'rgba(255,255,255,0.82)' }}
                        placeholder="如 12" value={style.episode_count} onChange={e => setStyle({ ...style, episode_count: e.target.value })} />
                    </div>
                    <div>
                      <label className="text-[10px] text-white/30 block mb-2">单集时长</label>
                      <input className="w-full rounded-xl px-4 py-2.5 text-xs outline-none"
                        style={{ background: 'rgba(255,255,255,0.08)', border: '1px solid rgba(255,255,255,0.22)', color: 'rgba(255,255,255,0.82)' }}
                        placeholder="如 45分钟" value={style.episode_duration} onChange={e => setStyle({ ...style, episode_duration: e.target.value })} />
                    </div>
                  </div>
                )}
              </div>
            )}

            {step === 3 && (
              <div className="space-y-5">
                <div>
                  <label className="text-[11px] text-white/30 block mb-2">项目名称</label>
                  <input className="w-full rounded-xl px-4 py-2.5 text-xs outline-none"
                    style={{ background: 'rgba(255,255,255,0.08)', border: '1px solid rgba(255,255,255,0.22)', color: 'rgba(255,255,255,0.82)' }}
                    placeholder="给你的项目起个名字" value={projectName} onChange={e => setProjectName(e.target.value)} />
                </div>
                <div>
                  <label className="text-[11px] text-white/30 block mb-2">故事描述 <span className="text-red-400/60">*</span>
                    <button onClick={handleRandomIdea}
                      className="ml-2 inline-flex items-center gap-1 px-2 py-0.5 rounded-lg text-[10px] transition-all"
                      style={{ background: 'rgba(255,255,255,0.08)', border: '1px solid rgba(255,255,255,0.18)', color: 'rgba(255,255,255,0.75)' }}>
                      {randomLoading ? <span className="w-2.5 h-2.5 border border-white/30 border-t-transparent rounded-full inline-block animate-spin" /> : <Sparkles className="w-2.5 h-2.5" />}
                      {randomLoading ? '生成中...' : '随机生成'}
                    </button>
                  </label>
                  <textarea className="w-full rounded-xl px-4 py-3 h-32 resize-none text-xs outline-none"
                    style={{ background: 'rgba(255,255,255,0.08)', border: '1px solid rgba(255,255,255,0.22)', color: 'rgba(255,255,255,0.82)' }}
                    placeholder="用一段话描述你想讲的故事..."
                    value={storyIdea} onChange={e => setStoryIdea(e.target.value)} />
                </div>
                <div>
                  <label className="text-[11px] text-white/30 block mb-2">额外要求（可选）</label>
                  <textarea className="w-full rounded-xl px-4 py-3 h-20 resize-none text-xs outline-none"
                    style={{ background: 'rgba(255,255,255,0.08)', border: '1px solid rgba(255,255,255,0.22)', color: 'rgba(255,255,255,0.82)' }}
                    placeholder="参考作品、情绪基调等..." value={style.custom_requirements} onChange={e => setStyle({ ...style, custom_requirements: e.target.value })} />
                </div>
              </div>
            )}

            {step === 4 && (
              <div className="space-y-4">
                <p className="text-[11px] text-white/30 mb-3">选择本次创作使用的 AI 模型</p>
                <div className="p-4 rounded-xl" style={{ background: 'rgba(255,255,255,0.07)', border: '1px solid rgba(255,255,255,0.16)' }}>
                  <label className="text-[9px] text-white/25 mb-1.5 block">LLM 文本生成模型</label>
                  <select value={selectedModel} onChange={e => setSelectedModel(e.target.value)}
                    className="w-full rounded-xl px-4 py-2.5 text-xs outline-none"
                    style={{ background: 'rgba(255,255,255,0.08)', border: '1px solid rgba(255,255,255,0.22)', color: 'rgba(255,255,255,0.82)' }}>
                    {llmModels.length === 0 && <option value="">暂无可用模型，请先到设置页配置</option>}
                    {llmModels.map(m => <option key={m.value} value={m.value}>{m.label}</option>)}
                  </select>
                  <p className="text-[9px] text-white/15 mt-1.5">可在设置页配置更多模型</p>
                </div>
              </div>
            )}
          </div>
        </div>

        <div className="flex justify-between mt-6 animate-fade-in-up delay-200">
          <button onClick={() => step > 0 ? setStep(step - 1) : navigate('/home')}
            className="flex items-center gap-1.5 px-5 py-2.5 rounded-xl text-[11px] transition-all"
            style={{ border: '1px solid rgba(255,255,255,0.15)', color: 'rgba(255,255,255,0.6)', background: 'rgba(255,255,255,0.05)' }}>
            <ArrowLeft className="w-3.5 h-3.5" /> 上一步
          </button>
          {step < 4 ? (
            <button onClick={() => {
              if (step === 0 && !style.story_type) { toast('请先选择故事类型', 'info'); return }
              if (step === 3 && !storyIdea.trim()) { toast('请填写故事描述', 'info'); return }
              setStep(step + 1)
            }}
              className="flex items-center gap-1.5 px-6 py-2.5 rounded-xl text-[11px] font-medium transition-all"
              style={{ background: '#fff', color: '#000' }}>
              下一步 <ArrowRight className="w-3.5 h-3.5" />
            </button>
          ) : (
            <button onClick={handleCreate} disabled={loading || !storyIdea}
              className="flex items-center gap-1.5 px-8 py-2.5 rounded-xl text-[11px] font-medium transition-all disabled:opacity-40"
              style={{ background: '#fff', color: '#000' }}>
              <Sparkles className="w-3.5 h-3.5" /> {loading ? '创建中...' : '开始创作'}
            </button>
          )}
        </div>
      </div>
    </div>
  )
}
