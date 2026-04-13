import { type FormEvent, useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  fetchCorpora,
  fetchManuscripts,
  fetchPages,
  listProfiles,
  createCorpus,
  deleteCorpus,
  fetchProviders,
  fetchProviderModels,
  selectModel,
  getCorpusModel,
  ingestImages,
  ingestManifest,
  ingestFiles,
  runCorpus,
  getJob,
  retryJob,
  type Corpus,
  type CorpusProfile,
  type CorpusModelConfig,
  type ProviderInfo,
  type ModelInfo,
  type Job,
  type CreateCorpusInput,
} from '../lib/api.ts'
import {
  RetroMenuBar,
  RetroWindow,
  RetroButton,
  RetroInput,
  RetroTextarea,
  RetroSelect,
  RetroBadge,
} from '../components/retro'

type IngestSubTab = 'urls' | 'manifest' | 'files'

// ── Feedback helpers ───────────────────────────────────────────────────────

function ErrorMsg({ message }: { message: string }) {
  return (
    <div className="border border-retro-black bg-retro-white p-2 text-retro-sm">
      <span className="font-bold">Erreur:</span> {message}
    </div>
  )
}

function SuccessMsg({ message }: { message: string }) {
  return (
    <div className="border border-retro-black bg-retro-light p-2 text-retro-sm">
      <span className="font-bold">OK:</span> {message}
    </div>
  )
}

// ── CreateCorpusPanel ─────────────────────────────────────────────────────

interface CreateCorpusPanelProps {
  onCreated: (corpus: Corpus) => void
}

function CreateCorpusPanel({ onCreated }: CreateCorpusPanelProps) {
  const [profiles, setProfiles] = useState<CorpusProfile[]>([])
  const [form, setForm] = useState<CreateCorpusInput>({ slug: '', title: '', profile_id: '' })
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)

  useEffect(() => {
    listProfiles()
      .then((ps) => {
        setProfiles(ps)
        if (ps.length > 0) setForm((f) => ({ ...f, profile_id: ps[0].profile_id }))
      })
      .catch(() => {})
  }, [])

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setError(null)
    setSuccess(null)
    setLoading(true)
    try {
      const corpus = await createCorpus(form)
      setSuccess(`Corpus "${corpus.title}" cree.`)
      setForm((f) => ({ ...f, slug: '', title: '' }))
      onCreated(corpus)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Erreur inconnue')
    } finally {
      setLoading(false)
    }
  }

  return (
    <RetroWindow title="Creer un corpus" className="max-w-lg">
      <form onSubmit={(e) => void handleSubmit(e)} className="p-3 flex flex-col gap-2">
        <RetroInput
          label="Slug (identifiant unique)"
          value={form.slug}
          onChange={(e) => setForm((f) => ({ ...f, slug: e.target.value }))}
          required
          placeholder="ex. beatus-lat8878"
        />
        <RetroInput
          label="Titre"
          value={form.title}
          onChange={(e) => setForm((f) => ({ ...f, title: e.target.value }))}
          required
          placeholder="ex. Beatus de Saint-Sever"
        />
        {profiles.length === 0 ? (
          <div className="text-retro-sm text-retro-darkgray">Chargement des profils...</div>
        ) : (
          <RetroSelect
            label="Profil"
            value={form.profile_id}
            onChange={(e) => setForm((f) => ({ ...f, profile_id: e.target.value }))}
            options={profiles.map((p) => ({ value: p.profile_id, label: `${p.label} (${p.profile_id})` }))}
          />
        )}
        {error && <ErrorMsg message={error} />}
        {success && <SuccessMsg message={success} />}
        <div className="mt-1">
          <RetroButton
            type="submit"
            disabled={loading || !form.slug || !form.title || !form.profile_id}
          >
            {loading ? 'Creation...' : 'Creer le corpus'}
          </RetroButton>
        </div>
      </form>
    </RetroWindow>
  )
}

// ── ModelPanel ────────────────────────────────────────────────────────────

interface ModelPanelProps {
  corpusId: string
  onSaved: () => void
}

