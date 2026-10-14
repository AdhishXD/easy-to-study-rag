import {
  ArrowDown,
  ArrowRight,
  FileText,
  Loader2,
  UploadCloud,
  X,
} from 'lucide-react'
import { useRef, useState } from 'react'
import { type Material } from '../api'
import { errorText, kinds } from '../utils'
import { Modal } from './Common'

export function NewSubject({
  close,
  save,
}: {
  close: () => void
  save: (name: string) => Promise<void>
}) {
  const [name, setName] = useState('')
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)
  return (
    <Modal title="A space for your subject" close={close}>
      <form
        className="modal-body"
        onSubmit={async (e) => {
          e.preventDefault()
          setSaving(true)
          try {
            await save(name.trim())
          } catch (err) {
            setError(errorText(err))
          } finally {
            setSaving(false)
          }
        }}
      >
        <p className="muted">
          Keep one course's teaching materials and past papers together.
        </p>
        <label className="field-label" htmlFor="subject-name">
          Subject name
        </label>
        <input
          id="subject-name"
          autoFocus
          className="text-input"
          maxLength={100}
          placeholder="e.g. Database Management Systems"
          value={name}
          onChange={(e) => setName(e.target.value)}
          required
        />
        {error && (
          <p className="inline-error" role="alert">
            {error}
          </p>
        )}
        <div className="modal-actions">
          <button type="button" className="button secondary" onClick={close}>
            Cancel
          </button>
          <button className="button primary" disabled={!name.trim() || saving}>
            {saving && <Loader2 size={16} className="animate-spin" />}Create
            subject
            <ArrowRight size={16} />
          </button>
        </div>
      </form>
    </Modal>
  )
}

export function EditYear({
  material,
  close,
  save,
}: {
  material: Material
  close: () => void
  save: (year: number) => Promise<void>
}) {
  const [year, setYear] = useState(material.year || new Date().getFullYear())
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)
  return (
    <Modal title="Correct the exam year" close={close}>
      <form
        className="modal-body"
        onSubmit={async (e) => {
          e.preventDefault()
          setSaving(true)
          try {
            await save(year)
          } catch (err) {
            setError(errorText(err))
          } finally {
            setSaving(false)
          }
        }}
      >
        <p className="muted">{material.filename}</p>
        <label className="field-label" htmlFor="correct-year">
          Exam year
        </label>
        <input
          className="text-input"
          type="number"
          min="1900"
          max="2100"
          id="correct-year"
          value={year}
          onChange={(e) => setYear(Number(e.target.value))}
          required
        />
        <p className="privacy-note">
          Use the year printed on the paper. This clears saved analysis so
          recurrence can be recalculated.
        </p>
        {error && (
          <p className="inline-error" role="alert">
            {error}
          </p>
        )}
        <div className="modal-actions">
          <button className="button secondary" type="button" onClick={close}>
            Cancel
          </button>
          <button className="button primary" disabled={saving}>
            Save year
          </button>
        </div>
      </form>
    </Modal>
  )
}

