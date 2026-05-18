import type { Shot } from '../components/ShotListView'
import { fetchPhaseContent } from './api'

export async function loadShotsFromPrompts(projectName: string): Promise<Shot[]> {
  const content = await fetchPhaseContent(projectName, '06_提示词/分镜提示词.md')
  if (!content || !content.content) return []

  const text = content.content
  const shots: Shot[] = []

  let currentAct = '全部'

  const actRegex = /^#{1,2}\s+(第[^场\n]+?)(?:\s*分镜提示词)?\s*$/m
  const shotHeaderRegex = /^###\s+(镜头\d+)/m

  const lines = text.split('\n')
  let currentBlock: string[] = []
  let inShot = false

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i]

    const actMatch = line.match(actRegex)
    if (actMatch) {
      currentAct = actMatch[1].trim()
      continue
    }

    const shotMatch = line.match(shotHeaderRegex)
    if (shotMatch) {
      if (inShot && currentBlock.length > 0) {
        shots.push({
          index: shots.length + 1,
          act: currentAct,
          scene: '',
          prompt: currentBlock.join('\n').trim(),
          status: 'pending',
        })
      }
      currentBlock = [line]
      inShot = true
      continue
    }

    if (inShot) {
      if (line.trim() === '---' || (line.trim().startsWith('✅') && inShot)) {
        if (currentBlock.length > 0) {
          shots.push({
            index: shots.length + 1,
            act: currentAct,
            scene: '',
            prompt: currentBlock.join('\n').trim(),
            status: 'pending',
          })
        }
        currentBlock = []
        inShot = false
      } else {
        currentBlock.push(line)
      }
    }
  }

  if (inShot && currentBlock.length > 0) {
    shots.push({
      index: shots.length + 1,
      act: currentAct,
      scene: '',
      prompt: currentBlock.join('\n').trim(),
      status: 'pending',
    })
  }

  if (shots.length === 0 && text.trim()) {
    shots.push({
      index: 1,
      act: '全部',
      scene: '',
      prompt: text.slice(0, 500).trim(),
      status: 'pending',
    })
  }

  return shots
}