function ModelPanel({ corpusId, onSaved }: ModelPanelProps) {
  const [providers, setProviders] = useState<ProviderInfo[]>([])
  const [loadingProviders, setLoadingProviders] = useState(true)
  const [providersError, setProvidersError] = useState<string | null>(null)
  const [selectedProvider, setSelectedProvider] = useState<string>('')
  const [models, setModels] = useState<ModelInfo[]>([])
  const [loadingModels, setLoadingModels] = useState(false)
  const [modelsError, setModelsError] = useState<string | null>(null)
  const [selectedModelId, setSelectedModelId] = useState('')
  const [currentModel, setCurrentModel] = useState<CorpusModelConfig | null>(null)
  const [savingModel, setSavingModel] = useState(false)
  const [saveError, setSaveError] = useState<string | null>(null)
  const [saveSuccess, setSaveSuccess] = useState<string | null>(null)

  useEffect(() => {
    void getCorpusModel(corpusId).then(setCurrentModel)
    setLoadingProviders(true)
    setProvidersError(null)
    fetchProviders()
      .then((ps) => {
        setProviders(ps)
        const first = ps.find((p) => p.available)
        if (first) setSelectedProvider(first.provider_type)
      })
      .catch((err) => setProvidersError(err instanceof Error ? err.message : 'Erreur'))
      .finally(() => setLoadingProviders(false))
  }, [corpusId])

  useEffect(() => {
    if (!selectedProvider) return
    setModels([])
    setSelectedModelId('')
    setModelsError(null)
    setLoadingModels(true)
    fetchProviderModels(selectedProvider)
      .then((ms) => { setModels(ms); if (ms.length > 0) setSelectedModelId(ms[0].model_id) })
      .catch((err) => setModelsError(err instanceof Error ? err.message : 'Erreur'))
      .finally(() => setLoadingModels(false))
  }, [selectedProvider])

  const handleSelectModel = async (e: FormEvent) => {
    e.preventDefault()
    setSaveError(null)
    setSaveSuccess(null)
    setSavingModel(true)
    const model = models.find((m) => m.model_id === selectedModelId)
    try {
      await selectModel(corpusId, selectedModelId, model?.display_name ?? selectedModelId, selectedProvider)
      const updated = await getCorpusModel(corpusId)
      setCurrentModel(updated)
      setSaveSuccess(`Modele "${model?.display_name ?? selectedModelId}" associe.`)
      onSaved()
    } catch (err) {
      setSaveError(err instanceof Error ? err.message : 'Erreur')
    } finally {
      setSavingModel(false)
    }
  }

  return (
    <div className="flex flex-col gap-2">
      {currentModel && (
        <div className="text-retro-sm border border-retro-black p-2 bg-retro-light">
          Modele actuel: <span className="font-bold">{currentModel.selected_model_display_name}</span>
          {' '}({currentModel.provider_type})
        </div>
      )}

      {loadingProviders && <div className="text-retro-sm text-retro-darkgray">Detection providers...</div>}
      {!loadingProviders && providersError && <ErrorMsg message={providersError} />}
      {!loadingProviders && providers.length > 0 && (
        <div className="flex flex-wrap gap-[2px]">
          {providers.map((p) => (
            <RetroButton
              key={p.provider_type}
              size="sm"
              pressed={selectedProvider === p.provider_type}
              disabled={!p.available}
              onClick={() => p.available && setSelectedProvider(p.provider_type)}
            >
              {p.display_name} {p.available ? `(${p.model_count})` : '— N/A'}
            </RetroButton>
          ))}
        </div>
      )}

      {selectedProvider && (
        <form onSubmit={(e) => void handleSelectModel(e)} className="flex flex-col gap-2 max-w-sm">
          {loadingModels && <div className="text-retro-sm text-retro-darkgray">Chargement modeles...</div>}
          {!loadingModels && modelsError && <ErrorMsg message={modelsError} />}
          {!loadingModels && models.length > 0 && (
            <RetroSelect
              label={`Modele — ${providers.find((p) => p.provider_type === selectedProvider)?.display_name}`}
              value={selectedModelId}
              onChange={(e) => setSelectedModelId(e.target.value)}
              options={models.map((m) => ({
                value: m.model_id,
                label: `${m.display_name}${m.supports_vision ? ' (vision)' : ''}`,
              }))}
            />
          )}
          {saveError && <ErrorMsg message={saveError} />}
          {saveSuccess && <SuccessMsg message={saveSuccess} />}
          {!loadingModels && models.length > 0 && (
            <RetroButton type="submit" disabled={savingModel || !selectedModelId}>
              {savingModel ? 'Enregistrement...' : 'Selectionner'}
            </RetroButton>
          )}
        </form>
      )}
    </div>
  )
}

