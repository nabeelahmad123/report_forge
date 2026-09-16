import { CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { buildRunCurveData } from '../lib/curves'
import { chartInk, compoundColor, COMPOUND_COLOR_ORDER } from '../lib/colors'
import { useIsDark } from '../lib/useIsDark'
import type { RunMetrics } from '../types'

export function DegradationCurveChart({ run }: { run: RunMetrics }) {
  const isDark = useIsDark()
  const ink = chartInk(isDark)
  const data = buildRunCurveData(run)
  const compounds = run.compounds
    .filter((c) => c.decay_rate_k_per_min != null && !c.insufficient_data)
    .map((c) => c.compound)
    .sort((a, b) => COMPOUND_COLOR_ORDER.indexOf(a as never) - COMPOUND_COLOR_ORDER.indexOf(b as never))

  if (compounds.length === 0) {
    return <p className="text-sm text-slate-500 dark:text-slate-400">No fitted decay curve available for this run.</p>
  }

  return (
    <div className="h-64 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data} margin={{ top: 8, right: 16, bottom: 0, left: 0 }}>
          <CartesianGrid strokeDasharray="0" stroke={ink.gridline} vertical={false} />
          <XAxis
            dataKey="t"
            stroke={ink.axis}
            tick={{ fill: ink.mutedText, fontSize: 12 }}
            label={{ value: 'Minutes', position: 'insideBottom', offset: -2, fill: ink.mutedText, fontSize: 12 }}
          />
          <YAxis
            stroke={ink.axis}
            tick={{ fill: ink.mutedText, fontSize: 12 }}
            label={{ value: 'µg/L', angle: -90, position: 'insideLeft', fill: ink.mutedText, fontSize: 12 }}
          />
          <Tooltip
            contentStyle={{ fontSize: 12, borderRadius: 6, color: ink.primaryText }}
            itemStyle={{ color: ink.primaryText }}
            labelStyle={{ color: ink.secondaryText }}
            formatter={(value, name) => [`${Number(value).toFixed(2)} µg/L`, name]}
            labelFormatter={(t) => `t = ${t} min`}
          />
          <Legend
            wrapperStyle={{ fontSize: 12 }}
            formatter={(value) => <span style={{ color: ink.secondaryText }}>{value}</span>}
          />
          {compounds.map((compound) => (
            <Line
              key={compound}
              type="monotone"
              dataKey={compound}
              stroke={compoundColor(compound, isDark)}
              strokeWidth={2}
              dot={false}
              isAnimationActive={false}
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}
