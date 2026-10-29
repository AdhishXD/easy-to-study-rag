import {
  ArrowLeft,
  ArrowRight,
  BookOpen,
  Check,
  ChevronRight,
  FileText,
  Loader2,
  Sparkles,
  Target,
} from 'lucide-react'
import { useEffect, useState } from 'react'
import { post, type Analysis, type Quiz } from '../api'
import { Empty } from './Common'

function citationDetails(label: string) {
  const match = label.match(/^(.*) \(page\/slide\/segment (\d+)\)$/)
  return match
    ? { filename: match[1], page: Number(match[2]) }
    : { filename: label, page: undefined }
}

type PracticeState = {
  index: number
  answers: Record<number, string>
  results: Record<number, { correct: boolean }>
  revealed: Record<number, boolean>
}

function restore(quiz: Quiz | null): PracticeState {
  let state: PracticeState = {
    index: 0,
    answers: {},
    results: {},
    revealed: {},
  }
  if (!quiz) return state
  try {
    const saved = JSON.parse(
      sessionStorage.getItem(`practice:${quiz.quiz_id}`) || 'null',
    )
    if (saved)
      state = {
        index:
          Number.isInteger(saved.index) &&
          saved.index >= 0 &&
          saved.index < quiz.questions.length
            ? saved.index
            : 0,
        answers: saved.answers || {},
        results: saved.results || {},
        revealed: saved.revealed || {},
      }
  } catch {
    /* A new session can still restore submitted answers from the server. */
  }
  for (const attempt of quiz.attempts || []) {
    state.answers[attempt.question_index] = attempt.answer
    state.results[attempt.question_index] = { correct: attempt.correct }
  }
  return state
}

