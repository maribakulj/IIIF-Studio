import type { FC } from 'react'
import type { Translation, EditorialInfo, EditorialStatus } from '../lib/api.ts'
import { RetroBadge } from './retro'

const STATUS_LABELS: Record<EditorialStatus, string> = {
  machine_draft: 'Brouillon IA',
  needs_review: 'A reviser',
  reviewed: 'Revise',
  validated: 'Valide',
  published: 'Publie',
}

const STATUS_VARIANTS: Record<EditorialStatus, 'default' | 'success' | 'warning' | 'error' | 'info'> = {
  machine_draft: 'info',
  needs_review: 'warning',
  reviewed: 'default',
  validated: 'success',
  published: 'success',
}

interface Props {
  translation: Translation | null
  editorial: EditorialInfo
  visible: boolean
}

const TranslationPanel: FC<Props> = ({ translation, editorial, visible }) => {
  if (!visible) return null

  return (
    <div className="p-2">
      <div className="flex items-center justify-between mb-2">
        <span className="text-retro-xs font-bold">Traduction (FR)</span>
        <RetroBadge variant={STATUS_VARIANTS[editorial.status]}>
          {STATUS_LABELS[editorial.status]}
        </RetroBadge>
      </div>
      {translation?.fr ? (
        <p className="text-retro-sm whitespace-pre-wrap font-retro leading-relaxed">
          {translation.fr}
        </p>
      ) : (
        <p className="text-retro-sm text-retro-darkgray">Traduction non disponible.</p>
      )}
    </div>
  )
}

export default TranslationPanel
