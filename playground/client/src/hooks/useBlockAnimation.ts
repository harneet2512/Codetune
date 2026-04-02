import { useState, useRef, useCallback, useEffect } from 'react'
import type { Block } from '../data/blocks'

// ---------------------------------------------------------------------------
// Speed constants
// ---------------------------------------------------------------------------
const BASE_CHAR_DELAY = 20        // ms per character
const PAUSE_BETWEEN_BLOCKS = 400  // ms between blocks
const PAUSE_TOOL_RESULT = 600     // extra pause before result child of tool
const PAUSE_FIELD_SWITCH = 100    // pause between title → detail

// ---------------------------------------------------------------------------
// Config & return types
// ---------------------------------------------------------------------------

export interface BlockAnimationConfig {
  speedMultiplier: number  // 1.0 = fast (base), 2.0 = medium (sft), 3.3 = slow (grpo)
}

export interface UseBlockAnimationReturn {
  completedBlocks: Block[]
  activeBlock: Block | null
  activeField: 'title' | 'detail'
  charIndex: number
  isAnimating: boolean
  visibleBlockIds: Set<string>
  sourceCount: number
  sourceTags: string[]
  start: () => void
  stop: () => void
  reset: () => void
  showAll: () => void
}

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

export function useBlockAnimation(
  blocks: Block[],
  config: BlockAnimationConfig = { speedMultiplier: 1.0 },
): UseBlockAnimationReturn {
  const [completedBlocks, setCompletedBlocks] = useState<Block[]>([])
  const [activeBlock, setActiveBlock] = useState<Block | null>(null)
  const [activeField, setActiveField] = useState<'title' | 'detail'>('title')
  const [charIndex, setCharIndex] = useState(0)
  const [isAnimating, setIsAnimating] = useState(false)
  const [visibleBlockIds, setVisibleBlockIds] = useState<Set<string>>(new Set())
  const [sourceTags, setSourceTags] = useState<string[]>([])

  const rafId = useRef<number | null>(null)
  const lastTickTime = useRef(0)

  const animState = useRef({
    blockIdx: 0,
    charIdx: 0,
    field: 'title' as 'title' | 'detail',
    completed: [] as Block[],
    visible: new Set<string>(),
    sources: [] as string[],
    pausing: false,
    pauseUntil: 0,
    running: false,
  })

  const blocksRef = useRef(blocks)
  blocksRef.current = blocks

  const configRef = useRef(config)
  configRef.current = config

  const tick = useCallback((now: number) => {
    const state = animState.current
    const allBlocks = blocksRef.current
    const mult = configRef.current.speedMultiplier

    if (!state.running) return

    // Handle pause
    if (state.pausing) {
      if (now < state.pauseUntil) {
        rafId.current = requestAnimationFrame(tick)
        return
      }
      state.pausing = false
    }

    // Check if all blocks done
    if (state.blockIdx >= allBlocks.length) {
      state.running = false
      setIsAnimating(false)
      setActiveBlock(null)
      return
    }

    const block = allBlocks[state.blockIdx]
    const currentText = state.field === 'title' ? block.title : (block.detail ?? '')

    // Make block visible as soon as we start it
    if (!state.visible.has(block.id)) {
      state.visible = new Set(state.visible)
      state.visible.add(block.id)
      setVisibleBlockIds(new Set(state.visible))
      setActiveBlock(block)
      setActiveField('title')
      setCharIndex(0)
    }

    // Advance characters
    const charDelay = BASE_CHAR_DELAY * mult
    if (!lastTickTime.current) lastTickTime.current = now
    const elapsed = now - lastTickTime.current

    if (elapsed >= charDelay) {
      lastTickTime.current = now
      state.charIdx++
      setCharIndex(state.charIdx)

      // Check if current field is done
      if (state.charIdx >= currentText.length) {
        if (state.field === 'title' && block.detail) {
          // Switch to detail
          state.field = 'detail'
          state.charIdx = 0
          state.pausing = true
          state.pauseUntil = now + PAUSE_FIELD_SWITCH * mult
          setActiveField('detail')
          setCharIndex(0)
        } else {
          // Block complete
          state.completed = [...state.completed, block]
          setCompletedBlocks([...state.completed])

          // Track sources
          if (block.sourceTag && !state.sources.includes(block.sourceTag)) {
            state.sources = [...state.sources, block.sourceTag]
            setSourceTags([...state.sources])
          }

          // Move to next block
          state.blockIdx++
          state.charIdx = 0
          state.field = 'title'
          lastTickTime.current = 0
          setActiveBlock(null)

          // Determine pause duration
          const nextBlock = allBlocks[state.blockIdx]
          let pauseDuration = PAUSE_BETWEEN_BLOCKS * mult
          if (nextBlock?.parentId) {
            pauseDuration = PAUSE_TOOL_RESULT * mult
          }

          state.pausing = true
          state.pauseUntil = now + pauseDuration
        }
      }
    }

    rafId.current = requestAnimationFrame(tick)
  }, [])

  const cancelFrame = useCallback(() => {
    if (rafId.current !== null) {
      cancelAnimationFrame(rafId.current)
      rafId.current = null
    }
  }, [])

  const start = useCallback(() => {
    cancelFrame()
    const state = animState.current
    state.blockIdx = 0
    state.charIdx = 0
    state.field = 'title'
    state.completed = []
    state.visible = new Set()
    state.sources = []
    state.pausing = false
    state.pauseUntil = 0
    state.running = true
    lastTickTime.current = 0

    setCompletedBlocks([])
    setActiveBlock(null)
    setActiveField('title')
    setCharIndex(0)
    setIsAnimating(true)
    setVisibleBlockIds(new Set())
    setSourceTags([])

    rafId.current = requestAnimationFrame(tick)
  }, [cancelFrame, tick])

  const stop = useCallback(() => {
    cancelFrame()
    animState.current.running = false
    setIsAnimating(false)
  }, [cancelFrame])

  const reset = useCallback(() => {
    cancelFrame()
    const state = animState.current
    state.blockIdx = 0
    state.charIdx = 0
    state.field = 'title'
    state.completed = []
    state.visible = new Set()
    state.sources = []
    state.pausing = false
    state.running = false
    lastTickTime.current = 0

    setCompletedBlocks([])
    setActiveBlock(null)
    setActiveField('title')
    setCharIndex(0)
    setIsAnimating(false)
    setVisibleBlockIds(new Set())
    setSourceTags([])
  }, [cancelFrame])

  const showAll = useCallback(() => {
    cancelFrame()
    const allBlocks = blocksRef.current
    const state = animState.current
    state.running = false
    state.blockIdx = allBlocks.length
    state.completed = [...allBlocks]

    const allVisible = new Set(allBlocks.map(b => b.id))
    state.visible = allVisible

    const allSources = allBlocks
      .filter(b => b.sourceTag)
      .map(b => b.sourceTag!)
      .filter((v, i, a) => a.indexOf(v) === i)
    state.sources = allSources

    setCompletedBlocks([...allBlocks])
    setActiveBlock(null)
    setIsAnimating(false)
    setVisibleBlockIds(allVisible)
    setSourceTags(allSources)
  }, [cancelFrame])

  // Reset when blocks change
  useEffect(() => {
    showAll()
  }, [blocks]) // eslint-disable-line react-hooks/exhaustive-deps

  // Cleanup on unmount
  useEffect(() => {
    return cancelFrame
  }, [cancelFrame])

  return {
    completedBlocks,
    activeBlock,
    activeField,
    charIndex,
    isAnimating,
    visibleBlockIds,
    sourceCount: sourceTags.length,
    sourceTags,
    start,
    stop,
    reset,
    showAll,
  }
}
