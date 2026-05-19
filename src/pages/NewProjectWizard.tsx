import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { ArrowLeft, ArrowRight, Check, Sparkles, Wand2, X } from 'lucide-react'
import { createProject, StyleConfig, CreateProjectPayload, generateRandomIdea, fetchSettings, fetchAvailableModels, fetchTemplates } from '../lib/api'

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
  const [step, setStep] = useState(0)
  const [style, setStyle] = useState<StyleConfig>({ story_type: '', genre: '', writing_style: '', visual_style: '', art_style: '', screen_aspect: '', script_style: '', script_format: '', duration_mode: '1', episode_count: '', episode_duration: '', custom_requirements: '', visual_reference: '', action_reference: '' })
  const [storyIdea, setStoryIdea] = useState('')
  const [projectName, setProjectName] = useState('')
  const [loading, setLoading] = useState(false)
  const [randomLoading, setRandomLoading] = useState(false)
  const steps = ['故事类型', '风格偏好', '时长设置', '故事描述', '模型选择']
  const [selectedGenres, setSelectedGenres] = useState<string[]>([])
  const [selectedMoods, setSelectedMoods] = useState<string[]>([])
  const [customActive, setCustomActive] = useState<Record<string, boolean>>({})
  const [customTexts, setCustomTexts] = useState<Record<string, string>>({})
  const [llmModels, setLlmModels] = useState<{ value: string; label: string }[]>([])
  const [selectedModel, setSelectedModel] = useState('')
  const [templates, setTemplates] = useState<any[]>([])

  useEffect(() => {
    fetchAvailableModels().then(data => {
      const groups = data.llm_groups || []
      const all: { value: string; label: string }[] = []
      for (const g of groups) {
        for (const m of (g.models || [])) {
          all.push({ value: m.value, label: `[${g.name}] ${m.label}` })
        }
      }
      setLlmModels(all)
      if (all.length > 0) setSelectedModel(all[0].value)
    })
    fetchTemplates().then(setTemplates)
  }, [])

  const applyTemplate = (t: any) => {
    setStyle(prev => ({
      ...prev,
      story_type: t.story_type || '',
      genre: t.genre || '',
      writing_style: t.writing_style || '',
      visual_style: t.visual_style || '',
      art_style: t.art_style || '',
      screen_aspect: t.screen_aspect || '',
      script_style: t.script_style || '',
      script_format: t.script_format || '',
      duration_mode: t.duration_mode || '1',
    }))
    if (t.genre) setSelectedGenres(t.genre.split(',').filter(Boolean))
    setStep(1)
  }

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
    const hasKey = settings?.deepseek_api_key || settings?.openai_api_key || settings?.claude_api_key
    if (!hasKey) {
      alert('请先在设置页面配置 API Key')
      navigate('/settings')
      setLoading(false)
      return
    }
    const dl = style.duration_mode === '1' ? '自动（由Agent推荐）' : (style.episode_count && style.episode_duration ? `${style.episode_count}集 × ${style.episode_duration}/集` : style.episode_duration || style.episode_count || '')
    try { const r = await createProject({ name: projectName || 'untitled', story_idea: storyIdea, style, duration_line: dl }); navigate(`/project/${encodeURIComponent(r.name)}`) }
    catch (e) { alert('创建失败: ' + String(e)) }
    finally { setLoading(false) }
  }

  const handleRandomIdea = async () => {
    if (!style.story_type) { alert('请先选择故事类型和题材风格'); return }
    setRandomLoading(true)
    try {
      const idea = await generateRandomIdea(style)
      setStoryIdea(idea)
    } catch (e) {
      alert('随机生成失败: ' + String(e))
    } finally {
      setRandomLoading(false)
    }
  }

  return (
    <div className="min-h-screen relative overflow-hidden">
      <div className="fixed inset-0 pointer-events-none">
        <div className="absolute -top-20 right-1/4 w-80 h-80 rounded-full opacity-10" style={{ background: 'radial-gradient(circle, hsl(252, 87%, 67%), transparent 70%)' }} />
      </div>

      <div className="max-w-3xl mx-auto px-6 py-10 relative z-10">
        <button onClick={() => navigate('/')} className="flex items-center gap-1.5 text-muted-foreground hover:text-foreground mb-8 transition-colors">
          <ArrowLeft className="w-4 h-4" /> 返回
        </button>

        <div className="flex items-center justify-center gap-1 mb-12">
          {steps.map((s, i) => (
            <div key={i} className="flex items-center gap-1">
              <div className={`w-8 h-8 rounded-xl flex items-center justify-center text-xs font-bold transition-all duration-300 ${
                i <= step ? 'text-white' : 'text-muted-foreground bg-muted'
              }`} style={i <= step ? { background: 'linear-gradient(135deg, hsl(252, 87%, 67%), hsl(265, 87%, 60%))' } : {}}>
                {i < step ? <Check className="w-4 h-4" /> : i + 1}
              </div>
              <span className={`text-xs hidden sm:inline transition-colors ${i <= step ? 'text-foreground font-medium' : 'text-muted-foreground'}`}>{s}</span>
              {i < steps.length - 1 && <div className={`w-6 h-0.5 rounded transition-colors ${i < step ? 'bg-primary' : 'bg-muted'}`} />}
            </div>
          ))}
        </div>

        <div className="glass-card rounded-2xl p-8 animate-fade-in-up mb-6">
          <h2 className="text-xl font-bold mb-6 flex items-center gap-2">
            <Wand2 className="w-5 h-5" style={{ color: 'hsl(252, 87%, 67%)' }} />
            {steps[step]}
          </h2>

          {step === 0 && (
            <div>
              <div className="mb-6">
                <label className="text-sm text-muted-foreground block mb-3">📂 从模板创建</label>
                {templates.length > 0 ? (
                  <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                    {templates.map((t: any) => (
                      <button key={t.name} onClick={() => applyTemplate(t)}
                        className="p-4 rounded-2xl border-2 border-border text-left hover:border-primary/50 transition-all duration-200 text-sm">
                        <span className="font-medium block mb-1">{t.name}</span>
                        <span className="text-[10px] text-muted-foreground">
                          {STORY_TYPES[t.story_type] || ''} · {t.genre || ''}
                        </span>
                      </button>
                    ))}
                  </div>
                ) : (
                   <div className="text-center bg-muted rounded-xl px-6 py-6">
                      <div className="empty-icon"><Sparkles className="w-4 h-4 text-muted-foreground" /></div>
                      <p className="text-xs text-muted-foreground">还没有模板，在项目工作区可保存当前项目的风格为模板</p>
                   </div>
                 )}
                <div className="my-4 flex items-center gap-3">
                  <div className="flex-1 h-px bg-border" />
                  <span className="text-xs text-muted-foreground">或手动配置</span>
                  <div className="flex-1 h-px bg-border" />
                </div>
              </div>
              <p className="text-sm text-muted-foreground mb-4">选择故事类型</p>
              <div className="grid grid-cols-2 md:grid-cols-3 gap-3 mb-6">
                {Object.entries(STORY_TYPES).map(([k, v]) => (
                  <button key={k} onClick={() => setStyle({ ...style, story_type: k })} className={`p-4 rounded-2xl border-2 text-left transition-all duration-200 ${
                    style.story_type === k ? 'border-primary bg-primary/10 shadow-lg shadow-primary/10' : 'border-border hover:border-primary/30'}`}>
                    <div className="font-medium text-sm">{v}</div>
                  </button>
                ))}
              </div>
              <p className="text-sm text-muted-foreground mb-4">选择题材风格 <span className="text-xs text-muted-foreground/60">（可多选）</span></p>
              {selectedGenres.length > 0 && (
                <div className="flex flex-wrap gap-1.5 mb-4">
                  {selectedGenres.map(g => (
                    <span key={g} className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs font-medium"
                      style={{ background: 'hsla(252, 87%, 67%, 0.15)', color: 'hsl(252, 87%, 80%)' }}>
                      {g}
                      <button onClick={() => toggleGenre(g)} className="hover:opacity-70"><X className="w-3 h-3" /></button>
                    </span>
                  ))}
                </div>
              )}
              <div className="flex flex-wrap gap-2">
                {GENRE_TAGS.map(g => (
                  <button key={g} onClick={() => toggleGenre(g)} className={`px-4 py-2 rounded-xl border-2 text-sm transition-all duration-200 ${
                    selectedGenres.includes(g) ? 'border-primary bg-primary/10 text-primary font-medium' : 'border-border hover:border-primary/30 text-muted-foreground hover:text-foreground'}`}>
                    {selectedGenres.includes(g) && <Check className="w-3.5 h-3.5 inline mr-1" />}
                    {g}
                  </button>
                ))}
              </div>
            </div>
          )}

          {step === 1 && (
            <div className="space-y-8">
              {[
                ['文笔风格', WRITING_STYLES, 'writing_style'],
                ['视觉/叙事风格', VISUAL_STYLES, 'visual_style'],
                ['渲染画风', RENDER_STYLES, 'art_style'],
                ['剧本写作风格', SCRIPT_STYLES, 'script_style'],
                ['剧本格式', SCRIPT_FORMATS, 'script_format'],
                ['画面比例', SCREEN_ASPECTS, 'screen_aspect'],
              ].map(([label, options, field]) => (
                <div key={field}>
                  <p className="text-sm text-muted-foreground mb-3">{label}</p>
                  <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
                    {Object.entries(options as Record<string, string>).map(([k, v]) => (
                      <button key={k} onClick={() => {
                        setStyle({ ...style, [field]: k })
                        setCustomActive(a => ({ ...a, [field]: false }))
                      }} className={`py-2.5 px-3 rounded-xl border-2 text-sm transition-all duration-200 ${
                        !customActive[field] && (style as any)[field] === k ? 'border-primary bg-primary/10 text-primary font-medium' : 'border-border hover:border-primary/30 text-muted-foreground'}`}>
                        {v}
                      </button>
                    ))}
                    <button onClick={() => {
                      setCustomActive(a => ({ ...a, [field]: true }))
                      setStyle({ ...style, [field]: customTexts[field] || '' })
                    }} className={`py-2.5 px-3 rounded-xl border-2 border-dashed text-sm transition-all duration-200 ${
                      customActive[field] ? 'border-primary bg-primary/10 text-primary font-medium' : 'border-border hover:border-primary/30 text-muted-foreground'}`}>
                      + 自定义
                    </button>
                  </div>
                  {customActive[field] && (
                    <input autoFocus className="w-full mt-2 bg-muted border border-primary/50 rounded-xl px-4 py-2.5 text-sm outline-none"
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
                <p className="text-sm text-muted-foreground mb-4">情绪氛围 <span className="text-xs text-muted-foreground/60">（可多选）</span></p>
                {selectedMoods.length > 0 && (
                  <div className="flex flex-wrap gap-1.5 mb-4">
                    {selectedMoods.map(m => (
                      <span key={m} className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs font-medium"
                        style={{ background: 'hsla(35, 90%, 60%, 0.15)', color: 'hsl(35, 90%, 75%)' }}>
                        {m}
                        <button onClick={() => toggleMood(m)} className="hover:opacity-70"><X className="w-3 h-3" /></button>
                      </span>
                    ))}
                  </div>
                )}
                <div className="flex flex-wrap gap-2">
                  {MOOD_TAGS.map(m => (
                    <button key={m} onClick={() => toggleMood(m)} className={`px-4 py-2 rounded-xl border-2 text-sm transition-all duration-200 ${
                      selectedMoods.includes(m) ? 'border-primary bg-primary/10 text-primary font-medium' : 'border-border hover:border-primary/30 text-muted-foreground hover:text-foreground'}`}>
                      {selectedMoods.includes(m) && <Check className="w-3.5 h-3.5 inline mr-1" />}
                      {m}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          )}

          {step === 2 && (
            <div>
              <div className="flex gap-3 mb-6">
                <button onClick={() => setStyle({ ...style, duration_mode: '1' })} className={`flex-1 py-3 px-5 rounded-2xl border-2 text-sm font-medium transition-all ${style.duration_mode === '1' ? 'border-primary bg-primary/10 text-primary' : 'border-border text-muted-foreground hover:border-primary/30'}`}>自动时长</button>
                <button onClick={() => setStyle({ ...style, duration_mode: '2' })} className={`flex-1 py-3 px-5 rounded-2xl border-2 text-sm font-medium transition-all ${style.duration_mode === '2' ? 'border-primary bg-primary/10 text-primary' : 'border-border text-muted-foreground hover:border-primary/30'}`}>自定义时长</button>
              </div>
              {style.duration_mode === '2' && (
                <div className="grid grid-cols-2 gap-4 animate-fade-in">
                  <div>
                    <label className="text-sm text-muted-foreground block mb-2">集数/章节数</label>
                    <input className="w-full bg-muted border border-border rounded-xl px-4 py-3 text-sm" placeholder="如 12" value={style.episode_count} onChange={e => setStyle({ ...style, episode_count: e.target.value })} />
                  </div>
                  <div>
                    <label className="text-sm text-muted-foreground block mb-2">单集时长</label>
                    <input className="w-full bg-muted border border-border rounded-xl px-4 py-3 text-sm" placeholder="如 45分钟" value={style.episode_duration} onChange={e => setStyle({ ...style, episode_duration: e.target.value })} />
                  </div>
                </div>
              )}
            </div>
          )}

          {step === 3 && (
            <div className="space-y-5">
              <div>
                <label className="text-sm text-muted-foreground block mb-2">项目名称</label>
                <input className="w-full bg-muted border border-border rounded-xl px-4 py-3 text-sm" placeholder="给你的项目起个名字" value={projectName} onChange={e => setProjectName(e.target.value)} />
              </div>
              <div>
                <label className="text-sm text-muted-foreground block mb-2">故事描述 <span className="text-red-400">*</span>
                  <button onClick={handleRandomIdea} disabled={randomLoading} className="ml-2 inline-flex items-center gap-1 px-2.5 py-1 rounded-lg border border-border text-xs hover:bg-muted transition-colors disabled:opacity-50">
                    {randomLoading ? <span className="w-3 h-3 border border-primary border-t-transparent rounded-full inline-block animate-spin" /> : <Sparkles className="w-3 h-3" />}
                    {randomLoading ? '生成中...' : '随机生成'}
                  </button>
                </label>
                <textarea className="w-full bg-muted border border-border rounded-xl px-4 py-3 h-36 resize-none text-sm" placeholder="用一段话描述你想讲的故事...&#10;&#10;例如：一个落魄刑警在调查连环失踪案时，发现所有的线索都指向三年前那场他亲手终结的灭门惨案..." value={storyIdea} onChange={e => setStoryIdea(e.target.value)} />
              </div>
              <div>
                <label className="text-sm text-muted-foreground block mb-2">额外要求（可选）</label>
                <textarea className="w-full bg-muted border border-border rounded-xl px-4 py-3 h-24 resize-none text-sm" placeholder="参考作品、情绪基调等..." value={style.custom_requirements} onChange={e => setStyle({ ...style, custom_requirements: e.target.value })} />
              </div>
            </div>
          )}

          {step === 4 && (
            <div className="space-y-4">
              <p className="text-sm text-muted-foreground mb-2">选择本次创作使用的 AI 模型</p>
              <div className="glass-card rounded-2xl p-4">
                <label className="text-[10px] text-muted-foreground mb-1.5 block">LLM 文本生成模型</label>
                <select value={selectedModel} onChange={e => setSelectedModel(e.target.value)}
                  className="w-full bg-muted border border-border rounded-xl px-4 py-3 text-sm">
                  {llmModels.length === 0 && <option value="">暂无可用模型，请先到设置页配置</option>}
                  {llmModels.map(m => <option key={m.value} value={m.value}>{m.label}</option>)}
                </select>
                <p className="text-[10px] text-muted-foreground mt-1.5">可在设置页配置更多模型</p>
              </div>
            </div>
          )}
        </div>

        <div className="flex justify-between">
          <button onClick={() => step > 0 ? setStep(step - 1) : navigate('/')} className="flex items-center gap-1.5 px-5 py-3 rounded-xl border-2 border-border text-sm font-medium hover:bg-muted transition-all">
            <ArrowLeft className="w-4 h-4" /> 上一步
          </button>
          {step < 3 ? (
            <button onClick={() => setStep(step + 1)} className="btn-gradient flex items-center gap-1.5 px-6 py-3 rounded-xl text-sm font-medium">
              下一步 <ArrowRight className="w-4 h-4" />
            </button>
          ) : (
            <button onClick={handleCreate} disabled={loading || !storyIdea} className="btn-gradient flex items-center gap-1.5 px-8 py-3 rounded-xl text-sm font-medium disabled:opacity-50">
              <Sparkles className="w-4 h-4" /> {loading ? '创建中...' : '开始创作'}
            </button>
          )}
        </div>
      </div>
    </div>
  )
}
