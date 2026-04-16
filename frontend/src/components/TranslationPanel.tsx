import type { FC } from 'react'
import type { Translation, EditorialInfo } from '../lib/api.ts'
import { STATUS_LABELS, STATUS_VARIANTS } from '../lib/editorial.ts'
import { RetroBadge } from './retro'

interface Props {
  translation: Translation | null
  editorial: EditorialInfo
  visible: boolean
  /** Active layers from profile — controls which languages are shown */
  activeLayers?: string[]
}

const TranslationPanel: FC<Props> = ({ translation, editorial, visible, activeLayers }) => {
  if (!visible) return null

  const showFr = !activeLayers || activeLayers.includes('translation_fr')
  const showEn = !activeLayers || activeLayers.includes('translation_en')

  return (
    <div className="p-2">
      <div className="flex items-center justify-between mb-2">
        <span className="text-retro-xs font-bold">Traduction</span>
        <RetroBadge variant={STATUS_VARIANTS[editorial.status]}>
          {STATUS_LABELS[editorial.status]}
        </RetroBadge>
      </div>
      {showFr && (
        <div className="mb-2">
          <div className="text-retro-xs font-bold text-retro-darkgray mb-1">FR</div>
          {translation?.fr ? (
            <p className="text-retro-sm whitespace-pre-wrap font-retro leading-relaxed">
              {translation.fr}
            </p>
          ) : (
            <p className="text-retro-sm text-retro-darkgray">Traduction FR non disponible.</p>
          )}
        </div>
      )}
      {showEn && (
        <div>
          <div className="text-retro-xs font-bold text-retro-darkgray mb-1">EN</div>
          {translation?.en ? (
            <p className="text-retro-sm whitespace-pre-wrap font-retro leading-relaxed">
              {translation.en}
            </p>
          ) : (
            <p className="text-retro-sm text-retro-darkgray">Traduction EN non disponible.</p>
          )}
        </div>
      )}
      {!showFr && !showEn && (
        <p className="text-retro-sm text-retro-darkgray">Aucune couche de traduction active.</p>
      )}
    </div>
  )
}

export default TranslationPanel
