import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import ProjectAssetPicker from '../ProjectAssetPicker'

const mockAssets = {
  characters: [
    { name: '林深', file: 'char_1.png' },
    { name: '天眼', file: 'char_2.png' },
  ],
  scenes: [
    { name: '第10场-虚拟城市', file: 'scene_1.png' },
    { name: '第14场-对话', file: 'scene_2.png' },
  ],
}

const mockEntityImages = {
  characters: {
    '林深': [{ name: '林深', url: '/img.png' }],
  },
  scenes: {},
}

describe('ProjectAssetPicker', () => {
  it('renders project name and entity count', () => {
    render(<ProjectAssetPicker
      projectName="测试2"
      assets={mockAssets}
      entityImages={mockEntityImages}
      selectedEntity={null}
      onSelectEntity={vi.fn()}
      onAddAsset={vi.fn()}
    />)
    expect(screen.getByText('测试2', { exact: false })).toBeInTheDocument()
    expect(screen.getByText('角色 (2)', { exact: false })).toBeInTheDocument()
    expect(screen.getByText('场景 (2)', { exact: false })).toBeInTheDocument()
  })

  it('calls onAddAsset when clicking an image', () => {
    const onAdd = vi.fn()
    render(<ProjectAssetPicker
      projectName="测试2"
      assets={mockAssets}
      entityImages={mockEntityImages}
      selectedEntity="林深"
      onSelectEntity={vi.fn()}
      onAddAsset={onAdd}
    />)
    const img = screen.getByRole('img')
    fireEvent.click(img)
    expect(onAdd).toHaveBeenCalledWith('/img.png')
  })

  it('shows empty state when selected entity has no images', () => {
    render(<ProjectAssetPicker
      projectName="测试2"
      assets={mockAssets}
      entityImages={{ characters: {}, scenes: {} }}
      selectedEntity="天眼"
      onSelectEntity={vi.fn()}
      onAddAsset={vi.fn()}
    />)
    expect(screen.getByText('该实体暂无生成图片')).toBeInTheDocument()
  })

  it('switches between character and scene tabs', () => {
    render(<ProjectAssetPicker
      projectName="测试2"
      assets={mockAssets}
      entityImages={mockEntityImages}
      selectedEntity={null}
      onSelectEntity={vi.fn()}
      onAddAsset={vi.fn()}
    />)
    expect(screen.getByText('角色 (2)', { exact: false })).toBeInTheDocument()
    expect(screen.getByText('场景 (2)', { exact: false })).toBeInTheDocument()
    fireEvent.click(screen.getByText('场景 (2)', { exact: false }))
    expect(screen.getByText('第10场-虚拟城市')).toBeInTheDocument()
  })
})
