export interface ThinkingLine {
  type: 'think' | 'strong' | 'tool_call' | 'observe' | 'conclusion' | 'error' | 'separator'
  text: string
}

export interface TypingState {
  displayedLines: ThinkingLine[]
  currentLineIndex: number
  charIndex: number
  isAnimating: boolean
}

export type ViewMode = 'blocks' | 'raw' | 'flow'
export type ModelKey = 'base' | 'sft' | 'grpo'
