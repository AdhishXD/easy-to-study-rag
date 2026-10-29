import {
  ArrowRight,
  BookOpen,
  CheckCircle2,
  ChevronRight,
  CircleHelp,
  Clock3,
  FileText,
  GraduationCap,
  Layers3,
  Loader2,
  Menu,
  Plus,
  Settings2,
  Sparkles,
  X,
} from 'lucide-react'
import { motion } from 'motion/react'
import { useCallback, useEffect, useRef, useState } from 'react'
import {
  api,
  post,
  query,
  type Analysis,
  type Config,
  type Job,
  type Material,
  type Progress,
  type Quiz,
  type Subject,
  type Topic,
} from './api'

import { Empty, Modal } from './components/Common'
import { EditYear, NewSubject, Upload } from './components/Forms'
import { Library } from './components/Library'
import { Practice } from './components/Practice'
import { ProgressView } from './components/Progress'
import { Settings, TokenInput } from './components/Settings'
import { TopicList } from './components/Topics'
import { Subjects } from './components/Subjects'
import { SourceReader } from './components/SourceReader'
import { active, errorText, stamp } from './utils'

type View =
  'subjects' | 'overview' | 'materials' | 'practice' | 'progress' | 'settings'
function App() {
  const [subjects, setSubjects] = useState<Subject[]>([])
  const [subject, setSubject] = useState(
    localStorage.getItem('selected-subject') || '',
  )
  const [view, setView] = useState<View>('subjects')
  const [config, setConfig] = useState<Config | null>(null)
  const [materials, setMaterials] = useState<Material[]>([])
  const [analysis, setAnalysis] = useState<Analysis | null>(null)
  const [progress, setProgress] = useState<Progress[]>([])
  const [jobs, setJobs] = useState<Job[]>([])
  const [booting, setBooting] = useState(true)
  const [loadingCourse, setLoadingCourse] = useState(false)
  const [connectionError, setConnectionError] = useState('')
  const [notice, setNotice] = useState<{
    text: string
    error?: boolean
  } | null>(null)
  const [mobileNav, setMobileNav] = useState(false)
  const [isMobile, setIsMobile] = useState(
    () => window.matchMedia('(max-width: 760px)').matches,
  )
  const [modal, setModal] = useState<'subject' | 'upload' | null>(null)
  const [topic, setTopic] = useState<Topic | null>(null)
  const [source, setSource] = useState<Material | null>(null)
  const [sourcePage, setSourcePage] = useState<number | undefined>()
  const [deleting, setDeleting] = useState<Material | null>(null)
  const [editingYear, setEditingYear] = useState<Material | null>(null)
  const [quiz, setQuiz] = useState<Quiz | null>(null)
  const [quizSubject, setQuizSubject] = useState('')
  const handled = useRef(new Set<string>())
  const selection = useRef(subject)
  selection.current = subject
  useEffect(() => {
    const media = window.matchMedia('(max-width: 760px)')
    const update = () => {
      setIsMobile(media.matches)
      if (!media.matches) setMobileNav(false)
    }
    media.addEventListener('change', update)
    return () => media.removeEventListener('change', update)
  }, [])
  useEffect(() => {
    if (!isMobile || !mobileNav) return
    const previous = document.activeElement as HTMLElement | null
    const items = Array.from(
      document.querySelectorAll<HTMLButtonElement>(
        '.sidebar button, .sidebar a',
      ),
    )
    items[0]?.focus()
    const keyboard = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setMobileNav(false)
      if (event.key === 'Tab' && items.length) {
        if (event.shiftKey && document.activeElement === items[0]) {
          event.preventDefault()
          items.at(-1)?.focus()
        } else if (!event.shiftKey && document.activeElement === items.at(-1)) {
          event.preventDefault()
          items[0]?.focus()
        }
      }
    }
    document.addEventListener('keydown', keyboard)
    return () => {
      document.removeEventListener('keydown', keyboard)
      previous?.focus()
    }
  }, [isMobile, mobileNav])
  const notify = useCallback(
    (error: unknown) => setNotice({ text: errorText(error), error: true }),
    [],
  )

  const boot = useCallback(async () => {
    setBooting(true)
    try {
      const [list, settings, jobList] = await Promise.all([
        api<Subject[]>('/subjects'),
        api<Config>('/config'),
        api<Job[]>('/jobs'),
      ])
      setSubjects(list)
      setConfig(settings)
      setJobs(jobList)
      setConnectionError('')
      setSubject((current) =>
        list.some((s) => s.name === current) ? current : list[0]?.name || '',
      )
    } catch (error) {
      setConnectionError(errorText(error))
    } finally {
      setBooting(false)
    }
  }, [])
  useEffect(() => {
    void boot()
  }, [boot])

  const loadCourse = useCallback(async (name: string) => {
    const list = await api<Subject[]>('/subjects')
    setSubjects(list)
    if (!name) return
    const [library, insights, results, savedQuiz] = await Promise.all([
      api<Material[]>(`/library?${query({ subject: name })}`),
      api<Analysis | null>(`/analysis?${query({ subject: name })}`),
      api<Progress[]>(`/progress?${query({ subject: name })}`),
      api<Quiz | null>(`/quizzes/latest?${query({ subject: name })}`),
    ])
    if (selection.current !== name) return
    setMaterials(library)
    setAnalysis(insights)
    setProgress(results)
    setQuiz(savedQuiz)
    setQuizSubject(name)
  }, [])

  useEffect(() => {
    setTopic(null)
    setMaterials([])
    setAnalysis(null)
    setProgress([])
    if (!subject) return
    localStorage.setItem('selected-subject', subject)
    setLoadingCourse(true)
    void loadCourse(subject)
      .catch(notify)
      .finally(() => {
        if (selection.current === subject) setLoadingCourse(false)
      })
  }, [subject, loadCourse, notify])

  const runningIds = jobs
    .filter(active)
    .map((j) => j.id)
    .join(',')
  useEffect(() => {
    if (!runningIds) return
    let stopped = false
    let timer: ReturnType<typeof setTimeout>
    const poll = async () => {
      try {
        const updated = await Promise.all(
          runningIds.split(',').map((id) => api<Job>(`/jobs/${id}`)),
        )
        if (stopped) return
        setJobs((previous) =>
          previous.map((job) => updated.find((j) => j.id === job.id) || job),
        )
        for (const job of updated) {
          if (active(job) || handled.current.has(job.id)) continue
          handled.current.add(job.id)
          if (job.status === 'failed')
            setNotice({ text: job.error || 'Processing failed', error: true })
          if (job.status === 'completed') {
            if (job.kind === 'quiz') {
              setQuiz(job.result as Quiz)
              setQuizSubject(job.subject)
              if (selection.current === job.subject) setView('practice')
            } else {
              await loadCourse(selection.current)
              const files = (
                job.result as {
                  files?: {
                    filename: string
                    status: string
                    error?: string
                  }[]
                }
              )?.files
              const failed = files?.filter((file) => file.status === 'failed')
              setNotice(
                failed?.length
                  ? {
                      text: failed
                        .map((f) => `${f.filename}: ${f.error}`)
                        .join(' · '),
                      error: true,
                    }
                  : {
                      text:
                        job.kind === 'analysis'
                          ? 'Your course insights are ready.'
                          : 'Materials are ready to study.',
                    },
              )
            }
          }
        }
      } catch (error) {
        if (!stopped) notify(error)
      }
      if (!stopped) timer = setTimeout(poll, document.hidden ? 5000 : 1200)
    }
    timer = setTimeout(poll, 0)
    return () => {
      stopped = true
      clearTimeout(timer)
    }
  }, [runningIds, loadCourse, notify])

  const enqueue = async (path: string, body: unknown) => {
    try {
      const job = await post<Job>(path, body)
      setJobs((previous) => [job, ...previous])
      return job
    } catch (error) {
      notify(error)
    }
  }
  const current = subjects.find((s) => s.name === subject)
  const subjectJobs = jobs.filter((j) => j.subject === subject)
  const running = subjectJobs.filter(active)
  const paperYears = [
    ...new Set(
      materials
        .filter((m) => m.source_type === 'past_qp')
        .map((m) => m.year)
        .filter((year): year is number => year !== null),
    ),
  ].sort()
  const recurring = analysis?.topics.filter((t) => t.num_years >= 2) || []
  const changeView = (next: View) => {
    setView(next)
    setMobileNav(false)
  }

  const openSource = (material: Material, page?: number) => {
    setSource(material)
    setSourcePage(page)
  }
  const openCitation = (filename: string, page?: number) => {
    const material = materials.find((m) => m.filename === filename)
    if (material) {
      setTopic(null)
      void openSource(material, page)
    }
  }

  return (
    <div className="app-shell">
      <a href="#main-content" className="skip-link">
        Skip to content
      </a>
      {mobileNav && (
        <button
          className="nav-scrim"
          aria-label="Close navigation"
          onClick={() => setMobileNav(false)}
        />
      )}
      <aside
        className={`sidebar ${mobileNav ? 'sidebar-open' : ''}`}
        inert={isMobile && !mobileNav}
      >
        {isMobile && mobileNav && (
          <button
            className="icon-button sidebar-close"
            onClick={() => setMobileNav(false)}
            aria-label="Close navigation"
          >
            <X size={19} />
          </button>
        )}
        <a
          className="brand"
          href="#"
          onClick={(e) => {
            e.preventDefault()
            changeView('subjects')
          }}
        >
          <span className="brand-mark">
            <BookOpen size={21} strokeWidth={1.8} />
          </span>
          <span>
            easy to study
            <span className="brand-caption">Make room for understanding.</span>
          </span>
        </a>
        <div className="sidebar-label">Workspace</div>
        <nav className="workspace-nav" aria-label="Workspace">
          <button
            className={view === 'subjects' ? 'nav-item selected' : 'nav-item'}
            aria-current={view === 'subjects' ? 'page' : undefined}
            onClick={() => changeView('subjects')}
          >
            <Layers3 size={18} />
            My subjects<span className="nav-count">{subjects.length}</span>
          </button>
        </nav>
        <div className="sidebar-label flex items-center justify-between">
          Subjects
          {config?.uploads_enabled && (
            <button
              className="small-icon"
              onClick={() => {
                setModal('subject')
                setMobileNav(false)
              }}
              aria-label="Add subject"
            >
              <Plus size={16} />
            </button>
          )}
        </div>
        <nav className="subject-nav" aria-label="Subjects">
          {subjects.map((s) => (
            <button
              key={s.name}
              className={`subject-link ${s.name === subject && view !== 'settings' && view !== 'subjects' ? 'subject-selected' : ''}`}
              onClick={() => {
                setSubject(s.name)
                changeView('overview')
              }}
            >
              <span className="subject-dot" />{' '}
              <span className="truncate">{s.name}</span>
            </button>
          ))}
          {!subjects.length && !booting && (
            <p className="sidebar-empty">Your courses will appear here.</p>
          )}
        </nav>
        {config?.uploads_enabled && (
          <button
            className="add-subject"
            onClick={() => {
              setModal('subject')
              setMobileNav(false)
            }}
          >
            <Plus size={16} />
            New subject
          </button>
        )}
        <div className="sidebar-bottom">
          <div className="workspace-note">
            <GraduationCap size={20} />
            <p>
              A little focus.
              <br />
              <strong>A lot more clarity.</strong>
            </p>
          </div>
          <button
            className={`nav-item ${view === 'settings' ? 'selected' : ''}`}
            onClick={() => changeView('settings')}
          >
            <Settings2 size={18} />
            Settings & activity
          </button>
          <div className="provider-note">
            <span className="status-dot" />
            {config?.provider === 'groq'
              ? 'Groq · free inference'
              : 'Local workspace'}
            <span className="ml-auto text-[10px]">v0.2</span>
          </div>
        </div>
      </aside>
      <div className="main-shell" inert={isMobile && mobileNav}>
        <header className="topbar">
          <button
            className="icon-button mobile-menu"
            onClick={() => setMobileNav(true)}
            aria-label="Open navigation"
          >
            <Menu size={20} />
          </button>
          <div className="breadcrumb">
            <button onClick={() => changeView('subjects')}>My subjects</button>
            <ChevronRight size={13} />
            <strong>
              {view === 'settings'
                ? 'Settings & activity'
                : view === 'subjects'
                  ? 'All courses'
                  : subject || 'Get started'}
            </strong>
          </div>
          <span className="topbar-label">Private study workspace</span>
        </header>
        <main id="main-content" className="main-content">
          {notice && (
            <div
              role="alert"
              className={`notice ${notice.error ? 'notice-error' : ''}`}
            >
              <span>
                {notice.error ? (
                  <CircleHelp size={17} />
                ) : (
                  <CheckCircle2 size={17} />
                )}
                {notice.text}
              </span>
              <button
                className="icon-button"
                aria-label="Dismiss notification"
                onClick={() => setNotice(null)}
              >
                <X size={16} />
              </button>
            </div>
          )}
          {connectionError ? (
            <Empty
              icon={<CircleHelp size={28} />}
              title="Your workspace is offline"
              text={`Start the FastAPI backend and try again. ${connectionError}`}
            >
              <button className="button primary" onClick={() => void boot()}>
                Reconnect
              </button>
              <TokenInput onSave={() => void boot()} />
            </Empty>
          ) : booting ? (
            <div className="loading-state" role="status">
              <Loader2 className="animate-spin" size={22} />
              Opening your workspace…
            </div>
          ) : view === 'settings' ? (
            <Settings jobs={jobs} config={config} notify={notify} />
          ) : view === 'subjects' ? (
            <Subjects
              subjects={subjects}
              canCreate={!!config?.uploads_enabled}
              open={(name) => {
                setSubject(name)
                changeView('overview')
              }}
              create={() => setModal('subject')}
            />
          ) : !subject ? (
            <div className="onboarding">
              <span className="eyebrow">Start here</span>
              <h1>
                Your next exam.
                <br />A clearer plan.
              </h1>
              <p>
                Bring your notes, textbooks, and past papers together. Find what
                matters, understand the context, and practice with purpose.
              </p>
              <button
                className="button primary"
                onClick={() => {
                  setModal('subject')
                  setMobileNav(false)
                }}
              >
                <Plus size={17} />
                Create your first subject
              </button>
              <div className="onboarding-steps">
                {[
                  'Add your course materials',
                  'Discover recurring exam topics',
                  'Practice with source-backed questions',
                ].map((text, i) => (
                  <div key={text}>
                    <span>{String(i + 1).padStart(2, '0')}</span>
                    {text}
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <>
              <section className="course-heading">
                <div>
                  <span className="eyebrow">Course overview</span>
                  <h1>{subject}</h1>
                  <p>
                    {current?.files || 0} materials <span>·</span>{' '}
                    {current?.pages || 0} source pages <span>·</span>{' '}
                    {paperYears.length} exam{' '}
                    {paperYears.length === 1 ? 'year' : 'years'}
                  </p>
                </div>
                {config?.uploads_enabled && (
                  <button
                    className="button secondary"
                    onClick={() => setModal('upload')}
                  >
                    <Plus size={17} />
                    Add material
                  </button>
                )}
              </section>
              <nav className="course-tabs" aria-label="Course sections">
                {(
                  ['overview', 'materials', 'practice', 'progress'] as View[]
                ).map((item) => (
                  <button
                    key={item}
                    aria-current={view === item ? 'page' : undefined}
                    className={view === item ? 'tab-active' : ''}
                    onClick={() => setView(item)}
                  >
                    {view === item && (
                      <motion.span
                        layoutId="tab-highlight"
                        className="tab-highlight"
                        transition={{
                          type: 'spring',
                          bounce: 0,
                          duration: 0.3,
                        }}
                      />
                    )}
                    <span>
                      {item === 'overview'
                        ? 'Overview'
                        : item[0].toUpperCase() + item.slice(1)}
                    </span>
                    {item === 'materials' && <small>{materials.length}</small>}
                  </button>
                ))}
              </nav>
              {running.map((job) => (
                <div key={job.id} className="job-banner" role="status">
                  <Loader2 size={18} className="animate-spin shrink-0" />
                  <div>
                    <strong>
                      {job.kind === 'analysis'
                        ? 'Building your study insights'
                        : job.kind === 'upload'
                          ? 'Preparing your materials'
                          : 'Creating your practice questions'}
                    </strong>
                    <p>{job.message}</p>
                    <div className="progress-track">
                      <span
                        style={{ width: `${Math.max(3, job.progress * 100)}%` }}
                      />
                    </div>
                  </div>
                  <button
                    className="button quiet"
                    onClick={() =>
                      void post<Job>(`/jobs/${job.id}/cancel`, {})
                        .then((updated) =>
                          setJobs((previous) =>
                            previous.map((j) =>
                              j.id === job.id ? updated : j,
                            ),
                          ),
                        )
                        .catch(notify)
                    }
                  >
                    Cancel
                  </button>
                </div>
              ))}
              {loadingCourse ? (
                <div className="loading-state" role="status">
                  <Loader2 className="animate-spin" size={20} />
                  Loading course materials…
                </div>
              ) : view === 'overview' ? (
                <>
                  <div className="overview-grid">
                    <section className="focus-panel">
                      <span className="eyebrow">
                        <Sparkles size={14} />
                        Your study plan
                      </span>
                      <h2>
                        {analysis
                          ? 'Know where to focus.'
                          : 'Less scattered. More prepared.'}
                      </h2>
                      <p>
                        {analysis
                          ? 'Explore concepts that have appeared across exam years, with your teaching material beside every question.'
                          : 'Your past papers tell a story. Connect them to your course material to find the topics worth your attention.'}
                      </p>
                      <button
                        className="button primary"
                        disabled={
                          running.some((j) => j.kind === 'analysis') ||
                          !materials.some((m) => m.source_type !== 'past_qp')
                        }
                        onClick={() => void enqueue('/analysis', { subject })}
                      >
                        {analysis ? 'Refresh insights' : 'Analyze this course'}
                        <ArrowRight size={16} />
                      </button>
                      {analysis ? (
                        <span className="panel-footnote">
                          Updated {stamp(analysis.generated_at)} · unchanged
                          steps are reused
                        </span>
                      ) : (
                        <span className="panel-footnote">
                          Add teaching material to begin. Past papers unlock
                          exam patterns.
                        </span>
                      )}
                    </section>
                    <section className="coverage-panel">
                      <span className="eyebrow">At a glance</span>
                      <div className="coverage-number">
                        {analysis ? recurring.length : paperYears.length}
                        <span>
                          {analysis
                            ? 'recurring topics'
                            : 'exam years available'}
                        </span>
                      </div>
                      <div className="year-strip">
                        {paperYears.length ? (
                          paperYears.map((year) => (
                            <div key={year}>
                              <span className="year-bar" />
                              <span>{year}</span>
                            </div>
                          ))
                        ) : (
                          <p>
                            Add past papers from different years to uncover
                            patterns.
                          </p>
                        )}
                      </div>
                      <p>
                        {analysis
                          ? `${analysis.questions.length} complete exam questions connected to ${analysis.topics.length} taught topics.`
                          : 'Recurrence is counted by distinct exam years, so repeated copies do not inflate the signal.'}
                      </p>
                    </section>
                  </div>
                  <div className="section-heading">
                    <div>
                      <span className="eyebrow">What to study</span>
                      <h2>
                        {analysis ? 'Your topic map' : 'Build your foundation'}
                      </h2>
                    </div>
                    {analysis && (
                      <span className="subtle-label">
                        {analysis.topics.length} topics · ranked by exam
                        recurrence
                      </span>
                    )}
                  </div>
                  {analysis ? (
                    <TopicList topics={analysis.topics} onSelect={setTopic} />
                  ) : (
                    <div className="foundation-grid">
                      {[
                        {
                          icon: <FileText />,
                          title: 'Teaching material',
                          text: 'Notes, slides, and textbooks give each topic its context.',
                          count: materials.filter(
                            (m) => m.source_type !== 'past_qp',
                          ).length,
                        },
                        {
                          icon: <Clock3 />,
                          title: 'Past exam papers',
                          text: 'Dated papers show which topics recur across years.',
                          count: materials.filter(
                            (m) => m.source_type === 'past_qp',
                          ).length,
                        },
                      ].map((item) => (
                        <button
                          key={item.title}
                          className="foundation-item"
                          onClick={() => setView('materials')}
                        >
                          <span className="foundation-icon">{item.icon}</span>
                          <div>
                            <h3>{item.title}</h3>
                            <p>{item.text}</p>
                            <span>
                              {item.count
                                ? `${item.count} materials added`
                                : 'Ready when you are'}
                            </span>
                          </div>
                          <ChevronRight size={18} />
                        </button>
                      ))}
                    </div>
                  )}
                  {analysis && (
                    <p className="context-note">
                      <CircleHelp size={15} />
                      Past recurrence helps you prioritize. It does not predict
                      your next exam.
                    </p>
                  )}
                </>
              ) : view === 'materials' ? (
                <Library
                  materials={materials}
                  demo={!!config?.demo}
                  busy={running.length > 0}
                  open={(m) => void openSource(m)}
                  remove={setDeleting}
                  editYear={setEditingYear}
                  add={() => setModal('upload')}
                />
              ) : view === 'practice' ? (
                <Practice
                  key={`${subject}:${quizSubject === subject ? quiz?.quiz_id || 'new' : 'new'}`}
                  analysis={analysis}
                  quiz={quizSubject === subject ? quiz : null}
                  busy={running.some((j) => j.kind === 'quiz')}
                  generate={(name, kind, count) => {
                    void enqueue('/quizzes', {
                      subject,
                      topic: name,
                      question_type: kind,
                      count,
                    })
                  }}
                  notify={notify}
                  onAnswer={() => void loadCourse(subject)}
                  citation={openCitation}
                />
              ) : (
                <ProgressView
                  progress={progress}
                  practice={() => setView('practice')}
                />
              )}
            </>
          )}
          <footer className="page-footer">
            <BookOpen size={14} />
            <span>A calmer way to prepare.</span>
            <span className="ml-auto">Easy to Study</span>
          </footer>
        </main>
      </div>
      {modal === 'subject' && (
        <NewSubject
          close={() => setModal(null)}
          save={async (name) => {
            await post('/subjects', { name })
            const list = await api<Subject[]>('/subjects')
            setSubjects(list)
            setSubject(name)
            setView('overview')
            setModal(null)
          }}
        />
      )}
      {modal === 'upload' && config && (
        <Upload
          subject={subject}
          maxMB={config.max_upload_mb}
          close={() => setModal(null)}
          save={async (form) => {
            const job = await api<Job>('/uploads', {
              method: 'POST',
              body: form,
            })
            setJobs((previous) => [job, ...previous])
            setModal(null)
            setView('materials')
          }}
        />
      )}
      {topic && (
        <Modal title={topic.name} wide close={() => setTopic(null)}>
          <div className="topic-detail">
            <span className="eyebrow">From your materials</span>
            <p className="topic-summary">{topic.summary}</p>
            <div className="flex flex-wrap gap-2 mb-7">
              {topic.years.map((year) => (
                <span className="year-pill" key={year}>
                  {year}
                </span>
              ))}
              <span className="subtle-label">
                {topic.num_years} distinct exam years
              </span>
            </div>
            <h3>Sources</h3>
            <div className="source-links">
              {topic.sources.map((s) => (
                <button
                  key={`${s.filename}:${s.page}`}
                  onClick={() => openCitation(s.filename, s.page)}
                  aria-label={`Open ${s.filename}, page ${s.page}`}
                >
                  <FileText size={15} />
                  <span>
                    {s.filename} · Page {s.page}
                  </span>
                  <ChevronRight size={14} />
                </button>
              ))}
            </div>
            <h3>Past-paper questions</h3>
            {analysis?.questions
              .filter((q) => q.topic === topic.name)
              .map((q) => (
                <article className="paper-question" key={q.id}>
                  <button
                    className="source-caption"
                    onClick={() => openCitation(q.filename, q.page)}
                  >
                    {q.year} · {q.filename} · Page {q.page}
                    <ArrowRight size={12} />
                  </button>
                  <p>{q.question}</p>
                </article>
              ))}
            {!analysis?.questions.some((q) => q.topic === topic.name) && (
              <p className="muted">
                No past-paper questions have been matched to this topic.
              </p>
            )}
            <h3>Recurring exam questions</h3>
            {analysis?.recurring_groups
              .filter((g) => g.topic === topic.name)
              .map((group, i) => (
                <article className="repeat-group" key={i}>
                  <strong>{group.years.join(' · ')}</strong>
                  <p>{group.reason}</p>
                  {group.questions.map((q) => (
                    <div key={q.id}>
                      <span>{q.year}</span>
                      {q.question}
                    </div>
                  ))}
                </article>
              ))}
            {!analysis?.recurring_groups.some(
              (g) => g.topic === topic.name,
            ) && (
              <p className="muted">
                No questions with a repeated task were found across years.
              </p>
            )}
            <p className="context-note">
              These are candidate repeats. Check the original pages before
              relying on them.
            </p>
            <button
              className="button primary"
              onClick={() => {
                setTopic(null)
                setView('practice')
              }}
            >
              Practice this course
              <ArrowRight size={16} />
            </button>
          </div>
        </Modal>
      )}
      {source && (
        <Modal title={source.filename} wide close={() => setSource(null)}>
          <SourceReader
            key={`${subject}:${source.source_type}:${source.filename}:${sourcePage || 0}`}
            subject={subject}
            material={source}
            initialPage={sourcePage}
          />
        </Modal>
      )}
      {deleting && (
        <Modal title="Remove this material?" close={() => setDeleting(null)}>
          <div className="modal-body">
            <p>
              <strong>{deleting.filename}</strong> will be removed from{' '}
              <strong>{subject}</strong>. Saved course insights will be cleared
              so they cannot refer to this file.
            </p>
            <div className="modal-actions">
              <button
                className="button secondary"
                onClick={() => setDeleting(null)}
              >
                Keep material
              </button>
              <button
                className="button danger"
                onClick={async () => {
                  try {
                    await api(
                      `/library?${query({ subject, filename: deleting.filename, source_type: deleting.source_type })}`,
                      { method: 'DELETE' },
                    )
                    setDeleting(null)
                    await loadCourse(subject)
                    setNotice({
                      text: 'Material removed. Analyze the remaining course files to refresh insights.',
                    })
                  } catch (error) {
                    notify(error)
                  }
                }}
              >
                Remove material
              </button>
            </div>
          </div>
        </Modal>
      )}
      {editingYear && (
        <EditYear
          material={editingYear}
          close={() => setEditingYear(null)}
          save={async (year) => {
            await api('/library/year', {
              method: 'PATCH',
              body: JSON.stringify({
                subject,
                filename: editingYear.filename,
                year,
              }),
            })
            setEditingYear(null)
            await loadCourse(subject)
            setNotice({
              text: 'Exam year updated. Refresh course insights to recalculate recurrence.',
            })
          }}
        />
      )}
    </div>
  )
}

export default App
