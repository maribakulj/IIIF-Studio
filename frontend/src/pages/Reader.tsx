import { useCallback, useEffect, useState } from 'react'
import { useNavigate, useParams, useSearchParams } from 'react-router-dom'
import type OpenSeadragon from 'openseadragon'
import {
  fetchPages,
  fetchMasterJson,
  fetchProfile,
  type Page,
  type PageMaster,
  type CorpusProfile,
  type Region,
} from '../lib/api.ts'
import Viewer from '../components/Viewer.tsx'
import RegionOverlay from '../components/RegionOverlay.tsx'
import LayerPanel from '../components/LayerPanel.tsx'
import TranscriptionPanel from '../components/TranscriptionPanel.tsx'
import TranslationPanel from '../components/TranslationPanel.tsx'
import CommentaryPanel from '../components/CommentaryPanel.tsx'
import { RetroMenuBar, RetroWindow, RetroButton, RetroBadge } from '../components/retro'

export default function Reader() {
  const { manuscriptId = '' } = useParams()
  const [searchParams] = useSearchParams()
  const profileId = searchParams.get('profile') ?? ''
  const navigate = useNavigate()
  const [pages, setPages] = useState<Page[]>([])
  const [currentIndex, setCurrentIndex] = useState(0)
  const [master, setMaster] = useState<PageMaster | null>(null)
  const [profile, setProfile] = useState<CorpusProfile | null>(null)
  const [visibleLayers, setVisibleLayers] = useState<Set<string>>(new Set())
  const [osdViewer, setOsdViewer] = useState<OpenSeadragon.Viewer | null>(null)
  const [selectedRegion, setSelectedRegion] = useState<Region | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const loadPages = fetchPages(manuscriptId)
    const loadProfile = profileId
      ? fetchProfile(profileId).catch(() => null)
      : Promise.resolve(null)

    Promise.all([loadPages, loadProfile])
      .then(([pgs, prof]) => {
        const sorted = [...pgs].sort((a, b) => a.sequence - b.sequence)
        setPages(sorted)
        if (prof) {
          setProfile(prof)
          setVisibleLayers(new Set(prof.active_layers))
        }
      })
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false))
  }, [manuscriptId, profileId])

  const [masterError, setMasterError] = useState<string | null>(null)

  useEffect(() => {
    if (pages.length === 0) return
    setMaster(null)
    setMasterError(null)
    setSelectedRegion(null)
    fetchMasterJson(pages[currentIndex].id)
      .then(setMaster)
      .catch((e: unknown) => {
        // 404 = page non analysée (normal), autres erreurs = problème réseau
        const msg = e instanceof Error ? e.message : ''
        if (msg.includes('404')) {
          setMaster(null)
        } else {
          setMasterError(msg || 'Erreur de chargement')
        }
      })
  }, [pages, currentIndex])

  const handleViewerReady = useCallback((v: OpenSeadragon.Viewer) => {
    setOsdViewer(v)
  }, [])

  const toggleLayer = useCallback((layer: string) => {
    setVisibleLayers((prev) => {
      const next = new Set(prev)
      if (next.has(layer)) next.delete(layer)
      else next.add(layer)
      return next
    })
  }, [])

  // ── Loading ─────────────────────────────────────────────────────────
  if (loading) {
    return (
      <div className="min-h-screen bg-retro-dither flex items-center justify-center">
        <RetroWindow title="Chargement" className="w-64">
          <div className="p-4 text-retro-sm text-center">Chargement...</div>
        </RetroWindow>
      </div>
    )
  }

  if (error) {
    return (
      <div className="min-h-screen bg-retro-dither flex items-center justify-center">
        <RetroWindow title="Erreur" className="w-80">
          <div className="p-4 text-retro-sm">{error}</div>
        </RetroWindow>
      </div>
    )
  }

  if (pages.length === 0) {
    return (
      <div className="min-h-screen bg-retro-dither flex items-center justify-center">
        <RetroWindow title="Manuscrit vide" className="w-80">
          <div className="p-4 text-retro-sm">
            Aucune page dans ce manuscrit.
            <div className="mt-2">
              <RetroButton onClick={() => navigate('/')}>Retour</RetroButton>
            </div>
          </div>
        </RetroWindow>
      </div>
    )
  }

  const currentPage = pages[currentIndex]
  const imageUrl = currentPage.image_master_path ?? ''
  const regions: Region[] = master?.layout?.regions ?? []

  return (
    <div className="flex flex-col h-screen bg-retro-dither">
      {/* ── Menu bar ───────────────────────────────────────────────── */}
      <RetroMenuBar
        items={[
          { label: 'IIIF Studio', onClick: () => navigate('/') },
          { label: profile?.label ?? profileId },
        ]}
        right={
          <div className="flex items-center gap-1">
            <span className="text-retro-xs px-2">
              {currentPage.folio_label} — {currentIndex + 1}/{pages.length}
            </span>
            <RetroButton
              size="sm"
              disabled={currentIndex === 0}
              onClick={() => setCurrentIndex((i) => i - 1)}
            >
              Prev
            </RetroButton>
            <RetroButton
              size="sm"
              disabled={currentIndex === pages.length - 1}
              onClick={() => setCurrentIndex((i) => i + 1)}
            >
              Next
            </RetroButton>
            <RetroButton size="sm" onClick={() => navigate(`/editor/${currentPage.id}`)}>
              Editer
            </RetroButton>
          </div>
        }
      />

      {/* ── Main content ───────────────────────────────────────────── */}
      <div className="flex flex-1 min-h-0 overflow-hidden p-1 gap-1">

        {/* ── Viewer window (left, 70%) ──────────────────────────── */}
        <RetroWindow
          title={`Folio ${currentPage.folio_label}`}
          statusBar={
            master
              ? `${master.editorial.status} — v${master.editorial.version}`
              : imageUrl ? 'Page non analysee' : 'Aucune image'
          }
          className="flex-[7] min-w-0"
        >
          <div className="relative w-full h-full">
            <Viewer imageUrl={imageUrl} onViewerReady={handleViewerReady} />
            <RegionOverlay
              viewer={osdViewer}
              regions={regions}
              onRegionClick={setSelectedRegion}
            />

            {/* Region info popup */}
            {selectedRegion && (
              <div
                className="
                  absolute bottom-12 left-2
                  border-retro border-retro-black
                  bg-retro-white shadow-retro
                  text-retro-xs p-2 max-w-[220px]
                "
              >
                <div className="flex items-center justify-between gap-2 mb-1">
                  <span className="font-bold capitalize">
                    {selectedRegion.type.replace(/_/g, ' ')}
                  </span>
                  <button
                    type="button"
                    onClick={() => setSelectedRegion(null)}
                    className="text-retro-black font-bold hover:bg-retro-black hover:text-retro-white px-1"
                  >
                    x
                  </button>
                </div>
                <div className="space-y-[1px] text-retro-darkgray">
                  <div>id: {selectedRegion.id}</div>
                  <div>confiance: {(selectedRegion.confidence * 100).toFixed(0)}%</div>
                  <div>bbox: [{selectedRegion.bbox.join(', ')}]</div>
                </div>
              </div>
            )}

            {/* Not analyzed / error badge */}
            {!master && !loading && imageUrl && (
              <div className="absolute top-2 left-2">
                {masterError
                  ? <RetroBadge variant="error">Erreur: {masterError}</RetroBadge>
                  : <RetroBadge variant="warning">Non analysee</RetroBadge>
                }
              </div>
            )}
          </div>
        </RetroWindow>

        {/* ── Right panels (30%) ─────────────────────────────────── */}
        <RetroWindow
          title="Analyse"
          className="flex-[3] min-w-0"
          scrollable
        >
          <div className="flex flex-col">
            {/* Layer toggles */}
            {profile && (
              <LayerPanel
                activeLayers={profile.active_layers}
                visibleLayers={visibleLayers}
                onToggle={toggleLayer}
              />
            )}

            {/* Content panels */}
            {master ? (
              <div className="divide-y divide-retro-gray">
                <TranscriptionPanel
                  ocr={master.ocr}
                  editorial={master.editorial}
                  visible={visibleLayers.has('ocr_diplomatic')}
                />
                <TranslationPanel
                  translation={master.translation}
                  editorial={master.editorial}
                  visible={visibleLayers.has('translation_fr') || visibleLayers.has('translation_en')}
                  activeLayers={profile?.active_layers}
                />
                <CommentaryPanel
                  commentary={master.commentary}
                  editorial={master.editorial}
                  visiblePublic={visibleLayers.has('public_commentary')}
                  visibleScholarly={visibleLayers.has('scholarly_commentary')}
                />
              </div>
            ) : (
              <div className="p-3 text-retro-sm text-retro-darkgray">
                {imageUrl
                  ? 'Page non encore analysee par l\'IA.'
                  : 'Aucune image associee a cette page.'
                }
              </div>
            )}
          </div>
        </RetroWindow>
      </div>
    </div>
  )
}
