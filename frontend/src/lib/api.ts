import type { AnalyzeResponse, FeedResponse, ReportResponse } from '../types'

const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

async function parseErrorDetail(res: Response): Promise<string> {
  try {
    const body = await res.json()
    return typeof body.detail === 'string' ? body.detail : res.statusText
  } catch {
    return res.statusText
  }
}

export async function analyzeDemoDataset(): Promise<AnalyzeResponse> {
  const res = await fetch(`${API_URL}/analyze?use_demo=true`, { method: 'POST' })
  if (!res.ok) throw new Error(await parseErrorDetail(res))
  return res.json()
}

export async function analyzeUpload(file: File): Promise<AnalyzeResponse> {
  const formData = new FormData()
  formData.append('file', file)
  const res = await fetch(`${API_URL}/analyze`, { method: 'POST', body: formData })
  if (!res.ok) throw new Error(await parseErrorDetail(res))
  return res.json()
}

export async function generateReport(metrics: AnalyzeResponse): Promise<ReportResponse> {
  const res = await fetch(`${API_URL}/report`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(metrics),
  })
  if (!res.ok) throw new Error(await parseErrorDetail(res))
  return res.json()
}

export async function fetchFeed(): Promise<FeedResponse> {
  const res = await fetch(`${API_URL}/feed`)
  if (!res.ok) throw new Error(await parseErrorDetail(res))
  return res.json()
}
