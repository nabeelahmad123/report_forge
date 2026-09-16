import { STATUS_COLORS } from '../lib/colors'
import type { RunMetrics } from '../types'

const TREND_STATUS: Record<RunMetrics['electrode_trend']['trend'], { color: string; label: string }> = {
  stable: { color: STATUS_COLORS.good, label: 'Stable' },
  improving: { color: STATUS_COLORS.good, label: 'Improving' },
  degrading: { color: STATUS_COLORS.warning, label: 'Degrading' },
  insufficient_data: { color: STATUS_COLORS.serious, label: 'Insufficient data' },
}

export function RunSummaryCard({ run, selected, onSelect }: { run: RunMetrics; selected: boolean; onSelect: () => void }) {
  const trend = TREND_STATUS[run.electrode_trend.trend]
  const bestEfficiency = Math.max(...run.compounds.map((c) => c.degradation_efficiency_pct))

  return (
    <button
      type="button"
      onClick={onSelect}
      className={`w-full rounded-lg border p-4 text-left transition ${
        selected
          ? 'border-teal-500 bg-teal-50 dark:border-teal-400 dark:bg-teal-950/40'
          : 'border-slate-200 bg-white hover:border-slate-300 dark:border-slate-800 dark:bg-slate-900 dark:hover:border-slate-700'
      }`}
    >
      <div className="flex items-center justify-between">
        <span className="font-mono text-sm font-medium text-slate-900 dark:text-slate-100">{run.run_id}</span>
        <span className="flex items-center gap-1.5 text-xs font-medium" style={{ color: trend.color }}>
          <span className="inline-block h-2 w-2 rounded-full" style={{ backgroundColor: trend.color }} />
          {trend.label}
        </span>
      </div>
      <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
        {run.sample_id} · {run.electrode_pair} · {run.duration_min.toFixed(0)} min
      </p>
      <div className="mt-3 flex items-baseline gap-1">
        <span className="text-2xl font-semibold text-slate-900 dark:text-slate-100">{bestEfficiency.toFixed(1)}%</span>
        <span className="text-xs text-slate-500 dark:text-slate-400">best degradation</span>
      </div>
      {run.anomalies.length > 0 && (
        <p className="mt-2 text-xs font-medium" style={{ color: STATUS_COLORS.serious }}>
          {run.anomalies.length} anomal{run.anomalies.length === 1 ? 'y' : 'ies'} flagged
        </p>
      )}
    </button>
  )
}
