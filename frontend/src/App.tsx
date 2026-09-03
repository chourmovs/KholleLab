import { useEffect, useMemo, useState } from 'react'
import katex from 'katex'
import { Tldraw } from 'tldraw'
import { fetchProblem, type Problem } from './api'

const FALLBACK_PROBLEM: Problem = {
  id: 'demo-001',
  title: 'Échauffement algébrique',
  level: 'Première / Terminale',
  difficulty: 2,
  topics: ['algèbre', 'raisonnement'],
  statement_tex:
    String.raw`\text{Déterminer tous les réels }x\text{ tels que }\sqrt{x+2}+\sqrt{4-x}=3.`,
}

export default function App() {
  const [problem, setProblem] = useState<Problem>(FALLBACK_PROBLEM)
  const [apiState, setApiState] = useState<'loading' | 'ready' | 'offline'>('loading')

  useEffect(() => {
    fetchProblem('demo-001')
      .then((loadedProblem) => {
        setProblem(loadedProblem)
        setApiState('ready')
      })
      .catch(() => setApiState('offline'))
  }, [])

  const renderedStatement = useMemo(
    () =>
      katex.renderToString(problem.statement_tex, {
        displayMode: true,
        throwOnError: false,
      }),
    [problem.statement_tex],
  )

  return (
    <main className="app-shell">
      <header className="topbar">
        <div>
          <p className="eyebrow">KHOLLELAB · COLLE #001</p>
          <h1>Le tableau d'abord. Le corrigé ensuite.</h1>
        </div>
        <span className={`api-status api-status--${apiState}`}>API · {apiState}</span>
      </header>

      <section className="workbench">
        <aside className="problem-panel">
          <div className="problem-meta">
            <span>{problem.level}</span>
            <span>{'★'.repeat(problem.difficulty)}{'☆'.repeat(5 - problem.difficulty)}</span>
          </div>
          <h2>{problem.title}</h2>
          <div
            className="statement"
            data-testid="problem-statement"
            dangerouslySetInnerHTML={{ __html: renderedStatement }}
          />
          <div className="topic-list">
            {problem.topics.map((topic) => (
              <span key={topic}>{topic}</span>
            ))}
          </div>
          <div className="teacher-card">
            <strong>Professeur</strong>
            <p>Commence par poser ton raisonnement au tableau. Les interventions arrivent dans une prochaine PR.</p>
          </div>
        </aside>

        <div className="board-panel" aria-label="Tableau de résolution">
          <Tldraw persistenceKey="khollelab-pr01-demo-board" />
        </div>
      </section>
    </main>
  )
}
