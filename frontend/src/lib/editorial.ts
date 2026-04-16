import type { EditorialStatus } from './api.ts'

export const STATUS_LABELS: Record<EditorialStatus, string> = {
  machine_draft: 'Brouillon IA',
  needs_review: 'A reviser',
  reviewed: 'Revise',
  validated: 'Valide',
  published: 'Publie',
}

export const STATUS_VARIANTS: Record<EditorialStatus, 'default' | 'success' | 'warning' | 'error' | 'info'> = {
  machine_draft: 'info',
  needs_review: 'warning',
  reviewed: 'default',
  validated: 'success',
  published: 'success',
}
