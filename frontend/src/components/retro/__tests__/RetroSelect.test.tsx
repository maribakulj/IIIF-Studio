import { render, screen } from '@testing-library/react'
import { RetroSelect } from '../index'

test('select has accessible label', () => {
  render(
    <RetroSelect
      label="Profil"
      options={[{ value: 'a', label: 'Option A' }]}
      value="a"
      onChange={() => {}}
    />
  )
  expect(screen.getByLabelText('Profil')).toBeInTheDocument()
})

test('renders all options', () => {
  render(
    <RetroSelect
      label="Test"
      options={[
        { value: 'a', label: 'A' },
        { value: 'b', label: 'B' },
      ]}
      value="a"
      onChange={() => {}}
    />
  )
  expect(screen.getAllByRole('option')).toHaveLength(2)
})
