export interface UserItem {
  id: string;
  username: string;
  display_name: string;
  email?: string | null;
  avatar_color: string;
  bio: string;
  created_at: string;
  document_count: number;
  tmu_count: number;
  earliest_memory_date?: string | null;
  latest_memory_date?: string | null;
}

export interface UserCreateRequest {
  username: string;
  display_name: string;
  email?: string;
  avatar_color?: string;
  bio?: string;
}

export interface UserRegisterRequest {
  email: string;
  username: string;
  password: string;
  display_name: string;
  bio?: string;
  avatar_color?: string;
}

export interface UserLoginRequest {
  username_or_email: string;
  password: string;
}

export interface AuthResponse {
  token: string;
  user: UserItem;
}

export interface LodgeThoughtRequest {
  statement: string;
  memory_type: 'belief' | 'goal' | 'preference' | 'decision' | 'interest' | 'fact';
  event_date?: string; // e.g. "2026-10-06" for today, or "2019-04-12" for past memory
  stance_polarity?: number; // -1.0 to 1.0
  entities?: string[];
  topics?: string[];
  context_note?: string;
}

export interface DocumentItem {
  id: string;
  user_id: string;
  title: string;
  file_path: string;
  file_type: string;
  file_size: number;
  hash_sha256: string;
  document_date: string | null;
  created_at: string;
  chunk_count: number;
  tmu_count: number;
}

export interface TimelinePoint {
  period: string;
  date_display: string;
  event_date: string;
  headline: string;
  statement: string;
  memory_type: string;
  document_title: string;
  document_id: string;
  tmu_id: string;
  confidence: number;
  stance_polarity: number;
}

export interface GroundedClaim {
  claim_id: string;
  claim_text: string;
  claim_type: string;
  confidence: number;
  evidence_tmu_ids: string[];
  source_citations: Array<{
    document_title: string;
    document_id: string;
    statement: string;
    date: string;
  }>;
  is_uncertain: boolean;
  uncertainty_note: string | null;
}

export interface ChangePoint {
  id: string;
  user_id: string;
  topic_or_entity: string;
  from_period: string;
  to_period: string;
  change_type: string;
  magnitude: number;
  earlier_memory_id: string;
  later_memory_id: string;
  earlier_statement: string;
  later_statement: string;
  earlier_date: string;
  later_date: string;
  uncertainty_bounds: string | null;
  created_at: string;
}

export interface Contradiction {
  id: string;
  source_memory_id: string;
  target_memory_id: string;
  relation_type: string;
  confidence: number;
  evidence_rationale: string;
  source_statement: string;
  target_statement: string;
  source_date: string;
  target_date: string;
  created_at: string;
}

export interface QueryResponse {
  query: string;
  detected_intent: string;
  pipeline_used: string;
  answer: string;
  timeline: TimelinePoint[];
  detected_changes: ChangePoint[];
  potential_contradictions: Contradiction[];
  grounded_claims: GroundedClaim[];
  uncertainty_notes: string[];
  execution_time_ms: number;
  model_calls: number;
}

export interface PipelineMetric {
  pipeline: string;
  chronological_ordering_accuracy: number;
  temporal_coverage_recall: number;
  change_point_f1: number;
  unsupported_claim_rate: number;
  average_latency_ms: number;
  total_token_usage: number;
}

export interface BenchmarkRun {
  id: string;
  run_name: string;
  created_at: string;
  metrics: Record<string, PipelineMetric>;
  summary_findings: string;
}

export interface VersionDiff {
  series_name: string;
  earlier_version: string;
  later_version: string;
  added_skills_or_topics: string[];
  removed_skills_or_topics: string[];
  retained_skills_or_topics: string[];
  semantic_changes: Array<{
    earlier_statement: string;
    later_statement: string;
    similarity: number;
    drift: number;
  }>;
  summary: string;
}

