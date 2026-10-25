import type { Job } from './api'

export const kinds: Record<string, string> = {
  lecture_note: 'Lecture notes',
  lecture_slide: 'Lecture slides',
  textbook: 'Textbook',
  lecture_video: 'Lecture recording',
  past_qp: 'Past paper',
}
export const active = (job: Job) => ['queued', 'running'].includes(job.status)
export const errorText = (error: unknown) =>
  error instanceof Error
    ? error.message
    : 'Something went wrong. Please try again.'
export const stamp = (value: string) =>
  new Date(value).toLocaleDateString(undefined, {
    month: 'short',
    day: 'numeric',
  })