// ── IngestPanel ───────────────────────────────────────────────────────────

function IngestPanel({ corpusId }: { corpusId: string }) {
  const [subTab, setSubTab] = useState<IngestSubTab>('urls')
  const [urlsText, setUrlsText] = useState('')
  const [folioLabelsText, setFolioLabelsText] = useState('')
  const [urlsLoading, setUrlsLoading] = useState(false)
  const [urlsError, setUrlsError] = useState<string | null>(null)
  const [urlsSuccess, setUrlsSuccess] = useState<string | null>(null)
  const [manifestUrl, setManifestUrl] = useState('')
  const [manifestLoading, setManifestLoading] = useState(false)
  const [manifestError, setManifestError] = useState<string | null>(null)
  const [manifestSuccess, setManifestSuccess] = useState<string | null>(null)
  const [selectedFiles, setSelectedFiles] = useState<File[]>([])
  const [filesLoading, setFilesLoading] = useState(false)
  const [filesError, setFilesError] = useState<string | null>(null)
  const [filesSuccess, setFilesSuccess] = useState<string | null>(null)

  const handleUrlsSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setUrlsError(null); setUrlsSuccess(null)
    const urls = urlsText.split('\n').map((l) => l.trim()).filter(Boolean)
    const labels = folioLabelsText.split('\n').map((l) => l.trim()).filter(Boolean)
    if (urls.length === 0) { setUrlsError('Aucune URL.'); return }
    if (labels.length !== urls.length) { setUrlsError(`Labels (${labels.length}) != URLs (${urls.length})`); return }
    setUrlsLoading(true)
    try {
      const resp = await ingestImages(corpusId, urls, labels)
      setUrlsSuccess(`${resp.pages_created} page(s) ingeree(s).`)
      setUrlsText(''); setFolioLabelsText('')
    } catch (err) { setUrlsError(err instanceof Error ? err.message : 'Erreur') }
    finally { setUrlsLoading(false) }
  }

  const handleManifestSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setManifestError(null); setManifestSuccess(null); setManifestLoading(true)
    try {
      const resp = await ingestManifest(corpusId, manifestUrl)
      setManifestSuccess(`${resp.pages_created} page(s) ingeree(s).`)
      setManifestUrl('')
    } catch (err) { setManifestError(err instanceof Error ? err.message : 'Erreur') }
    finally { setManifestLoading(false) }
  }

  const handleFilesSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setFilesError(null); setFilesSuccess(null)
    if (selectedFiles.length === 0) { setFilesError('Aucun fichier.'); return }
    setFilesLoading(true)
    try {
      const resp = await ingestFiles(corpusId, selectedFiles)
      setFilesSuccess(`${resp.pages_created} page(s) ingeree(s).`)
      setSelectedFiles([])
    } catch (err) { setFilesError(err instanceof Error ? err.message : 'Erreur') }
    finally { setFilesLoading(false) }
  }

  return (
    <div className="flex flex-col gap-2">
      <div className="flex gap-[2px]">
        {(['urls', 'manifest', 'files'] as IngestSubTab[]).map((t) => (
          <RetroButton key={t} size="sm" pressed={subTab === t} onClick={() => setSubTab(t)}>
            {t === 'urls' ? 'URLs' : t === 'manifest' ? 'Manifest' : 'Fichiers'}
          </RetroButton>
        ))}
      </div>

      {subTab === 'urls' && (
        <form onSubmit={(e) => void handleUrlsSubmit(e)} className="flex flex-col gap-2">
          <RetroTextarea label="URLs d'images (1/ligne)" value={urlsText} onChange={(e) => setUrlsText(e.target.value)} rows={4} placeholder="https://..." />
          <RetroTextarea label="Folio labels (1/ligne)" value={folioLabelsText} onChange={(e) => setFolioLabelsText(e.target.value)} rows={4} placeholder={'001r\n001v'} />
          {urlsError && <ErrorMsg message={urlsError} />}
          {urlsSuccess && <SuccessMsg message={urlsSuccess} />}
          <RetroButton type="submit" disabled={urlsLoading}>{urlsLoading ? 'Ingestion...' : 'Ingerer'}</RetroButton>
        </form>
      )}

      {subTab === 'manifest' && (
        <form onSubmit={(e) => void handleManifestSubmit(e)} className="flex flex-col gap-2">
          <RetroInput label="URL manifest IIIF" type="url" value={manifestUrl} onChange={(e) => setManifestUrl(e.target.value)} required placeholder="https://.../manifest.json" />
          {manifestError && <ErrorMsg message={manifestError} />}
          {manifestSuccess && <SuccessMsg message={manifestSuccess} />}
          <RetroButton type="submit" disabled={manifestLoading || !manifestUrl}>{manifestLoading ? 'Ingestion...' : 'Importer'}</RetroButton>
        </form>
      )}

      {subTab === 'files' && (
        <form onSubmit={(e) => void handleFilesSubmit(e)} className="flex flex-col gap-2">
          <div className="flex flex-col gap-[2px]">
            <label className="text-retro-xs font-bold">Fichiers images</label>
            <input
              type="file" multiple accept="image/*"
              onChange={(e) => setSelectedFiles(Array.from(e.target.files ?? []))}
              className="text-retro-sm font-retro border border-retro-black bg-retro-white p-1"
            />
            {selectedFiles.length > 0 && (
              <span className="text-retro-xs text-retro-darkgray">{selectedFiles.length} fichier(s)</span>
            )}
          </div>
          {filesError && <ErrorMsg message={filesError} />}
          {filesSuccess && <SuccessMsg message={filesSuccess} />}
          <RetroButton type="submit" disabled={filesLoading || selectedFiles.length === 0}>{filesLoading ? 'Envoi...' : 'Envoyer'}</RetroButton>
        </form>
      )}
    </div>
  )
}

