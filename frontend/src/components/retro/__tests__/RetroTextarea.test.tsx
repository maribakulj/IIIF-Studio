import { render, screen } from '@testing-library/react'
import { RetroTextarea } from '../index'

test('textarea has accessible label', () => {
  render(<RetroTextarea label="Notes" />)
  expect(screen.getByLabelText('Notes')).toBeInTheDocument()
  expect(screen.getByLabelText('Notes').tagName).toBe('TEXTAREA')
})

test('renders without label', () => {
  render(<RetroTextarea placeholder="Type here" />)
  expect(screen.getByPlaceholderText('Type here')).toBeInTheDocument()
})
