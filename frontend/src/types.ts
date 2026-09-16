export interface CompoundMetrics {
  compound: string
  c0_ug_l: number
  c_end_ug_l: number
  degradation_efficiency_pct: number
  decay_rate_k_per_min: number | null
  half_life_min: number | null
  eeo_kwh_per_m3_per_order: number | null
  fit_r_squared: number | null
  insufficient_data: boolean
}

export interface AnomalyFlag {
  type: string
  timestamp: string
  detail: string
  severity: string
}

export interface ElectrodeTrend {
  electrode_pair: string
  slope_kwh_per_ug_l_removed_per_min: number | null
  trend: 'stable' | 'degrading' | 'improving' | 'insufficient_data'
}

export interface RunMetrics {
  run_id: string
  sample_id: string
  electrode_pair: string
  start_time: string
  end_time: string
  duration_min: number
  n_samples: number
  compounds: CompoundMetrics[]
  electrode_trend: ElectrodeTrend
  anomalies: AnomalyFlag[]
}

export interface AnalyzeResponse {
  source: 'upload' | 'demo'
  generated_at: string
  runs: RunMetrics[]
}

export interface ReportResponse {
  markdown: string
  source: 'llm' | 'template_fallback'
  model: string | null
  generated_at: string
}

export type RegWatchCategory = 'Regulation' | 'Litigation' | 'Science' | 'Industry'

export interface RegWatchItem {
  title: string
  source: string
  published_at: string
  url: string
  summary: string
  category: RegWatchCategory
  relevance_score: number
}

export interface FeedResponse {
  source: 'snapshot' | 'live'
  generated_at: string
  items: RegWatchItem[]
}