export function Upload({
  subject,
  maxMB,
  close,
  save,
}: {
  subject: string
  maxMB: number
  close: () => void
  save: (data: FormData) => Promise<void>
}) {
  const [kind, setKind] = useState('lecture_note')
  const [year, setYear] = useState('')
  const [files, setFiles] = useState<File[]>([])
  const [dragging, setDragging] = useState(false)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const input = useRef<HTMLInputElement>(null)
  const addFiles = (items: File[]) => {
    setFiles((previous) => [
      ...previous,
      ...items.filter(
        (item) => !previous.some((file) => file.name === item.name),
      ),
    ])
    setError('')
  }
  const size = files.reduce((n, file) => n + file.size, 0) / 1024 / 1024
  return (
    <Modal title="Bring your material together" close={close}>
      <form
        className="modal-body"
        onSubmit={async (e) => {
          e.preventDefault()
          setSaving(true)
          setError('')
          try {
            const data = new FormData()
            data.set('subject', subject)
            data.set('source_type', kind)
            data.set('year', year || '0')
            files.forEach((file) => data.append('files', file))
            await save(data)
          } catch (err) {
            setError(errorText(err))
          } finally {
            setSaving(false)
          }
        }}
      >
        <p className="muted">
          Adding to <strong>{subject}</strong>. Choose files that belong to this
          course.
        </p>
        <label className="field-label" htmlFor="material-type">
          Material type
        </label>
        <select
          id="material-type"
          className="text-input"
          value={kind}
          onChange={(e) => {
            setKind(e.target.value)
            setFiles([])
          }}
        >
          {Object.entries(kinds)
            .filter(([k]) => k !== 'lecture_slide')
            .map(([key, value]) => (
              <option key={key} value={key}>
                {value}
              </option>
            ))}
        </select>
        {kind === 'past_qp' && (
          <>
            <label className="field-label" htmlFor="exam-year">
              Exam year{' '}
              <span className="muted font-normal">
                (optional if present in filename)
              </span>
            </label>
            <input
              className="text-input"
              id="exam-year"
              type="number"
              min="1900"
              max="2100"
              placeholder="2025"
              value={year}
              onChange={(e) => setYear(e.target.value)}
            />
          </>
        )}
        <div
          className={`dropzone ${dragging ? 'dropzone-active' : ''}`}
          onDragOver={(e) => {
            e.preventDefault()
            setDragging(true)
          }}
          onDragLeave={() => setDragging(false)}
          onDrop={(e) => {
            e.preventDefault()
            setDragging(false)
            addFiles(Array.from(e.dataTransfer.files))
          }}
        >
          <UploadCloud size={30} strokeWidth={1.4} />
          <h3>Drop your files here</h3>
          <p>
            or{' '}
            <button
              type="button"
              className="text-button"
              onClick={() => input.current?.click()}
            >
              browse files
            </button>
          </p>
          <span>
            {kind === 'lecture_video'
              ? 'MP4, MP3, WAV, M4A, WEBM'
              : 'PDF, PPTX, PPT, DOCX, TXT, MD'}{' '}
            · up to {maxMB} MB per batch
          </span>
          <input
            ref={input}
            aria-label="Choose material files"
            type="file"
            multiple
            className="sr-only"
            accept={
              kind === 'lecture_video'
                ? '.mp4,.mp3,.wav,.m4a,.webm'
                : '.pdf,.pptx,.ppt,.docx,.txt,.md'
            }
            onChange={(e) => {
              addFiles(Array.from(e.target.files || []))
              e.target.value = ''
            }}
          />
        </div>
        <div className="upload-file-list">
          {files.map((file) => (
            <div key={file.name}>
              <FileText size={16} />
              <span>
                {file.name}
                <small>{(file.size / 1024 / 1024).toFixed(1)} MB</small>
              </span>
              <button
                className="icon-button"
                type="button"
                aria-label={`Remove selected ${file.name}`}
                onClick={() => setFiles(files.filter((f) => f !== file))}
              >
                <X size={15} />
              </button>
            </div>
          ))}
        </div>
        {size > maxMB && (
          <p className="inline-error">
            Choose a smaller batch. These files total {size.toFixed(1)} MB.
          </p>
        )}
        {files.length > 20 && (
          <p className="inline-error">Upload at most 20 files at a time.</p>
        )}
        {error && (
          <p className="inline-error" role="alert">
            {error}
          </p>
        )}
        <div className="modal-actions">
          <button type="button" className="button secondary" onClick={close}>
            Cancel
          </button>
          <button
            className="button primary"
            disabled={
              !files.length || size > maxMB || files.length > 20 || saving
            }
          >
            {saving ? (
              <Loader2 size={16} className="animate-spin" />
            ) : (
              <ArrowDown size={16} />
            )}
            {saving
              ? 'Uploading…'
              : `Prepare ${files.length || ''} ${files.length === 1 ? 'file' : 'files'}`}
          </button>
        </div>
        <p className="privacy-note">
          Unchanged files are reused. Video transcription and first-time
          indexing can take longer.
        </p>
      </form>
    </Modal>
  )
}
