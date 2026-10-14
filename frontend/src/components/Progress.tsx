import { ArrowRight, Target } from 'lucide-react'
import { type Progress } from '../api'
import { Empty } from './Common'

export function ProgressView({
  progress,
  practice,
}: {
  progress: Progress[]
  practice: () => void
}) {
  const answered = progress.reduce((n, t) => n + t.answered, 0)
  const correct = progress.reduce((n, t) => n + t.correct, 0)
  return (
    <section>
      <div className="section-heading">
        <div>
          <span className="eyebrow">SMALL STEPS ADD UP</span>
          <h2>See your understanding grow.</h2>
        </div>
      </div>
      {!answered ? (
        <Empty
          icon={<Target size={28} />}
          title="Your progress starts with one question"
          text="Answer a practice set to see your strengths and topics that need another look."
        >
          <button className="button primary" onClick={practice}>
            Start practicing
            <ArrowRight size={16} />
          </button>
        </Empty>
      ) : (
        <>
          <div className="progress-summary">
            <div>
              <strong>{answered}</strong>
              <span>Questions answered</span>
            </div>
            <div>
              <strong>
                {Math.round((correct / answered) * 100)}
                <small>%</small>
              </strong>
              <span>Correct or self-assessed</span>
            </div>
            <div>
              <strong>{progress.length}</strong>
              <span>Topics practiced</span>
            </div>
          </div>
          <div className="topic-list">
            {[...progress]
              .sort((a, b) => a.correct / a.answered - b.correct / b.answered)
              .map((t) => (
                <div className="progress-row" key={t.topic}>
                  <div>
                    <strong>{t.topic}</strong>
                    <span>
                      {t.correct} of {t.answered} answers correct
                    </span>
                  </div>
                  <div className="progress-track">
                    <span
                      style={{ width: `${(t.correct / t.answered) * 100}%` }}
                    />
                  </div>
                  <button className="button quiet" onClick={practice}>
                    Practice
                    <ArrowRight size={14} />
                  </button>
                </div>
              ))}
          </div>
          <p className="context-note">
            MCQs are checked automatically. Written answers use your own
            assessment.
          </p>
        </>
      )}
    </section>
  )
}
