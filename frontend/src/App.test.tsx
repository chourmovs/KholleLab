import { render, screen } from '@testing-library/react'
import { test, vi } from 'vitest'
import App from './App'

vi.mock('tldraw', () => ({
  Tldraw: () => <div data-testid="tldraw-board">board</div>,
}))

vi.stubGlobal(
  'fetch',
  vi.fn().mockResolvedValue({
    ok: true,
    json: async () => ({
      id: 'demo-001',
      title: 'Échauffement algébrique',
      level: 'Première / Terminale',
      difficulty: 2,
      topics: ['algèbre', 'raisonnement'],
      statement_tex: String.raw`x^2=1`,
    }),
  }),
)

test('renders the problem and blackboard surface', async () => {
  render(<App />)

  expect(screen.getByText("Le tableau d'abord. Le corrigé ensuite.")).toBeInTheDocument()
  expect(screen.getByTestId('tldraw-board')).toBeInTheDocument()
  expect(await screen.findByText('API · ready')).toBeInTheDocument()
})
