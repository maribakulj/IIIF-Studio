import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import SearchBar from '../components/SearchBar.tsx'
import { RetroMenuBar, RetroWindow, RetroIcon } from '../components/retro'
import {
  fetchCorpora,
  fetchManuscripts,
  type Corpus,
  type Manuscript,
} from '../lib/api.ts'

/** Map profile IDs to desktop icon glyphs */
const PROFILE_GLYPHS: Record<string, string> = {
  'medieval-illuminated': '\u{1F4DC}',
  'medieval-textual':     '\u{1F4D6}',
  'early-modern-print':   '\u{1F5A8}',
  'modern-handwritten':   '\u{270D}',
}

export default function Home() {
  const navigate = useNavigate()
  const [corpora, setCorpora] = useState<Corpus[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [manuscripts, setManuscripts] = useState<Record<string, Manuscript[]>>({})
  const [expanding, setExpanding] = useState<string | null>(null)
  const [selectedCorpus, setSelectedCorpus] = useState<Corpus | null>(null)
  const [expandError, setExpandError] = useState<string | null>(null)

  useEffect(() => {
    fetchCorpora()
      .then(setCorpora)
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false))
  }, [])

  const handleCorpusClick = async (corpus: Corpus) => {
    setSelectedCorpus(corpus)

    const cached = manuscripts[corpus.id]
    if (cached) {
      if (cached.length === 1) navigate(`/reader/${cached[0].id}?profile=${corpus.profile_id}`)
      return
    }

    setExpanding(corpus.id)
    setExpandError(null)
    try {
      const ms = await fetchManuscripts(corpus.id)
      setManuscripts((prev) => ({ ...prev, [corpus.id]: ms }))
      if (ms.length === 1) navigate(`/reader/${ms[0].id}?profile=${corpus.profile_id}`)
    } catch (e: unknown) {
      setExpandError(e instanceof Error ? e.message : 'Erreur de chargement')
    } finally {
      setExpanding(null)
    }
  }

  // ── Loading state ───────────────────────────────────────────────────
  if (loading) {
    return (
      <div className="min-h-screen bg-retro-dither flex items-center justify-center">
        <RetroWindow title="IIIF Studio" className="w-72">
          <div className="p-4 text-retro-sm text-center">
            Chargement...
          </div>
        </RetroWindow>
      </div>
    )
  }

  // ── Error state ─────────────────────────────────────────────────────
  if (error) {
    return (
      <div className="min-h-screen bg-retro-dither flex items-center justify-center">
        <RetroWindow title="Erreur" className="w-80">
          <div className="p-4 text-retro-sm">
            <p className="font-bold mb-2">Erreur de connexion</p>
            <p className="text-retro-xs">{error}</p>
          </div>
        </RetroWindow>
      </div>
    )
  }

  const selectedMs = selectedCorpus ? manuscripts[selectedCorpus.id] : undefined

  return (
    <div className="min-h-screen bg-retro-dither flex flex-col">
      {/* ── Menu bar (top of screen) ─────────────────────────────── */}
      <RetroMenuBar
        items={[
          { label: 'IIIF Studio' },
          { label: 'Administration', onClick: () => navigate('/admin') },
        ]}
        right={
          <SearchBar onSelectResult={(r) => navigate(`/editor/${r.page_id}`)} />
        }
      />

      {/* ── Desktop area ─────────────────────────────────────────── */}
      <div className="flex-1 flex flex-col">

        {/* ── Corpus list window (center) ──────────────────────── */}
        <div className="flex-1 flex items-start justify-center p-6 gap-4">
          <RetroWindow
            title="Corpus disponibles"
            statusBar={`${corpora.length} corpus enregistre${corpora.length > 1 ? 's' : ''}`}
            className="w-full max-w-2xl"
            scrollable
          >
            {corpora.length === 0 ? (
              <div className="p-4 text-retro-sm text-retro-darkgray">
                Aucun corpus enregistre. Creez-en un via Administration.
              </div>
            ) : (
              <div className="divide-y divide-retro-gray">
                {corpora.map((corpus) => (
                  <div key={corpus.id}>
                    <button
                      type="button"
                      onClick={() => void handleCorpusClick(corpus)}
                      className={`
                        w-full text-left px-3 py-[6px] flex items-center gap-3
                        text-retro-sm font-retro
                        ${selectedCorpus?.id === corpus.id
                          ? 'bg-retro-select text-retro-select-text'
                          : 'hover:bg-retro-select hover:text-retro-select-text'
                        }
                      `}
                    >
                      <span className="text-[18px] leading-none shrink-0">
                        {PROFILE_GLYPHS[corpus.profile_id] || '\u{1F4C1}'}
                      </span>
                      <div className="flex-1 min-w-0">
                        <div className="font-bold truncate">{corpus.title}</div>
                        <div className={`text-retro-xs truncate ${
                          selectedCorpus?.id === corpus.id ? 'opacity-70' : 'text-retro-darkgray'
                        }`}>
                          {corpus.profile_id} — {corpus.slug}
                        </div>
                      </div>
                    </button>

                    {expanding === corpus.id && (
                      <div className="px-3 py-1 text-retro-xs text-retro-darkgray bg-retro-light">
                        Chargement...
                      </div>
                    )}
                    {expandError && selectedCorpus?.id === corpus.id && !expanding && (
                      <div className="px-3 py-1 text-retro-xs text-retro-black bg-retro-light">
                        Erreur: {expandError}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </RetroWindow>

          {/* ── Manuscripts sub-window (appears when a corpus has multiple) ── */}
          {selectedMs && selectedMs.length > 1 && selectedCorpus && (
            <RetroWindow
              title={`Manuscrits — ${selectedCorpus.title}`}
              onClose={() => setSelectedCorpus(null)}
              statusBar={`${selectedMs.length} manuscrit${selectedMs.length > 1 ? 's' : ''}`}
              className="w-80"
              scrollable
            >
              <div className="divide-y divide-retro-gray">
                {selectedMs.map((ms) => (
                  <button
                    type="button"
                    key={ms.id}
                    onClick={() => navigate(`/reader/${ms.id}?profile=${selectedCorpus.profile_id}`)}
                    className="
                      w-full text-left px-3 py-[6px]
                      text-retro-sm font-retro
                      hover:bg-retro-select hover:text-retro-select-text
                    "
                  >
                    <div className="font-bold truncate">{ms.title}</div>
                    {ms.total_pages > 0 && (
                      <div className="text-retro-xs text-retro-darkgray">
                        {ms.total_pages} pages
                      </div>
                    )}
                  </button>
                ))}
              </div>
            </RetroWindow>
          )}
        </div>

        {/* ── Desktop icons (bottom dock) ────────────────────────── */}
        <div
          className="
            shrink-0 flex items-end justify-center gap-1 px-4 py-3
            border-t-retro border-retro-black
            bg-retro-gray
            shadow-retro-outset
          "
        >
          {corpora.map((corpus) => (
            <RetroIcon
              key={corpus.id}
              glyph={PROFILE_GLYPHS[corpus.profile_id] || '\u{1F4C1}'}
              label={corpus.slug}
              selected={selectedCorpus?.id === corpus.id}
              onClick={() => void handleCorpusClick(corpus)}
            />
          ))}
          {corpora.length === 0 && (
            <div className="text-retro-xs text-retro-darkgray py-2">
              Aucun corpus
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
