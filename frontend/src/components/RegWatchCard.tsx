import { categoryColor } from '../lib/colors'
import type { RegWatchItem } from '../types'

export function RegWatchCard({ item }: { item: RegWatchItem }) {
  const date = new Date(item.published_at).toLocaleDateString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  })

  return (
    <article className="rounded-lg border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900">
      <div className="flex items-center justify-between gap-2">
        <span className="flex items-center gap-1.5 text-xs font-medium text-slate-600 dark:text-slate-400">
          <span
            className="inline-block h-2 w-2 rounded-full"
            style={{ backgroundColor: categoryColor(item.category) }}
            aria-hidden
          />
          {item.category}
        </span>
        <span className="text-xs text-slate-400" title={`Relevance ${item.relevance_score}/5`}>
          {'●'.repeat(item.relevance_score)}
          {'○'.repeat(5 - item.relevance_score)}
        </span>
      </div>

      <h3 className="mt-2 font-medium text-slate-900 dark:text-slate-100">{item.title}</h3>
      <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
        {item.source} · {date}
      </p>
      <p className="mt-2 text-sm text-slate-600 dark:text-slate-300">{item.summary}</p>

      <a
        href={item.url}
        target="_blank"
        rel="noopener noreferrer"
        className="mt-3 inline-block text-xs font-medium text-teal-700 hover:underline dark:text-teal-400"
      >
        Source ↗
      </a>
    </article>
  )
}
