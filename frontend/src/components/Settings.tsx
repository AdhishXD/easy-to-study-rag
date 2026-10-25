import { CheckCircle2, Clock3, Loader2, Settings2 } from 'lucide-react'
import { useState } from 'react'
import { api, type Config, type Diagnostic, type Job } from '../api'
import { active } from '../utils'

export function TokenInput({ onSave }: { onSave: () => void }) {
  const [token, setToken] = useState('')
  return (
    <form
      className="token-form"
      onSubmit={(e) => {
        e.preventDefault()
        sessionStorage.setItem('workspace-token', token.trim())
        setToken('')
        onSave()
      }}
    >
      <input
        type="password"
        aria-label="Workspace access token"
        placeholder="Workspace access token, if required"
        value={token}
        onChange={(e) => setToken(e.target.value)}
      />
      <button className="button secondary">Connect</button>
    </form>
  )
}

export function Settings({
  jobs,
  config,
  notify,
}: {
  jobs: Job[]
  config: Config | null
  notify: (e: unknown) => void
}) {
  const [diagnostics, setDiagnostics] = useState<Diagnostic | null>(null)
  const [loading, setLoading] = useState(false)
  const refresh = async () => {
    setLoading(true)
    try {
      setDiagnostics(await api<Diagnostic>('/diagnostics'))
    } catch (error) {
      notify(error)
    } finally {
      setLoading(false)
    }
  }
  return (
    <section>
      <div className="course-heading">
        <div>
          <span className="eyebrow">BEHIND YOUR STUDY SPACE</span>
          <h1>Settings & activity</h1>
          <p>
            See what is running, what is saved, and how your model is
            performing.
          </p>
        </div>
      </div>
      <div className="settings-panel">
        <div className="flex gap-3 items-center">
          <span className="file-icon">
            <Settings2 size={20} />
          </span>
          <div>
            <h3>
              {config?.provider === 'groq'
                ? 'Groq inference'
                : 'Ollama inference'}
            </h3>
            <p className="muted">{config?.model}</p>
          </div>
          <button
            className="button secondary ml-auto"
            disabled={loading}
            onClick={() => void refresh()}
          >
            {loading ? 'Checking…' : 'Check connection'}
          </button>
        </div>
        <p className="settings-description">
          {config?.provider === 'groq'
            ? 'Retrieved course text is sent to Groq for generation. Your API key stays on the backend.'
            : 'Course text is processed by your local Ollama model. Add a free Groq key to the backend .env and restart it to use hosted inference.'}
        </p>
        {config?.demo && (
          <p className="settings-description">
            Public demo: a fixed synthetic course. Private uploads are available
            in local mode.
          </p>
        )}
        <TokenInput onSave={() => void refresh()} />
        {diagnostics && (
          <div className="diagnostics">
            <h3>Model connection</h3>
            <pre>{JSON.stringify(diagnostics.model, null, 2)}</pre>
            <details>
              <summary>Request timing and errors</summary>
              <pre>{diagnostics.recent_calls}</pre>
            </details>
            {diagnostics.trace && (
              <details>
                <summary>Latest local prompt and response</summary>
                <pre>{diagnostics.trace.prompt}</pre>
                <pre>{diagnostics.trace.response}</pre>
              </details>
            )}
          </div>
        )}
      </div>
      <div className="section-heading">
        <div>
          <span className="eyebrow">RECENT PROCESSING</span>
          <h2>Your activity</h2>
        </div>
      </div>
      <div className="activity-list">
        {jobs.length ? (
          jobs.map((job) => (
            <div key={job.id}>
              <span className="activity-icon">
                {job.status === 'completed' ? (
                  <CheckCircle2 size={18} />
                ) : active(job) ? (
                  <Loader2 className="animate-spin" size={18} />
                ) : (
                  <Clock3 size={18} />
                )}
              </span>
              <div>
                <strong>
                  {job.kind[0].toUpperCase() + job.kind.slice(1)} ·{' '}
                  {job.subject}
                </strong>
                <p>{job.error || job.message}</p>
                <small>
                  {job.metrics.llm_calls || 0} model calls ·{' '}
                  {job.metrics.cache_hits || 0} reused responses
                </small>
              </div>
              <span className="activity-status">
                {job.status}
                <small>{job.elapsed.toFixed(1)}s</small>
              </span>
            </div>
          ))
        ) : (
          <p className="p-6 muted">Processing activity will appear here.</p>
        )}
      </div>
    </section>
  )
}
