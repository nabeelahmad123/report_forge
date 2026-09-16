import { AnomalyList } from '../components/AnomalyList'
import { ComparisonBarChart } from '../components/ComparisonBarChart'
import { DegradationCurveChart } from '../components/DegradationCurveChart'
import { ReportPane } from '../components/ReportPane'
import { RunSummaryCard } from '../components/RunSummaryCard'
import type { ReportFlow } from '../hooks/useReportFlow'

function Skeleton({ className }: { className?: string }) {
  return <div className={`animate-pulse rounded-md bg-slate-200 dark:bg-slate-800 ${className ?? ''}`} />
}

export function ReportPage(flow: ReportFlow) {
  const { status, error, metrics, selectedRunId, setSelectedRunId, report, loadDemo, upload, generate } = flow
  const selectedRun = metrics?.runs.find((r) => r.run_id === selectedRunId) ?? metrics?.runs[0]

  return (
    <>
      <header className="mx-auto max-w-5xl px-4 pt-12 pb-8 text-center">
        <h1 className="text-3xl font-semibold tracking-tight text-slate-900 sm:text-4xl dark:text-slate-100">
          Turn electrochemical experiment data into reports in seconds
        </h1>
        <p className="mx-auto mt-3 max-w-2xl text-slate-600 dark:text-slate-400">
          Upload PFAS electrochemical oxidation experiment data and get an AI-generated lab report with
          degradation kinetics, energy analysis, and anomaly detection.
        </p>
      </header>

      <main className="mx-auto max-w-5xl px-4 pb-20">
        {!metrics && status !== 'loading-metrics' && (
          <div className="flex flex-col items-center gap-4 rounded-xl border border-dashed border-slate-300 bg-white p-12 text-center dark:border-slate-700 dark:bg-slate-900">
            <button
              type="button"
              onClick={loadDemo}
              className="rounded-lg bg-teal-600 px-6 py-3 text-base font-medium text-white shadow-sm hover:bg-teal-700"
            >
              Load demo dataset
            </button>
            <p className="text-sm text-slate-500 dark:text-slate-400">
              3 runs · PFOA / PFOS / PFHxS · 90-minute electrochemical oxidation experiments
            </p>
            <label className="mt-2 cursor-pointer text-xs text-slate-400 underline hover:text-slate-600 dark:hover:text-slate-300">
              or upload your own CSV
              <input
                type="file"
                accept=".csv"
                className="hidden"
                onChange={(e) => e.target.files?.[0] && upload(e.target.files[0])}
              />
            </label>
          </div>
        )}

        {status === 'loading-metrics' && (
          <div className="space-y-4">
            <Skeleton className="h-32 w-full" />
            <div className="grid gap-4 sm:grid-cols-3">
              <Skeleton className="h-40" />
              <Skeleton className="h-40" />
              <Skeleton className="h-40" />
            </div>
          </div>
        )}

        {error && (
          <div className="mt-4 rounded-md border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700 dark:border-red-900 dark:bg-red-950 dark:text-red-300">
            {error}
          </div>
        )}

        {metrics && selectedRun && (
          <div className="space-y-8">
            <section>
              <h2 className="mb-3 text-lg font-semibold">Experiment runs</h2>
              <div className="grid gap-4 sm:grid-cols-3">
                {metrics.runs.map((run) => (
                  <RunSummaryCard
                    key={run.run_id}
                    run={run}
                    selected={run.run_id === selectedRun.run_id}
                    onSelect={() => setSelectedRunId(run.run_id)}
                  />
                ))}
              </div>
            </section>

            <div className="grid gap-8 lg:grid-cols-2">
              <div className="space-y-6">
                <section className="rounded-lg border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900">
                  <h3 className="mb-2 text-sm font-semibold text-slate-700 dark:text-slate-300">
                    Degradation curves — {selectedRun.run_id}
                  </h3>
                  <DegradationCurveChart run={selectedRun} />
                </section>

                <section className="rounded-lg border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900">
                  <h3 className="mb-2 text-sm font-semibold text-slate-700 dark:text-slate-300">
                    Degradation efficiency — run comparison
                  </h3>
                  <ComparisonBarChart runs={metrics.runs} metricKey="degradation_efficiency_pct" unit="%" />
                </section>

                <section className="rounded-lg border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900">
                  <h3 className="mb-2 text-sm font-semibold text-slate-700 dark:text-slate-300">
                    Energy per order of magnitude removed (EEO) — run comparison
                  </h3>
                  <ComparisonBarChart runs={metrics.runs} metricKey="eeo_kwh_per_m3_per_order" unit="kWh/m³/order" />
                </section>

                <section className="rounded-lg border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900">
                  <h3 className="mb-2 text-sm font-semibold text-slate-700 dark:text-slate-300">
                    Anomalies — {selectedRun.run_id}
                  </h3>
                  <AnomalyList anomalies={selectedRun.anomalies} />
                </section>
              </div>

              <div>
                {!report && status !== 'loading-report' && (
                  <button
                    type="button"
                    onClick={generate}
                    className="w-full rounded-lg bg-teal-600 px-6 py-3 text-base font-medium text-white shadow-sm hover:bg-teal-700"
                  >
                    Generate AI Report
                  </button>
                )}
                {status === 'loading-report' && (
                  <div className="space-y-2">
                    <Skeleton className="h-6 w-1/3" />
                    <Skeleton className="h-64 w-full" />
                  </div>
                )}
                {report && <ReportPane report={report} />}
              </div>
            </div>
          </div>
        )}
      </main>
    </>
  )
}
