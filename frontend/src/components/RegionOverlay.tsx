import { useEffect, type FC } from 'react'
import type OpenSeadragon from 'openseadragon'
import type { Region } from '../lib/api.ts'

const REGION_COLORS: Record<string, string> = {
  text_block: '#3b82f6',         // bleu
  miniature: '#f59e0b',          // or
  decorated_initial: '#10b981',  // vert
  margin: '#6b7280',             // gris
  rubric: '#ef4444',             // rouge
  other: '#8b5cf6',              // violet
}

interface Props {
  viewer: OpenSeadragon.Viewer | null
  regions: Region[]
  onRegionClick: (region: Region) => void
}

const RegionOverlay: FC<Props> = ({ viewer, regions, onRegionClick }) => {
  useEffect(() => {
    if (!viewer) return

    // AbortController pour nettoyer proprement tous les event listeners
    // lors du démontage ou du re-rendu (évite les fuites mémoire).
    const controller = new AbortController()
    const { signal } = controller

    const addOverlays = () => {
      viewer.clearOverlays()
      const item = viewer.world.getItemAt(0)
      if (!item) return

      for (const region of regions) {
        const [x, y, w, h] = region.bbox
        const color = REGION_COLORS[region.type] ?? REGION_COLORS['other']

        const el = document.createElement('div')
        el.style.border = `2px solid ${color}`
        el.style.boxSizing = 'border-box'
        el.style.cursor = 'pointer'
        el.title = `${region.type} · ${(region.confidence * 100).toFixed(0)} %`

        el.addEventListener('mouseenter', () => {
          el.style.backgroundColor = `${color}33`
        }, { signal })
        el.addEventListener('mouseleave', () => {
          el.style.backgroundColor = ''
        }, { signal })
        el.addEventListener('click', (e: MouseEvent) => {
          e.stopPropagation()
          onRegionClick(region)
        }, { signal })

        const rect = item.imageToViewportRectangle(x, y, w, h)
        viewer.addOverlay(el, rect)
      }
    }

    if (viewer.isOpen()) {
      addOverlays()
    } else {
      viewer.addOnceHandler('open', addOverlays)
    }

    return () => {
      // Supprime tous les event listeners d'un coup, puis les overlays
      controller.abort()
      try {
        viewer.clearOverlays()
      } catch {
        // viewer peut avoir été détruit lors du démontage
      }
    }
  }, [viewer, regions, onRegionClick])

  return null
}

export default RegionOverlay
