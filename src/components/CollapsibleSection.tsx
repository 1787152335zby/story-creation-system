import { useState } from 'react'
import { ChevronDown, ChevronRight } from 'lucide-react'

interface CollapsibleSectionProps {
  title: string
  defaultOpen?: boolean
  actions?: React.ReactNode
  children: React.ReactNode
}

export default function CollapsibleSection({ title, defaultOpen = false, actions, children }: CollapsibleSectionProps) {
  const [open, setOpen] = useState(defaultOpen)

  return (
    <div>
      <div
        onClick={() => setOpen(!open)}
        className="flex items-center justify-between cursor-pointer select-none py-1 group"
      >
        <div className="flex items-center gap-1">
          <span className="text-muted-foreground group-hover:text-foreground transition-colors">
            {open ? <ChevronDown className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />}
          </span>
          <span className="text-[10px] font-medium text-muted-foreground group-hover:text-foreground transition-colors">
            {title}
          </span>
        </div>
        {actions && <div onClick={e => e.stopPropagation()}>{actions}</div>}
      </div>
      {open && <div className="mt-1">{children}</div>}
    </div>
  )
}
