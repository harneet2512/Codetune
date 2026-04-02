import { useState, useCallback, useEffect } from 'react'
import { tasks } from '../data/tasks'
import { getBlocksForTask, type Block } from '../data/blocks'
import { useBlockAnimation } from '../hooks/useBlockAnimation'
import { TaskTabs } from '../components/playground/TaskTabs'
import { PromptHero } from '../components/playground/PromptHero'
import { ViewTabBar } from '../components/playground/ViewTabBar'
import { ModelColumn } from '../components/playground/ModelColumn'
import { colors, fonts } from '../theme/tokens'
import type { ViewMode, ModelKey } from '../types/playground'
import type { AppMode } from '../hooks/useAppMode'

const MODELS: ModelKey[] = ['base', 'sft', 'grpo']

// Placeholder trace for custom mode
const customTrace = {
  verdict: 'partial' as const,
  correct: false,
  tool_calls_used: 0,
  optimal_tool_calls: 0,
  steps: 0,
  restraint: 'n/a',
  recovery: 'n/a',
  behaviors_detected: [] as string[],
  confidence: 'n/a',
  evidence_count: 0,
  summary: 'Custom prompt — run with live model for real traces',
  raw_trace: '<think>Custom prompt mode. Connect a live model endpoint to generate real traces.</think>',
  nodes: [],
}

export function PlaygroundPage({ appMode = 'demo' }: { appMode?: AppMode }) {
  const isLive = appMode === 'live'
  const [activeTaskId, setActiveTaskId] = useState(tasks[0].id)
  const [viewMode, setViewMode] = useState<ViewMode>('blocks')
  const [isRunning, setIsRunning] = useState(false)
  const [customPrompt, setCustomPrompt] = useState('')
  const [isCustomMode, setIsCustomMode] = useState(false)

  const task = tasks.find(t => t.id === activeTaskId) || tasks[0]

  // Get blocks for each model
  const getBlocks = (model: ModelKey): Block[] => {
    if (isCustomMode) return getBlocksForTask('__custom__', model)
    return getBlocksForTask(task.id, model)
  }

  const getTrace = (model: ModelKey) => {
    if (isCustomMode) return customTrace
    return task.traces[model] || customTrace
  }

  // Three independent block animation hooks with different speeds
  const baseAnim = useBlockAnimation(getBlocks('base'), { speedMultiplier: 1.0 })
  const sftAnim = useBlockAnimation(getBlocks('sft'), { speedMultiplier: 2.0 })
  const grpoAnim = useBlockAnimation(getBlocks('grpo'), { speedMultiplier: 3.3 })
  const animMap = { base: baseAnim, sft: sftAnim, grpo: grpoAnim }

  // Show all content instantly on task change
  useEffect(() => {
    baseAnim.showAll()
    sftAnim.showAll()
    grpoAnim.showAll()
    setIsRunning(false)
  }, [activeTaskId, isCustomMode]) // eslint-disable-line react-hooks/exhaustive-deps

  const handleRun = useCallback(() => {
    if (isRunning) return
    setIsRunning(true)
    setViewMode('blocks')
    baseAnim.start()
    sftAnim.start()
    grpoAnim.start()
  }, [isRunning, baseAnim, sftAnim, grpoAnim])

  const handleReset = useCallback(() => {
    setIsRunning(false)
    baseAnim.showAll()
    sftAnim.showAll()
    grpoAnim.showAll()
  }, [baseAnim, sftAnim, grpoAnim])

  // Auto-stop when all done
  useEffect(() => {
    if (isRunning && !baseAnim.isAnimating && !sftAnim.isAnimating && !grpoAnim.isAnimating) {
      setIsRunning(false)
    }
  }, [isRunning, baseAnim.isAnimating, sftAnim.isAnimating, grpoAnim.isAnimating])

  const handleTaskSelect = useCallback((id: string) => {
    if (id === '__custom__') {
      setIsCustomMode(true)
    } else {
      setIsCustomMode(false)
      setActiveTaskId(id)
    }
  }, [])

  const handleCustomSubmit = useCallback(() => {
    if (!customPrompt.trim()) return
    handleRun()
  }, [customPrompt, handleRun])

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      {/* Live mode banner */}
      {isLive && (
        <div style={{
          padding: '8px 16px', display: 'flex', alignItems: 'center', gap: 8,
          background: 'rgba(52,211,153,0.06)', borderLeft: `3px solid ${colors.green}`,
          fontSize: 10, fontFamily: fonts.mono, color: colors.textSecondary, flexShrink: 0,
        }}>
          Live mode. Your GRPO model runs on HuggingFace. Tool calls hit real APIs.
        </div>
      )}

      <TaskTabs
        tasks={tasks.map(t => ({ id: t.id, title: t.title }))}
        activeId={isCustomMode ? '__custom__' : task.id}
        onSelect={handleTaskSelect}
      />

      <PromptHero
        prompt={task.prompt}
        difficulty={isCustomMode ? 'Custom' : task.difficulty}
        category={isCustomMode ? 'Free Input' : task.category}
        isRunning={isRunning}
        isCustom={isCustomMode}
        customPrompt={customPrompt}
        onRun={handleRun}
        onReset={handleReset}
        onCustomPromptChange={setCustomPrompt}
        onCustomSubmit={handleCustomSubmit}
      />

      <ViewTabBar activeTab={viewMode} onChange={setViewMode} />

      <div style={{ flex: 1, display: 'flex', overflow: 'hidden', gap: 8, padding: 8 }}>
        {MODELS.map((model) => (
          <ModelColumn
            key={`${isCustomMode ? 'custom' : task.id}-${model}`}
            modelKey={model}
            trace={getTrace(model)}
            blocks={getBlocks(model)}
            viewMode={viewMode}
            blockState={animMap[model]}
          />
        ))}
      </div>
    </div>
  )
}
