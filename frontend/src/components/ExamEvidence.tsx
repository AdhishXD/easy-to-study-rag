import { ChevronRight, FileText } from 'lucide-react'
import { type Analysis, type Topic } from '../api'

export function ExamEvidence({
  analysis,
  openTopic,
  openCitation,
}: {
  analysis: Analysis
  openTopic: (topic: Topic) => void
  openCitation: (filename: string, page?: number) => void
}) {
  const priorities = analysis.topics
    .filter((topic) => (topic.question_count || 0) > 0)
    .slice(0, 6)
  const repeats = [...analysis.recurring_groups].sort(
    (a, b) => b.years.length - a.years.length,
  )
  const evidence = analysis.exam_evidence || {
    known_marks: 0,
    marked_questions: 0,
    total_questions: analysis.questions.length,
  }

  if (!priorities.length && !repeats.length) return null

  return (
    <section className="exam-evidence" aria-labelledby="exam-evidence-title">
      <div className="section-heading evidence-heading">
        <div>
          <span className="eyebrow">Past-paper evidence</span>
          <h2 id="exam-evidence-title">What the exams have emphasized</h2>
        </div>
        <span className="subtle-label">
          Based on {analysis.questions.length} extracted questions
        </span>
      </div>

      <div className="evidence-grid">
        <div className="evidence-column">
          <div className="evidence-column-heading">
            <h3>Frequently tested topics</h3>
            <p>Ranked by exam years, then by explicitly printed marks.</p>
          </div>
          <div className="priority-list">
            {priorities.map((topic) => (
              <button
                className="priority-row"
                key={topic.name}
                onClick={() => openTopic(topic)}
              >
                <span className="priority-copy">
                  <strong>{topic.name}</strong>
                  <span>
                    {topic.question_count || 0}{' '}
                    {topic.question_count === 1 ? 'question' : 'questions'} ·{' '}
                    {topic.num_years} exam{' '}
                    {topic.num_years === 1 ? 'year' : 'years'}
                  </span>
                </span>
                <span className="priority-weight">
                  {topic.weightage_percent != null ? (
                    <>
                      <strong>{topic.weightage_percent}%</strong>
                      <small>{topic.total_marks || 0} known marks</small>
                    </>
                  ) : (
                    <small>Marks unavailable</small>
                  )}
                </span>
                <ChevronRight size={16} />
              </button>
            ))}
          </div>
          <p className="evidence-note">
            {evidence.marked_questions
              ? `Mark weightage uses ${evidence.known_marks} marks printed across ${evidence.marked_questions} of ${evidence.total_questions} extracted questions.`
              : 'No reliable mark labels were found, so topics are ranked by recurrence only.'}
          </p>
        </div>

        <div className="evidence-column">
          <div className="evidence-column-heading">
            <h3>Questions repeated across years</h3>
            <p>Same task or concept found in more than one exam year.</p>
          </div>
          {repeats.length ? (
            <div className="repeat-list">
              {repeats.map((group) => (
                <details
                  className="repeat-item"
                  key={`${group.topic}:${group.years.join('-')}:${group.questions.map((q) => q.id).join('-')}`}
                >
                  <summary>
                    <span>
                      <strong>{group.topic}</strong>
                      <small>{group.years.join(', ')}</small>
                    </span>
                    <span>{group.questions.length} questions</span>
                  </summary>
                  <p>{group.reason}</p>
                  <div className="repeat-questions">
                    {group.questions.map((question) => (
                      <button
                        key={question.id}
                        onClick={() =>
                          openCitation(question.filename, question.page)
                        }
                      >
                        <span className="question-source">
                          <FileText size={14} />
                          {question.year}
                          {question.marks ? ` · ${question.marks} marks` : ''}
                        </span>
                        <span>{question.question}</span>
                      </button>
                    ))}
                  </div>
                </details>
              ))}
            </div>
          ) : (
            <p className="evidence-empty">
              No substantially repeated questions were found across different
              years.
            </p>
          )}
        </div>
      </div>
    </section>
  )
}
