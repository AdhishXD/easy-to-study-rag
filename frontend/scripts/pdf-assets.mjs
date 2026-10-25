import { cpSync, mkdirSync } from 'node:fs'
import { fileURLToPath } from 'node:url'

// Serve fonts and decoders locally; no third-party viewer or CDN requests.
const root = new URL('../', import.meta.url)
for (const directory of ['cmaps', 'standard_fonts', 'wasm', 'iccs']) {
  const target = new URL(`public/pdfjs/${directory}`, root)
  mkdirSync(fileURLToPath(target), { recursive: true })
  cpSync(new URL(`node_modules/pdfjs-dist/${directory}`, root), target, { recursive: true })
}
