import {
  AudioLines,
  ChevronRight,
  CircleHelp,
  FileText,
  FolderOpen,
  Search,
  Settings2,
  Trash2,
  UploadCloud,
} from 'lucide-react'
import { useState } from 'react'
import { type Material } from '../api'
import { kinds } from '../utils'
import { Empty } from './Common'

export function Library({
  materials,
  demo,
  busy,
  open,
  remove,
  editYear,
  add,
}: {
  materials: Material[]
  demo: boolean
  busy: boolean
  open: (m: Material) => void
  remove: (m: Material) => void
  editYear: (m: Material) => void
  add: () => void
}) {
  const [filter, setFilter] = useState('all')
  const [search, setSearch] = useState('')
  const filtered = materials.filter(
    (m) =>
      (filter === 'all' || m.source_type === filter) &&
      m.filename.toLowerCase().includes(search.toLowerCase()),
  )
  return (
    <section>
      <div className="section-heading">
        <div>
          <span className="eyebrow">EVERYTHING IN ONE PLACE</span>
          <h2>Your course library</h2>
        </div>
        <span className="subtle-label">{materials.length} materials</span>
      </div>
      {!materials.length ? (
        <Empty
          icon={<FolderOpen size={28} />}
          title="Start with what you already have"
          text="Upload lecture notes, slides, textbooks, recordings, and past papers for this subject."
        >
          {!demo && (
            <button className="button primary" onClick={add}>
              <UploadCloud size={17} />
              Add course material
            </button>
          )}
        </Empty>
      ) : (
        <div className="library-panel">
          <div className="list-toolbar">
            <div className="search-field">
              <Search size={16} />
              <input
                aria-label="Search materials"
                placeholder="Search your materials"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
              />
            </div>
            <select
              aria-label="Filter material type"
              value={filter}
              onChange={(e) => setFilter(e.target.value)}
            >
              <option value="all">All materials</option>
              {Object.entries(kinds).map(([kind, label]) => (
                <option key={kind} value={kind}>
                  {label}
                </option>
              ))}
            </select>
          </div>
          {filtered.map((m) => (
            <div
              key={`${m.source_type}:${m.filename}`}
              className="material-row"
            >
              <span className="file-icon">
                {m.source_type === 'lecture_video' ? (
                  <AudioLines size={21} />
                ) : (
                  <FileText size={21} />
                )}
              </span>
              <button className="material-copy" onClick={() => open(m)}>
                <strong>{m.filename}</strong>
                <span>
                  {kinds[m.source_type]} · {m.pages}{' '}
                  {m.source_type === 'lecture_video' ? 'segments' : 'pages'}
                  {m.year ? ` · ${m.year}` : ''}
                </span>
              </button>
              <button
                className="button quiet inspect-button"
                onClick={() => open(m)}
              >
                View source
                <ChevronRight size={14} />
              </button>
              {!demo && m.source_type === 'past_qp' && (
                <button
                  className="button quiet"
                  disabled={busy}
                  aria-label={`Change exam year for ${m.filename}`}
                  onClick={() => editYear(m)}
                >
                  {m.year}
                  <Settings2 size={13} />
                </button>
              )}
              {!demo && (
                <button
                  className="icon-button delete-button"
                  disabled={busy}
                  aria-label={`Remove ${m.filename}`}
                  onClick={() => remove(m)}
                >
                  <Trash2 size={16} />
                </button>
              )}
            </div>
          ))}
          {!filtered.length && (
            <p className="p-6 muted">No materials match this search.</p>
          )}
        </div>
      )}
      <p className="context-note">
        <CircleHelp size={15} />
        Keep each course separate. Read the extracted text if topics or
        questions look incorrect.
      </p>
    </section>
  )
}
