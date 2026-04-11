import type { FC } from 'react'
import { RetroCheckbox } from './retro'

const LAYER_LABELS: Record<string, string> = {
  image: 'Image',
  ocr_diplomatic: 'Transcription',
  ocr_normalized: 'Normalise',
  translation_fr: 'Traduction FR',
  translation_en: 'Traduction EN',
  summary: 'Resume',
  scholarly_commentary: 'Comm. savant',
  public_commentary: 'Comm. public',
  iconography_detection: 'Iconographie',
  material_notes: 'Notes mat.',
  uncertainty: 'Incertitudes',
}

interface Props {
  activeLayers: string[]
  visibleLayers: Set<string>
  onToggle: (layer: string) => void
}

const LayerPanel: FC<Props> = ({ activeLayers, visibleLayers, onToggle }) => (
  <div className="px-2 py-2 shrink-0 border-b border-retro-black bg-retro-gray">
    <div className="text-retro-xs font-bold mb-1">Couches</div>
    <div className="flex flex-wrap gap-x-3 gap-y-1">
      {activeLayers.map((layer) => (
        <RetroCheckbox
          key={layer}
          label={LAYER_LABELS[layer] ?? layer}
          checked={visibleLayers.has(layer)}
          onChange={() => onToggle(layer)}
        />
      ))}
    </div>
  </div>
)

export default LayerPanel
