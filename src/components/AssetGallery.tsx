import { useState } from 'react'
import { Loader2 } from 'lucide-react'
import type { EntityImagesMap } from '../lib/types'

interface AssetGalleryProps {
  projectName: string
  projectImages: EntityImagesMap
  loading?: boolean
  onPreview?: (url: string) => void
  onConfirmVersion?: (type: string, name: string, version: string) => void
  onDeleteVersion?: (type: string, name: string, version: string) => void
}

export default function AssetGallery({
  projectName,
  projectImages,
  loading,
  onPreview,
  onConfirmVersion,
  onDeleteVersion,
}: AssetGalleryProps) {
  const [expandedVersions, setExpandedVersions] = useState<Record<string, boolean>>({})
  const [selectionMode, setSelectionMode] = useState(false)
  const [selectedVersions, setSelectedVersions] = useState<Set<string>>(new Set())

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="w-5 h-5 animate-spin text-muted-foreground" />
        <span className="ml-2 text-sm text-muted-foreground">加载中...</span>
      </div>
    )
  }

  const charNames = Object.keys(projectImages.characters)
  const sceneNames = Object.keys(projectImages.scenes)

  if (charNames.length === 0 && sceneNames.length === 0) {
    return (
      <div className="glass-card rounded-xl p-6 text-center">
        <p className="text-sm text-muted-foreground">暂无素材</p>
      </div>
    )
  }

  const renderEntityCard = (name: string, data: any, type: string) => {
    const imgs = data.images || []
    const versions = data.versions || {}
    const versionKeys = Object.keys(versions).sort()
    const key = `${type}-${name}`
    const expanded = expandedVersions[key]

    return (
      <div key={name} className="bg-muted/40 rounded-xl p-3 border border-border/30">
        <div className="flex items-center gap-2 mb-2">
          <span className="text-xs font-medium truncate flex-1">{name}</span>
          {imgs.length > 0 && <span className="text-green-400 text-[10px]" title="已确认">✓</span>}
        </div>
        {imgs.length > 0 && (
          <div className="flex gap-1.5 mb-2">
            {imgs.slice(0, 3).map((img: any, i: number) => (
              <img key={i} src={img.url} alt={name}
                className="w-12 h-12 rounded-lg object-cover border border-border/40 cursor-pointer hover:ring-2 hover:ring-primary/50"
                onClick={() => onPreview?.(img.url)} />
            ))}
          </div>
        )}
        {versionKeys.length > 0 && (
          <div className="space-y-1">
            <button onClick={() => setExpandedVersions(prev => ({ ...prev, [key]: !prev[key] }))}
              className="text-[10px] text-muted-foreground hover:text-primary flex items-center gap-1 px-1 py-0.5 rounded">
              {expanded ? '▼' : '▶'} v{versionKeys.join(' v')}
            </button>
            {expanded && versionKeys.map(vk => {
              const v = versions[vk]
              return (
                <div key={vk} className="pl-2 border-l-2 border-border/40">
                  <div className="flex items-center justify-between mb-1">
                    {selectionMode && (
                      <input type="checkbox" checked={selectedVersions.has(`${type}:${name}:${vk}`)}
                        onChange={() => {
                          const key = `${type}:${name}:${vk}`
                          const next = new Set(selectedVersions)
                          if (next.has(key)) next.delete(key); else next.add(key)
                          setSelectedVersions(next)
                        }}
                        className="mr-1 accent-primary"
                      />
                    )}
                    <span className="text-[10px] text-muted-foreground">v{vk} {v.confirmed && <span className="text-green-400">✓</span>}</span>
                    {onDeleteVersion && (
                      <button onClick={() => onDeleteVersion(type, name, vk)}
                        className="text-[10px] text-red-400 hover:text-red-300 px-1 rounded hover:bg-red-500/10">删除</button>
                    )}
                  </div>
                  <div className="flex gap-1 overflow-x-auto">
                    {v.images.map((img: any, j: number) => (
                      <img key={j} src={img.url} alt=""
                        className="w-9 h-9 rounded object-cover border border-border/40 cursor-pointer hover:border-primary/50 flex-shrink-0"
                        onClick={() => onPreview?.(img.url)} title={img.name} />
                    ))}
                  </div>
                  {!v.confirmed && onConfirmVersion && (
                    <button onClick={() => onConfirmVersion(type, name, vk)}
                      className="mt-1 w-full text-[10px] py-0.5 rounded bg-primary/20 text-primary hover:bg-primary/30 transition-colors">确认此版</button>
                  )}
                </div>
              )
            })}
          </div>
        )}
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {(charNames.length > 0 || sceneNames.length > 0) && (
        <div className="flex items-center justify-between mb-3">
          <p className="text-xs text-muted-foreground font-medium">素材库</p>
          <div className="flex gap-2">
            {!selectionMode ? (
              <button onClick={() => setSelectionMode(true)}
                className="text-[10px] text-muted-foreground hover:text-red-400 px-2 py-0.5 rounded hover:bg-red-500/5 transition-all">
                批量删除
              </button>
            ) : (
              <>
                <span className="text-[10px] text-muted-foreground">已选 {selectedVersions.size} 项</span>
                <button onClick={() => {
                  selectedVersions.forEach(key => {
                    const [type, name, version] = key.split(':')
                    onDeleteVersion?.(type, name, version)
                  })
                  setSelectedVersions(new Set())
                  setSelectionMode(false)
                }} disabled={selectedVersions.size === 0}
                  className="text-[10px] text-red-400 hover:text-red-300 px-2 py-0.5 rounded hover:bg-red-500/10 transition-all disabled:opacity-30">
                  删除选中
                </button>
                <button onClick={() => { setSelectionMode(false); setSelectedVersions(new Set()) }}
                  className="text-[10px] text-muted-foreground px-2 py-0.5 rounded hover:bg-muted transition-all">
                  取消
                </button>
              </>
            )}
          </div>
        </div>
      )}
      {charNames.length > 0 && (
        <div>
          <p className="text-xs text-muted-foreground font-medium mb-2">👤 角色</p>
          <div className="grid grid-cols-2 gap-2">
            {charNames.map(n => renderEntityCard(n, projectImages.characters[n], 'characters'))}
          </div>
        </div>
      )}
      {sceneNames.length > 0 && (
        <div>
          <p className="text-xs text-muted-foreground font-medium mb-2">🌆 场景</p>
          <div className="grid grid-cols-2 gap-2">
            {sceneNames.map(n => renderEntityCard(n, projectImages.scenes[n], 'scenes'))}
          </div>
        </div>
      )}
    </div>
  )
}
