export function getPhaseNames(storyType?: string): string[] {
  const s = storyType || ''
  if (['1', '2', '3'].includes(s)) {
    return ['故事大纲', '完整剧情', '完整剧本', '视觉提取', '分镜设计', '生图准备']
  }
  if (s === '4') {
    return ['故事大纲', '完整剧情', '完整剧本', '视觉提取']
  }
  return ['故事大纲', '完整剧情', '完整剧本']
}

export const PHASE_DIRS = ['01_故事大纲', '02_完整剧情', '03_完整剧本', '04_角色场景', '05_分镜脚本', '06_生图需求']
export const PHASE_ICONS = ['📋', '📖', '🎭', '🔍', '🎬', '🖼️']
