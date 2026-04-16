import { describe, it, expect, vi, beforeEach } from 'vitest'

// We need to mock fetch before importing the module,
// and also need to handle import.meta.env used by the module.

// Mock global fetch
const mockFetch = vi.fn()
vi.stubGlobal('fetch', mockFetch)

// Dynamic import so our fetch stub is in place
const api = await import('../api')

beforeEach(() => {
  mockFetch.mockReset()
})

describe('fetchCorpora', () => {
  it('calls the correct endpoint', async () => {
    const mockCorpora = [
      { id: '1', slug: 'test', title: 'Test', profile_id: 'medieval-illuminated', created_at: '', updated_at: '' },
    ]
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve(mockCorpora),
    })

    const result = await api.fetchCorpora()

    expect(mockFetch).toHaveBeenCalledOnce()
    expect(mockFetch).toHaveBeenCalledWith('/api/v1/corpora')
    expect(result).toEqual(mockCorpora)
  })

  it('throws ApiError on non-200 response', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 404,
    })

    await expect(api.fetchCorpora()).rejects.toThrow(api.ApiError)
    await mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 500,
    })
    await expect(api.fetchCorpora()).rejects.toThrow('HTTP 500')
  })
})

describe('ApiError', () => {
  it('has correct name and status', () => {
    const err = new api.ApiError(422, 'Validation failed')
    expect(err.name).toBe('ApiError')
    expect(err.status).toBe(422)
    expect(err.message).toBe('Validation failed')
    expect(err).toBeInstanceOf(Error)
  })
})

describe('post helper — error extraction', () => {
  it('extracts string detail from FastAPI error', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 400,
      json: () => Promise.resolve({ detail: 'Corpus not found' }),
    })

    await expect(
      api.createCorpus({ slug: 'x', title: 'X', profile_id: 'p' })
    ).rejects.toThrow('Corpus not found')
  })

  it('extracts array detail from FastAPI validation error', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 422,
      json: () =>
        Promise.resolve({
          detail: [
            { loc: ['body', 'slug'], msg: 'field required', type: 'missing' },
          ],
        }),
    })

    await expect(
      api.createCorpus({ slug: '', title: '', profile_id: '' })
    ).rejects.toThrow('body \u2192 slug : field required')
  })

  it('falls back to HTTP status when json parsing fails', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 500,
      json: () => Promise.reject(new Error('not json')),
    })

    await expect(
      api.createCorpus({ slug: 'x', title: 'X', profile_id: 'p' })
    ).rejects.toThrow('HTTP 500')
  })
})

describe('deleteCorpus', () => {
  it('calls DELETE on the correct endpoint', async () => {
    mockFetch.mockResolvedValueOnce({ ok: true })

    await api.deleteCorpus('abc-123')

    expect(mockFetch).toHaveBeenCalledWith('/api/v1/corpora/abc-123', {
      method: 'DELETE',
    })
  })
})
