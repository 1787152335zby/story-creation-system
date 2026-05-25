import { X, Trash2 } from 'lucide-react'

interface ConfirmModalProps {
  icon?: React.ReactNode
  title: string
  message: string
  confirmText?: string
  cancelText?: string
  confirmColor?: string
  onConfirm: () => void | Promise<void>
  onCancel: () => void
}

export default function ConfirmModal({
  icon,
  title,
  message,
  confirmText = '确认删除',
  cancelText = '取消',
  confirmColor = 'bg-red-500 hover:bg-red-600',
  onConfirm,
  onCancel,
}: ConfirmModalProps) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm" onClick={onCancel}>
      <div className="bg-background border border-border rounded-2xl p-6 w-full max-w-sm mx-4 shadow-2xl" onClick={e => e.stopPropagation()}>
        <div className="flex items-center gap-3 mb-4">
          {icon || (
            <div className="w-10 h-10 rounded-xl bg-red-500/10 flex items-center justify-center">
              <Trash2 className="w-5 h-5 text-red-400" />
            </div>
          )}
          <div>
            <h3 className="font-semibold text-sm">{title}</h3>
            <p className="text-xs text-muted-foreground">此操作不可撤销</p>
          </div>
          <button onClick={onCancel} className="ml-auto p-1 rounded-lg hover:bg-muted text-muted-foreground">
            <X className="w-4 h-4" />
          </button>
        </div>
        <p className="text-sm mb-6">{message}</p>
        <div className="flex gap-2 justify-end">
          <button onClick={onCancel}
            className="px-4 py-2 rounded-xl border border-border text-sm hover:bg-muted transition-colors">{cancelText}</button>
          <button onClick={onConfirm}
            className={`px-4 py-2 rounded-xl text-white text-sm transition-colors ${confirmColor}`}>{confirmText}</button>
        </div>
      </div>
    </div>
  )
}
