import { ArrowUpRight, BookOpen, FileText, Plus, Search } from 'lucide-react'
import { useState } from 'react'
import { type Subject } from '../api'
import { Empty } from './Common'

export function Subjects({
  subjects,
  canCreate,
  open,
  create,
}: {
  subjects: Subject[]
  canCreate: boolean
  open: (name: string) => void
  create: () => void
}) {
  const [search, setSearch] = useState('')
  const filtered = subjects.filter((subject) =>
    subject.name.toLowerCase().includes(search.toLowerCase()),
  )
  return (
    <section>
      <div className="course-heading">
        <div>
          <span className="eyebrow">Your study space</span>
          <h1>My subjects</h1>
          <p>Pick up where you left off, or make room for a new course.</p>
        </div>
        {canCreate && (
          <button className="button primary" onClick={create}>
            <Plus size={17} /> New subject
          </button>
        )}
      </div>
      {subjects.length > 0 && (
        <div className="subjects-toolbar">
          <div className="search-field">
            <Search size={16} />
            <input
              aria-label="Search subjects"
              placeholder="Find a subject"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>
          <span className="subtle-label">
            {subjects.length} {subjects.length === 1 ? 'subject' : 'subjects'}
          </span>
        </div>
      )}
      {filtered.length ? (
        <div className="subject-grid">
          {filtered.map((subject) => (
            <button
              className="subject-card"
              key={subject.name}
              onClick={() => open(subject.name)}
              aria-label={`Open ${subject.name}`}
            >
              <div className="subject-card-top">
                <span className="subject-card-icon">
                  <BookOpen size={24} strokeWidth={1.5} />
                </span>
                <ArrowUpRight size={18} />
              </div>
              <h2>{subject.name}</h2>
              <p>
                <FileText size={14} /> {subject.files}{' '}
                {subject.files === 1 ? 'material' : 'materials'} ·{' '}
                {subject.pages} source pages
              </p>
              <div className="subject-card-footer">
                <span>
                  {subject.years
                    ? `${subject.years} exam ${subject.years === 1 ? 'year' : 'years'}`
                    : subject.files
                      ? 'Teaching material available'
                      : 'Ready for your course material'}
                </span>
                <span>
                  Continue <ArrowUpRight size={13} />
                </span>
              </div>
            </button>
          ))}
        </div>
      ) : (
        <Empty
          icon={<BookOpen size={28} />}
          title={
            subjects.length
              ? 'No matching subjects'
              : 'Make room for your first course'
          }
          text={
            subjects.length
              ? 'Try a different subject name.'
              : 'Create a subject to organize your notes, textbooks, and past papers.'
          }
        >
          {!subjects.length && canCreate && (
            <button className="button primary" onClick={create}>
              <Plus size={17} /> Create your first subject
            </button>
          )}
        </Empty>
      )}
    </section>
  )
}
