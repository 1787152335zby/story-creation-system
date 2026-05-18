import { describe, it, expect } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import ThemeSwitcher from '../ThemeSwitcher'

const STORAGE_KEYS = {
  palette: 'theme_palette',
  background: 'theme_background',
  texture: 'theme_texture',
  ambient: 'theme_ambient',
  animated: 'theme_animated',
  presets: 'theme_presets',
} as const

describe('ThemeSwitcher', () => {
  it('renders the trigger button', () => {
    render(<ThemeSwitcher />)
    expect(screen.getByTitle('定制主题')).toBeInTheDocument()
  })

  it('opens the drawer panel when button is clicked', () => {
    render(<ThemeSwitcher />)
    fireEvent.click(screen.getByTitle('定制主题'))
    expect(screen.getByText('主题定制')).toBeInTheDocument()
  })

  it('shows all 6 palette options when panel is open', () => {
    render(<ThemeSwitcher />)
    fireEvent.click(screen.getByTitle('定制主题'))
    expect(screen.getByText('星云紫')).toBeInTheDocument()
    expect(screen.getByText('极光蓝')).toBeInTheDocument()
    expect(screen.getByText('琥珀橙')).toBeInTheDocument()
    expect(screen.getByText('翡翠绿')).toBeInTheDocument()
    expect(screen.getByText('玫瑰红')).toBeInTheDocument()
    expect(screen.getByText('月光白')).toBeInTheDocument()
  })

  it('shows background mode section', () => {
    render(<ThemeSwitcher />)
    fireEvent.click(screen.getByTitle('定制主题'))
    expect(screen.getByText('纯色')).toBeInTheDocument()
    expect(screen.getByText('极光')).toBeInTheDocument()
  })

  it('shows texture section', () => {
    render(<ThemeSwitcher />)
    fireEvent.click(screen.getByTitle('定制主题'))
    expect(screen.getByText('噪点')).toBeInTheDocument()
    expect(screen.getByText('网格')).toBeInTheDocument()
  })

  it('shows ambient light section', () => {
    render(<ThemeSwitcher />)
    fireEvent.click(screen.getByTitle('定制主题'))
    expect(screen.getByText('顶光')).toBeInTheDocument()
    expect(screen.getByText('星尘')).toBeInTheDocument()
  })

  it('migrates old localStorage app_theme key', () => {
    localStorage.setItem('app_theme', 'aurora')
    const { unmount } = render(<ThemeSwitcher />)
    unmount()
    expect(localStorage.getItem(STORAGE_KEYS.palette)).toBe('aurora')
    localStorage.removeItem('app_theme')
    localStorage.removeItem(STORAGE_KEYS.palette)
  })

  it('shows an inline input when saving a preset instead of prompt()', () => {
    render(<ThemeSwitcher />)
    fireEvent.click(screen.getByTitle('定制主题'))
    fireEvent.click(screen.getByRole('button', { name: /保存为预设/ }))
    expect(screen.getByPlaceholderText('输入预设名称')).toBeInTheDocument()
    expect(screen.getByText('确认')).toBeInTheDocument()
    expect(screen.getByText('取消')).toBeInTheDocument()
  })

  it('saves a preset via inline input and shows it in the list', () => {
    render(<ThemeSwitcher />)
    fireEvent.click(screen.getByTitle('定制主题'))
    fireEvent.click(screen.getByRole('button', { name: /保存为预设/ }))
    const input = screen.getByPlaceholderText('输入预设名称')
    fireEvent.change(input, { target: { value: '我的最爱' } })
    fireEvent.click(screen.getByText('确认'))
    expect(screen.getByRole('button', { name: /我的最爱/ })).toBeInTheDocument()
    expect(localStorage.getItem(STORAGE_KEYS.presets)).toContain('我的最爱')
    localStorage.removeItem(STORAGE_KEYS.presets)
  })
})