export function Practice({
  analysis,
  quiz,
  busy,
  generate,
  notify,
  onAnswer,
  citation,
}: {
  analysis: Analysis | null
  quiz: Quiz | null
  busy: boolean
  generate: (topic: string, kind: string, count: number) => void
  notify: (error: unknown) => void
  onAnswer: () => void
  citation: (filename: string, page?: number) => void
}) {
  const [topic, setTopic] = useState(
    quiz?.questions[0]?.topic || analysis?.topics[0]?.name || '',
  )
  const [kind, setKind] = useState(quiz?.questions[0]?.question_type || 'mcq')
  const [count, setCount] = useState(3)
  const [initial] = useState(() => restore(quiz))
  const [index, setIndex] = useState(initial.index)
  const [answers, setAnswers] = useState<Record<number, string>>(
    initial.answers,
  )
  const [results, setResults] = useState<Record<number, { correct: boolean }>>(
    initial.results,
  )
  const [revealed, setRevealed] = useState<Record<number, boolean>>(
    initial.revealed,
  )
  const [saving, setSaving] = useState(false)
  useEffect(() => {
    if (!quiz) return
    try {
      sessionStorage.setItem(
        `practice:${quiz.quiz_id}`,
        JSON.stringify({ index, answers, results, revealed }),
      )
    } catch {
      /* Submitted answers remain saved on the backend. */
    }
  }, [quiz, index, answers, results, revealed])
  const question = quiz?.questions[index]
  const submit = async (self_correct?: boolean) => {
    if (!quiz) return
    setSaving(true)
    try {
      const result = await post<{ correct: boolean; selected_answer: string }>(
        '/attempts',
        {
          quiz_id: quiz.quiz_id,
          question_index: index,
          answer: answers[index] || '',
          self_correct,
        },
      )
      setResults((current) => ({ ...current, [index]: result }))
      setAnswers((current) => ({ ...current, [index]: result.selected_answer }))
      onAnswer()
    } catch (error) {
      notify(error)
    } finally {
      setSaving(false)
    }
  }
  if (!analysis)
    return (
      <Empty
        icon={<Target size={28} />}
        title="Practice starts with understanding"
        text="Analyze your teaching material first. Then choose a topic for questions grounded in your course. Past papers are optional for practice."
      />
    )
  return (
    <section>
      <div className="section-heading">
        <div>
          <span className="eyebrow">TURN UNDERSTANDING INTO CONFIDENCE</span>
          <h2>A little practice goes a long way.</h2>
        </div>
      </div>
      <form
        className="practice-controls"
        onSubmit={(e) => {
          e.preventDefault()
          generate(topic, kind, count)
        }}
      >
        <label>
          Topic
          <select value={topic} onChange={(e) => setTopic(e.target.value)}>
            {analysis.topics.map((t) => (
              <option key={t.name} value={t.name}>
                {t.name}
              </option>
            ))}
          </select>
        </label>
        <label>
          Question type
          <select value={kind} onChange={(e) => setKind(e.target.value)}>
            <option value="mcq">Multiple choice</option>
            <option value="2_mark">2 marks</option>
            <option value="3_mark">3 marks</option>
            <option value="5_mark">5 marks</option>
          </select>
        </label>
        <label>
          Questions
          <select
            value={count}
            onChange={(e) => setCount(Number(e.target.value))}
          >
            {[1, 2, 3, 4, 5].map((n) => (
              <option key={n}>{n}</option>
            ))}
          </select>
        </label>
        <button className="button primary" disabled={busy || !topic}>
          {busy ? (
            <Loader2 className="animate-spin" size={16} />
          ) : (
            <Sparkles size={16} />
          )}
          Create practice
        </button>
      </form>
      {!question ? (
        <Empty
          icon={<BookOpen size={28} />}
          title={
            busy
              ? 'A focused practice set is on its way'
              : 'Choose a topic. Find your rhythm.'
          }
          text={
            busy
              ? 'You can browse your materials while the questions are being prepared.'
              : 'Questions use retrieved teaching passages. Answers include the source pages supplied to the model.'
          }
        />
      ) : (
        <article className="quiz-panel">
          <div className="quiz-topline">
            <span className="eyebrow">{question.topic}</span>
            <span className="subtle-label">
              Question {index + 1} of {quiz!.questions.length}
            </span>
          </div>
          <div className="quiz-dots">
            {quiz!.questions.map((_, i) => (
              <button
                key={i}
                aria-label={`Go to question ${i + 1}`}
                className={
                  i === index
                    ? 'current'
                    : results[i]
                      ? results[i].correct
                        ? 'correct'
                        : 'incorrect'
                      : ''
                }
                onClick={() => setIndex(i)}
              />
            ))}
          </div>
          <h3>{question.question}</h3>
          {question.options.length ? (
            <fieldset disabled={!!results[index]} aria-label="Answer options">
              <legend className="sr-only">Choose your answer</legend>
              {question.options.map((option, i) => (
                <label
                  key={option}
                  className={`answer-option ${answers[index] === option ? 'answer-selected' : ''} ${results[index] && question.correct_answer === option ? 'answer-correct' : ''}`}
                >
                  <input
                    type="radio"
                    name={`answer-${index}`}
                    value={option}
                    checked={answers[index] === option}
                    onChange={() =>
                      setAnswers((current) => ({ ...current, [index]: option }))
                    }
                  />
                  <span className="option-letter">
                    {String.fromCharCode(65 + i)}
                  </span>
                  <span>{option}</span>
                  {results[index] && question.correct_answer === option && (
                    <Check size={17} className="ml-auto shrink-0" />
                  )}
                </label>
              ))}
            </fieldset>
          ) : (
            <label className="field-label">
              Your answer
              <textarea
                className="text-input mt-2"
                rows={5}
                value={answers[index] || ''}
                onChange={(e) =>
                  setAnswers((current) => ({
                    ...current,
                    [index]: e.target.value,
                  }))
                }
                disabled={!!results[index]}
                placeholder="Work through your answer before revealing the model answer."
              />
            </label>
          )}
          {!results[index] && !revealed[index] && (
            <button
              className="button primary mt-6"
              disabled={!answers[index]?.trim() || saving}
              onClick={() =>
                question.options.length
                  ? void submit()
                  : setRevealed((current) => ({ ...current, [index]: true }))
              }
            >
              {saving
                ? 'Checking…'
                : question.options.length
                  ? 'Check answer'
                  : 'Review model answer'}
              <ArrowRight size={16} />
            </button>
          )}
          {(results[index] || revealed[index]) && (
            <div className="answer-feedback">
              <strong>
                {results[index]
                  ? results[index].correct
                    ? 'You’ve got it.'
                    : 'A useful topic to revisit.'
                  : 'Compare with the model answer'}
              </strong>
              <p>{question.correct_answer}</p>
              <p className="muted">{question.explanation}</p>
              <div className="source-links">
                {question.sources.map((label) => {
                  const source = citationDetails(label)
                  return (
                    <button
                      key={`${source.filename}:${source.page ?? 'source'}`}
                      onClick={() => citation(source.filename, source.page)}
                    >
                      <FileText size={14} />
                      <span>
                        {source.filename}
                        {source.page ? ` · Page ${source.page}` : ''}
                      </span>
                      <ChevronRight size={13} />
                    </button>
                  )
                })}
              </div>
              {!question.options.length && !results[index] && (
                <div className="flex gap-3 mt-5">
                  <button
                    className="button secondary"
                    disabled={saving}
                    onClick={() => void submit(false)}
                  >
                    I need more practice
                  </button>
                  <button
                    className="button secondary"
                    disabled={saving}
                    onClick={() => void submit(true)}
                  >
                    I understood it
                  </button>
                </div>
              )}
            </div>
          )}
          <div className="quiz-navigation">
            <button
              className="button quiet"
              disabled={index === 0}
              onClick={() => setIndex(index - 1)}
            >
              <ArrowLeft size={15} />
              Previous
            </button>
            <span>
              {Object.keys(results).length} / {quiz!.questions.length} answered
            </span>
            <button
              className="button secondary"
              disabled={index === quiz!.questions.length - 1}
              onClick={() => setIndex(index + 1)}
            >
              Next
              <ArrowRight size={15} />
            </button>
          </div>
        </article>
      )}
    </section>
  )
}
