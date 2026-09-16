import { useEffect, useState } from 'react'
import { RegWatchCard } from '../components/RegWatchCard'
import { fetchFeed } from '../lib/api'
import { categoryColor, REGWATCH_CATEGORY_ORDER } from '../lib/colors'
import type { FeedResponse, RegWatchCategory } from '../types'

type Status = 'loading' | 'ready' | 'error'

function Skeleton({ className }: { className?: string }) {
  return <div className={`animate-pulse rounded-md bg-slate-200 dark:bg-slate-800 ${className ?? ''}`} />
}

export function RegWatchPage() {
  const [status, setStatus] = useState<Status>('loading')
  const [error, setError] = useState<string | null>(null)
  const [feed, setFeed] = useState<FeedResponse | null>(null)
  const [activeCategories, setActiveCategories] = useState<Set<RegWatchCategory>>(new Set())

  useEffect(() => {
    fetchFeed()
      .then((result) => {
        setFeed(result)
        setStatus('ready')
      })
      .catch((e) => {
        setError(e instanceof Error ? e.message : 'Failed to load RegWatch feed')
        setStatus('error')
      })
  }, [])

  function toggleCategory(category: RegWatchCategory) {
    setActiveCategories((prev) => {
      const next = new Set(prev)
      if (next.has(category)) next.delete(category)
      else next.add(category)
      return next
    })
  }

  const items = feed?.items.filter((item) => activeCategories.size === 0 || activeCategories.has(item.category))

  return (
    <>
      <header className="mx-auto max-w-5xl px-4 pt-12 pb-8 text-center">
        <h1 className="text-3xl font-semibold tracking-tight text-slate-900 sm:text-4xl dark:text-slate-100">
          RegWatch — PFAS regulatory intelligence
        </h1>
        <p className="mx-auto mt-3 max-w-2xl text-slate-600 dark:text-slate-400">
          A digest of regulatory, legal, scientific, and industry developments relevant to PFAS
          electrochemical treatment operators.
        </p>
      </header>

      <main className="mx-auto max-w-5xl px-4 pb-20">
        <div className="mb-4 rounded-md border border-slate-200 bg-slate-100 px-4 py-2 text-center text-xs text-slate-600 dark:border-slate-800 dark:bg-slate-900 dark:text-slate-400">
          Sample data — live feed available on request.
        </div>

        <div className="mb-6 flex flex-wrap justify-center gap-2">
          <button
            type="button"
            onClick={() => setActiveCategories(new Set())}
            className={`rounded-full border px-3 py-1 text-xs font-medium transition ${
              activeCategories.size === 0
                ? 'border-teal-600 bg-teal-600 text-white'
                : 'border-slate-300 text-slate-600 hover:bg-slate-100 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-800'
            }`}
          >
            All
          </button>
          {REGWATCH_CATEGORY_ORDER.map((category) => {
            const active = activeCategories.has(category)
            return (
              <button
                key={category}
                type="button"
                onClick={() => toggleCategory(category)}
                className={`flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-medium transition ${
                  active
                    ? 'border-slate-400 bg-slate-100 dark:border-slate-600 dark:bg-slate-800'
                    : 'border-slate-300 text-slate-600 hover:bg-slate-100 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-800'
                }`}
              >
                <span
                  className="inline-block h-2 w-2 rounded-full"
                  style={{ backgroundColor: categoryColor(category) }}
                  aria-hidden
                />
                {category}
              </button>
            )
          })}
        </div>

        {status === 'loading' && (
          <div className="grid gap-4 sm:grid-cols-2">
            <Skeleton className="h-40" />
            <Skeleton className="h-40" />
            <Skeleton className="h-40" />
            <Skeleton className="h-40" />
          </div>
        )}

        {error && (
          <div className="rounded-md border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700 dark:border-red-900 dark:bg-red-950 dark:text-red-300">
            {error}
          </div>
        )}

        {items && (
          <div className="grid gap-4 sm:grid-cols-2">
            {items.map((item) => (
              <RegWatchCard key={item.title} item={item} />
            ))}
          </div>
        )}
      </main>
    </>
  )
}
