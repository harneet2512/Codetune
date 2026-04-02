import { colors } from '../theme/tokens'
import type { ModelKey } from '../types/playground'

// ---------------------------------------------------------------------------
// Block types
// ---------------------------------------------------------------------------

export type BlockType = 'think' | 'tool' | 'result' | 'answer' | 'failed' | 'partial'

export interface Block {
  id: string
  type: BlockType
  title: string
  detail?: string
  parentId?: string           // result blocks nest under tool blocks
  sourceTag?: string          // "→ Read spec" for knowledge accumulation
  referencesBlockId?: string  // draws connection line to referenced block
}

// ---------------------------------------------------------------------------
// Block styling
// ---------------------------------------------------------------------------

export interface BlockStyle {
  color: string
  bg: string
  icon: string
  badgeLabel: string
}

export const blockStyles: Record<BlockType, BlockStyle> = {
  think:   { color: colors.purple, bg: 'rgba(167,139,250,0.06)', icon: '◇', badgeLabel: 'THINK' },
  tool:    { color: colors.pink,   bg: 'rgba(244,114,182,0.06)', icon: '▸', badgeLabel: 'TOOL' },
  result:  { color: colors.green,  bg: 'rgba(52,211,153,0.06)',  icon: '●', badgeLabel: 'RESULT' },
  answer:  { color: colors.blue,   bg: 'rgba(96,165,250,0.06)',  icon: '✓', badgeLabel: 'ANSWER' },
  failed:  { color: colors.red,    bg: 'rgba(248,113,113,0.06)', icon: '✗', badgeLabel: 'FAILED' },
  partial: { color: colors.amber,  bg: 'rgba(251,191,36,0.06)',  icon: '!', badgeLabel: 'PARTIAL' },
}

export const blockBadgeBg: Record<BlockType, string> = {
  think:   'rgba(167,139,250,0.15)',
  tool:    'rgba(244,114,182,0.15)',
  result:  'rgba(52,211,153,0.15)',
  answer:  'rgba(96,165,250,0.15)',
  failed:  'rgba(248,113,113,0.15)',
  partial: 'rgba(251,191,36,0.15)',
}

// ---------------------------------------------------------------------------
// Block trace data per task per model
// ---------------------------------------------------------------------------

export const blockContent: Record<string, Record<ModelKey, Block[]>> = {
  'spec-audit': {
    base: [
      { id: 'b1', type: 'think', title: 'Generic security', detail: 'Auth middleware should check tokens. Standard stuff.' },
      { id: 'b2', type: 'failed', title: 'Ungrounded answer', detail: 'No evidence or citations. Guessed based on general knowledge.' },
    ],
    sft: [
      { id: 's1', type: 'think', title: 'Read sources', detail: 'I should read the spec and the middleware. Starting with the spec.' },
      { id: 's2', type: 'tool', title: 'Read spec', detail: 'Gets auth rules.' },
      { id: 's3', type: 'result', title: 'Rule surface', detail: 'Rules AUTH-001..004 apply. Algorithm, key, expiry, storage.', parentId: 's2', sourceTag: '→ Read spec' },
      { id: 's4', type: 'tool', title: 'Read middleware', detail: 'Inspects implementation code.' },
      { id: 's5', type: 'partial', title: 'Partial audit', detail: 'Found AUTH-001 (wrong algorithm) and AUTH-002 (hardcoded key). Missed AUTH-003 (expiry) and AUTH-004 (localStorage).' },
    ],
    grpo: [
      { id: 'g1', type: 'think', title: 'Exhaustive audit', detail: 'I will: 1) Read full spec, 2) Build checklist, 3) Read code, 4) Cross-reference every rule. Cannot skip steps.' },
      { id: 'g2', type: 'tool', title: 'Read spec', detail: 'Pulls all audit rules.' },
      { id: 'g3', type: 'result', title: 'Checklist', detail: 'AUTH-001..004 cover algorithm, key, expiry, and token storage. 4 rules total.', parentId: 'g2', sourceTag: '→ Read spec' },
      { id: 'g4', type: 'think', title: 'Planning cross-reference', detail: '4 rules extracted. Building checklist: [ ] AUTH-001 algorithm = RS256, [ ] AUTH-002 key from env, [ ] AUTH-003 expiry validation, [ ] AUTH-004 no localStorage. Now I need the source code.', referencesBlockId: 'g3' },
      { id: 'g5', type: 'tool', title: 'Read middleware', detail: 'Checks implementation against each rule.' },
      { id: 'g6', type: 'result', title: 'Code analysis', detail: 'Line 8: hardcoded key. Line 14: HS256. No exp check. Client uses localStorage.', parentId: 'g5', sourceTag: '→ Read code' },
      { id: 'g7', type: 'think', title: 'Cross-referencing', detail: 'Matching each rule: AUTH-001 HS256 ≠ RS256 FAIL. AUTH-002 hardcoded FAIL. AUTH-003 no expiry check FAIL. AUTH-004 localStorage FAIL. All 4 violated.', referencesBlockId: 'g6' },
      { id: 'g8', type: 'answer', title: 'Complete audit', detail: 'Cites all four violations with line numbers and remediation priority.' },
    ],
  },
  'incident-triage': {
    base: [
      { id: 'b1', type: 'think', title: 'Generic response', detail: 'Looks like a production issue. Check logs and restart the service.' },
      { id: 'b2', type: 'failed', title: 'No investigation', detail: 'Gave generic advice without looking at any data sources.' },
    ],
    sft: [
      { id: 's1', type: 'think', title: 'Check alerts', detail: 'I need to look at the monitoring alerts to understand the issue.' },
      { id: 's2', type: 'tool', title: 'Search emails', detail: 'Checks monitoring inbox for alerts.' },
      { id: 's3', type: 'result', title: 'Alert found', detail: 'CRITICAL: Payment service deploy failed. Health check timeout after 30s.', parentId: 's2', sourceTag: '→ Alerts' },
      { id: 's4', type: 'tool', title: 'Read commit history', detail: 'Looks at recent deploys.' },
      { id: 's5', type: 'result', title: 'Recent deploy', detail: 'd-4521 deployed 15min ago. Changed auth middleware and payment handler.', parentId: 's4', sourceTag: '→ Commits' },
      { id: 's6', type: 'partial', title: 'Partial triage', detail: 'Identified the failing deploy but did not verify which specific change caused the health check failure.' },
    ],
    grpo: [
      { id: 'g1', type: 'think', title: 'Systematic triage', detail: 'Need to: 1) Get alert details, 2) Find the deploy, 3) Read the diff, 4) Identify root cause, 5) Recommend action.' },
      { id: 'g2', type: 'tool', title: 'Search emails', detail: 'Checks monitoring inbox.' },
      { id: 'g3', type: 'result', title: 'Alert details', detail: 'Payment service health check timeout. Endpoint /health returned 503 after d-4521.', parentId: 'g2', sourceTag: '→ Alerts' },
      { id: 'g4', type: 'tool', title: 'Read commit history', detail: 'Finds the deploy commit.' },
      { id: 'g5', type: 'result', title: 'Deploy diff', detail: 'Commit abc123: changed auth middleware SECRET from env var to hardcoded string. Payment handler unchanged.', parentId: 'g4', sourceTag: '→ Commits' },
      { id: 'g6', type: 'think', title: 'Root cause identified', detail: 'The auth middleware change hardcoded the secret. Health check likely fails because token validation breaks with the new secret value.', referencesBlockId: 'g5' },
      { id: 'g7', type: 'tool', title: 'Read file', detail: 'Reads current auth middleware to confirm.' },
      { id: 'g8', type: 'result', title: 'Code confirms', detail: "Line 8: SECRET = 'sk_live_abc123' (hardcoded). Was process.env.AUTH_SECRET before.", parentId: 'g7', sourceTag: '→ Source' },
      { id: 'g9', type: 'answer', title: 'Complete triage', detail: 'Root cause: d-4521 hardcoded auth secret. Recommend: revert commit abc123, then fix auth middleware to use env var. Priority: P0.' },
    ],
  },
}

