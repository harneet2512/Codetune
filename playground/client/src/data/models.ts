export interface ModelDef {
  key: string
  label: string
  fullLabel: string
  tag: string
  tagColor: string
  desc: string
  color: string
  bg: string
  accuracy: number
  toolPrecision: number
  restraint: number
}

export const models: ModelDef[] = [
  {
    key: 'base',
    label: 'Qwen 2.5 7B',
    fullLabel: 'Qwen 2.5 7B',
    tag: 'BASE',
    tagColor: '#6b6574',
    desc: 'Unmodified base model. 8% tool accuracy.',
    color: '#f87171',
    bg: 'rgba(248,113,113,0.08)',
    accuracy: 8,
    toolPrecision: 12,
    restraint: 15,
  },
  {
    key: 'sft',
    label: 'Qwen 2.5 7B + SFT',
    fullLabel: 'Qwen 2.5 7B + SFT',
    tag: 'SFT',
    tagColor: '#fbbf24',
    desc: '250 expert traces, QLoRA r=64, 2 epochs on Modal A10G.',
    color: '#fbbf24',
    bg: 'rgba(251,191,36,0.08)',
    accuracy: 60,
    toolPrecision: 85,
    restraint: 60,
  },
  {
    key: 'grpo',
    label: 'Qwen 2.5 7B + GRPO',
    fullLabel: 'Qwen 2.5 7B + GRPO',
    tag: 'GRPO',
    tagColor: '#34d399',
    desc: '300 steps, 8 gen/prompt, β=0. Multi-signal reward.',
    color: '#34d399',
    bg: 'rgba(52,211,153,0.08)',
    accuracy: 62,
    toolPrecision: 94,
    restraint: 85,
  },
]

export function getModel(key: string): ModelDef | undefined {
  return models.find((m) => m.key === key)
}
