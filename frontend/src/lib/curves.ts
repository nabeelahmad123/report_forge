import type { RunMetrics } from '../types'

export type CurvePoint = { t: number } & Record<string, number>

/**
 * Reconstructs a smooth C(t) = C0 * exp(-k*t) curve per compound from the
 * fitted rate constant for chart display. The API returns summary metrics
 * (c0, k, half-life), not the raw time series, so this is a visualization
 * aid, not a re-plot of measured points. Compounds with no valid fit
 * (insufficient_data) are omitted.
 */
export function buildRunCurveData(run: RunMetrics, steps = 24): CurvePoint[] {
  const fittable = run.compounds.filter((c) => c.decay_rate_k_per_min != null && !c.insufficient_data)
  const points: CurvePoint[] = []
  for (let i = 0; i <= steps; i++) {
    const t = (run.duration_min * i) / steps
    const point: CurvePoint = { t: Math.round(t * 10) / 10 }
    for (const c of fittable) {
      point[c.compound] = Number((c.c0_ug_l * Math.exp(-(c.decay_rate_k_per_min ?? 0) * t)).toFixed(2))
    }
    points.push(point)
  }
  return points
}
