import { useEffect, useMemo, useRef, type FC } from 'react'
import OpenSeadragon from 'openseadragon'
import { RetroButton } from './retro'

interface Props {
  /** URL du IIIF Image Service (zoom tuilé natif) */
  iiifServiceUrl?: string | null
  /** URL image statique (fallback si pas de service IIIF) */
  fallbackImageUrl?: string | null
  onViewerReady?: (viewer: OpenSeadragon.Viewer) => void
}

const Viewer: FC<Props> = ({ iiifServiceUrl, fallbackImageUrl, onViewerReady }) => {
  const containerRef = useRef<HTMLDivElement>(null)
  const viewerRef = useRef<OpenSeadragon.Viewer | null>(null)
  const onViewerReadyRef = useRef(onViewerReady)
  onViewerReadyRef.current = onViewerReady

  useEffect(() => {
    if (!containerRef.current) return

    const viewer = OpenSeadragon({
      element: containerRef.current,
      showNavigationControl: false,
      gestureSettingsMouse: { clickToZoom: false, scrollToZoom: true, dragToPan: true },
      gestureSettingsTouch: { scrollToZoom: true, dragToPan: true, pinchToZoom: true },
      animationTime: 0.3,
      minZoomLevel: 0.1,
      maxZoomLevel: 20,
      crossOriginPolicy: 'Anonymous',
    })

    viewerRef.current = viewer

    return () => {
      viewer.destroy()
      viewerRef.current = null
    }
  }, [])

  // Source à ouvrir : préférer le service IIIF (zoom tuilé), sinon image statique
  const source = useMemo(
    () => iiifServiceUrl || fallbackImageUrl || '',
    [iiifServiceUrl, fallbackImageUrl]
  )

  useEffect(() => {
    const viewer = viewerRef.current
    if (!viewer || !source) return

    // Remove previous handlers to avoid accumulation on rapid page changes
    viewer.removeAllHandlers('open')
    viewer.removeAllHandlers('open-failed')

    if (iiifServiceUrl) {
      // Zoom tuilé natif — OpenSeadragon fetch info.json et configure les tuiles
      viewer.open(iiifServiceUrl + '/info.json')
    } else {
      // Image statique simple (pas de zoom tuilé)
      viewer.open({ type: 'image', url: source })
    }

    viewer.addOnceHandler('open', () => {
      onViewerReadyRef.current?.(viewer)
    })

    viewer.addOnceHandler('open-failed', () => {
      console.warn('[Viewer] Failed to open image source:', source)
    })
  }, [source, iiifServiceUrl])

  return (
    <div className="relative w-full h-full bg-retro-black">
      <div ref={containerRef} className="w-full h-full" />
      <div className="absolute bottom-2 right-2 flex gap-[2px]">
        <RetroButton
          size="sm"
          onClick={() => viewerRef.current?.viewport.zoomBy(1.5)}
          title="Zoom +"
        >
          +
        </RetroButton>
        <RetroButton
          size="sm"
          onClick={() => viewerRef.current?.viewport.zoomBy(0.67)}
          title="Zoom -"
        >
          -
        </RetroButton>
        <RetroButton
          size="sm"
          onClick={() => viewerRef.current?.viewport.goHome()}
          title="Reset"
        >
          o
        </RetroButton>
        <RetroButton
          size="sm"
          onClick={() => viewerRef.current?.setFullScreen(true)}
          title="Plein ecran"
        >
          []
        </RetroButton>
      </div>
    </div>
  )
}

export default Viewer