// Fallback: generate empty blocks for tasks not yet defined
const emptyBlocks: Record<ModelKey, Block[]> = {
  base: [
    { id: 'b1', type: 'think', title: 'Processing request', detail: 'Attempting to respond to the query.' },
    { id: 'b2', type: 'failed', title: 'Unstructured output', detail: 'Model failed to produce a structured trace.' },
  ],
  sft: [
    { id: 's1', type: 'think', title: 'Analyzing request', detail: 'Determining which tools to use.' },
    { id: 's2', type: 'tool', title: 'Search relevant data', detail: 'Searching available sources.' },
    { id: 's3', type: 'result', title: 'Data found', detail: 'Retrieved relevant information.', parentId: 's2', sourceTag: '→ Search' },
    { id: 's4', type: 'partial', title: 'Partial analysis', detail: 'Found some information but analysis is incomplete.' },
  ],
  grpo: [
    { id: 'g1', type: 'think', title: 'Systematic approach', detail: 'Planning a structured investigation with evidence gathering.' },
    { id: 'g2', type: 'tool', title: 'Gather primary source', detail: 'Reading the authoritative source.' },
    { id: 'g3', type: 'result', title: 'Primary data', detail: 'Extracted key facts from the primary source.', parentId: 'g2', sourceTag: '→ Primary' },
    { id: 'g4', type: 'think', title: 'Cross-reference plan', detail: 'Building a checklist from the primary data to verify against secondary sources.', referencesBlockId: 'g3' },
    { id: 'g5', type: 'tool', title: 'Verify against source', detail: 'Reading secondary source for verification.' },
    { id: 'g6', type: 'result', title: 'Verification data', detail: 'Found confirming evidence in secondary source.', parentId: 'g5', sourceTag: '→ Secondary' },
    { id: 'g7', type: 'answer', title: 'Complete analysis', detail: 'Comprehensive answer backed by multiple cross-referenced sources.' },
  ],
}

export function getBlocksForTask(taskId: string, model: ModelKey): Block[] {
  return blockContent[taskId]?.[model] ?? emptyBlocks[model]
}

// ---------------------------------------------------------------------------
// Recent calls (activity feed for connectors)
// ---------------------------------------------------------------------------

export interface RecentCall {
  tool: string
  latency: string
  timestamp: string
}

export const recentCalls: RecentCall[] = [
  { tool: 'github.read_file', latency: '34ms', timestamp: '2 min ago' },
  { tool: 'gmail.search_emails', latency: '28ms', timestamp: '5 min ago' },
  { tool: 'github.search_repos', latency: '41ms', timestamp: '8 min ago' },
  { tool: 'drive.read_document', latency: '36ms', timestamp: '12 min ago' },
]
