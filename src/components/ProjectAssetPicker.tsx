import { useState } from 'react'
import type { VisualAsset } from '../lib/types'

interface ProjectAssetPickerProps {
  projectName: string
  assets: { characters: VisualAsset[]; scenes: VisualAsset[] }
  entityImages: { characters: Record<string, { name: string; url: string }[]>; scenes: Record<string, { name: string; url: string }[]> }
  selectedEntity: string | null
  onSelectEntity: (name: string | null) => void
  onAddAsset: (url: string) => void
}

export default function ProjectAssetPicker({
  projectName,
  assets,
  entityImages,
  selectedEntity,
  onSelectEntity,
  onAddAsset,
}: ProjectAssetPickerProps) {
  const [view, setView] = useState<'characters' | 'scenes'>('characters')

  const chars = assets.characters || []
  const scns = assets.scenes || []

  const currentImages = selectedEntity
    ? (view === 'characters'
        ? (entityImages.characters[selectedEntity] || [])
        : (entityImages.scenes[selectedEntity] || []))
    : []

  return (
    <div className="glass-card rounded-xl p-4">
      <h3 className="text-xs font-medium text-muted-foreground mb-3">{`📂 ${projectName} 素材库`}</h3>

      <div className="flex gap-2 mb-3">
        <button onClick={() => setView('characters')}
          className={`text-[10px] px-2.5 py-1 rounded-lg transition-all ${view === 'characters' ? 'bg-primary/15 text-primary font-medium' : 'text-muted-foreground hover:text-foreground hover:bg-muted'}`}>
          {`👤 角色 (${chars.length})`}
        </button>
        <button onClick={() => setView('scenes')}
          className={`text-[10px] px-2.5 py-1 rounded-lg transition-all ${view === 'scenes' ? 'bg-primary/15 text-primary font-medium' : 'text-muted-foreground hover:text-foreground hover:bg-muted'}`}>
          {`🌆 场景 (${scns.length})`}
        </button>
      </div>

      <div className="flex flex-wrap gap-1.5 mb-3">
        {(view === 'characters' ? chars : scns).map(item => (
          <button key={item.name} onClick={() => onSelectEntity(selectedEntity === item.name ? null : item.name)}
            className={`text-[10px] px-2 py-1 rounded-lg transition-all ${
              selectedEntity === item.name
                ? 'bg-primary/20 text-primary font-medium ring-1 ring-primary/40'
                : 'bg-muted/50 text-muted-foreground hover:bg-muted'
            }`}>
            {item.name}
          </button>
        ))}
      </div>

      {selectedEntity && currentImages.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {currentImages.map((img, i) => (
            <img key={i} src={img.url} alt={img.name}
              className="w-16 h-16 object-contain rounded-lg bg-muted border border-border cursor-pointer hover:ring-2 hover:ring-primary/50 transition-all"
              onClick={() => onAddAsset(img.url)} title={`点击添加到参考: ${img.name}`} />
          ))}
        </div>
      )}
      {selectedEntity && currentImages.length === 0 && (
        <p className="text-[10px] text-muted-foreground">该实体暂无生成图片</p>
      )}
    </div>
  )
}
