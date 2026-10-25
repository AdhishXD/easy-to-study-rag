# Performance audit

Audit date: 14 October 2026. Source sizes came from this workspace's existing extracted pages. HTTP measurements used FastAPI's in-process test client, ten repetitions per endpoint; they exclude network and real inference time.

## Main findings and fixes

| Cause | Impact | Change |
| --- | --- | --- |
| Small teaching batches and one request per paper page | Many sequential model calls before results | Larger bounded batches, with stable boundaries per file |
| Every analysis repeated unchanged stages | Long waits after minor uploads or refresh | Content-addressed response cache and completed-analysis fingerprint |
| One embedding HTTP request per chunk | Request overhead and repeated inference | Batches of 32, duplicate text reuse, bulk cache reads/writes |
| Identical uploads repeated parsing and transcription | Video re-uploads were particularly expensive | File and processing-setting fingerprints |
| Synchronous Streamlit rendering and reruns | Navigation blocked and stale content duplicated | React state and FastAPI background jobs |
| Concurrent local jobs could contend for model memory | Unpredictable latency and wasted duplicate requests | One bounded worker and duplicate-job checks |
| Model loading/output growth | Cold-start waits and long generation | Configurable keep-alive, bounded context/output, optional free Groq |
| Large topic and page DOM trees | Hundreds of rows and complete textbooks rendered | Twenty topics initially; source reader loads one page at a time |
| Unused pandas import through a compatibility facade | Extra startup work and dependencies | Removed the facade, old checkpoint scripts, and unused direct dependencies |
| Local Whisper decoding | CPU transcription can dominate an upload | Cached model, VAD, configurable beam size (default 1 instead of 5) |
| Stale chunks after replacing a shorter file | Retrieval returned outdated passages | Remove obsolete chunk IDs after successful replacement |

## Measured extraction work

| Course | Source pages | Old extraction requests | New extraction requests |
| --- | --- | --- | --- |
| Databases | 329 teaching + 16 paper pages | 77 teaching + 16 paper = **93** | 43 teaching + 5 paper = **48** |
| Neural Network and Deep Learning | 114 teaching pages | **10** | **6** |

The Databases extraction count falls by about **48%**. These are request counts, not a promised 48% reduction in total elapsed time. Topic merging, question assignment, and repeat checking add further work. The new repeat step packs compatible topic sets into bounded requests instead of issuing a request for every small topic group. Existing synthetic unit checks show identical analysis and identical embedding inputs do not invoke the model again.

Read endpoint medians in the final audit were approximately 3 ms for health, 5 ms for subjects, and 18 ms for the existing Databases analysis. These should be remeasured on deployed hardware. The original logs include local requests ranging from below a second to more than 30 seconds, depending on prompt size, output, and model state.

## Correctness issues found during the audit

- Databases contains question papers from other courses. The library now allows the user to remove misclassified sources; no existing study files were automatically deleted.
- A fallback exam year could override a year in a filename. Filename years now take priority. Existing stored years can be corrected without uploading again.
- An oversized merge prompt could truncate a model response. Merge prompts are bounded and ask only for duplicate groups, preserving distinct concepts.
- Background work stages vectors before committing a file, checks cancellation between inference steps, and refuses to save analysis if the course changed during processing.

## Remaining limits

- First-time analysis still reads the full corpus and takes model time. Caching helps repeated work; it does not remove the first pass.
- Free Groq token quotas can require waiting. A hosted model does not make a large course instantaneous.
- Hardware determines local token speed. Smaller models may lose accuracy; compare complete questions, topic mapping, and answers on real course pages before switching defaults.
- OCR, diagram interpretation, and handwritten notes are not implemented. Poor text extraction is reported instead of repaired with fabricated questions.
- Overlapping repeat windows can still miss a paraphrased repeat far apart in very large topic groups. Candidate groups require source review.
- The queue supports one backend process. Multiple workers or shared public uploads need a separate job system, storage, authentication, and tenant isolation.
- SQLite and Chroma are separate stores. A process crash during the final file commit can still require re-indexing that source; the next upload reconciles its passages.

## Follow-up verification, 15 October 2026

Uploads now use FastEmbed's small BGE model on the CPU, independently of Ollama. Its first download is about 67 MB. Provider-specific collections keep the new 384-dimensional vectors separate from the old index. Existing extracted pages rebuild the new search index on demand.

A real end-to-end test used synthetic DBMS slides, two dated papers, the cached CPU embedding model, and Groq `openai/gpt-oss-20b`. PPTX upload took 1.06 seconds, teaching-only topic analysis 2.28 seconds (two model calls), two MCQs 1.25 seconds, and one 3-mark question 1.89 seconds. Adding two tiny paper files took 0.22 seconds; analysis with those papers took 2.06 seconds (four model calls and two cache hits). Normalization was correctly grouped across 2023 and 2024. Correct MCQ grading, written self-assessment, and restoring submitted answers passed. These tiny-corpus timings do not predict full textbook performance.

Groq requests now include an application User-Agent; the previous default urllib request received HTTP 403 even with a configured key. The frontend lockfile was regenerated from a clean directory because `npm ci` on Linux rejected missing optional WASM dependencies. Actions now use Node 24-compatible releases.

Use `scripts/audit_performance.py` for work sizes and **Settings & activity** for timings on your actual course.
