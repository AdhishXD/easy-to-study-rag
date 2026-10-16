import { lazy, Suspense, useEffect, useState } from 'react'
import { ChevronLeft, ChevronRight, Loader2, Minus, Plus } from 'lucide-react'
import { api, apiUrl, query, type Material, type Page } from '../api'
import { kinds, errorText } from '../utils'

const PdfPage = lazy(() => import('./PdfPage'))
type Original = {
  available: boolean
  size: number | null
  version: string | null
}

export function SourceReader({
  subject,
  material,
  initialPage,
}: {
  subject: string
  material: Material
  initialPage?: number
}) {
  const params = query({
    subject,
    filename: material.filename,
    source_type: material.source_type,
  })
  const [original, setOriginal] = useState<Original | null>(null)
  const [numbers, setNumbers] = useState<number[]>([])
  const [page, setPage] = useState(initialPage || 1)
  const [pdfPages, setPdfPages] = useState(0)
  const [mode, setMode] = useState<'original' | 'text'>('original')
  const [zoom, setZoom] = useState(1)
  const [text, setText] = useState<Page | null>(null)
  const [loading, setLoading] = useState(true)
  const [loadingText, setLoadingText] = useState(false)
  const [error, setError] = useState('')
  const isPdf = material.filename.toLowerCase().endsWith('.pdf')

  useEffect(() => {
    const controller = new AbortController()
    void Promise.all([
      api<Original>(`/original-info?${params}`, { signal: controller.signal }),
      api<number[]>(`/page-numbers?${params}`, { signal: controller.signal }),
    ])
      .then(([info, pages]) => {
        setOriginal(info)
        setNumbers(pages)
        setPage(initialPage || (info.available ? 1 : pages[0] || 1))
        if (!info.available) setMode('text')
      })
      .catch((cause) => {
        if (!controller.signal.aborted) setError(errorText(cause))
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false)
      })
    return () => controller.abort()
  }, [params, initialPage])

  useEffect(() => {
    if (mode !== 'text' || loading) return
    const controller = new AbortController()
    setLoadingText(true)
    setText(null)
    setError('')
    void api<Page[]>(`/pages?${params}&page=${page}`, {
      signal: controller.signal,
    })
      .then((pages) => setText(pages[0] || null))
      .catch((cause) => {
        if (!controller.signal.aborted) setError(errorText(cause))
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoadingText(false)
      })
    return () => controller.abort()
  }, [params, page, mode, loading])

  const availablePages = pdfPages
    ? Array.from({ length: pdfPages }, (_, i) => i + 1)
    : numbers
  const position = availablePages.indexOf(page)
  return (
    <div className="source-reader">
      <p className="muted">
        {kinds[material.source_type]}
        {material.year ? ` · ${material.year}` : ''}
      </p>
      {loading ? (
        <div className="loading-state" role="status">
          <Loader2 className="animate-spin" size={20} /> Opening source…
        </div>
      ) : (
        <>
          {isPdf && (
            <div
              className="reader-tabs"
              role="group"
              aria-label="Source display"
            >
              <button
                className={mode === 'original' ? 'active' : ''}
                aria-pressed={mode === 'original'}
                disabled={!original?.available}
                onClick={() => setMode('original')}
              >
                Original page
              </button>
              <button
                className={mode === 'text' ? 'active' : ''}
                aria-pressed={mode === 'text'}
                onClick={() => setMode('text')}
              >
                Extracted text
              </button>
            </div>
          )}
          {isPdf && original && !original.available && (
            <p className="reader-message">
              The original PDF was not saved with this older upload. Upload the
              same PDF again to enable page preview. Its extracted text is
              available below.
            </p>
          )}
          <div className="reader-toolbar">
            <div className="reader-page-controls">
              <button
                className="icon-button"
                aria-label="Previous source page"
                disabled={position <= 0}
                onClick={() => setPage(availablePages[position - 1])}
              >
                <ChevronLeft size={18} />
              </button>
              <label>
                Page / slide / segment{' '}
                <select
                  aria-label="Source page"
                  value={page}
                  onChange={(e) => setPage(Number(e.target.value))}
                >
                  {!availablePages.includes(page) && (
                    <option value={page}>{page}</option>
                  )}
                  {availablePages.map((number) => (
                    <option key={number} value={number}>
                      {number}
                    </option>
                  ))}
                </select>
                {pdfPages > 0 && <span> of {pdfPages}</span>}
              </label>
              <button
                className="icon-button"
                aria-label="Next source page"
                disabled={position < 0 || position >= availablePages.length - 1}
                onClick={() => setPage(availablePages[position + 1])}
              >
                <ChevronRight size={18} />
              </button>
            </div>
            {mode === 'original' && original?.available && (
              <div className="reader-zoom" role="group" aria-label="PDF zoom">
                <button
                  className="icon-button"
                  aria-label="Zoom out"
                  disabled={zoom <= 0.5}
                  onClick={() => setZoom((value) => value - 0.25)}
                >
                  <Minus size={16} />
                </button>
                <button
                  className="button quiet"
                  aria-label="Fit page width"
                  onClick={() => setZoom(1)}
                >
                  {zoom === 1 ? 'Fit width' : `${Math.round(zoom * 100)}%`}
                </button>
                <button
                  className="icon-button"
                  aria-label="Zoom in"
                  disabled={zoom >= 2}
                  onClick={() => setZoom((value) => value + 0.25)}
                >
                  <Plus size={16} />
                </button>
              </div>
            )}
          </div>
          {error && (
            <p className="reader-message" role="alert">
              {error}
            </p>
          )}
          {mode === 'original' && original?.available ? (
            <Suspense
              fallback={
                <div className="loading-state" role="status">
                  Opening PDF viewer…
                </div>
              }
            >
              <PdfPage
                url={apiUrl(`/original?${params}&version=${original.version}`)}
                page={page}
                zoom={zoom}
                onPages={setPdfPages}
              />
            </Suspense>
          ) : loadingText ? (
            <div className="loading-state" role="status">
              <Loader2 className="animate-spin" size={18} /> Reading saved text…
            </div>
          ) : (
            <section aria-label={`Extracted text for page ${page}`}>
              <span className="eyebrow">PAGE / SLIDE / SEGMENT {page}</span>
              <pre>
                {text?.text ||
                  'No extracted text for this page. It may be blank or contain an image that needs OCR.'}
              </pre>
            </section>
          )}
        </>
      )}
    </div>
  )
}
