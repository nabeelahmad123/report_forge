import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { chartInk, compoundColor, COMPOUND_COLOR_ORDER } from '../lib/colors'
import { useIsDark } from '../lib/useIsDark'
import type { CompoundMetrics, RunMetrics } from '../types'

type MetricKey = 'degradation_efficiency_pct' | 'eeo_kwh_per_m3_per_order'

export function ComparisonBarChart({
  runs,
  metricKey,
  unit,
}: {
  runs: RunMetrics[]
  metricKey: MetricKey
  unit: string
}) {
  const isDark = useIsDark()
  const ink = chartInk(isDark)
  const compoundsPresent = COMPOUND_COLOR_ORDER.filter((compound) =>
    runs.some((r) => r.compounds.some((c) => c.compound === compound)),
  )

  const data = runs.map((run) => {
    const row: Record<string, string | number> = { run_id: run.run_id }
    for (const compound of compoundsPresent) {
      const c = run.compounds.find((c): c is CompoundMetrics => c.compound === compound)
      const value = c?.[metricKey]
      if (value != null) row[compound] = Number(value.toFixed(2))
    }
    return row
  })

  return (
    <div className="h-64 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} margin={{ top: 8, right: 16, bottom: 0, left: 0 }} barGap={2}>
          <CartesianGrid strokeDasharray="0" stroke={ink.gridline} vertical={false} />
          <XAxis dataKey="run_id" stroke={ink.axis} tick={{ fill: ink.mutedText, fontSize: 11 }} />
          <YAxis
            stroke={ink.axis}
            tick={{ fill: ink.mutedText, fontSize: 12 }}
            label={{ value: unit, angle: -90, position: 'insideLeft', fill: ink.mutedText, fontSize: 12 }}
          />
          <Tooltip
            contentStyle={{ fontSize: 12, borderRadius: 6, color: ink.primaryText }}
            itemStyle={{ color: ink.primaryText }}
            labelStyle={{ color: ink.secondaryText }}
            formatter={(value) => `${value} ${unit}`}
          />
          <Legend
            wrapperStyle={{ fontSize: 12 }}
            formatter={(value) => <span style={{ color: ink.secondaryText }}>{value}</span>}
          />
          {compoundsPresent.map((compound) => (
            <Bar
              key={compound}
              dataKey={compound}
              fill={compoundColor(compound, isDark)}
              maxBarSize={24}
              radius={[4, 4, 0, 0]}
              isAnimationActive={false}
            />
          ))}
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
