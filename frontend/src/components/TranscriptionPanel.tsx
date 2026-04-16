import type { FC } from 'react'
import type { OCRResult, EditorialInfo } from '../lib/api.ts'
import { STATUS_LABELS, STATUS_VARIANTS } from '../lib/editorial.ts'
import { RetroBadge } from './retro'

interface Props {
  ocr: OCRResult | null
  editorial: EditorialInfo
  visible: boolean
}

const TranscriptionPanel: FC<Props> = ({ ocr, editorial, visible }) => {
  if (!visible) return null

  return (
    <div className="p-2">
      <div className="flex items-center justify-between mb-2">
        <span className="text-retro-xs font-bold">Transcription diplomatique</span>
        <RetroBadge variant={STATUS_VARIANTS[editorial.status]}>
          {STATUS_LABELS[editorial.status]}
        </RetroBadge>
      </div>
      {ocr ? (
        <div>
          {ocr.diplomatic_text ? (
            <p className="text-retro-sm whitespace-pre-wrap font-retro leading-relaxed">
              {ocr.diplomatic_text}
            </p>
          ) : (
            <p className="text-retro-sm text-retro-darkgray">Texte vide.</p>
          )}
          {ocr.confidence > 0 && (
            <div className="mt-2 text-retro-xs text-retro-darkgray">
              Confiance : {(ocr.confidence * 100).toFixed(0)}% — Langue : {ocr.language}
            </div>
          )}
        </div>
      ) : (
        <p className="text-retro-sm text-retro-darkgray">Transcription non disponible.</p>
      )}
    </div>
  )
}

export default TranscriptionPanel
