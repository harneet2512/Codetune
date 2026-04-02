export interface ToolParameter {
  name: string
  type: 'string' | 'integer' | 'boolean'
  required: boolean
  description: string
}

export interface ConnectorTool {
  name: string
  description: string
  parameters: ToolParameter[]
  exampleValues: Record<string, string>
  mockResponse: { success: boolean; data: string; latencyMs: number }
}

export interface Connector {
  service: string
  icon: string
  color: string
  connected: boolean
  description: string
  tools: ConnectorTool[]
  schema?: Record<string, unknown>
}

export const connectors: Connector[] = [
  {
    service: 'GitHub',
    icon: 'GitBranch',
    color: '#e2e0e6',
    connected: true,
    description: 'Repository search, file reading, PR management, commit history, and issue creation.',
    tools: [
      {
        name: 'search_repos',
        description: 'Search repositories by query, language, and sort criteria',
        parameters: [
          { name: 'query', type: 'string', required: true, description: 'Search query' },
          { name: 'language', type: 'string', required: false, description: 'Filter by language' },
          { name: 'sort', type: 'string', required: false, description: 'Sort by: stars, forks, updated' },
        ],
        exampleValues: { query: 'auth middleware', language: 'typescript', sort: 'stars' },
        mockResponse: {
          success: true,
          latencyMs: 230,
          data: JSON.stringify({
            results: [
              { name: 'acme/api-server', description: 'Core API with auth middleware', stars: 342, language: 'TypeScript', updated: '2 days ago' },
              { name: 'acme/auth-service', description: 'Standalone authentication service', stars: 128, language: 'TypeScript', updated: '1 week ago' },
            ],
            total_count: 2,
          }, null, 2),
        },
      },
      {
        name: 'read_file',
        description: 'Read file contents at a specific path in a repository',
        parameters: [
          { name: 'repo', type: 'string', required: true, description: 'Repository in owner/repo format' },
          { name: 'path', type: 'string', required: true, description: 'File path within the repository' },
        ],
        exampleValues: { repo: 'acme/api-server', path: 'src/middleware/auth.js' },
        mockResponse: {
          success: true,
          latencyMs: 180,
          data: `const jwt = require('jsonwebtoken');
const SECRET = 'sk_live_abc123';

module.exports = function authenticate(req, res, next) {
  const token = req.headers.authorization?.split(' ')[1];
  if (!token) return res.status(401).json({ error: 'Missing token' });

  try {
    const decoded = jwt.verify(token, SECRET, { algorithms: ['HS256'] });
    res.locals.token = decoded;
    next();
  } catch (err) {
    return res.status(403).json({ error: 'Invalid token' });
  }
};`,
        },
      },
      {
        name: 'list_pull_requests',
        description: 'List pull requests filtered by status, author, or label',
        parameters: [
          { name: 'repo', type: 'string', required: true, description: 'Repository in owner/repo format' },
          { name: 'state', type: 'string', required: false, description: 'Filter: open, closed, all' },
        ],
        exampleValues: { repo: 'acme/api-server', state: 'open' },
        mockResponse: {
          success: true,
          latencyMs: 210,
          data: JSON.stringify({ pull_requests: [{ number: 142, title: 'Fix auth middleware RS256 migration', author: 'jchen', status: 'open', created: '3 hours ago' }], total: 1 }, null, 2),
        },
      },
      {
        name: 'get_commit_history',
        description: 'Get recent commits for a branch with diff summaries',
        parameters: [
          { name: 'repo', type: 'string', required: true, description: 'Repository in owner/repo format' },
          { name: 'branch', type: 'string', required: false, description: 'Branch name (default: main)' },
        ],
        exampleValues: { repo: 'acme/api-server', branch: 'main' },
        mockResponse: {
          success: true,
          latencyMs: 190,
          data: JSON.stringify({ commits: [{ sha: 'abc123', message: 'fix: hardcode auth secret for staging', author: 'deploy-bot', date: '15 min ago' }] }, null, 2),
        },
      },
      {
        name: 'create_issue',
        description: 'Create a new issue with title, body, and optional labels',
        parameters: [
          { name: 'repo', type: 'string', required: true, description: 'Repository in owner/repo format' },
          { name: 'title', type: 'string', required: true, description: 'Issue title' },
          { name: 'body', type: 'string', required: false, description: 'Issue body (markdown)' },
        ],
        exampleValues: { repo: 'acme/api-server', title: 'AUTH-001: Migrate to RS256', body: 'Spec requires RS256, currently using HS256.' },
        mockResponse: {
          success: true,
          latencyMs: 320,
          data: JSON.stringify({ issue: { number: 89, title: 'AUTH-001: Migrate to RS256', url: 'https://github.com/acme/api-server/issues/89', created: 'just now' } }, null, 2),
        },
      },
    ],
    schema: {
      name: 'search_repos',
      description: 'Search repositories by query, language, and sort criteria',
      parameters: {
        type: 'object',
        properties: {
          query: { type: 'string', description: 'Search query' },
          language: { type: 'string', description: 'Filter by language' },
          sort: { type: 'string', enum: ['stars', 'forks', 'updated'] },
        },
        required: ['query'],
      },
    },
  },
  {
    service: 'Gmail',
    icon: 'Mail',
    color: '#ea4335',
    connected: true,
    description: 'Email search, reading, composing, and thread management.',
    tools: [
      {
        name: 'search_emails',
        description: 'Search emails by sender, subject, date range, or keywords',
        parameters: [
          { name: 'query', type: 'string', required: true, description: 'Search query string' },
          { name: 'from', type: 'string', required: false, description: 'Filter by sender email' },
        ],
        exampleValues: { query: 'deployment failure', from: 'alerts@monitoring.io' },
        mockResponse: {
          success: true,
          latencyMs: 280,
          data: JSON.stringify({
            emails: [{ id: 'msg_8f2a', from: 'alerts@monitoring.io', subject: 'CRITICAL: Payment service deploy failed', snippet: 'Deploy d-4521 failed at rollout stage 2/3. Error: health check timeout after 30s...', date: '2025-03-28T14:02:00Z', unread: true }],
            total: 1,
          }, null, 2),
        },
      },
      {
        name: 'read_email',
        description: 'Read full email content including headers and attachments',
        parameters: [
          { name: 'id', type: 'string', required: true, description: 'Email message ID' },
        ],
        exampleValues: { id: 'msg_8f2a' },
        mockResponse: {
          success: true,
          latencyMs: 150,
          data: JSON.stringify({ id: 'msg_8f2a', from: 'alerts@monitoring.io', subject: 'CRITICAL: Payment service deploy failed', body: 'Deploy d-4521 failed at rollout stage 2/3.\n\nError: health check timeout after 30s on /health endpoint.\nService: payment-api\nCluster: prod-us-east-1' }, null, 2),
        },
      },
      {
        name: 'send_email',
        description: 'Compose and send an email with recipients, subject, and body',
        parameters: [
          { name: 'to', type: 'string', required: true, description: 'Recipient email' },
          { name: 'subject', type: 'string', required: true, description: 'Email subject' },
          { name: 'body', type: 'string', required: true, description: 'Email body' },
        ],
        exampleValues: { to: 'oncall@acme.com', subject: 'P0: Auth secret regression', body: 'Deploy d-4521 hardcoded the auth secret.' },
        mockResponse: { success: true, latencyMs: 420, data: JSON.stringify({ status: 'sent', messageId: 'msg_9c3b' }, null, 2) },
      },
      {
        name: 'list_threads',
        description: 'List email threads with preview snippets and participant info',
        parameters: [
          { name: 'label', type: 'string', required: false, description: 'Filter by label' },
        ],
        exampleValues: { label: 'INBOX' },
        mockResponse: {
          success: true,
          latencyMs: 200,
          data: JSON.stringify({ threads: [{ id: 'thread_1', subject: 'Re: Deploy rollback plan', participants: 3, snippet: 'Rollback confirmed. ETA 5 min...' }], total: 1 }, null, 2),
        },
      },
    ],
    schema: {
      name: 'search_emails',
      description: 'Search emails by sender, subject, date range, or keywords',
      parameters: { type: 'object', properties: { query: { type: 'string', description: 'Search query' }, from: { type: 'string', description: 'Filter by sender' } }, required: ['query'] },
    },
  },
  {
    service: 'Google Drive',
    icon: 'FileText',
    color: '#4285f4',
    connected: true,
    description: 'File search, document reading, folder browsing, and metadata access.',
    tools: [
      {
        name: 'search_files',
        description: 'Search files by name, type, owner, or modified date',
        parameters: [
          { name: 'query', type: 'string', required: true, description: 'Search query' },
          { name: 'type', type: 'string', required: false, description: 'Filter by file type' },
        ],
        exampleValues: { query: 'api security spec', type: 'document' },
        mockResponse: {
          success: true,
          latencyMs: 260,
          data: JSON.stringify({ files: [{ id: 'doc_7k2a', name: 'API Security Spec v2.1', type: 'Google Doc', modified: '1 week ago', owner: 'security-team@acme.com' }], total: 1 }, null, 2),
        },
      },
      {
        name: 'read_document',
        description: 'Read the full text content of a document or spreadsheet',
        parameters: [
          { name: 'file_id', type: 'string', required: true, description: 'File ID from search results' },
        ],
        exampleValues: { file_id: 'doc_7k2a' },
        mockResponse: {
          success: true,
          latencyMs: 310,
          data: '# API Security Spec v2.1\n\n## Auth Rules\n- AUTH-001: Signing algorithm must be RS256\n- AUTH-002: Keys must use env vars, not hardcoded\n- AUTH-003: Tokens must have expiry validation\n- AUTH-004: Tokens must not be stored in localStorage',
        },
      },
      {
        name: 'list_folder',
        description: 'List all files and subfolders in a specific directory',
        parameters: [
          { name: 'folder_id', type: 'string', required: true, description: 'Folder ID' },
        ],
        exampleValues: { folder_id: 'folder_root' },
        mockResponse: {
          success: true,
          latencyMs: 180,
          data: JSON.stringify({ items: [{ name: 'Specs', type: 'folder' }, { name: 'Runbooks', type: 'folder' }, { name: 'API Security Spec v2.1', type: 'document' }] }, null, 2),
        },
      },
      {
        name: 'get_file_metadata',
        description: 'Get file details including sharing permissions and history',
        parameters: [
          { name: 'file_id', type: 'string', required: true, description: 'File ID' },
        ],
        exampleValues: { file_id: 'doc_7k2a' },
        mockResponse: {
          success: true,
          latencyMs: 140,
          data: JSON.stringify({ id: 'doc_7k2a', name: 'API Security Spec v2.1', owner: 'security-team@acme.com', shared_with: ['eng-all@acme.com'], last_modified: '2025-03-21T10:30:00Z' }, null, 2),
        },
      },
    ],
    schema: {
      name: 'search_files',
      description: 'Search files by name, type, owner, or modified date',
      parameters: { type: 'object', properties: { query: { type: 'string', description: 'Search query' }, type: { type: 'string', description: 'File type filter' } }, required: ['query'] },
    },
  },
  {
    service: 'Confluence',
    icon: 'Database',
    color: '#1868db',
    connected: false,
    description: 'Wiki page search, content reading, and space browsing.',
    tools: [
      {
        name: 'search_pages',
        description: 'Search wiki pages by title, space, or content keywords',
        parameters: [
          { name: 'query', type: 'string', required: true, description: 'Search keywords' },
          { name: 'space', type: 'string', required: false, description: 'Confluence space key' },
        ],
        exampleValues: { query: 'auth middleware', space: 'ENG' },
        mockResponse: { success: true, latencyMs: 350, data: JSON.stringify({ pages: [{ id: 'page_42', title: 'Auth Middleware Architecture', space: 'ENG', excerpt: 'Overview of the authentication middleware...' }] }, null, 2) },
      },
      {
        name: 'read_page',
        description: 'Read the full content of a Confluence page with formatting',
        parameters: [
          { name: 'page_id', type: 'string', required: true, description: 'Page ID' },
        ],
        exampleValues: { page_id: 'page_42' },
        mockResponse: { success: true, latencyMs: 280, data: '# Auth Middleware Architecture\n\nThe auth middleware validates JWT tokens using RS256...' },
      },
      {
        name: 'list_spaces',
        description: 'List all available Confluence spaces with descriptions',
        parameters: [],
        exampleValues: {},
        mockResponse: { success: true, latencyMs: 200, data: JSON.stringify({ spaces: [{ key: 'ENG', name: 'Engineering', description: 'Technical docs' }, { key: 'OPS', name: 'Operations', description: 'Runbooks and procedures' }] }, null, 2) },
      },
    ],
    schema: {
      name: 'search_pages',
      description: 'Search wiki pages by title, space, or content keywords',
      parameters: { type: 'object', properties: { query: { type: 'string', description: 'Search keywords' }, space: { type: 'string', description: 'Space key' } }, required: ['query'] },
    },
  },
  {
    service: 'Jira',
    icon: 'Target',
    color: '#0052cc',
    connected: false,
    description: 'Issue search, sprint tracking, board metrics, and issue management.',
    tools: [
      {
        name: 'search_issues',
        description: 'Search issues by project, status, assignee, or JQL query',
        parameters: [
          { name: 'project', type: 'string', required: true, description: 'Project key' },
          { name: 'status', type: 'string', required: false, description: 'Filter by status' },
        ],
        exampleValues: { project: 'AUTH', status: 'open' },
        mockResponse: { success: true, latencyMs: 310, data: JSON.stringify({ issues: [{ key: 'AUTH-42', summary: 'Migrate to RS256 signing', status: 'In Progress', assignee: 'jchen' }], total: 1 }, null, 2) },
      },
      {
        name: 'read_issue',
        description: 'Read full issue details including comments and attachments',
        parameters: [
          { name: 'issue_key', type: 'string', required: true, description: 'Issue key (e.g., AUTH-42)' },
        ],
        exampleValues: { issue_key: 'AUTH-42' },
        mockResponse: { success: true, latencyMs: 250, data: JSON.stringify({ key: 'AUTH-42', summary: 'Migrate to RS256 signing', description: 'Per API Security Spec AUTH-001, migrate jwt.verify from HS256 to RS256.', priority: 'High', comments: 1 }, null, 2) },
      },
      {
        name: 'list_sprints',
        description: 'List sprints for a board with status and date ranges',
        parameters: [
          { name: 'board_id', type: 'string', required: true, description: 'Board ID' },
        ],
        exampleValues: { board_id: 'board_1' },
        mockResponse: { success: true, latencyMs: 180, data: JSON.stringify({ sprints: [{ id: 'sprint_14', name: 'Sprint 14', status: 'active', start: '2025-03-24', end: '2025-04-07' }] }, null, 2) },
      },
      {
        name: 'get_board_summary',
        description: 'Get board-level metrics: velocity, burndown, open count',
        parameters: [
          { name: 'board_id', type: 'string', required: true, description: 'Board ID' },
        ],
        exampleValues: { board_id: 'board_1' },
        mockResponse: { success: true, latencyMs: 220, data: JSON.stringify({ velocity: 34, open_issues: 12, in_progress: 5, done_this_sprint: 17, burndown_on_track: true }, null, 2) },
      },
    ],
    schema: {
      name: 'search_issues',
      description: 'Search issues by project, status, assignee, or JQL query',
      parameters: { type: 'object', properties: { project: { type: 'string', description: 'Project key' }, status: { type: 'string', description: 'Filter by status' } }, required: ['project'] },
    },
  },
]
