import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import AssetGallery from '../AssetGallery'

const mockImages = {
  characters: {
    '林深': [{ name: '林深', url: '/api/gen-files/char_1.png' }],
  },
  scenes: {
    '第10场': [
      { name: '第10场', url: '/api/gen-files/scene_1.png' },
      { name: '第10场', url: '/api/gen-files/scene_2.png' },
    ],
  },
}

describe('AssetGallery', () => {
  it('renders entity names', () => {
    render(<AssetGallery projectName="test" projectImages={mockImages} />)
    expect(screen.getByText('林深')).toBeInTheDocument()
    expect(screen.getByText('第10场')).toBeInTheDocument()
  })

  it('shows loading state', () => {
    render(<AssetGallery projectName="test" projectImages={{ characters: {}, scenes: {} }} loading={true} />)
    expect(screen.getByText('加载中...')).toBeInTheDocument()
  })

  it('shows empty state when no assets', () => {
    render(<AssetGallery projectName="test" projectImages={{ characters: {}, scenes: {} }} />)
    expect(screen.getByText('暂无素材')).toBeInTheDocument()
  })

  it('renders version badges for entities with versions', () => {
    const imagesWithVersions = {
      characters: {
        '林深': { images: [{ name: '林深', url: '/img.png' }], versions: { '1': { confirmed: false, images: [{ name: '1', url: '/img.png' }] } } },
      },
      scenes: {},
    }
    render(<AssetGallery projectName="test" projectImages={imagesWithVersions as any} />)
    expect(screen.getByText(/v1/)).toBeInTheDocument()
  })

  it('shows batch delete button and enters selection mode', () => {
    const imagesWithVersions = {
      characters: {
        '林深': { images: [], versions: { '1': { confirmed: false, images: [{ name: '1', url: '/img.png' }] } } },
      },
      scenes: {},
    }
    const onDelete = vi.fn()
    render(<AssetGallery projectName="test" projectImages={imagesWithVersions as any} onDeleteVersion={onDelete} />)
    expect(screen.getByText('批量删除')).toBeInTheDocument()
    fireEvent.click(screen.getByText('批量删除'))
    expect(screen.getByText('取消')).toBeInTheDocument()
    expect(screen.getByText(/0 项/)).toBeInTheDocument()
  })
})
