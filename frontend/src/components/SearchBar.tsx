import { useCallback, useEffect, useRef, useState } from 'react'
import { searchPages, type SearchResult } from '../lib/api.ts'

interface Props {
  onSelectResult?: (result: SearchResult) => void
}

export default function SearchBar({ onSelectResult }: Props) {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<SearchResult[]>([])
  const [open, setOpen] = useState(false)
  const [loading, setLoading] = useState(false)
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const containerRef = useRef<HTMLDivElement>(null)

  const runSearch = useCallback(async (q: string) => {
    if (q.trim().length < 2) {
      setResults([])
      setOpen(false)
      return
    }
    setLoading(true)
    try {
      const res = await searchPages(q.trim())
      setResults(res)
      setOpen(true)
    } catch {
      setResults([])
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current)
    debounceRef.current = setTimeout(() => {
      void runSearch(query)
    }, 300)
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current)
    }
  }, [query, runSearch])

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false)
      }
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  return (
    <div ref={containerRef} className="relative w-64">
      <div className="relative">
        <input
          type="search"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onFocus={() => results.length > 0 && setOpen(true)}
          placeholder="Rechercher..."
          className="
            w-full px-2 py-[2px]
            text-retro-sm font-retro
            bg-retro-white text-retro-black
            border border-retro-black
            shadow-retro-well
            placeholder:text-retro-darkgray
          "
        />
        {loading && (
          <span className="absolute right-2 top-1/2 -translate-y-1/2 text-retro-darkgray text-retro-xs">
            ...
          </span>
        )}
      </div>

      {open && (
        <div
          className="
            absolute top-full left-0 right-0 mt-[2px]
            bg-retro-white
            border-retro border-retro-black
            shadow-retro-lg
            z-50 max-h-60
            overflow-y-auto retro-scroll
          "
        >
          {results.length === 0 ? (
            <div className="px-2 py-2 text-retro-xs text-retro-darkgray">
              Aucun resultat.
            </div>
          ) : (
            <ul>
              {results.map((r) => (
                <li key={r.page_id}>
                  <button
                    onClick={() => {
                      setOpen(false)
                      onSelectResult?.(r)
                    }}
                    className="
                      w-full text-left px-2 py-[3px]
                      text-retro-sm font-retro
                      hover:bg-retro-select hover:text-retro-select-text
                      border-b border-retro-gray last:border-0
                    "
                  >
                    <div className="flex items-center justify-between gap-2">
                      <span className="font-bold">{r.folio_label}</span>
                      <span className="text-retro-xs opacity-60">
                        {r.score}
                      </span>
                    </div>
                    <div className="text-retro-xs truncate opacity-70">
                      {r.excerpt}
                    </div>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  )
}
