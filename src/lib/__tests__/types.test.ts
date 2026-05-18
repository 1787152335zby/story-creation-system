import { describe, it, expect } from 'vitest'
import type {
  ProjectInfo, PhaseInfo, VisualAsset, VisualAssetsData,
  EntityImage, EntityImagesMap, FreeImageResult,
  ProjectImageGenResult, FreeVideoResult, GenerationHistory, Template
} from '../types'

describe('types', () => {
  it('ProjectInfo can be constructed', () => {
    const p: ProjectInfo = { name: 'test', phases: [{ name: '大纲', done: false }] }
    expect(p.name).toBe('test')
  })
  it('EntityImagesMap can hold character images', () => {
    const m: EntityImagesMap = {
      characters: { '林深': [{ name: '林深', url: '/img.png' }] },
      scenes: {}
    }
    expect(m.characters['林深'][0].name).toBe('林深')
  })
  it('FreeImageResult can hold images', () => {
    const r: FreeImageResult = { images: [{ url: 'http://x.com/a.png', local: 'a.png' }] }
    expect(r.images.length).toBe(1)
  })
  it('FreeVideoResult can hold error', () => {
    const r: FreeVideoResult = { error: 'timeout' }
    expect(r.error).toBe('timeout')
  })
  it('GenerationHistory can hold history items', () => {
    const h: GenerationHistory = { images_free: [], images_project: [], videos: [{ name: 'v', url: '/v.mp4' }] }
    expect(h.videos.length).toBe(1)
  })
})
