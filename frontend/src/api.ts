export type Problem = {
  id: string
  title: string
  level: string
  difficulty: number
  topics: string[]
  statement_tex: string
}

export async function fetchProblem(problemId: string): Promise<Problem> {
  const response = await fetch(`/api/v1/problems/${problemId}`)
  if (!response.ok) {
    throw new Error(`Problem request failed with HTTP ${response.status}`)
  }
  return response.json() as Promise<Problem>
}
