export interface Metric {
  label: string
  value: string
  change: string
  changeColor: string
  sparkline: number[]
  color: string
}

export interface Category {
  name: string
  tasks: number
  base: number
  sft: number
  grpo: number
}

export interface EvalRun {
  runId: string
  model: string
  suite: string
  tasks: number
  accuracy: number
  toolPrecision: number
  restraint: number
  duration: string
  timestamp: string
}

export interface FailureMode {
  name: string
  count: number
  percentage: number
  example: string
}

export interface HeatmapRow {
  category: string
  values: number[] // [Base, SFT v1, SFT v2, GRPO v1, GRPO v2, GRPO v3]
}

export const metrics: Metric[] = [
  {
    label: 'Overall Accuracy',
    value: '62%',
    change: '↑ +54%',
    changeColor: '#34d399',
    sparkline: [8, 12, 28, 35, 42, 48, 53, 56, 58, 60, 60, 61, 61, 62, 62],
    color: '#34d399',
  },
  {
    label: 'Tool Precision',
    value: '94%',
    change: '↑ +82%',
    changeColor: '#a78bfa',
    sparkline: [12, 20, 45, 65, 80, 90, 94],
    color: '#a78bfa',
  },
  {
    label: 'Restraint Score',
    value: '85%',
    change: '↑ +70%',
    changeColor: '#fbbf24',
    sparkline: [15, 20, 30, 50, 65, 78, 85],
    color: '#fbbf24',
  },
  {
    label: 'Evidence Quality',
    value: '4.2/5',
    change: '↑ +3.8',
    changeColor: '#60a5fa',
    sparkline: [0.4, 0.8, 1.5, 2.5, 3.2, 3.8, 4.2],
    color: '#60a5fa',
  },
]

export const categories: Category[] = [
  { name: 'Single-tool', tasks: 100, base: 12, sft: 78, grpo: 80 },
  { name: 'Multi-step', tasks: 80, base: 4, sft: 55, grpo: 58 },
  { name: 'Cross-service', tasks: 50, base: 2, sft: 42, grpo: 45 },
  { name: 'Restraint', tasks: 20, base: 15, sft: 60, grpo: 85 },
]

export const evalHistory: EvalRun[] = [
  { runId: 'eval-047', model: 'GRPO v3', suite: 'full-250', tasks: 250, accuracy: 62, toolPrecision: 94, restraint: 85, duration: '142s', timestamp: '2 hours ago' },
  { runId: 'eval-046', model: 'SFT v2', suite: 'full-250', tasks: 250, accuracy: 60, toolPrecision: 85, restraint: 60, duration: '138s', timestamp: '5 hours ago' },
  { runId: 'eval-045', model: 'Base', suite: 'full-250', tasks: 250, accuracy: 8, toolPrecision: 12, restraint: 15, duration: '89s', timestamp: '5 hours ago' },
  { runId: 'eval-044', model: 'GRPO v3', suite: 'restraint-20', tasks: 20, accuracy: 85, toolPrecision: 90, restraint: 85, duration: '12s', timestamp: 'yesterday' },
  { runId: 'eval-043', model: 'SFT v2', suite: 'restraint-20', tasks: 20, accuracy: 60, toolPrecision: 80, restraint: 60, duration: '11s', timestamp: 'yesterday' },
  { runId: 'eval-042', model: 'GRPO v2', suite: 'full-250', tasks: 250, accuracy: 59, toolPrecision: 88, restraint: 78, duration: '140s', timestamp: '2 days ago' },
  { runId: 'eval-041', model: 'GRPO v1', suite: 'full-250', tasks: 250, accuracy: 55, toolPrecision: 82, restraint: 70, duration: '136s', timestamp: '3 days ago' },
  { runId: 'eval-040', model: 'SFT v1', suite: 'full-250', tasks: 250, accuracy: 52, toolPrecision: 78, restraint: 45, duration: '135s', timestamp: '4 days ago' },
]

export const failureModes: FailureMode[] = [
  { name: 'Hallucinated tool', count: 3, percentage: 1.2, example: "Called `analyze_security()` which doesn't exist" },
  { name: 'Malformed arguments', count: 5, percentage: 2.0, example: 'Passed integer for `query` parameter expecting string' },
  { name: 'Wrong tool selection', count: 8, percentage: 3.2, example: 'Used `search_emails` when task required `search_files`' },
  { name: 'Premature termination', count: 12, percentage: 4.8, example: 'Answered after reading spec but before reading source code' },
  { name: 'Over-planning', count: 4, percentage: 1.6, example: 'Called 6 tools for a single-step lookup task' },
  { name: 'Missed restraint', count: 6, percentage: 2.4, example: "Called `search_pages` for 'What is HTTP 409?'" },
]

export const heatmapCheckpoints = ['Base', 'SFT v1', 'SFT v2', 'GRPO v1', 'GRPO v2', 'GRPO v3']

export const heatmapData: HeatmapRow[] = [
  { category: 'Single-tool', values: [12, 65, 78, 75, 78, 80] },
  { category: 'Multi-step', values: [4, 40, 55, 50, 54, 58] },
  { category: 'Cross-service', values: [2, 30, 42, 38, 42, 45] },
  { category: 'Restraint', values: [15, 35, 60, 65, 78, 85] },
]

export const trainingData = {
  labels: ['BASE', 'S1', 'S2', 'S3', 'S4', 'S5', 'S6', 'S7', 'S8', 'S9', 'S10', 'G1', 'G2', 'G3', 'G4'],
  values: [8, 12, 28, 35, 42, 48, 53, 56, 58, 60, 60, 61, 61, 62, 62],
}
