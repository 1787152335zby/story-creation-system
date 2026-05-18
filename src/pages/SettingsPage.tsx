import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ArrowLeft, Save, Loader2, Lock, ExternalLink, Zap, Settings, Check, Eye, EyeOff, Plus, Trash2, RefreshCw } from 'lucide-react'
import { fetchSettings, updateSettings, testLLM, fetchAggConfigs, createAggConfig, updateAggConfig, deleteAggConfig, activateAggConfig, deactivateAggType, testAggConfig, fetchAggConfigModels, fetchProviderConfigs, createProviderConfig, updateProviderConfig, deleteProviderConfig, activateProviderConfig } from '../lib/api'
import type { AggConfig, ProviderConfig, ModelFamily } from '../lib/api'
import ModelSelector from '../components/ModelSelector'
import { useToast } from '../components/Toast'

const KEY_LINKS: Record<string, string> = {
  deepseek: 'https://platform.deepseek.com/api_keys',
  openai: 'https://platform.openai.com/api-keys',
  claude: 'https://console.anthropic.com/settings/keys',
  volcengine: 'https://console.volcengine.com/ark/region:ark+cn-beijing/apiKey',
}

const GROUPS = [
  {
    name: 'LLM 文本生成', icon: '📝', env_field: 'llm_backend',
    providers: [
      { id: 'deepseek', label: 'DeepSeek', key_field: 'deepseek_api_key', key_link: KEY_LINKS.deepseek, key_tip: 'DeepSeek API Key', model_field: 'deepseek_model', models: ['deepseek-v4-pro', 'deepseek-v4-flash', 'deepseek-chat', 'deepseek-reasoner'], default_model: 'deepseek-v4-flash', base_url: 'https://api.deepseek.com', test_backend: 'deepseek', env_value: 'deepseek' },
    ],
  },
  {
    name: '图片生成', icon: '🖼️', env_field: 'image_backend',
    providers: [],
  },
  {
    name: '视频生成', icon: '🎬', env_field: 'video_backend',
    providers: [],
  },
]

type Provider = (typeof GROUPS)[number]['providers'][number]

