import { describe, it, expect, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import ThemeSwitcher from '../ThemeSwitcher'

beforeEach(() => {
  localStorage.clear()
})

describe('ThemeSwitcher', () => {
  it('renders the trigger button', () => {
    render(<ThemeSwitcher />)
    expect(screen.getByTitle('主题与场景')).toBeInTheDocument()
  })

  it('opens the drawer panel when button is clicked', () => {
    render(<ThemeSwitcher />)
    fireEvent.click(screen.getByTitle('主题与场景'))
    expect(screen.getByText('主题定制')).toBeInTheDocument()
  })

  it('shows all 6 palette options when panel is open', () => {
    render(<ThemeSwitcher />)
    fireEvent.click(screen.getByTitle('主题与场景'))
    expect(screen.getByText('星云紫')).toBeInTheDocument()
    expect(screen.getByText('极光蓝')).toBeInTheDocument()
    expect(screen.getByText('琥珀橙')).toBeInTheDocument()
    expect(screen.getByText('翡翠绿')).toBeInTheDocument()
    expect(screen.getByText('玫瑰红')).toBeInTheDocument()
    expect(screen.getByText('月光白')).toBeInTheDocument()
  })

  it('shows background scene section', () => {
    render(<ThemeSwitcher />)
    fireEvent.click(screen.getByTitle('主题与场景'))
    expect(screen.getByText(/背景场景/)).toBeInTheDocument()
    expect(screen.getByText('星空')).toBeInTheDocument()
    expect(screen.getByText('海洋')).toBeInTheDocument()
    expect(screen.getByText('纯色')).toBeInTheDocument()
  })
})
