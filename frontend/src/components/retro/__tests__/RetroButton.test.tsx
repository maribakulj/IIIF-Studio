import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { RetroButton } from '../index'

test('renders button with text', () => {
  render(<RetroButton>Click me</RetroButton>)
  expect(screen.getByRole('button', { name: 'Click me' })).toBeInTheDocument()
})

test('calls onClick when clicked', async () => {
  const handleClick = vi.fn()
  render(<RetroButton onClick={handleClick}>Click</RetroButton>)
  await userEvent.click(screen.getByRole('button'))
  expect(handleClick).toHaveBeenCalledOnce()
})

test('disabled button does not call onClick', async () => {
  const handleClick = vi.fn()
  render(<RetroButton disabled onClick={handleClick}>Click</RetroButton>)
  await userEvent.click(screen.getByRole('button'))
  expect(handleClick).not.toHaveBeenCalled()
})