// ── RunPanel ──────────────────────────────────────────────────────────────

function RunPanel({ corpusId, hasModel }: { corpusId: string; hasModel: boolean }) {
  const [pageCount, setPageCount] = useState<number | null>(null)
  const [launching, setLaunching] = useState(false)
  const [launchError, setLaunchError] = useState<string | null>(null)
  const [jobIds, setJobIds] = useState<string[]>([])
  const [jobs, setJobs] = useState<Record<string, Job>>({})
  const [polling, setPolling] = useState(false)

  useEffect(() => {
    fetchManuscripts(corpusId)
      .then(async (manuscripts) => {
        if (manuscripts.length === 0) { setPageCount(0); return }
        const pagesArrays = await Promise.all(manuscripts.map((m) => fetchPages(m.id)))
        setPageCount(pagesArrays.reduce((sum, ps) => sum + ps.length, 0))
      })
      .catch(() => setPageCount(null))
  }, [corpusId])

  useEffect(() => {
    if (!polling || jobIds.length === 0) return
    const poll = async () => {
      try {
        const results = await Promise.all(jobIds.map((id) => getJob(id)))
        const map: Record<string, Job> = {}
        for (const job of results) map[job.id] = job
        setJobs(map)
        if (results.every((j) => j.status === 'done' || j.status === 'failed')) setPolling(false)
      } catch { /* transient */ }
    }
    const id = setInterval(() => void poll(), 3000)
    return () => clearInterval(id)
  }, [polling, jobIds])

  const handleRun = async () => {
    setLaunchError(null); setJobIds([]); setJobs({}); setLaunching(true)
    try {
      const resp = await runCorpus(corpusId)
      setJobIds(resp.job_ids); setPolling(true)
    } catch (err) { setLaunchError(err instanceof Error ? err.message : 'Erreur') }
    finally { setLaunching(false) }
  }

  const handleRetryFailed = async () => {
    if (polling || launching) return
    const failedIds = Object.values(jobs).filter((j) => j.status === 'failed').map((j) => j.id)
    if (failedIds.length === 0) return
    await Promise.allSettled(failedIds.map((id) => retryJob(id)))
    setPolling(true)
  }

  const jobList = Object.values(jobs)
  const doneCount = jobList.filter((j) => j.status === 'done').length
  const failedCount = jobList.filter((j) => j.status === 'failed').length
  const totalCount = jobList.length

  const statusVariant = (s: string): 'default' | 'success' | 'warning' | 'error' | 'info' => {
    if (s === 'done') return 'success'
    if (s === 'failed') return 'error'
    if (s === 'running') return 'info'
    return 'default'
  }

  if (!hasModel) {
    return <div className="text-retro-sm border border-retro-black p-2 bg-retro-white">Configurez d'abord un modele IA.</div>
  }

  return (
    <div className="flex flex-col gap-2">
      {pageCount !== null && (
        <div className="text-retro-sm">{pageCount === 0 ? 'Aucune page ingeree.' : `${pageCount} page(s).`}</div>
      )}
      {launchError && <ErrorMsg message={launchError} />}
      <div className="flex flex-wrap gap-[2px]">
        <RetroButton onClick={() => void handleRun()} disabled={launching || polling || pageCount === 0}>
          {launching ? 'Demarrage...' : polling ? 'En cours...' : 'Analyser tout'}
        </RetroButton>
        {failedCount > 0 && !polling && (
          <RetroButton onClick={() => void handleRetryFailed()}>
            Relancer {failedCount} erreur(s)
          </RetroButton>
        )}
      </div>
      {totalCount > 0 && (
        <div>
          <div className="text-retro-sm mb-1">
            <span className="font-bold">{doneCount}</span>/{totalCount} traitees
            {failedCount > 0 && <span className="ml-2 font-bold">{failedCount} erreur(s)</span>}
            {polling && <span className="ml-2 text-retro-darkgray">(actualisation 3s)</span>}
          </div>
          <div className="border border-retro-black bg-retro-white max-h-48 overflow-y-auto retro-scroll">
            {jobList.map((job) => (
              <div key={job.id} className="flex items-center justify-between text-retro-xs px-2 py-[2px] border-b border-retro-gray last:border-0">
                <span className="truncate max-w-[200px]">{job.page_id ?? job.id}</span>
                <div className="flex items-center gap-1 shrink-0">
                  <RetroBadge variant={statusVariant(job.status)}>{job.status}</RetroBadge>
                  {job.error_message && <span className="text-retro-xs truncate max-w-[120px]" title={job.error_message}>{job.error_message}</span>}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

// ── CorpusDetail ──────────────────────────────────────────────────────────

function CorpusDetail({ corpus, onDeleted }: { corpus: Corpus; onDeleted: () => void }) {
  const [hasModel, setHasModel] = useState(false)
  const [deleting, setDeleting] = useState(false)
  const [deleteError, setDeleteError] = useState<string | null>(null)
  const [confirmDelete, setConfirmDelete] = useState(false)

  useEffect(() => {
    getCorpusModel(corpus.id).then((m) => setHasModel(m !== null)).catch(() => {})
  }, [corpus.id])

  const handleDelete = async () => {
    setDeleteError(null); setDeleting(true)
    try { await deleteCorpus(corpus.id); onDeleted() }
    catch (err) { setDeleteError(err instanceof Error ? err.message : 'Erreur'); setDeleting(false); setConfirmDelete(false) }
  }

  return (
    <div className="flex flex-col gap-2">
      {/* Header */}
      <div className="flex items-center justify-between border border-retro-black bg-retro-light p-2">
        <div>
          <span className="text-retro-lg font-bold">{corpus.title}</span>
          <div className="text-retro-xs text-retro-darkgray">{corpus.slug} — {corpus.profile_id}</div>
        </div>
        <div className="flex items-center gap-1">
          {deleteError && <span className="text-retro-xs">{deleteError}</span>}
          {confirmDelete ? (
            <>
              <span className="text-retro-xs">Confirmer?</span>
              <RetroButton size="sm" onClick={() => void handleDelete()} disabled={deleting}>
                {deleting ? '...' : 'Oui'}
              </RetroButton>
              <RetroButton size="sm" onClick={() => setConfirmDelete(false)}>Non</RetroButton>
            </>
          ) : (
            <RetroButton size="sm" onClick={() => setConfirmDelete(true)}>Supprimer</RetroButton>
          )}
        </div>
      </div>

      <RetroWindow title="Modele IA">
        <div className="p-2">
          <ModelPanel key={corpus.id} corpusId={corpus.id} onSaved={() => setHasModel(true)} />
        </div>
      </RetroWindow>

      <RetroWindow title="Ingestion">
        <div className="p-2">
          <IngestPanel key={corpus.id} corpusId={corpus.id} />
        </div>
      </RetroWindow>

      <RetroWindow title="Traitement">
        <div className="p-2">
          <RunPanel key={corpus.id} corpusId={corpus.id} hasModel={hasModel} />
        </div>
      </RetroWindow>
    </div>
  )
}

// ── Admin (main component) ─────────────────────────────────────────────────

export default function Admin() {
  const navigate = useNavigate()
  const onHome = () => navigate('/')
  const [corpora, setCorpora] = useState<Corpus[]>([])
  const [selectedCorpusId, setSelectedCorpusId] = useState<string | null>(null)
  const [showCreate, setShowCreate] = useState(false)
  const didInit = useRef(false)

  const refreshCorpora = (selectId?: string) => {
    fetchCorpora()
      .then((cs) => {
        setCorpora(cs)
        if (selectId) { setSelectedCorpusId(selectId); setShowCreate(false) }
        else if (!didInit.current) {
          didInit.current = true
          if (cs.length > 0) { setSelectedCorpusId(cs[0].id); setShowCreate(false) }
          else setShowCreate(true)
        }
      })
      .catch(() => {})
  }

  useEffect(() => { refreshCorpora() }, [])

  const selectedCorpus = corpora.find((c) => c.id === selectedCorpusId) ?? null

  return (
    <div className="h-screen flex flex-col bg-retro-dither">
      <RetroMenuBar
        items={[
          { label: 'IIIF Studio', onClick: onHome },
          { label: 'Administration' },
        ]}
      />

      <div className="flex flex-1 min-h-0 overflow-hidden p-1 gap-1">
        {/* Sidebar */}
        <RetroWindow title="Corpus" className="w-56 shrink-0" scrollable>
          <div className="flex flex-col">
            <button
              type="button"
              onClick={() => { setShowCreate(true); setSelectedCorpusId(null) }}
              className={`
                w-full text-left px-2 py-[4px] text-retro-sm font-bold
                border-b border-retro-gray
                ${showCreate && !selectedCorpusId ? 'bg-retro-select text-retro-select-text' : 'hover:bg-retro-select hover:text-retro-select-text'}
              `}
            >
              + Nouveau corpus
            </button>
            {corpora.length === 0 && (
              <div className="px-2 py-2 text-retro-xs text-retro-darkgray">Aucun corpus</div>
            )}
            {corpora.map((c) => (
              <button
                type="button"
                key={c.id}
                onClick={() => { setSelectedCorpusId(c.id); setShowCreate(false) }}
                className={`
                  w-full text-left px-2 py-[4px] text-retro-sm
                  border-b border-retro-gray
                  ${selectedCorpusId === c.id && !showCreate
                    ? 'bg-retro-select text-retro-select-text'
                    : 'hover:bg-retro-select hover:text-retro-select-text'}
                `}
              >
                <div className="truncate font-bold">{c.title}</div>
                <div className={`truncate text-retro-xs ${selectedCorpusId === c.id && !showCreate ? 'opacity-70' : 'text-retro-darkgray'}`}>
                  {c.slug}
                </div>
              </button>
            ))}
          </div>
        </RetroWindow>

        {/* Main panel */}
        <div className="flex-1 overflow-y-auto retro-scroll p-2">
          {showCreate && !selectedCorpusId && (
            <CreateCorpusPanel onCreated={(corpus) => refreshCorpora(corpus.id)} />
          )}
          {!showCreate && selectedCorpus && (
            <CorpusDetail
              key={selectedCorpus.id}
              corpus={selectedCorpus}
              onDeleted={() => {
                const remaining = corpora.filter((c) => c.id !== selectedCorpus.id)
                setCorpora(remaining)
                if (remaining.length > 0) { setSelectedCorpusId(remaining[0].id); setShowCreate(false) }
                else { setSelectedCorpusId(null); setShowCreate(true) }
              }}
            />
          )}
          {!showCreate && !selectedCorpus && corpora.length > 0 && (
            <div className="text-retro-sm text-retro-darkgray p-2">Selectionnez un corpus.</div>
          )}
        </div>
      </div>
    </div>
  )
}
