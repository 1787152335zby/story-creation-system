import { useState } from 'react'
import { Save } from 'lucide-react'
import { useToast } from './Toast'

interface Props {
  show: boolean
  defaultName: string
  onClose: () => void
  onSave: (templateName: string) => Promise<void>
}

export default function TemplateModal({ show, defaultName, onClose, onSave }: Props) {
  const { toast } = useToast()
  const [name, setName] = useState(defaultName)
  const [saving, setSaving] = useState(false)

  if (!show) return null

  const handleSave = async () => {
    if (!name.trim()) return
    setSaving(true)
    try {
      await onSave(name.trim())
      toast('已保存为模板', 'success')
      onClose()
    } catch (e: any) {
      toast(e.message || '保存失败', 'error')
    }
    setSaving(false)
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm" onClick={onClose}>
      <div className="glass-card rounded-2xl p-6 w-full max-w-sm mx-4 animate-fade-in-up" onClick={e => e.stopPropagation()}>
        <h3 className="font-bold text-lg mb-1">💾 保存为模板</h3>
        <p className="text-sm text-muted-foreground mb-4">将当前项目的风格配置保存为模板，新建项目时可一键复用</p>
        <input className="w-full bg-muted border border-border rounded-xl px-4 py-3 text-sm mb-4"
          placeholder="模板名称" value={name} onChange={e => setName(e.target.value)} autoFocus disabled={saving} />
        <div className="flex justify-end gap-3">
          <button onClick={onClose} disabled={saving}
            className="px-5 py-2.5 rounded-xl border border-border text-sm hover:bg-muted transition-colors disabled:opacity-50">取消</button>
          <button onClick={handleSave} disabled={saving || !name.trim()}
            className="btn-gradient px-6 py-2.5 rounded-xl text-sm font-medium disabled:opacity-50">
            <Save className="w-4 h-4 inline mr-1" />保存模板
          </button>
        </div>
      </div>
    </div>
  )
}
