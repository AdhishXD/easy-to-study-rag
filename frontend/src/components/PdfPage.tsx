import { useEffect, useRef, useState } from 'react'
import { Loader2 } from 'lucide-react'
import {
  getDocument,
  GlobalWorkerOptions,
  type PDFDocumentProxy,
  type RenderTask,
} from 'pdfjs-dist'
import workerUrl from 'pdfjs-dist/build/pdf.worker.min.mjs?url'
import { authHeaders } from '../api'

GlobalWorkerOptions.workerSrc = workerUrl

export default function PdfPage({
  url,
  page,
  zoom,
  onPages,
}: {
  url: string
  page: number
  zoom: number
  onPages: (count: number) => void
}) {
  const container = useRef<HTMLDivElement>(null)
  const canvasHost = useRef<HTMLDivElement>(null)
  const [document, setDocument] = useState<PDFDocumentProxy | null>(null)
  const [width, setWidth] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    const observer = new ResizeObserver(([entry]) =>
      setWidth(Math.floor(entry.contentRect.width)),
    )
    observer.observe(container.current!)
    return () => observer.disconnect()
  }, [])

  useEffect(() => {
    let stopped = false
    setError('')
    setDocument(null)
    setLoading(true)
    const assets = new URL(
      `${import.meta.env.BASE_URL}pdfjs/`,
      window.location.origin,
    ).href
    const task = getDocument({
      url,
      httpHeaders: authHeaders(),
      disableAutoFetch: true,
      disableStream: true,
      cMapUrl: assets + 'cmaps/',
      cMapPacked: true,
      standardFontDataUrl: assets + 'standard_fonts/',
      wasmUrl: assets + 'wasm/',
      iccUrl: assets + 'iccs/',
    })
    void task.promise
      .then((pdf) => {
        if (stopped) return
        setDocument(pdf)
        onPages(pdf.numPages)
      })
      .catch(() => {
        if (!stopped) {
          setError(
            'The PDF could not be opened. Try the extracted text or upload the original PDF again.',
          )
          setLoading(false)
        }
      })
    return () => {
      stopped = true
      void task.destroy().catch(() => {})
    }
  }, [url, onPages])

  useEffect(() => {
    if (!document || !width) return
    let stopped = false
    let render: RenderTask | undefined
    setError('')
    setLoading(true)
    // Each render owns its canvas. Cancelled renders cannot paint a new page.
    const canvas = window.document.createElement('canvas')
    canvas.setAttribute('role', 'img')
    canvas.setAttribute('aria-label', `Original PDF page ${page}`)
    canvasHost.current!.replaceChildren(canvas)
    void document
      .getPage(page)
      .then(async (pdfPage) => {
        if (stopped) {
          pdfPage.cleanup()
          return
        }
        const natural = pdfPage.getViewport({ scale: 1 })
        const viewport = pdfPage.getViewport({
          scale: (Math.max(1, width - 24) / natural.width) * zoom,
        })
        const ratio = Math.min(
          window.devicePixelRatio || 1,
          2,
          Math.sqrt(16_000_000 / (viewport.width * viewport.height)),
        )
        canvas.width = Math.ceil(viewport.width * ratio)
        canvas.height = Math.ceil(viewport.height * ratio)
        canvas.style.width = `${viewport.width}px`
        canvas.style.height = `${viewport.height}px`
        render = pdfPage.render({
          canvas,
          viewport,
          transform: ratio === 1 ? undefined : [ratio, 0, 0, ratio, 0, 0],
        })
        try {
          await render.promise
          if (!stopped) setLoading(false)
        } finally {
          pdfPage.cleanup()
        }
      })
      .catch(() => {
        if (!stopped) {
          setError(
            'This page could not be rendered. The extracted text is still available.',
          )
          setLoading(false)
        }
      })
    return () => {
      stopped = true
      render?.cancel()
      canvas.remove()
      canvas.width = 0
      canvas.height = 0
    }
  }, [document, width, page, zoom])

  return (
    <div className="pdf-viewport" ref={container}>
      {loading && (
        <div className="pdf-status" role="status">
          <Loader2 className="animate-spin" size={18} /> Loading page {page}…
        </div>
      )}
      {error && (
        <p className="reader-message" role="alert">
          {error}
        </p>
      )}
      <div className="pdf-canvas-host" ref={canvasHost} hidden={!!error} />
    </div>
  )
}
