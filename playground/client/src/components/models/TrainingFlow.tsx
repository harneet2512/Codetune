import { ArrowDown } from 'lucide-react'
import { colors, fonts } from '../../theme/tokens'
import { models } from '../../data/models'
import { ModelCard } from './ModelCard'

const flowSteps = [
  { label: '→ SFT training (250 traces, 2 epochs)' },
  { label: '→ LoRA merge → GRPO (300 steps)' },
]

function FlowArrow({ label }: { label: string }) {
  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        padding: '8px 0',
        gap: 4,
      }}
    >
      <ArrowDown size={16} color={colors.textFaintest} />
      <div
        style={{
          fontSize: 10,
          fontFamily: fonts.mono,
          color: colors.textFaintest,
        }}
      >
        {label}
      </div>
    </div>
  )
}

export function TrainingFlow() {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 0 }}>
      <ModelCard model={models[0]} />
      <FlowArrow label={flowSteps[0].label} />
      <ModelCard model={models[1]} />
      <FlowArrow label={flowSteps[1].label} />
      <ModelCard model={models[2]} />
    </div>
  )
}