export default function SettingsPage() {
  const navigate = useNavigate()
  const { toast } = useToast()
  const [activeTab, setActiveTab] = useState(0)
  const [envSettings, setEnvSettings] = useState<Record<string, string>>({})
  const [expandedId, setExpandedId] = useState<string | null>(null)
  const [visibleKeyId, setVisibleKeyId] = useState<string | null>(null)
  const [dirtyFields, setDirtyFields] = useState<Record<string, string>>({})
  const [saving, setSaving] = useState(false)
  const [testing, setTesting] = useState(false)
  const [testResult, setTestResult] = useState<{ success: boolean; message: string } | null>(null)
  const [aggConfigs, setAggConfigs] = useState<AggConfig[]>([])
  const [aggFamilies, setAggFamilies] = useState<Record<string, ModelFamily[]>>({})
  const [aggSelectedFamily, setAggSelectedFamily] = useState<Record<string, string>>({})
  const [aggLoadingModels, setAggLoadingModels] = useState<Record<string, boolean>>({})
  const [aggTestingSet, setAggTestingSet] = useState<Record<string, boolean>>({})
  const [aggTestResultSet, setAggTestResultSet] = useState<Record<string, { success: boolean; message: string } | null>>({})
  const [newAggExpanded, setNewAggExpanded] = useState(false)
  const [newAggName, setNewAggName] = useState('')
  const [newAggUrl, setNewAggUrl] = useState('')
  const [newAggKey, setNewAggKey] = useState('')
  const [newAggModel, setNewAggModel] = useState('')
  const [editingAggId, setEditingAggId] = useState<string | null>(null)
  const [editAggName, setEditAggName] = useState('')
  const [editAggUrl, setEditAggUrl] = useState('')
  const [editAggKey, setEditAggKey] = useState('')
  const [editAggModel, setEditAggModel] = useState('')
  const [providerConfigMap, setProviderConfigMap] = useState<Record<string, ProviderConfig[]>>({})
  const [provNewConfigId, setProvNewConfigId] = useState<string | null>(null)
  const [provNewKey, setProvNewKey] = useState('')
  const [provNewModel, setProvNewModel] = useState('')
  const [provNewProvider, setProvNewProvider] = useState('')
  const [provNewUrl, setProvNewUrl] = useState('')
  const [visibleAggKey, setVisibleAggKey] = useState<string | null>(null)

  useEffect(() => {
    fetchSettings().then(data => {
      const flat: Record<string, string> = {}
      for (const [k, v] of Object.entries(data)) flat[k] = typeof v === 'string' ? v : ''
      setEnvSettings(flat)
    })
  }, [])

  const typeKey = activeTab === 0 ? 'llm' : activeTab === 1 ? 'image' : 'video'

  const loadAggModels = async (configs: any[]) => {
    for (const cfg of configs) {
      if (cfg.id && cfg.base_url && cfg.api_key) {
        setAggLoadingModels(p => ({ ...p, [cfg.id]: true }))
        try {
          const { families } = await fetchAggConfigModels(cfg.id)
          setAggFamilies(p => ({ ...p, [cfg.id]: families }))
          if (families.length > 0) {
            // 根据已保存的模型找到正确的家族
            let targetFamily = families[0].id
            if (cfg.model) {
              for (const f of families) {
                if (f.versions.some(v => v.value === cfg.model)) {
                  targetFamily = f.id
                  break
                }
              }
            }
            setAggSelectedFamily(p => ({ ...p, [cfg.id]: targetFamily }))
          }
        } catch { /* ignore */ }
        setAggLoadingModels(p => ({ ...p, [cfg.id]: false }))
      }
    }
  }

  const fetchAggConfigsAndModels = async () => {
    const data = await fetchAggConfigs(typeKey)
    const configs = data.configs || []
    setAggConfigs(configs)
    loadAggModels(configs)
  }

  useEffect(() => {
    fetchAggConfigsAndModels()
    const provId = activeTab === 0 ? 'deepseek' : activeTab === 1 ? 'seedream' : 'seedance'
    fetchProviderConfigs(provId).then(d => setProviderConfigMap(prev => ({ ...prev, [provId]: d.configs })))
  }, [activeTab])

  const val = (f: string) => envSettings[f] || ''
  const update = (f: string, v: string) => {
    setEnvSettings(prev => ({ ...prev, [f]: v }))
    setDirtyFields(prev => ({ ...prev, [f]: v }))
  }

  const isProviderActive = (p: Provider, groupIdx: number) => {
    const grp = GROUPS[groupIdx]
    const aggType = groupIdx === 0 ? 'llm' : groupIdx === 1 ? 'image' : 'video'
    const aggActive = aggConfigs.some(c => c.type === aggType && c.active)
    if (aggActive) return false
    if (p.env_value) return val(grp.env_field) === p.env_value
    if (p.image_backend_value) return val('image_backend') === p.image_backend_value
    return false
  }

  const hasKey = (p: Provider) => {
    const v = val(p.key_field)
    return !!v && v !== '****' && !v.includes('your-key')
  }

  const getModel = (p: Provider) => {
    if (p.model_field) return val(p.model_field) || p.default_model
    return p.default_model
  }

  const expand = (id: string) => setExpandedId(expandedId === id ? null : id)

  const setActive = async (p: Provider, groupIdx: number) => {
    const grp = GROUPS[groupIdx]
    if (!grp.env_field) return
    const payload: Record<string, string> = { [grp.env_field]: p.env_value || p.image_backend_value || '' }
    if (p.model_field) payload[p.model_field] = getModel(p)
    await updateSettings(payload as any)
    setEnvSettings(prev => ({ ...prev, ...payload }))
    const aggType = groupIdx === 0 ? 'llm' : groupIdx === 1 ? 'image' : 'video'
    await deactivateAggType(aggType)
    fetchAggConfigsAndModels()
    toast(`已切换至 ${p.label}`, 'success')
  }

  const quickSave = (p: Provider, groupIdx: number) => {
    const payload: Record<string, string> = {}
    const k = val(p.key_field)
    if (k) payload[p.key_field] = k
    if (p.model_field) payload[p.model_field] = getModel(p)
    if (p.url_field) { const u = val(p.url_field); if (u) payload[p.url_field] = u }
    if (p.env_value) payload[GROUPS[groupIdx].env_field] = p.env_value
    if (p.image_backend_value) payload['image_backend'] = p.image_backend_value
    updateSettings(payload as any).then(() => {
      toast('已保存', 'success')
    })
  }

  const handleTest = async (p: Provider) => {
    if (!p.test_backend) return
    setTesting(true)
    setTestResult(null)
    const k = val(p.key_field)
    const m = getModel(p)
    if (!k) { setTestResult({ success: false, message: '请先填写 API Key' }); setTesting(false); return }
    const result = await testLLM(p.test_backend, k, m)
    setTestResult({ success: result.success, message: result.success ? result.response! : result.error! })
    setTesting(false)
  }

  const grp = GROUPS[activeTab]

  return (
    <div className="min-h-screen relative overflow-hidden">
      <div className="fixed inset-0 pointer-events-none">
        <div className="absolute -bottom-40 -right-40 w-96 h-96 rounded-full opacity-10"
          style={{ background: 'radial-gradient(circle, hsl(var(--primary)), transparent 70%)' }} />
      </div>

      <div className="max-w-4xl mx-auto px-6 py-10 relative z-10">
        <button onClick={() => navigate('/')} className="flex items-center gap-1.5 text-muted-foreground hover:text-foreground mb-8 transition-colors">
          <ArrowLeft className="w-4 h-4" /> 返回首页
        </button>

        <h1 className="text-2xl font-bold mb-2">⚙️ 设置</h1>
        <p className="text-sm text-muted-foreground mb-6">管理 AI 后端的 API Key 并选择当前使用的模型</p>

        {/* Tabs */}
        <div className="glass-card rounded-2xl p-1.5 mb-8 flex animate-fade-in-up">
          {GROUPS.map((g, i) => (
            <button key={g.name} onClick={() => { setActiveTab(i); setTestResult(null); setAggTestResultSet({}) }}
              className={`flex-1 flex items-center justify-center gap-2 py-3 px-4 rounded-xl text-sm font-medium transition-all ${
                activeTab === i ? 'bg-primary/20 text-primary shadow-sm' : 'text-muted-foreground hover:text-foreground'
              }`}>
              <span>{g.icon}</span>
              <span>{g.name}</span>
            </button>
          ))}
        </div>

        {/* Provider cards */}
        <div className="animate-fade-in-up" key={activeTab}>
          <div className="mb-3 flex items-center gap-2 mt-8">
            <h3 className="text-xs font-semibold text-muted-foreground">🔑 官网 API</h3>
            <div className="flex-1 h-px bg-border/50" />
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {grp.providers.map((p) => {
              const isExpanded = expandedId === p.id
              const active = isProviderActive(p, activeTab)
              const configured = hasKey(p)
              const model = getModel(p)

              return (
                <div key={p.id} className={`glass-card rounded-2xl overflow-hidden transition-all duration-300 ${active ? 'ring-2 ring-primary/40' : ''}`}>
                  <div className="p-5">
                    <div className="flex items-start justify-between mb-2">
                      <div className="flex-1 min-w-0">
                        <h3 className="font-semibold text-sm">{p.label}</h3>
                        <p className="text-[10px] text-muted-foreground truncate mt-0.5">{p.base_url || '自定义地址'}</p>
                      </div>
                      <div className={`flex items-center gap-1 badge ${
                        configured ? 'badge-success' : 'badge-warning'
                      } flex-shrink-0 ml-2`}>
                        {configured ? '已配' : '未配'}
                      </div>
                    </div>

                    {active && <p className="text-[10px] text-primary font-semibold mb-2">● 当前使用</p>}

                    {p.models.length > 0 && (
                      <div className="mb-2">
                        <select value={model} onChange={e => p.model_field && update(p.model_field, e.target.value)}
                          className="w-full bg-background border border-border rounded-lg px-2 py-1.5 text-xs">
                          {p.models.map(m => <option key={m} value={m}>{m}</option>)}
                        </select>
                      </div>
                    )}

                    <div className="flex items-center gap-1.5 mt-1">
                      <button onClick={() => expand(p.id)}
                        className={`flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-[10px] font-medium border transition-all ${
                          isExpanded ? 'bg-primary/15 text-primary border-primary/30' : 'border-border hover:border-primary/30 text-muted-foreground'
                        }`}>
                        <Settings className="w-3 h-3" /> {isExpanded ? '收起' : 'API Key'}
                      </button>
                      {configured && (
                        active ? (
                          <span className="flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-[10px] font-medium text-primary border border-primary/30 bg-primary/10">
                            <Check className="w-3 h-3" /> 使用中
                          </span>
                        ) : (
                          <button onClick={() => setActive(p, activeTab)}
                            className="flex items-center gap-1 px-2.5 py-1.5 rounded-lg border border-primary/30 text-[10px] text-primary hover:bg-primary/10 transition-colors">
                            <Check className="w-3 h-3" /> 使用
                          </button>
                        )
                      )}
                      {p.test_backend && (
                        <button onClick={() => handleTest(p)} disabled={testing}
                          className="flex items-center gap-1 px-2.5 py-1.5 rounded-lg border border-border text-[10px] hover:bg-background disabled:opacity-40 transition-colors ml-auto">
                          {testing ? <Loader2 className="w-2.5 h-2.5 animate-spin" /> : <Zap className="w-2.5 h-2.5" />}
                          测试
                        </button>
                      )}
                    </div>
                  </div>

                  {isExpanded && (
                    <div className="border-t border-border/50 bg-muted/50 p-4 space-y-3">
                      {p.url_field && (
                        <div>
                          <label className="text-[9px] text-muted-foreground mb-0.5 block">API 地址</label>
                          <input className="w-full bg-background border border-border rounded-lg px-3 py-2 text-xs font-mono"
                            placeholder="https://api.example.com/v1" value={val(p.url_field) || ''}
                            onChange={e => update(p.url_field, e.target.value)} />
                        </div>
                      )}

                      <div>
                        <label className="text-[9px] text-muted-foreground mb-0.5 block">{p.key_tip}</label>
                        <div className="relative">
                          <Lock className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3 h-3 text-muted-foreground" />
                          <input type={visibleKeyId === p.id ? 'text' : 'password'} className="w-full bg-background border border-border rounded-lg pl-8 pr-8 py-2 text-xs font-mono"
                            value={val(p.key_field)} onChange={e => update(p.key_field, e.target.value)} />
                          <button type="button" onClick={() => setVisibleKeyId(visibleKeyId === p.id ? null : p.id)}
                            className="absolute right-2 top-1/2 -translate-y-1/2 p-0.5 rounded text-muted-foreground hover:text-foreground transition-colors">
                            {visibleKeyId === p.id ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
                          </button>
                        </div>
                        {p.key_link && (
                          <a href={p.key_link} target="_blank" rel="noopener noreferrer"
                            className="inline-flex items-center gap-0.5 text-[9px] text-primary hover:underline mt-0.5">
                            📡 获取 {p.label} Key <ExternalLink className="w-2.5 h-2.5" />
                          </a>
                        )}
                      </div>

                      <div className="flex items-center gap-1.5 pt-0.5">
                        <button onClick={() => quickSave(p, activeTab)}
                          className="btn-gradient flex items-center gap-1 px-3 py-1.5 rounded-lg text-[10px] font-medium disabled:opacity-50">
                          <Save className="w-2.5 h-2.5" /> 保存
                        </button>
                      </div>

                      {testResult && (
                        <div className={`flex items-center gap-1.5 p-2 rounded-lg text-[10px] ${
                          testResult.success ? 'bg-green-400/5 border border-green-400/20' : 'bg-red-400/5 border border-red-400/20'
                        }`}>
                          <span>{testResult.success ? '✅' : '❌'}</span>
                          <span className={testResult.success ? 'text-green-400' : 'text-red-400'}>{testResult.message}</span>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              )
            })}

            {/* 已添加的额外 API 配置卡片 */}
            {(() => {
              const provId = activeTab === 0 ? 'deepseek' : activeTab === 1 ? 'seedream' : 'seedance'
              const label = activeTab === 0 ? 'DeepSeek' : activeTab === 1 ? 'Seedream' : 'Seedance'
              return (providerConfigMap[provId] || []).filter(pc => !pc.active).map(pc => (
              <div key={pc.id} className="glass-card rounded-2xl overflow-hidden border border-dashed border-primary/20 opacity-80 hover:opacity-100 transition-opacity">
                <div className="p-5">
                  <div className="flex items-start justify-between mb-2">
                    <div className="flex-1 min-w-0">
                      <h3 className="font-semibold text-sm">🔑 {pc.name || label}</h3>
                      <p className="text-[10px] text-muted-foreground font-mono truncate mt-0.5">{pc.base_url || '默认地址'}</p>
                    </div>
                  </div>
                  <p className="text-[10px] text-muted-foreground font-mono truncate">...{pc.api_key?.slice(-8) || ''}</p>
                  <div className="flex items-center gap-1.5 mt-1">
                    <button onClick={() => { activateProviderConfig(pc.id).then(() => {
                      fetchProviderConfigs(provId).then(d => setProviderConfigMap(prev => ({ ...prev, [provId]: d.configs })))
                      deactivateAggType(typeKey)
                      const isImage = activeTab === 1
                      const isVideo = activeTab === 2
                      const keyField = isImage ? 'seedance_api_key' : isVideo ? 'seedance_api_key' : `${provId}_api_key`
                      const payload: Record<string, string> = {}
                      if (!isVideo) {
                        payload[activeTab === 0 ? 'llm_backend' : 'image_backend'] = provId
                      }
                      payload[keyField] = pc.api_key
                      updateSettings(payload as any)
                      setEnvSettings(prev => ({ ...prev, ...payload }))
                    })}}
                      className="flex items-center gap-1 px-2.5 py-1.5 rounded-lg border border-primary/30 text-[10px] text-primary hover:bg-primary/10 transition-colors">
                      <Check className="w-3 h-3" /> 使用
                    </button>
                    <button onClick={() => { if (!confirm('确定删除这个 API 配置？')) return; deleteProviderConfig(pc.id).then(() => fetchProviderConfigs(provId).then(d => setProviderConfigMap(prev => ({ ...prev, [provId]: d.configs })))) }}
                      className="flex items-center gap-1 px-2.5 py-1.5 rounded-lg border border-red-400/30 text-[10px] text-red-400 hover:bg-red-400/10 transition-colors">
                      <Trash2 className="w-3 h-3" /> 删除
                    </button>
                  </div>
                </div>
              </div>
              ))
            })()}

            {/* 添加官网 API 卡片 */}
            {!provNewConfigId ? (
              <button onClick={() => setProvNewConfigId('__new_provider__')}
                className="w-full py-6 rounded-2xl border-2 border-dashed border-primary/30 text-sm text-primary hover:bg-primary/5 transition-colors glass-card">
                <Plus className="w-4 h-4 inline mr-1" /> 添加官网 API
              </button>
            ) : (
              <div className="glass-card rounded-2xl overflow-hidden">
                <div className="p-5">
                  <h4 className="text-xs font-medium text-muted-foreground mb-3">新建官网 API</h4>
                  <div className="space-y-2">
                    <input className="w-full bg-background border border-border rounded-lg px-3 py-2 text-xs"
                      placeholder="官网名称（如: OpenAI）" value={provNewProvider} onChange={e => setProvNewProvider(e.target.value)} />
                    <input className="w-full bg-background border border-border rounded-lg px-3 py-2 text-xs font-mono"
                      placeholder="API 地址" value={provNewUrl} onChange={e => setProvNewUrl(e.target.value)} />
                    <input className="w-full bg-background border border-border rounded-lg px-3 py-2 text-xs font-mono"
                      placeholder="API Key" value={provNewKey} onChange={e => setProvNewKey(e.target.value)} />
                    <ModelSelector type={typeKey} value={provNewModel} onChange={setProvNewModel} />
                    <div className="flex items-center gap-1.5">
                      <button onClick={async () => {
                        const pid = provNewProvider
                        await createProviderConfig({
                          provider_id: pid,
                          api_key: provNewKey,
                          model: provNewModel,
                          base_url: provNewUrl,
                          name: pid,
                        })
                        setProvNewConfigId(null)
                        setProvNewKey(''); setProvNewModel(''); setProvNewUrl(''); setProvNewProvider('')
                        fetchProviderConfigs(pid).then(d => setProviderConfigMap(prev => ({ ...prev, [pid]: d.configs })))
                        toast('已添加', 'success')
                      }} disabled={!provNewKey || !provNewUrl || !provNewProvider}
                        className="btn-gradient flex items-center gap-1 px-3 py-1.5 rounded-lg text-[10px] font-medium">
                        <Check className="w-3 h-3" /> 添加
                      </button>
                      <button onClick={() => setProvNewConfigId(null)}
                        className="px-3 py-1.5 rounded-lg border border-border text-[10px] hover:bg-background">
                        取消
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            )}

          </div>

          {/* 聚合平台区域 */}
          <div className="mb-3 flex items-center gap-2 mt-8">
            <h3 className="text-xs font-semibold text-muted-foreground">🌐 聚合平台</h3>
            <div className="flex-1 h-px bg-border/50" />
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mb-10">

            {/* 聚合平台配置 — 每个独立卡片 */}
            {aggConfigs.map(cfg => {
              const isEditing = editingAggId === cfg.id
              const keyHint = cfg.api_key?.length > 8 ? `...${cfg.api_key.slice(-8)}` : '已配置'
              return (
              <div key={cfg.id} className={`glass-card rounded-2xl overflow-hidden transition-all duration-300 ${cfg.active ? 'ring-2 ring-primary/40' : ''}`}>
                <div className="p-4">
                  {/* Header */}
                  <div className="flex items-center gap-2 mb-2">
                    <span className="text-sm">🌐</span>
                    {isEditing ? (
                      <input className="flex-1 bg-background border border-border rounded-lg px-2 py-1 text-xs"
                        value={editAggName} onChange={e => setEditAggName(e.target.value)} placeholder="名称" />
                    ) : (
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-1.5">
                          <span className="font-semibold text-xs truncate">{cfg.name}</span>
                          {cfg.active && <span className="text-[8px] text-primary font-semibold px-1.5 py-0.5 rounded-full bg-primary/10">当前</span>}
                        </div>
                      </div>
                    )}
                    {!isEditing && (
                      <button onClick={() => {
                        setEditingAggId(cfg.id)
                        setEditAggName(cfg.name || '')
                        setEditAggUrl(cfg.base_url || '')
                        setEditAggKey(cfg.api_key || '')
                      }} className="p-1 rounded-lg hover:bg-muted text-muted-foreground hover:text-foreground transition-colors">
                        <Settings className="w-3 h-3" />
                      </button>
                    )}
                  </div>

                  {/* URL and key row */}
                  {isEditing ? (
                    <div className="space-y-1.5 mb-2">
                      <input className="w-full bg-background border border-border rounded-lg px-2 py-1.5 text-[10px] font-mono"
                        value={editAggUrl} onChange={e => setEditAggUrl(e.target.value)} placeholder="API 地址" />
                      <div className="relative">
                        <Lock className="absolute left-2 top-1/2 -translate-y-1/2 w-3 h-3 text-muted-foreground" />
                        <input type={visibleAggKey === cfg.id ? 'text' : 'password'} className="w-full bg-background border border-border rounded-lg pl-7 pr-7 py-1.5 text-[10px] font-mono"
                          value={editAggKey} onChange={e => setEditAggKey(e.target.value)} placeholder="API Key" />
                        <button type="button" onClick={() => setVisibleAggKey(visibleAggKey === cfg.id ? null : cfg.id)}
                          className="absolute right-1.5 top-1/2 -translate-y-1/2 p-0.5 rounded text-muted-foreground hover:text-foreground transition-colors">
                          {visibleAggKey === cfg.id ? <EyeOff className="w-3 h-3" /> : <Eye className="w-3 h-3" />}
                        </button>
                      </div>
                    </div>
                  ) : (
                    <div className="flex items-center gap-2 mb-2">
                      <span className="text-[9px] text-muted-foreground font-mono truncate flex-1">{cfg.base_url}</span>
                      <button onClick={() => setVisibleAggKey(visibleAggKey === cfg.id ? null : cfg.id)}
                        className="text-[9px] text-muted-foreground font-mono bg-muted px-1.5 py-0.5 rounded flex items-center gap-1 hover:text-foreground transition-colors flex-shrink-0">
                        <Lock className="w-2.5 h-2.5" />
                        {visibleAggKey === cfg.id ? cfg.api_key : keyHint}
                        {visibleAggKey === cfg.id ? <EyeOff className="w-2.5 h-2.5" /> : <Eye className="w-2.5 h-2.5" />}
                      </button>
                    </div>
                  )}

                  {/* Model selector */}
                  <div className="flex items-center gap-1.5 mb-2">
                    <select value={aggSelectedFamily[cfg.id] || ''} onChange={e => setAggSelectedFamily(p => ({ ...p, [cfg.id]: e.target.value }))}
                      className="flex-1 bg-muted border border-border rounded-lg px-1.5 py-1 text-[9px] appearance-none min-w-0">
                      {(aggFamilies[cfg.id] || []).length === 0 && <option>加载中...</option>}
                      {(aggFamilies[cfg.id] || []).map(f => <option key={f.id} value={f.id}>{f.name}</option>)}
                    </select>
                    <select value={cfg.model || ''} onChange={async e => {
                      await updateAggConfig(cfg.id, { model: e.target.value })
                      fetchAggConfigsAndModels()
                    }}
                      className="flex-1 bg-muted border border-border rounded-lg px-1.5 py-1 text-[9px] appearance-none min-w-0">
                      {!cfg.model && <option value="">版本</option>}
                      {(() => {
                        const family = (aggFamilies[cfg.id] || []).find(f => f.id === aggSelectedFamily[cfg.id])
                        return (family?.versions || []).map(v => <option key={v.value} value={v.value}>{v.label}</option>)
                      })()}
                    </select>
                    {aggLoadingModels[cfg.id] && <Loader2 className="w-2.5 h-2.5 animate-spin text-muted-foreground flex-shrink-0" />}
                    <button onClick={() => loadAggModels([cfg])} disabled={aggLoadingModels[cfg.id]}
                      className="p-1 rounded-lg border border-border hover:bg-muted text-muted-foreground hover:text-foreground transition-colors flex-shrink-0">
                      <RefreshCw className="w-2.5 h-2.5" />
                    </button>
                  </div>

                  {/* Actions */}
                  {isEditing ? (
                    <div className="flex items-center gap-1.5 pt-1 border-t border-border/40">
                      <button onClick={async () => {
                        await updateAggConfig(cfg.id, { name: editAggName, base_url: editAggUrl, api_key: editAggKey })
                        setEditingAggId(null)
                        fetchAggConfigsAndModels()
                      }} disabled={!editAggName || !editAggUrl || !editAggKey}
                        className="btn-gradient flex items-center gap-1 px-2.5 py-1 rounded-lg text-[9px] font-medium">
                        <Save className="w-2.5 h-2.5" /> 保存
                      </button>
                      <button onClick={() => setEditingAggId(null)}
                        className="px-2.5 py-1 rounded-lg border border-border text-[9px] hover:bg-muted transition-colors">
                        取消
                      </button>
                    </div>
                  ) : (
                    <div className="flex items-center gap-1 pt-1 border-t border-border/40">
                      <button onClick={async () => {
                        setAggTestingSet(p => ({ ...p, [cfg.id]: true }))
                        const r = await testAggConfig({ base_url: cfg.base_url, api_key: cfg.api_key })
                        setAggTestResultSet(p => ({ ...p, [cfg.id]: r }))
                        setAggTestingSet(p => ({ ...p, [cfg.id]: false }))
                      }} disabled={aggTestingSet[cfg.id]}
                        className="flex items-center gap-0.5 px-2 py-1 rounded-lg border border-border text-[9px] hover:bg-muted disabled:opacity-40 transition-colors">
                        {aggTestingSet[cfg.id] ? <Loader2 className="w-2.5 h-2.5 animate-spin" /> : <Zap className="w-2.5 h-2.5" />}
                        测试
                      </button>
                      {cfg.active ? (
                        <span className="flex items-center gap-0.5 px-2 py-1 rounded-lg text-[9px] font-medium text-primary border border-primary/30 bg-primary/10">
                          <Check className="w-2.5 h-2.5" /> 使用中
                        </span>
                      ) : (
                        <button onClick={() => { activateAggConfig(cfg.id).then(() => fetchAggConfigsAndModels()) }}
                          className="flex items-center gap-0.5 px-2 py-1 rounded-lg border border-accent/30 text-[9px] text-accent hover:bg-accent/10 transition-colors">
                          <Check className="w-2.5 h-2.5" /> 使用
                        </button>
                      )}
                      <button onClick={() => { if (!confirm('确定删除？')) return; deleteAggConfig(cfg.id).then(() => fetchAggConfigsAndModels()) }}
                        className="flex items-center gap-0.5 px-2 py-1 rounded-lg border border-red-400/30 text-[9px] text-red-400 hover:bg-red-400/10 transition-colors ml-auto">
                        <Trash2 className="w-2.5 h-2.5" /> 删除
                      </button>
                    </div>
                  )}

                  {aggTestResultSet[cfg.id] && (
                    <div className={`flex items-center gap-1 p-1.5 mt-1.5 rounded-lg text-[9px] ${aggTestResultSet[cfg.id].success ? 'bg-green-400/5 border border-green-400/20' : 'bg-red-400/5 border border-red-400/20'}`}>
                      <span>{aggTestResultSet[cfg.id].success ? '✅' : '❌'}</span>
                      <span className={aggTestResultSet[cfg.id].success ? 'text-green-400' : 'text-red-400'}>{aggTestResultSet[cfg.id].message || aggTestResultSet[cfg.id].error}</span>
                    </div>
                  )}
                </div>
              </div>
            )
            })}

            {/* 添加聚合平台卡片 — 独立的虚线卡片 */}
            {!newAggExpanded ? (
              <button onClick={() => setNewAggExpanded(true)}
                className="w-full py-6 rounded-2xl border-2 border-dashed border-primary/30 text-sm text-primary hover:bg-primary/5 transition-colors glass-card">
                <Plus className="w-4 h-4 inline mr-1" /> 添加聚合平台
              </button>
            ) : (
              <div className="glass-card rounded-2xl overflow-hidden">
                <div className="p-5">
                  <h4 className="text-xs font-medium text-muted-foreground mb-3">新建聚合平台配置</h4>
                  <div className="space-y-2">
                    <input className="w-full bg-background border border-border rounded-lg px-3 py-2 text-xs"
                      placeholder="名称（如: 聚合A）" value={newAggName} onChange={e => setNewAggName(e.target.value)} />
                    <input className="w-full bg-background border border-border rounded-lg px-3 py-2 text-xs font-mono"
                      placeholder="API 地址（如: https://api.xxx.com/v1）" value={newAggUrl} onChange={e => setNewAggUrl(e.target.value)} />
                    <div className="relative">
                      <Lock className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3 h-3 text-muted-foreground" />
                      <input type="password" className="w-full bg-background border border-border rounded-lg pl-8 pr-8 py-2 text-xs font-mono"
                        placeholder="API Key" value={newAggKey} onChange={e => setNewAggKey(e.target.value)} />
                    </div>
                    <ModelSelector type={typeKey} value={newAggModel} onChange={setNewAggModel} />
                    <div className="flex items-center gap-1.5">
                      <button disabled={aggTestingSet['__new__']}
                        onClick={async () => {
                          setAggTestingSet(p => ({ ...p, ['__new__']: true }))
                          const r = await testAggConfig({ base_url: newAggUrl, api_key: newAggKey })
                          setAggTestResultSet(p => ({ ...p, ['__new__']: r }))
                          setAggTestingSet(p => ({ ...p, ['__new__']: false }))
                        }}
                        className="flex items-center gap-1 px-2.5 py-1.5 rounded-lg border border-border text-[10px] hover:bg-background">
                        {aggTestingSet['__new__'] ? <Loader2 className="w-2.5 h-2.5 animate-spin" /> : <Zap className="w-2.5 h-2.5" />}
                        测试
                      </button>
                      <button onClick={async () => {
                        await createAggConfig({
                          name: newAggName, base_url: newAggUrl, api_key: newAggKey,
                          type: typeKey, model: newAggModel,
                        })
                        setNewAggExpanded(false)
                        setNewAggName(''); setNewAggUrl(''); setNewAggKey(''); setNewAggModel('')
                        fetchAggConfigsAndModels()
                        toast('已添加', 'success')
                      }} disabled={!newAggName || !newAggUrl || !newAggKey}
                        className="btn-gradient flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-[10px] font-medium">
                        <Check className="w-2.5 h-2.5" /> 添加
                      </button>
                      <button onClick={() => setNewAggExpanded(false)}
                        className="px-2.5 py-1.5 rounded-lg border border-border text-[10px] hover:bg-background">
                        取消
                      </button>
                    </div>
                    {aggTestResultSet['__new__'] && (
                      <div className={`flex items-center gap-1.5 p-2 rounded-lg text-[10px] ${aggTestResultSet['__new__'].success ? 'bg-green-400/5 border border-green-400/20' : 'bg-red-400/5 border border-red-400/20'}`}>
                        <span>{aggTestResultSet['__new__'].success ? '✅' : '❌'}</span>
                        <span className={aggTestResultSet['__new__'].success ? 'text-green-400' : 'text-red-400'}>{aggTestResultSet['__new__'].message || aggTestResultSet['__new__'].error}</span>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Save bar */}
        <div className="sticky bottom-6 glass-card rounded-2xl p-4 flex items-center justify-between">
          <p className="text-xs text-muted-foreground">每个卡片内点「保存」单独生效</p>
          <div className="flex items-center gap-3">
            {Object.keys(dirtyFields).length > 0 && (
              <button onClick={async () => { setSaving(true); await updateSettings(dirtyFields as any); setDirtyFields({}); toast('已保存', 'success'); setSaving(false) }} disabled={saving}
                className="btn-gradient flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm font-medium disabled:opacity-50">
                {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
                保存所有更改
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
