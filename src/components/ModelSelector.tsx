import { useState, useEffect } from 'react'
import { Loader2, RefreshCw } from 'lucide-react'
import { fetchModelsFamilies } from '../lib/api'
import type { ModelFamily } from '../lib/api'

interface Props {
  type: 'llm' | 'image' | 'video'
  value: string
  onChange: (model: string) => void
  className?: string
}

export default function ModelSelector({ type, value, onChange, className = '' }: Props) {
  const [families, setFamilies] = useState<ModelFamily[]>([])
  const [loading, setLoading] = useState(true)
  const [selectedFamily, setSelectedFamily] = useState('')
  const [customInput, setCustomInput] = useState('')
  const [useCustom, setUseCustom] = useState(false)

  const loadFamilies = async (force = false) => {
    setLoading(true)
    try {
      const { families } = await fetchModelsFamilies(type as 'image' | 'video')
      setFamilies(families || [])
      if (families?.length > 0 && !selectedFamily) {
        setSelectedFamily(families[0].id)
      }
    } catch {
      setFamilies([])
    }
    setLoading(false)
  }

  useEffect(() => {
    loadFamilies()
  }, [type])

  useEffect(() => {
    if (value && families.length > 0) {
      for (const f of families) {
        if (f.versions.some(v => v.value === value)) {
          setSelectedFamily(f.id)
          setUseCustom(false)
          return
        }
      }
      setUseCustom(true)
      setCustomInput(value)
    }
  }, [value, families])

  const currentFamily = families.find(f => f.id === selectedFamily)

  const handleFamilyChange = (fid: string) => {
    setSelectedFamily(fid)
    setUseCustom(false)
    const family = families.find(f => f.id === fid)
    if (family && family.versions.length > 0) {
      onChange(family.versions[0].value)
    }
  }

  return (
    <div className={`flex items-stretch gap-1.5 ${className}`}>
      {!useCustom ? (
        <>
          <select value={selectedFamily} onChange={e => handleFamilyChange(e.target.value)}
            className="min-w-0 flex-1 bg-muted border border-border rounded-xl px-2 py-2 text-xs">
            {loading ? <option>加载中...</option>
            : families.length === 0 ? <option>无可用模型</option>
            : families.map(f => (
                <option key={f.id} value={f.id}>{f.name} ({f.versions.length})</option>
              ))}
          </select>
          <select value={value} onChange={e => onChange(e.target.value)}
            className="min-w-0 flex-[2] bg-muted border border-border rounded-xl px-2 py-2 text-xs"
            disabled={!selectedFamily || loading}>
            {loading ? <option>加载中...</option>
            : !currentFamily ? <option>选择家族</option>
            : currentFamily.versions.length === 0 ? <option>无版本</option>
            : currentFamily.versions.map(v => <option key={v.value} value={v.value} className="text-xs">{v.label}</option>)}
          </select>
          {loading && <Loader2 className="w-3.5 h-3.5 animate-spin text-muted-foreground my-auto flex-shrink-0" />}
          <button onClick={() => { setUseCustom(true); setCustomInput(value) }} title="自定义输入"
            className="p-1.5 rounded-lg border border-border hover:bg-background text-muted-foreground hover:text-foreground transition-colors flex-shrink-0 my-auto text-[10px]">
            ✏️
          </button>
          <button onClick={() => loadFamilies(true)} title="刷新模型列表"
            className="p-1.5 rounded-lg border border-border hover:bg-background text-muted-foreground hover:text-foreground transition-colors flex-shrink-0 my-auto">
            <RefreshCw className="w-3 h-3" />
          </button>
        </>
      ) : (
        <>
          <input value={customInput} onChange={e => { setCustomInput(e.target.value); onChange(e.target.value) }}
            placeholder="输入模型名" className="min-w-0 flex-1 bg-muted border border-border rounded-xl px-2 py-2 text-xs font-mono" />
          <button onClick={() => { setUseCustom(false); if (families.length > 0) handleFamilyChange(families[0].id) }}
            className="p-1.5 rounded-lg border border-border hover:bg-background text-muted-foreground hover:text-foreground transition-colors flex-shrink-0 my-auto text-[10px] whitespace-nowrap px-2">
            列表
          </button>
        </>
      )}
    </div>
  )
}
