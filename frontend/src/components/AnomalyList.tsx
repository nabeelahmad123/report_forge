import { STATUS_COLORS } from '../lib/colors'
import type { AnomalyFlag } from '../types'

const SEVERITY_COLOR: Record<string, string> = {
  high: STATUS_COLORS.critical,
  medium: STATUS_COLORS.warning,
  low: STATUS_COLORS.good,
}

export function AnomalyList({ anomalies }: { anomalies: AnomalyFlag[] }) {
  if (anomalies.length === 0) {
    return <p className="text-sm text-slate-500 dark:text-slate-400">No anomalies flagged for this run.</p>
  }

  return (
    <ul className="space-y-2">
      {anomalies.map((a, i) => (
        <li key={i} className="flex items-start gap-2 rounded-md border border-slate-200 p-2.5 text-sm dark:border-slate-800">
          <span
            className="mt-1 inline-block h-2 w-2 shrink-0 rounded-full"
            style={{ backgroundColor: SEVERITY_COLOR[a.severity] ?? STATUS_COLORS.warning }}
            aria-hidden
          />
          <div>
            <p className="font-medium text-slate-900 dark:text-slate-100">
              {a.type.replaceAll('_', ' ')}{' '}
              <span className="font-normal text-slate-500 dark:text-slate-400">
                {new Date(a.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
              </span>
            </p>
            <p className="text-slate-600 dark:text-slate-400">{a.detail}</p>
          </div>
        </li>
      ))}
    </ul>
  )
}
