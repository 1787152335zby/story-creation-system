import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ArrowLeft, Download, Trash2, Loader2 } from 'lucide-react'
import Starfield from '../components/Starfield'
import ConfirmModal from '../components/ConfirmModal'
import { fetchGenerationHistory, deleteGeneratedFile, fetchGenerationHistoryItem } from '../lib/api'
import ImagePreview from '../components/ImagePreview'
import { useToast } from '../components/Toast'
import type { HistoryEntry } from '../lib/types'

type MainTab = 'all' | 'images' | 'videos'
type SubFilter = 'free' | 'project'

export default function HistoryPage() {
  const navigate = useNavigate()
  const { toast } = useToast()
  const [loading, setLoading] = useState(true)
  const [freeImages, setFreeImages] = useState<HistoryEntry[]>([])
  const [projectImages, setProjectImages] = useState<HistoryEntry[]>([])
  const [videos, setVideos] = useState<HistoryEntry[]>([])
  const [videosFree, setVideosFree] = useState<HistoryEntry[]>([])
  const [videosProject, setVideosProject] = useState<HistoryEntry[]>([])
  const [tab, setTab] = useState<MainTab>('all')
  const [imgFilter, setImgFilter] = useState<SubFilter>('free')
  const [videoFilter, setVideoFilter] = useState<SubFilter>('free')
  const [previewSrc, setPreviewSrc] = useState<string | null>(null)
  const [confirmDelete, setConfirmDelete] = useState<{ message: string; action: () => void } | null>(null)
  const [detail, setDetail] = useState<HistoryEntry | null>(null)

  const loadHistory = () => {
    setLoading(true)
    fetchGenerationHistory().then(h => {
      setFreeImages(h.images_free || [])
      setProjectImages(h.images_project || [])
      setVideosFree(h.videos_free || [])
      setVideosProject(h.videos_project || [])
      setVideos(h.videos || [])
    }).catch(() => toast('加载历史记录失败', 'error'))
    .finally(() => setLoading(false))
  }

  useEffect(() => { loadHistory() }, [])

  const allImages = [...freeImages, ...projectImages]
  const allVideos = [...videosFree, ...videosProject]

  const handleViewDetail = async (entry: HistoryEntry) => {
    try {
      const d = await fetchGenerationHistoryItem(entry.name)
      setDetail({ ...entry, ...d })
    } catch {
      setDetail(entry)
    }
  }

  const renderImageCard = (img: HistoryEntry) => {
    const src = img.url
    return (
      <div className="bg-muted rounded-xl overflow-hidden group relative cursor-pointer">
        <img src={src} alt="" className="w-full h-48 object-contain bg-white"
          onClick={() => setPreviewSrc(src)} />
        <div className="px-3 py-2 bg-card space-y-1">
          <p className="text-[10px] text-muted-foreground leading-tight truncate">
            {img.prompt ? img.prompt.slice(0, 50) + (img.prompt.length > 50 ? '...' : '') : '无 prompt'}
          </p>
          <div className="flex items-center justify-between gap-1">
            <span className="text-[10px] text-muted-foreground/60">{img.model || '-'} · {img.size || '-'}</span>
            <div className="flex gap-1">
              {img.reference_urls && img.reference_urls.length > 0 && (
                <span className="text-[10px] text-amber-400/70">📎{img.reference_urls.length}</span>
              )}
              {img.mode === 'project' && img.project_name && (
                <span className="text-[10px] text-primary/60" title={img.project_name}>📂</span>
              )}
            </div>
          </div>
        </div>
        <div className="absolute top-2 right-2 flex gap-1 opacity-0 group-hover:opacity-100 transition-all" onClick={e => e.stopPropagation()}>
          <button onClick={() => navigate('/image-gen', { state: { remix: img.name } })}
            className="p-1.5 rounded-lg bg-primary/80 hover:bg-primary text-white text-[10px] pointer-events-auto" title="画同款">
            画同款
          </button>
          <a href={img.url} download={img.name} className="p-1.5 rounded-lg bg-white/20 hover:bg-white/30 text-white pointer-events-auto" title="下载"
            onClick={e => e.stopPropagation()}>
            <Download className="w-3 h-3" />
          </a>
          <button onClick={async () => { setConfirmDelete({ message: '确认删除这张图片？', action: async () => { try { await deleteGeneratedFile(img.url); loadHistory() } catch {} } }) }}
            className="p-1.5 rounded-lg bg-red-500/20 hover:bg-red-500/30 text-white pointer-events-auto" title="删除">
            <Trash2 className="w-3 h-3" />
          </button>
        </div>
        <button onClick={e => { e.stopPropagation(); handleViewDetail(img) }}
          className="absolute bottom-12 right-2 text-[10px] px-1.5 py-0.5 rounded bg-black/40 text-white/70 hover:text-white opacity-0 group-hover:opacity-100 transition-all">
          详情
        </button>
      </div>
    )
  }

  const renderProjectGroups = (items: HistoryEntry[]) => {
    const groups: Record<string, HistoryEntry[]> = {}
    for (const item of items) {
      const key = item.project_name || '未分组'
      if (!groups[key]) groups[key] = []
      groups[key].push(item)
    }
    return Object.entries(groups).map(([projName, imgs]) => (
      <div key={projName} className="mb-6">
        <h3 className="text-sm font-semibold mb-3 flex items-center gap-2">
          <span>📂 {projName}</span>
          <span className="text-[10px] text-muted-foreground font-normal">({imgs.length} 张)</span>
        </h3>
        <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-4 gap-4">
          {imgs.map((img, i) => (
            <div key={img.name + '-' + i}>
              {renderImageCard(img)}
            </div>
          ))}
        </div>
      </div>
    ))
  }

  return (
    <div className="min-h-screen relative overflow-hidden">
      <Starfield />
      <div className="max-w-6xl mx-auto px-6 py-10 relative z-10">
        <button onClick={() => navigate('/home')} className="flex items-center gap-1.5 text-muted-foreground hover:text-foreground mb-8 transition-colors">
          <ArrowLeft className="w-4 h-4" /> 返回首页
        </button>

        <h1 className="text-2xl font-bold mb-2"><span className="gradient-text">📋 创作历史</span></h1>
        <p className="text-sm text-muted-foreground mb-6">浏览和管理所有生成的图片和视频</p>

        {/* 一级 Tabs */}
        <div className="flex gap-2 mb-4">
          {[
            { key: 'all', label: `全部` },
            { key: 'images', label: `图片 (${allImages.length})` },
            { key: 'videos', label: `视频 (${allVideos.length})` },
          ].map(t => (
            <button key={t.key} onClick={() => setTab(t.key as MainTab)}
              className={`px-4 py-2 rounded-xl text-xs font-medium transition-all ${
                tab === t.key ? 'bg-primary/20 text-primary border-2 border-primary/50' : 'border-2 border-border text-muted-foreground hover:border-primary/30'
              }`}>
              {t.label}
            </button>
          ))}
          <button onClick={loadHistory} className="ml-auto px-3 py-2 rounded-xl border border-border text-xs text-muted-foreground hover:text-foreground hover:border-primary/30 transition-all flex items-center gap-1">
            <Loader2 className={`w-3 h-3 ${loading ? 'animate-spin' : ''}`} /> 刷新
          </button>
        </div>

        {/* 二级筛选 Tabs */}
        {tab !== 'all' && (
          <div className="flex gap-2 mb-6">
            {[
              { key: 'free', label: '✏️ 自由模式' },
              { key: 'project', label: '📂 项目模式' },
            ].map(sf => {
              const activeFilter = tab === 'images' ? imgFilter : videoFilter
              const setFilter = tab === 'images' ? setImgFilter : setVideoFilter
              return (
                <button key={sf.key} onClick={() => setFilter(sf.key as SubFilter)}
                  className={`px-3 py-1.5 rounded-lg text-[11px] font-medium transition-all ${
                    activeFilter === sf.key ? 'bg-muted-foreground/20 text-foreground border border-muted-foreground/30' : 'text-muted-foreground/60 hover:text-muted-foreground border border-transparent'
                  }`}>
                  {sf.label}
                </button>
              )
            })}
          </div>
        )}

        {loading ? (
          <div className="flex items-center justify-center py-20">
            <Loader2 className="w-8 h-8 animate-spin text-muted-foreground" />
          </div>
        ) : tab === 'all' ? (
          /* ===== 全部 Tab ===== */
          <>
            {allImages.length === 0 && allVideos.length === 0 ? (
              <div className="text-center py-20 text-muted-foreground text-sm">暂无记录</div>
            ) : (
              <>
                {/* 图片区域 */}
                {allImages.length > 0 && (
                  <div>
                    <h2 className="text-base font-bold mb-4">🖼️ 图片</h2>
                    <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-4 gap-4">
                      {allImages.map((img, i) => (
                        <div key={img.name + '-' + i}>
                          {renderImageCard(img)}
                        </div>
                      ))}
                    </div>
                  </div>
                )}
                {/* 视频区域 */}
                {allVideos.length > 0 && (
                  <div className="mt-8">
                    <h2 className="text-base font-bold mb-4">🎬 视频</h2>
                    <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-4 gap-4">
                      {allVideos.map((v, i) => {
                        const isProject = v.mode === 'project' || videosProject.some(vp => vp.name === v.name)
                        return (
                          <div key={v.name + '-' + i} className="bg-muted rounded-xl overflow-hidden group relative">
                            <video src={v.url} controls className="w-full h-48 object-cover bg-black" />
                            <div className="absolute top-2 left-2">
                              <span className={`text-[9px] px-1.5 py-0.5 rounded-full ${isProject ? 'bg-primary/70 text-white' : 'bg-white/20 text-white'}`}>
                                {isProject ? `📂 ${v.project_name || '项目'}` : '✏️ 自由'}
                              </span>
                            </div>
                            <div className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-all" onClick={e => e.stopPropagation()}>
                              <a href={v.url} download={v.name} className="p-1.5 rounded-lg bg-white/20 hover:bg-white/30 text-white pointer-events-auto inline-block" title="下载">
                                <Download className="w-3 h-3" />
                              </a>
                            </div>
                          </div>
                        )
                      })}
                    </div>
                  </div>
                )}
              </>
            )}
          </>
        ) : tab === 'images' ? (
          /* ===== 图片 Tab ===== */
          imgFilter === 'free' ? (
            freeImages.length === 0 ? (
              <div className="text-center py-20 text-muted-foreground text-sm">暂无自由模式图片记录</div>
            ) : (
              <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-4 gap-4">
                {freeImages.map((img, i) => (
                  <div key={img.name + '-' + i}>
                    {renderImageCard(img)}
                  </div>
                ))}
              </div>
            )
          ) : (
            projectImages.length === 0 ? (
              <div className="text-center py-20 text-muted-foreground text-sm">暂无项目模式图片记录</div>
            ) : (
              renderProjectGroups(projectImages)
            )
          )
        ) : (
          /* ===== 视频 Tab ===== */
          videoFilter === 'free' ? (
            videosFree.length === 0 ? (
              <div className="text-center py-20 text-muted-foreground text-sm">暂无自由模式视频记录</div>
            ) : (
              <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-4 gap-4">
                {videosFree.map((v, i) => (
                  <div key={v.name + '-' + i} className="bg-muted rounded-xl overflow-hidden group relative">
                    <video src={v.url} controls className="w-full h-48 object-cover bg-black" />
                    <div className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-all" onClick={e => e.stopPropagation()}>
                      <a href={v.url} download={v.name} className="p-1.5 rounded-lg bg-white/20 hover:bg-white/30 text-white pointer-events-auto inline-block" title="下载">
                        <Download className="w-3 h-3" />
                      </a>
                    </div>
                  </div>
                ))}
              </div>
            )
          ) : (
            videosProject.length === 0 ? (
              <div className="text-center py-20 text-muted-foreground text-sm">暂无项目模式视频记录</div>
            ) : (
              (() => {
                const groups: Record<string, HistoryEntry[]> = {}
                for (const v of videosProject) {
                  const key = v.project_name || '未分组'
                  if (!groups[key]) groups[key] = []
                  groups[key].push(v)
                }
                return Object.entries(groups).map(([projName, vs]) => (
                  <div key={projName} className="mb-6">
                    <h3 className="text-sm font-semibold mb-3 flex items-center gap-2">
                      <span>📂 {projName}</span>
                      <span className="text-[10px] text-muted-foreground font-normal">({vs.length} 个视频)</span>
                    </h3>
                    <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-4 gap-4">
                      {vs.map((v, i) => (
                        <div key={v.name + '-' + i} className="bg-muted rounded-xl overflow-hidden group relative">
                          <video src={v.url} controls className="w-full h-48 object-cover bg-black" />
                          <div className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-all" onClick={e => e.stopPropagation()}>
                            <a href={v.url} download={v.name} className="p-1.5 rounded-lg bg-white/20 hover:bg-white/30 text-white pointer-events-auto inline-block" title="下载">
                              <Download className="w-3 h-3" />
                            </a>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                ))
              })()
            )
          )
        )}
      </div>

      {previewSrc && <ImagePreview src={previewSrc} onClose={() => setPreviewSrc(null)} />}

      {detail && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50" onClick={() => setDetail(null)}>
          <div className="bg-background border border-border rounded-2xl p-6 max-w-md w-full mx-4 shadow-2xl max-h-[80vh] overflow-y-auto" onClick={e => e.stopPropagation()}>
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-semibold text-sm">📄 生成详情</h3>
              <button onClick={() => setDetail(null)} className="text-muted-foreground hover:text-foreground text-xs">✕</button>
            </div>
            <div className="space-y-2 text-xs">
              <div><span className="text-muted-foreground">文件名：</span><code className="text-foreground/80">{detail.name}</code></div>
              {detail.prompt && <div><span className="text-muted-foreground">Prompt：</span><p className="text-foreground/80 mt-0.5 whitespace-pre-wrap">{detail.prompt}</p></div>}
              {detail.negative_prompt && <div><span className="text-muted-foreground">负面提示：</span><span className="text-foreground/80">{detail.negative_prompt}</span></div>}
              {detail.model && <div><span className="text-muted-foreground">模型：</span><span className="text-foreground/80">{detail.model}</span></div>}
              {detail.size && <div><span className="text-muted-foreground">尺寸：</span><span className="text-foreground/80">{detail.size}</span></div>}
              {detail.mode && <div><span className="text-muted-foreground">模式：</span><span className="text-foreground/80">{detail.mode === 'project' ? '项目模式' : '自由创作'}</span></div>}
              {detail.timestamp && <div><span className="text-muted-foreground">生成时间：</span><span className="text-foreground/80">{detail.timestamp}</span></div>}
              {detail.reference_urls && detail.reference_urls.length > 0 && (
                <div><span className="text-muted-foreground">参考图：</span><span className="text-foreground/80">{detail.reference_urls.length} 张</span></div>
              )}
            </div>
          </div>
        </div>
      )}

      {confirmDelete && (
        <ConfirmModal
          title="删除图片"
          message={confirmDelete.message}
          confirmText="确定删除"
          onConfirm={async () => {
            try { await confirmDelete.action() } catch {}
            setConfirmDelete(null)
          }}
          onCancel={() => setConfirmDelete(null)}
        />
      )}
    </div>
  )
}
