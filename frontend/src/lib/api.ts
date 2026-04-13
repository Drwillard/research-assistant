const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
export type Provider = 'openai' | 'ollama'

export interface Document {
  doc_id: string
  filename: string
}

export interface Source {
  filename: string
  score: number
  chunk_index: number
}

export interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
  sources?: Source[]
}

export interface ChatResponse {
  answer: string
  sources: Source[]
}

export interface BenchmarkSummary {
  count: number
  min_ms: number
  max_ms: number
  mean_ms: number
  median_ms: number
  p95_ms: number
}

export interface LatencyBenchmarkResponse {
  provider: Provider
  ingest_result: { status: string; filename: string; chunks: number; provider: Provider }
  warmup_count: number
  summary: BenchmarkSummary
  per_query: Record<string, BenchmarkSummary>
}

export interface CostModelResponse {
  openai_monthly_total_usd: number
  local_monthly_total_usd: number
  monthly_delta_usd_openai_minus_local: number
  local_savings_percent_vs_openai: number
  openai_cost_per_request_usd: number
  local_cost_per_request_usd: number
}

export interface CompareBenchmarkResponse {
  cpu_label: string
  gpu_label: string
  cpu_mean_ms: number
  gpu_mean_ms: number
  cpu_p95_ms: number
  gpu_p95_ms: number
  mean_speedup_x: number
  p95_speedup_x: number
  cpu_rps: number
  gpu_rps: number
}

export async function uploadDocument(
  file: File,
  provider: Provider
): Promise<{ status: string; filename: string; chunks: number; provider: Provider }> {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('provider', provider)
  const res = await fetch(`${API_URL}/ingest`, { method: 'POST', body: formData })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Upload failed' }))
    throw new Error(err.detail || 'Upload failed')
  }
  return res.json()
}

export async function getDocuments(provider: Provider): Promise<Document[]> {
  const res = await fetch(`${API_URL}/documents?provider=${encodeURIComponent(provider)}`)
  if (!res.ok) throw new Error('Failed to fetch documents')
  const data = await res.json()
  return data.documents as Document[]
}

export async function deleteDocument(docId: string, provider: Provider): Promise<void> {
  const res = await fetch(`${API_URL}/documents/${docId}?provider=${encodeURIComponent(provider)}`, {
    method: 'DELETE',
  })
  if (!res.ok) throw new Error('Failed to delete document')
}

export async function chat(message: string, history: ChatMessage[], provider: Provider): Promise<ChatResponse> {
  const conversation_history = history.map((m) => ({ role: m.role, content: m.content }))
  const res = await fetch(`${API_URL}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message, conversation_history, provider }),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Chat failed' }))
    throw new Error(err.detail || 'Chat failed')
  }
  return res.json()
}

export async function runLatencyBenchmark(params: {
  provider: Provider
  file: File
  runs: number
  warmup_runs: number
  queries: string
}): Promise<LatencyBenchmarkResponse> {
  const formData = new FormData()
  formData.append('file', params.file)
  formData.append('provider', params.provider)
  formData.append('runs', String(params.runs))
  formData.append('warmup_runs', String(params.warmup_runs))
  formData.append('queries', params.queries)

  const res = await fetch(`${API_URL}/benchmarks/latency`, { method: 'POST', body: formData })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Latency benchmark failed' }))
    throw new Error(err.detail || 'Latency benchmark failed')
  }
  return res.json()
}

export async function runCostModel(params: {
  monthly_requests: number
  avg_input_tokens: number
  avg_output_tokens: number
  openai_input_per_1m: number
  openai_output_per_1m: number
  local_fixed_monthly: number
  local_power_monthly: number
}): Promise<CostModelResponse> {
  const res = await fetch(`${API_URL}/benchmarks/cost-model`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(params),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Cost model failed' }))
    throw new Error(err.detail || 'Cost model failed')
  }
  return res.json()
}

export async function runCompareBenchmarks(params: {
  cpu_report: Record<string, unknown>
  gpu_report: Record<string, unknown>
}): Promise<CompareBenchmarkResponse> {
  const res = await fetch(`${API_URL}/benchmarks/compare`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(params),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Benchmark comparison failed' }))
    throw new Error(err.detail || 'Benchmark comparison failed')
  }
  return res.json()
}
