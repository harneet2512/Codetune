import { useState, useRef, useCallback, useEffect } from 'react';
import type { ThinkingLine } from '../data/thinking';

// ---------------------------------------------------------------------------
// Speed constants (milliseconds per character)
// ---------------------------------------------------------------------------
const SPEED_THINK = 25;       // thinking / strong lines — deliberate pace
const SPEED_STRUCTURED = 12;  // tool_call / observe lines — faster, machine-like
const SPEED_CONCLUSION = 20;  // conclusions typed slightly faster than thinking

const PAUSE_BETWEEN_LINES = 300; // ms pause after finishing a line
const PAUSE_AFTER_SEPARATOR = 150; // ms pause for separator (visual breath)

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function getCharDelay(lineType: ThinkingLine['type']): number {
  switch (lineType) {
    case 'tool_call':
    case 'observe':
      return SPEED_STRUCTURED;
    case 'conclusion':
      return SPEED_CONCLUSION;
    case 'think':
    case 'strong':
    case 'error':
    default:
      return SPEED_THINK;
  }
}

// ---------------------------------------------------------------------------
// Hook return type
// ---------------------------------------------------------------------------

export interface UseTypingAnimationReturn {
  /** Lines that have been fully typed so far */
  displayedLines: ThinkingLine[];
  /** Index of the line currently being typed (-1 if idle) */
  currentLineIndex: number;
  /** How many characters of the current line have been revealed */
  charIndex: number;
  /** Whether the animation is actively running */
  isAnimating: boolean;
  /** Begin typing from the start */
  start: () => void;
  /** Pause at the current position */
  stop: () => void;
  /** Clear all displayed content and reset to initial state */
  reset: () => void;
  /** Instantly show all lines (skip animation) */
  showAll: () => void;
}

// ---------------------------------------------------------------------------
// useTypingAnimation
// ---------------------------------------------------------------------------

export function useTypingAnimation(lines: ThinkingLine[]): UseTypingAnimationReturn {
  // -- State visible to React renders --
  const [displayedLines, setDisplayedLines] = useState<ThinkingLine[]>([]);
  const [currentLineIndex, setCurrentLineIndex] = useState(-1);
  const [charIndex, setCharIndex] = useState(0);
  const [isAnimating, setIsAnimating] = useState(false);

  // -- Refs for the animation loop (not triggering re-renders) --
  const rafId = useRef<number | null>(null);
  const lastTickTime = useRef(0);

  // Mutable animation state kept in a ref so the rAF callback always reads
  // the latest values without depending on React state (avoids stale closures).
  const animState = useRef({
    lineIdx: 0,
    charIdx: 0,
    completed: [] as ThinkingLine[],
    pausing: false,      // true while we are in a between-line pause
    pauseUntil: 0,       // timestamp when the pause ends
    running: false,
  });

  // Keep a stable ref to the lines array so the rAF loop sees updates.
  const linesRef = useRef(lines);
  linesRef.current = lines;

  // ------------------------------------------------------------------
  // Core animation frame callback
  // ------------------------------------------------------------------
  const tick = useCallback((now: number) => {
    const state = animState.current;
    const allLines = linesRef.current;

    if (!state.running) return;

    // -- Handle inter-line pause --
    if (state.pausing) {
      if (now < state.pauseUntil) {
        rafId.current = requestAnimationFrame(tick);
        return;
      }
      state.pausing = false;
    }

    // -- All lines done? --
    if (state.lineIdx >= allLines.length) {
      setIsAnimating(false);
      state.running = false;
      setCurrentLineIndex(-1);
      return;
    }

    const currentLine = allLines[state.lineIdx];

    // -- Separator lines have no text to type; just pause and advance --
    if (currentLine.type === 'separator') {
      state.completed = [...state.completed, currentLine];
      setDisplayedLines([...state.completed]);
      state.lineIdx += 1;
      state.charIdx = 0;
      setCurrentLineIndex(state.lineIdx);
      setCharIndex(0);

      // Start a pause
      state.pausing = true;
      state.pauseUntil = now + PAUSE_AFTER_SEPARATOR;
      rafId.current = requestAnimationFrame(tick);
      return;
    }

    const charDelay = getCharDelay(currentLine.type);

    // Advance characters based on elapsed time
    const elapsed = now - lastTickTime.current;
    if (elapsed < charDelay) {
      rafId.current = requestAnimationFrame(tick);
      return;
    }

    lastTickTime.current = now;

    const textLength = currentLine.text.length;

    if (state.charIdx < textLength) {
      // Advance one character
      state.charIdx += 1;
      setCharIndex(state.charIdx);
      setCurrentLineIndex(state.lineIdx);
    } else {
      // Line complete — push to displayed, start inter-line pause
      state.completed = [...state.completed, currentLine];
      setDisplayedLines([...state.completed]);
      state.lineIdx += 1;
      state.charIdx = 0;
      setCurrentLineIndex(state.lineIdx);
      setCharIndex(0);

      state.pausing = true;
      state.pauseUntil = now + PAUSE_BETWEEN_LINES;
    }

    rafId.current = requestAnimationFrame(tick);
  }, []);

  // ------------------------------------------------------------------
  // Controls
  // ------------------------------------------------------------------

  const cancelFrame = useCallback(() => {
    if (rafId.current !== null) {
      cancelAnimationFrame(rafId.current);
      rafId.current = null;
    }
  }, []);

  const start = useCallback(() => {
    cancelFrame();

    const state = animState.current;
    state.lineIdx = 0;
    state.charIdx = 0;
    state.completed = [];
    state.pausing = false;
    state.pauseUntil = 0;
    state.running = true;

    setDisplayedLines([]);
    setCurrentLineIndex(0);
    setCharIndex(0);
    setIsAnimating(true);

    lastTickTime.current = performance.now();
    rafId.current = requestAnimationFrame(tick);
  }, [cancelFrame, tick]);

  const stop = useCallback(() => {
    cancelFrame();
    animState.current.running = false;
    setIsAnimating(false);
  }, [cancelFrame]);

  const reset = useCallback(() => {
    cancelFrame();
    const state = animState.current;
    state.lineIdx = 0;
    state.charIdx = 0;
    state.completed = [];
    state.pausing = false;
    state.running = false;

    setDisplayedLines([]);
    setCurrentLineIndex(-1);
    setCharIndex(0);
    setIsAnimating(false);
  }, [cancelFrame]);

  const showAll = useCallback(() => {
    cancelFrame();
    const state = animState.current;
    state.running = false;
    state.lineIdx = linesRef.current.length;
    state.charIdx = 0;
    state.completed = [...linesRef.current];

    setDisplayedLines([...linesRef.current]);
    setCurrentLineIndex(-1);
    setCharIndex(0);
    setIsAnimating(false);
  }, [cancelFrame]);

  // ------------------------------------------------------------------
  // Cleanup on unmount
  // ------------------------------------------------------------------
  useEffect(() => {
    return () => {
      cancelFrame();
      animState.current.running = false;
    };
  }, [cancelFrame]);

  // Reset when lines input changes (e.g., switching tasks/models)
  useEffect(() => {
    reset();
  }, [lines, reset]);

  return {
    displayedLines,
    currentLineIndex,
    charIndex,
    isAnimating,
    start,
    stop,
    reset,
    showAll,
  };
}
