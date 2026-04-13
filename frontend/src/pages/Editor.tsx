import { useCallback, useEffect, useRef, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import {
  applyCorrections,
  getHistory,
  fetchMasterJson,
  type PageMaster,
  type VersionInfo,
} from '../lib/api.ts'
import Viewer from '../components/Viewer.tsx'
import {
  RetroMenuBar,
  RetroWindow,
  RetroButton,
  RetroTextarea,
  RetroSelect,
  RetroBadge,
} from '../components/retro'

type Panel = 'transcription' | 'commentary' | 'regions' | 'history'

const PANEL_LABELS: Record<Panel, string> = {
  transcription: 'Transcription',
  commentary: 'Commentaire',
  regions: 'Regions',
  history: 'Historique',
}

export default function Editor() {
  const { pageId = '' } = useParams()
  const navigate = useNavigate()
  const [master, setMaster] = useState<PageMaster | null>(null)
  const [history, setHistory] = useState<VersionInfo[]>([])
  const [activePanel, setActivePanel] = useState<Panel>('transcription')
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [saveError, setSaveError] = useState<string | null>(null)
  const [saveSuccess, setSaveSuccess] = useState(false)

  const [ocrText, setOcrText] = useState('')
  const [commentaryPublic, setCommentaryPublic] = useState('')
  const [commentaryScholarly, setCommentaryScholarly] = useState('')
  const [editorialStatus, setEditorialStatus] = useState('')
  const [regionValidations, setRegionValidations] = useState<Record<string, string>>({})

  const successTimeout = useRef<ReturnType<typeof setTimeout> | null>(null)

  // Nettoyage du timeout de succès lors du démontage du composant
  useEffect(() => {
    return () => {
      if (successTimeout.current) clearTimeout(successTimeout.current)
    }
  }, [])

  const loadData = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const [m, h] = await Promise.all([fetchMasterJson(pageId), getHistory(pageId)])
      setMaster(m)
      setHistory(h)
      setOcrText(m.ocr?.diplomatic_text ?? '')
      setCommentaryPublic(m.commentary?.public ?? '')
      setCommentaryScholarly(m.commentary?.scholarly ?? '')
      setEditorialStatus(m.editorial.status)
      const ext = m.extensions as { region_validations?: Record<string, string> } | undefined
      setRegionValidations(ext?.region_validations ?? {})
    } catch (e: unknown) {
      const msg = (e as Error).message ?? ''
      if (msg.includes('404')) {
        setError('Cette page n\'a pas encore ete analysee par l\'IA. Lancez le pipeline depuis Administration.')
      } else {
        setError(msg)
      }
    } finally {
      setLoading(false)
    }
  }, [pageId])

  useEffect(() => {
    void loadData()
  }, [loadData])

  const handleSave = async () => {
    setSaving(true)
    setSaveError(null)
    setSaveSuccess(false)
    try {
      const updated = await applyCorrections(pageId, {
        ocr_diplomatic_text: ocrText !== (master?.ocr?.diplomatic_text ?? '') ? ocrText : undefined,
        editorial_status: editorialStatus !== master?.editorial.status ? editorialStatus : undefined,
        commentary_public: commentaryPublic !== (master?.commentary?.public ?? '') ? commentaryPublic : undefined,
        commentary_scholarly: commentaryScholarly !== (master?.commentary?.scholarly ?? '') ? commentaryScholarly : undefined,
        region_validations: Object.keys(regionValidations).length > 0 ? regionValidations : undefined,
      })
      setMaster(updated)
      const h = await getHistory(pageId)
      setHistory(h)
      setSaveSuccess(true)
      if (successTimeout.current) clearTimeout(successTimeout.current)
      successTimeout.current = setTimeout(() => setSaveSuccess(false), 3000)
    } catch (e: unknown) {
      setSaveError((e as Error).message)
    } finally {
      setSaving(false)
    }
  }

  const handleRestore = async (version: number) => {
    setSaving(true)
    setSaveError(null)
    try {
      const updated = await applyCorrections(pageId, { restore_to_version: version })
      setMaster(updated)
      setOcrText(updated.ocr?.diplomatic_text ?? '')
      setCommentaryPublic(updated.commentary?.public ?? '')
      setCommentaryScholarly(updated.commentary?.scholarly ?? '')
      setEditorialStatus(updated.editorial.status)
      const h = await getHistory(pageId)
      setHistory(h)
    } catch (e: unknown) {
      setSaveError((e as Error).message)
    } finally {
      setSaving(false)
    }
  }

  const setRegionValidation = (regionId: string, val: string) => {
    setRegionValidations((prev) => ({ ...prev, [regionId]: val }))
  }

  // ── Loading / Error ─────────────────────────────────────────────────
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
          <div className="p-4 text-retro-sm">
            {error}
            <div className="mt-2"><RetroButton onClick={() => navigate(-1)}>Retour</RetroButton></div>
          </div>
        </RetroWindow>
      </div>
    )
  }

  const imageUrl = master?.image?.derivative_web ?? master?.image?.master ?? ''
  const regions = master?.layout?.regions ?? []

  return (
    <div className="flex flex-col h-screen bg-retro-dither">
      {/* ── Menu bar ───────────────────────────────────────────────── */}
      <RetroMenuBar
        items={[
          { label: 'IIIF Studio', onClick: () => navigate('/') },
          { label: `Editeur — ${master?.folio_label ?? pageId}` },
        ]}
        right={
          <div className="flex items-center gap-1">
            {master && (
              <span className="text-retro-xs px-2">
                v{master.editorial.version} — {master.editorial.status}
              </span>
            )}
            {saveSuccess && <RetroBadge variant="success">OK</RetroBadge>}
            {saveError && <RetroBadge variant="error">Err</RetroBadge>}
            <RetroButton
              size="sm"
              onClick={() => void handleSave()}
              disabled={saving}
            >
              {saving ? 'Saving...' : 'Sauvegarder'}
            </RetroButton>
          </div>
        }
      />

      {/* ── Main layout 50/50 ──────────────────────────────────────── */}
      <div className="flex flex-1 min-h-0 overflow-hidden p-1 gap-1">

        {/* ── Viewer window (left) ───────────────────────────────── */}
        <RetroWindow
          title={`Image — ${master?.folio_label ?? pageId}`}
          className="flex-1 min-w-0"
        >
          <div className="relative w-full h-full">
            <Viewer imageUrl={imageUrl} onViewerReady={() => {}} />
            {!imageUrl && (
              <div className="absolute inset-0 flex items-center justify-center bg-retro-gray text-retro-darkgray text-retro-sm">
                Apercu non disponible
              </div>
            )}
          </div>
        </RetroWindow>

        {/* ── Editor window (right) ──────────────────────────────── */}
        <RetroWindow
          title="Editeur"
          className="flex-1 min-w-0"
          scrollable
        >
          <div className="flex flex-col">
            {/* ── Tab bar ──────────────────────────────────────── */}
            <div className="flex shrink-0 border-b border-retro-black bg-retro-gray">
              {(['transcription', 'commentary', 'regions', 'history'] as Panel[]).map((p) => (
                <RetroButton
                  key={p}
                  size="sm"
                  pressed={activePanel === p}
                  onClick={() => setActivePanel(p)}
                  className="flex-1 border-0 border-r border-retro-darkgray last:border-r-0"
                >
                  {PANEL_LABELS[p]}
                </RetroButton>
              ))}
            </div>

            {/* ── Panel content ─────────────────────────────────── */}
            <div className="p-2">

              {/* Transcription */}
              {activePanel === 'transcription' && (
                <div className="flex flex-col gap-2">
                  <RetroTextarea
                    label="Texte diplomatique (OCR)"
                    value={ocrText}
                    onChange={(e) => setOcrText(e.target.value)}
                    rows={12}
                  />
                  <RetroSelect
                    label="Statut editorial"
                    value={editorialStatus}
                    onChange={(e) => setEditorialStatus(e.target.value)}
                    options={[
                      { value: 'machine_draft', label: 'machine_draft' },
                      { value: 'needs_review', label: 'needs_review' },
                      { value: 'reviewed', label: 'reviewed' },
                      { value: 'validated', label: 'validated' },
                      { value: 'published', label: 'published' },
                    ]}
                  />
                  {master?.ocr && (
                    <div className="text-retro-xs text-retro-darkgray">
                      Langue: {master.ocr.language} — Confiance: {(master.ocr.confidence * 100).toFixed(0)}%
                    </div>
                  )}
                </div>
              )}

              {/* Commentary */}
              {activePanel === 'commentary' && (
                <div className="flex flex-col gap-2">
                  <RetroTextarea
                    label="Commentaire public"
                    value={commentaryPublic}
                    onChange={(e) => setCommentaryPublic(e.target.value)}
                    rows={6}
                  />
                  <RetroTextarea
                    label="Commentaire savant"
                    value={commentaryScholarly}
                    onChange={(e) => setCommentaryScholarly(e.target.value)}
                    rows={8}
                  />
                </div>
              )}

              {/* Regions */}
              {activePanel === 'regions' && (
                <div className="flex flex-col gap-[2px]">
                  {regions.length === 0 ? (
                    <p className="text-retro-sm text-retro-darkgray p-2">Aucune region detectee.</p>
                  ) : (
                    regions.map((region) => {
                      const validation = regionValidations[region.id]
                      return (
                        <div
                          key={region.id}
                          className="
                            flex items-center justify-between
                            border border-retro-black p-2
                            bg-retro-white
                          "
                        >
                          <div>
                            <span className="text-retro-sm font-bold capitalize">
                              {region.type.replace(/_/g, ' ')}
                            </span>
                            <span className="ml-2 text-retro-xs text-retro-darkgray">
                              {region.id}
                            </span>
                            <div className="text-retro-xs text-retro-darkgray">
                              confiance: {(region.confidence * 100).toFixed(0)}%
                            </div>
                          </div>
                          <div className="flex gap-[2px] ml-2 shrink-0">
                            <RetroButton
                              size="sm"
                              pressed={validation === 'validated'}
                              onClick={() => setRegionValidation(region.id, 'validated')}
                            >
                              OK
                            </RetroButton>
                            <RetroButton
                              size="sm"
                              pressed={validation === 'rejected'}
                              onClick={() => setRegionValidation(region.id, 'rejected')}
                            >
                              X
                            </RetroButton>
                          </div>
                        </div>
                      )
                    })
                  )}
                </div>
              )}

              {/* History */}
              {activePanel === 'history' && (
                <div className="flex flex-col gap-[2px]">
                  {history.length === 0 ? (
                    <p className="text-retro-sm text-retro-darkgray p-2">Aucune version archivee.</p>
                  ) : (
                    history.map((v) => (
                      <div
                        key={v.version}
                        className="
                          flex items-center justify-between
                          border border-retro-black p-2
                          bg-retro-white
                        "
                      >
                        <div>
                          <span className="text-retro-sm font-bold">v{v.version}</span>
                          <RetroBadge className="ml-2">{v.status}</RetroBadge>
                          <div className="text-retro-xs text-retro-darkgray mt-[2px]">
                            {new Date(v.saved_at).toLocaleString('fr-FR')}
                          </div>
                        </div>
                        <RetroButton
                          size="sm"
                          onClick={() => void handleRestore(v.version)}
                          disabled={saving}
                        >
                          Restaurer
                        </RetroButton>
                      </div>
                    ))
                  )}
                </div>
              )}
            </div>
          </div>
        </RetroWindow>
      </div>
    </div>
  )
}