export const API_BASE = (import.meta.env.VITE_API_BASE_URL ? String(import.meta.env.VITE_API_BASE_URL).replace(/\/+$/, '') : '') + '/api';
const TOKEN_KEY = 'memory_lane_auth_token';


export const api = {
  // Token storage helpers
  getToken(): string | null {
    try {
      return localStorage.getItem(TOKEN_KEY);
    } catch {
      return null;
    }
  },

  setToken(token: string): void {
    try {
      localStorage.setItem(TOKEN_KEY, token);
    } catch {
      // ignore
    }
  },

  clearToken(): void {
    try {
      localStorage.removeItem(TOKEN_KEY);
    } catch {
      // ignore
    }
  },

  authHeaders(): Record<string, string> {
    const token = this.getToken();
    return token ? { Authorization: `Bearer ${token}` } : {};
  },

  // Authentication
  async register(data: UserRegisterRequest): Promise<AuthResponse> {
    const res = await fetch(`${API_BASE}/auth/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Registration failed');
    }
    const result: AuthResponse = await res.json();
    this.setToken(result.token);
    return result;
  },

  async login(credentials: UserLoginRequest): Promise<AuthResponse> {
    const res = await fetch(`${API_BASE}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(credentials),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Invalid username/email or password');
    }
    const result: AuthResponse = await res.json();
    this.setToken(result.token);
    return result;
  },

  async getMe(): Promise<UserItem | null> {
    const token = this.getToken();
    if (!token) return null;
    try {
      const res = await fetch(`${API_BASE}/auth/me`, {
        headers: this.authHeaders(),
      });
      if (!res.ok) {
        this.clearToken();
        return null;
      }
      return res.json();
    } catch {
      return null;
    }
  },

  async logout(): Promise<void> {
    try {
      await fetch(`${API_BASE}/auth/logout`, {
        method: 'POST',
        headers: this.authHeaders(),
      });
    } finally {
      this.clearToken();
    }
  },

  // Users
  async getUsers(): Promise<UserItem[]> {
    const res = await fetch(`${API_BASE}/users`);
    if (!res.ok) throw new Error('Failed to fetch users');
    return res.json();
  },

  async createUser(data: UserCreateRequest): Promise<UserItem> {
    const res = await fetch(`${API_BASE}/users`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Failed to create user');
    }
    return res.json();
  },

  async lodgeThought(userId: string, data: LodgeThoughtRequest): Promise<any> {
    const res = await fetch(`${API_BASE}/users/${encodeURIComponent(userId)}/lodge`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...this.authHeaders(),
      },
      body: JSON.stringify(data),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Failed to lodge thought');
    }
    return res.json();
  },

  // Documents
  async getDocuments(userId?: string): Promise<DocumentItem[]> {
    const params = new URLSearchParams();
    if (userId) params.append('user_id', userId);
    const res = await fetch(`${API_BASE}/documents?${params.toString()}`, {
      headers: this.authHeaders(),
    });
    if (!res.ok) throw new Error('Failed to fetch documents');
    return res.json();
  },

  async uploadDocument(file: File, documentDate?: string, title?: string, userId?: string): Promise<DocumentItem> {
    const formData = new FormData();
    formData.append('file', file);
    if (documentDate) formData.append('document_date', documentDate);
    if (title) formData.append('title', title);
    if (userId) formData.append('user_id', userId);

    const res = await fetch(`${API_BASE}/documents/upload`, {
      method: 'POST',
      headers: this.authHeaders(),
      body: formData,
    });
    if (!res.ok) throw new Error('Upload failed');
    return res.json();
  },

  async addTextDocument(title: string, content: string, documentDate?: string, userId?: string): Promise<DocumentItem> {
    const res = await fetch(`${API_BASE}/documents/text`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...this.authHeaders(),
      },
      body: JSON.stringify({
        title,
        content,
        document_date: documentDate,
        file_type: 'txt',
        user_id: userId || 'default_user'
      }),
    });
    if (!res.ok) throw new Error('Failed to add document');
    return res.json();
  },

  async deleteDocument(id: string): Promise<void> {
    const res = await fetch(`${API_BASE}/documents/${id}`, {
      method: 'DELETE',
      headers: this.authHeaders(),
    });
    if (!res.ok) throw new Error('Failed to delete document');
  },

  // Query / Ask Memory Lane
  async ask(
    query: string,
    pipelineMode: 'memory_lane' | 'temporal' | 'baseline' = 'memory_lane',
    topK: number = 8,
    userId?: string
  ): Promise<QueryResponse> {
    const res = await fetch(`${API_BASE}/query`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...this.authHeaders(),
      },
      body: JSON.stringify({
        query,
        user_id: userId || 'default_user',
        pipeline_mode: pipelineMode,
        top_k: topK,
      }),
    });
    if (!res.ok) throw new Error('Query execution failed');
    return res.json();
  },

  // Timeline
  async getTimeline(startYear?: number, endYear?: number, userId?: string): Promise<TimelinePoint[]> {
    const params = new URLSearchParams();
    if (startYear) params.append('start_year', startYear.toString());
    if (endYear) params.append('end_year', endYear.toString());
    if (userId) params.append('user_id', userId);
    const res = await fetch(`${API_BASE}/timeline?${params.toString()}`, {
      headers: this.authHeaders(),
    });
    if (!res.ok) throw new Error('Failed to fetch timeline');
    return res.json();
  },

  // Changes & Contradictions
  async getChanges(userId?: string): Promise<ChangePoint[]> {
    const params = new URLSearchParams();
    if (userId) params.append('user_id', userId);
    const res = await fetch(`${API_BASE}/changes?${params.toString()}`, {
      headers: this.authHeaders(),
    });
    if (!res.ok) throw new Error('Failed to fetch changes');
    return res.json();
  },

  async getContradictions(userId?: string): Promise<Contradiction[]> {
    const params = new URLSearchParams();
    if (userId) params.append('user_id', userId);
    const res = await fetch(`${API_BASE}/contradictions?${params.toString()}`, {
      headers: this.authHeaders(),
    });
    if (!res.ok) throw new Error('Failed to fetch contradictions');
    return res.json();
  },

  // Versions & Diff
  async getVersionDiff(series: string, earlier: string, later: string, userId?: string): Promise<VersionDiff> {
    const params = new URLSearchParams({ series, earlier, later });
    if (userId) params.append('user_id', userId);
    const res = await fetch(`${API_BASE}/versions/diff?${params.toString()}`, {
      headers: this.authHeaders(),
    });
    if (!res.ok) throw new Error('Failed to fetch version diff');
    return res.json();
  },

  // Graph
  async getGraph(userId?: string): Promise<{ nodes: any[]; edges: any[]; summary: string }> {
    const params = new URLSearchParams();
    if (userId) params.append('user_id', userId);
    const res = await fetch(`${API_BASE}/graph?${params.toString()}`, {
      headers: this.authHeaders(),
    });
    if (!res.ok) throw new Error('Failed to fetch graph');
    return res.json();
  },

  // Research Benchmark
  async runBenchmark(runName: string = 'Interactive Studio Benchmark'): Promise<BenchmarkRun> {
    const res = await fetch(`${API_BASE}/research/benchmark`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...this.authHeaders(),
      },
      body: JSON.stringify({
        run_name: runName,
        pipelines: ['baseline', 'temporal', 'memory_lane'],
      }),
    });
    if (!res.ok) throw new Error('Benchmark execution failed');
    return res.json();
  },

  async getBenchmarkRuns(): Promise<BenchmarkRun[]> {
    const res = await fetch(`${API_BASE}/research/runs`, {
      headers: this.authHeaders(),
    });
    if (!res.ok) throw new Error('Failed to fetch runs');
    return res.json();
  },
};
