import { useEffect, useRef, type FC } from 'react'
import OpenSeadragon from 'openseadragon'
import { RetroButton } from './retro'

interface Props {
  imageUrl: string
  onViewerReady?: (viewer: OpenSeadragon.Viewer) => void
}

const Viewer: FC<Props> = ({ imageUrl, onViewerReady }) => {
  const containerRef = useRef<HTMLDivElement>(null)
  const viewerRef = useRef<OpenSeadragon.Viewer | null>(null)
  // Ref pour toujours accéder au callback le plus récent (évite stale closure)
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
    })

    viewerRef.current = viewer

    return () => {
      viewer.destroy()
      viewerRef.current = null
    }
  }, [])

  useEffect(() => {
    const viewer = viewerRef.current
    if (!viewer || !imageUrl) return

    viewer.open({ type: 'image', url: imageUrl })
    viewer.addOnceHandler('open', () => {
      onViewerReadyRef.current?.(viewer)
    })
  }, [imageUrl])

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
