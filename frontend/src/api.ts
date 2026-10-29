export type Subject = {
  name: string
  files: number
  pages: number
  years: number
}
export type Source = { filename: string; page: number }
export type Material = {
  filename: string
  source_type: string
  year: number | null
  pages: number
  characters: number
  chunks: number | null
}
export type Topic = {
  name: string
  summary: string
  sources: Source[]
  years: number[]
  num_years: number
  question_count?: number
  total_marks?: number
  weightage_percent?: number | null
}
export type PaperQuestion = {
  id: string
  question: string
  year: number
  filename: string
  page: number
  marks?: number | null
  topic?: string
}
export type Analysis = {
  subject: string
  generated_at: string
  topics: Topic[]
  questions: PaperQuestion[]
  recurring_groups: {
    topic: string
    years: number[]
    reason: string
    questions: PaperQuestion[]
  }[]
  exam_evidence?: {
    known_marks: number
    marked_questions: number
    total_questions: number
  }
}
export type QuizQuestion = {
  question: string
  options: string[]
  correct_answer: string
  explanation: string
  sources: string[]
  question_type: string
  topic: string
}
export type Quiz = {
  quiz_id: string
  questions: QuizQuestion[]
  attempts?: { question_index: number; correct: boolean; answer: string }[]
}
export type Job = {
  id: string
  subject: string
  kind: string
  status: string
  progress: number
  message: string
  error: string | null
  elapsed: number
  created: number
  metrics: { llm_calls?: number; cache_hits?: number; model_seconds?: number }
  result?: unknown
}
export type Progress = { topic: string; answered: number; correct: number }
export type Config = {
  demo: boolean
  uploads_enabled: boolean
  provider: string
  model: string
  max_upload_mb: number
}
export type Page = {
  filename: string
  page: number
  text: string
  year: number | null
  source_type: string
}
export type Diagnostic = {
  model: Record<string, unknown>
  recent_calls: string
  trace?: { model: string; prompt: string; response: string } | null
}
export const query = (values: Record<string, string | number>) =>
  new URLSearchParams(
    Object.entries(values).map(([k, v]) => [k, String(v)]),
  ).toString()

const base =
  (import.meta as ImportMeta & { env: Record<string, string> }).env
    .VITE_API_URL || ''
export const apiUrl = (path: string) => `${base}/api${path}`
export const authHeaders = (): Record<string, string> => {
  const token = sessionStorage.getItem('workspace-token')
  return token ? { Authorization: `Bearer ${token}` } : {}
}
export async function api<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const headers = new Headers(options.headers)
  if (options.body && !(options.body instanceof FormData))
    headers.set('Content-Type', 'application/json')
  const token = sessionStorage.getItem('workspace-token')
  if (token) headers.set('Authorization', `Bearer ${token}`)
  const response = await fetch(apiUrl(path), { ...options, headers })
  if (!response.ok) {
    let message = `Request failed (${response.status})`
    try {
      const body = await response.json()
      message =
        typeof body.detail === 'string'
          ? body.detail
          : 'Check the entered values and try again'
    } catch {
      /* keep status message */
    }
    throw new Error(message)
  }
  return response.json()
}

export const post = <T>(path: string, body: unknown) =>
  api<T>(path, { method: 'POST', body: JSON.stringify(body) })
