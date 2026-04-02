import { colors, fonts } from '../theme/tokens'
import { metrics } from '../data/eval'
import { MetricCard } from '../components/eval/MetricCard'
import { AccuracyTable } from '../components/eval/AccuracyTable'
import { TrainingCurve } from '../components/eval/TrainingCurve'
import { EvalHistory } from '../components/eval/EvalHistory'
import { FailureTaxonomy } from '../components/eval/FailureTaxonomy'
import { SuiteHeatmap } from '../components/eval/SuiteHeatmap'

export function EvalPage() {
  return (
    <div style={{ padding: '24px 28px', maxWidth: 1200 }}>
      {/* Header */}
      <div style={{ marginBottom: 24 }}>
        <h1
          style={{
            fontFamily: fonts.mono,
            fontSize: 18,
            fontWeight: 800,
            color: colors.text,
            margin: '0 0 4px 0',
          }}
        >
          Eval Dashboard
        </h1>
        <p style={{ color: colors.textMuted, fontSize: 12, fontFamily: fonts.mono, margin: 0 }}>
          Training metrics, category breakdowns, and eval run history.
        </p>
      </div>

      {/* Metric Cards */}
      <div style={{ display: 'flex', gap: 14, marginBottom: 20 }}>
        {metrics.map((m) => (
          <MetricCard
            key={m.label}
            label={m.label}
            value={m.value}
            change={m.change}
            changeColor={m.changeColor}
            sparklineData={m.sparkline}
            color={m.color}
          />
        ))}
      </div>

      {/* Accuracy Table */}
      <div style={{ marginBottom: 20 }}>
        <AccuracyTable />
      </div>

      {/* Training Progress + Failure Taxonomy side by side */}
      <div style={{ display: 'flex', gap: 14, marginBottom: 20 }}>
        <div style={{ flex: 1 }}>
          <TrainingCurve />
        </div>
        <div style={{ flex: 1 }}>
          <FailureTaxonomy />
        </div>
      </div>

      {/* Eval History */}
      <div style={{ marginBottom: 20 }}>
        <EvalHistory />
      </div>

      {/* Suite Heatmap */}
      <div style={{ marginBottom: 20 }}>
        <SuiteHeatmap />
      </div>
    </div>
  )
}
