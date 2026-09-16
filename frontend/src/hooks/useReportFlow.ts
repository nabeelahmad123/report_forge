import { useState } from 'react'
import { analyzeDemoDataset, analyzeUpload, generateReport } from '../lib/api'
import type { AnalyzeResponse, ReportResponse } from '../types'

export type ReportFlowStatus = 'idle' | 'loading-metrics' | 'ready' | 'loading-report' | 'error'

/**
 * Owns the Lab Report flow's state at the App level (not inside ReportPage)
 * so a loaded dataset / generated report survives navigating to RegWatch
 * and back — react-router unmounts route components on navigation, which
 * would otherwise silently drop this state and reset the demo.
 */
export function useReportFlow() {
  const [status, setStatus] = useState<ReportFlowStatus>('idle')
  const [error, setError] = useState<string | null>(null)
  const [metrics, setMetrics] = useState<AnalyzeResponse | null>(null)
  const [selectedRunId, setSelectedRunId] = useState<string | null>(null)
  const [report, setReport] = useState<ReportResponse | null>(null)

  async function loadDemo() {
    setStatus('loading-metrics')
    setError(null)
    setReport(null)
    try {
      const result = await analyzeDemoDataset()
      setMetrics(result)
      setSelectedRunId(result.runs[0]?.run_id ?? null)
      setStatus('ready')
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load demo dataset')
      setStatus('error')
    }
  }

  async function upload(file: File) {
    setStatus('loading-metrics')
    setError(null)
    setReport(null)
    try {
      const result = await analyzeUpload(file)
      setMetrics(result)
      setSelectedRunId(result.runs[0]?.run_id ?? null)
      setStatus('ready')
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to analyze CSV')
      setStatus('error')
    }
  }

  async function generate() {
    if (!metrics) return
    setStatus('loading-report')
    setError(null)
    try {
      const result = await generateReport(metrics)
      setReport(result)
      setStatus('ready')
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to generate report')
      setStatus('ready')
    }
  }

  return {
    status,
    error,
    metrics,
    selectedRunId,
    setSelectedRunId,
    report,
    loadDemo,
    upload,
    generate,
  }
}

export type ReportFlow = ReturnType<typeof useReportFlow>
