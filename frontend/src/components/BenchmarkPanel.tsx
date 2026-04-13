'use client'

import { useEffect, useMemo, useState } from 'react'
import {
  runCostModel,
  runLatencyBenchmark,
  type CostModelResponse,
  type LatencyBenchmarkResponse,
  type Provider,
} from '@/lib/api'

function StatCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-gray-200 bg-white px-3 py-2">
      <p className="text-[11px] uppercase tracking-wide text-gray-500">{label}</p>
      <p className="text-sm font-semibold text-gray-800 mt-0.5">{value}</p>
    </div>
  )
}

export default function BenchmarkPanel({ provider }: { provider: Provider }) {
  const [latencyFile, setLatencyFile] = useState<File | null>(null)
  const [latencyQueries, setLatencyQueries] = useState(
    'Summarize the paper in three bullet points.\nWhat method is used and what are key limitations?'
  )
  const [latencyRuns, setLatencyRuns] = useState(5)
  const [latencyWarmup, setLatencyWarmup] = useState(1)
  const [latencyLabel, setLatencyLabel] = useState(`${provider}-run`)
  const [latencyLoading, setLatencyLoading] = useState(false)
  const [latencyError, setLatencyError] = useState('')
  const [latencyResult, setLatencyResult] = useState<LatencyBenchmarkResponse | null>(null)
  const [latencyActionMsg, setLatencyActionMsg] = useState('')

  const [costLoading, setCostLoading] = useState(false)
  const [costError, setCostError] = useState('')
  const [costResult, setCostResult] = useState<CostModelResponse | null>(null)
  const [costInputs, setCostInputs] = useState({
    monthly_requests: 100000,
    avg_input_tokens: 1200,
    avg_output_tokens: 350,
    openai_input_per_1m: 0.15,
    openai_output_per_1m: 0.6,
    local_fixed_monthly: 250,
    local_power_monthly: 45,
  })

  const perQueryRows = useMemo(
    () => (latencyResult ? Object.entries(latencyResult.per_query) : []),
    [latencyResult]
  )

  useEffect(() => {
    setLatencyLabel(`${provider}-run`)
  }, [provider])

  function latencyReportForExport() {
    if (!latencyResult) return null
    return {
      label: latencyLabel.trim() || `${provider}-run`,
      provider: latencyResult.provider,
      ingest_result: latencyResult.ingest_result,
      warmup_count: latencyResult.warmup_count,
      summary: latencyResult.summary,
      per_query: latencyResult.per_query,
    }
  }

  async function copyLatencyJson() {
    const report = latencyReportForExport()
    if (!report) return
    const text = JSON.stringify(report, null, 2)
    try {
      await navigator.clipboard.writeText(text)
      setLatencyActionMsg('Copied benchmark JSON to clipboard.')
    } catch {
      setLatencyActionMsg('Clipboard blocked. Use Download JSON instead.')
    }
  }

  function downloadLatencyJson() {
    const report = latencyReportForExport()
    if (!report) return
    const json = JSON.stringify(report, null, 2)
    const blob = new Blob([json], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    const safeLabel = (latencyLabel.trim() || `${provider}-run`).replace(/[^a-zA-Z0-9-_]/g, '_')
    a.href = url
    a.download = `${safeLabel}.json`
    a.click()
    URL.revokeObjectURL(url)
    setLatencyActionMsg('Downloaded benchmark JSON.')
  }

  async function onRunLatency(e: React.FormEvent) {
    e.preventDefault()
    if (!latencyFile) {
      setLatencyError('Select a PDF file first.')
      return
    }
    setLatencyLoading(true)
    setLatencyError('')
    setLatencyActionMsg('')
    try {
      const res = await runLatencyBenchmark({
        provider,
        file: latencyFile,
        runs: latencyRuns,
        warmup_runs: latencyWarmup,
        queries: latencyQueries,
      })
      setLatencyResult(res)
      setLatencyActionMsg('Benchmark completed.')
    } catch (err: unknown) {
      setLatencyError(err instanceof Error ? err.message : 'Latency benchmark failed')
    } finally {
      setLatencyLoading(false)
    }
  }

  async function onRunCostModel(e: React.FormEvent) {
    e.preventDefault()
    setCostLoading(true)
    setCostError('')
    try {
      const res = await runCostModel(costInputs)
      setCostResult(res)
    } catch (err: unknown) {
      setCostError(err instanceof Error ? err.message : 'Cost model failed')
    } finally {
      setCostLoading(false)
    }
  }

  return (
    <div className="flex-1 overflow-y-auto bg-gray-50 p-6 space-y-6">
      <section className="rounded-xl border border-gray-200 bg-white p-5">
        <h3 className="text-sm font-semibold text-gray-800">Latency Benchmark</h3>
        <p className="text-xs text-gray-500 mt-1">Runs ingest + query timing for the active provider.</p>

        <form onSubmit={onRunLatency} className="mt-4 grid grid-cols-1 md:grid-cols-2 gap-3">
          <div>
            <label className="block text-xs text-gray-600 mb-1">PDF</label>
            <input
              type="file"
              accept=".pdf"
              onChange={(e) => setLatencyFile(e.target.files?.[0] ?? null)}
              className="w-full text-xs border border-gray-300 rounded-md px-2 py-2 bg-white"
            />
          </div>
          <div className="grid grid-cols-2 gap-2">
            <div>
              <label className="block text-xs text-gray-600 mb-1">Runs</label>
              <input
                type="number"
                min={1}
                max={100}
                value={latencyRuns}
                onChange={(e) => setLatencyRuns(Number(e.target.value))}
                className="w-full text-xs border border-gray-300 rounded-md px-2 py-2"
              />
            </div>
            <div>
              <label className="block text-xs text-gray-600 mb-1">Warmup</label>
              <input
                type="number"
                min={0}
                max={20}
                value={latencyWarmup}
                onChange={(e) => setLatencyWarmup(Number(e.target.value))}
                className="w-full text-xs border border-gray-300 rounded-md px-2 py-2"
              />
            </div>
          </div>
          <div>
            <label className="block text-xs text-gray-600 mb-1">Benchmark label</label>
            <input
              value={latencyLabel}
              onChange={(e) => setLatencyLabel(e.target.value)}
              className="w-full text-xs border border-gray-300 rounded-md px-2 py-2"
            />
          </div>
          <div className="md:col-span-2">
            <label className="block text-xs text-gray-600 mb-1">Queries (one per line)</label>
            <textarea
              value={latencyQueries}
              onChange={(e) => setLatencyQueries(e.target.value)}
              rows={4}
              className="w-full text-xs border border-gray-300 rounded-md px-2 py-2"
            />
          </div>
          <div className="md:col-span-2 flex items-center gap-3">
            <button
              type="submit"
              disabled={latencyLoading}
              className="rounded-md bg-blue-600 text-white text-xs px-3 py-2 disabled:opacity-50"
            >
              {latencyLoading ? 'Running...' : `Run (${provider})`}
            </button>
            {latencyError && <span className="text-xs text-red-600">{latencyError}</span>}
            {!latencyError && latencyActionMsg && <span className="text-xs text-green-700">{latencyActionMsg}</span>}
          </div>
        </form>

        {latencyResult && (
          <div className="mt-4 space-y-3">
            <div className="flex flex-wrap items-center gap-2">
              <button type="button" onClick={copyLatencyJson} className="rounded-md border border-gray-300 text-xs px-2 py-1.5">
                Copy JSON
              </button>
              <button type="button" onClick={downloadLatencyJson} className="rounded-md border border-gray-300 text-xs px-2 py-1.5">
                Download JSON
              </button>
            </div>
            <div className="grid grid-cols-2 md:grid-cols-5 gap-2">
              <StatCard label="Mean" value={`${latencyResult.summary.mean_ms} ms`} />
              <StatCard label="P95" value={`${latencyResult.summary.p95_ms} ms`} />
              <StatCard label="Min" value={`${latencyResult.summary.min_ms} ms`} />
              <StatCard label="Max" value={`${latencyResult.summary.max_ms} ms`} />
              <StatCard label="Samples" value={String(latencyResult.summary.count)} />
            </div>
            <div className="text-xs text-gray-600">
              Ingest status: <span className="font-medium">{latencyResult.ingest_result.status}</span> | Chunks:{' '}
              {latencyResult.ingest_result.chunks}
            </div>
            <div className="border border-gray-200 rounded-lg overflow-hidden">
              <table className="w-full text-xs">
                <thead className="bg-gray-100 text-gray-700">
                  <tr>
                    <th className="text-left px-2 py-1.5">Query</th>
                    <th className="text-right px-2 py-1.5">Mean ms</th>
                    <th className="text-right px-2 py-1.5">P95 ms</th>
                  </tr>
                </thead>
                <tbody>
                  {perQueryRows.map(([query, stats]) => (
                    <tr key={query} className="border-t border-gray-100">
                      <td className="px-2 py-1.5 text-gray-700">{query}</td>
                      <td className="px-2 py-1.5 text-right">{stats.mean_ms}</td>
                      <td className="px-2 py-1.5 text-right">{stats.p95_ms}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </section>

      <section className="rounded-xl border border-gray-200 bg-white p-5">
        <h3 className="text-sm font-semibold text-gray-800">Cost Savings Model</h3>
        <p className="text-xs text-gray-500 mt-1">Estimate monthly OpenAI cost versus local infrastructure cost.</p>

        <form onSubmit={onRunCostModel} className="mt-4 grid grid-cols-2 md:grid-cols-4 gap-3">
          {Object.entries(costInputs).map(([key, val]) => (
            <div key={key}>
              <label className="block text-xs text-gray-600 mb-1">{key}</label>
              <input
                type="number"
                step="any"
                value={val}
                onChange={(e) => setCostInputs((prev) => ({ ...prev, [key]: Number(e.target.value) }))}
                className="w-full text-xs border border-gray-300 rounded-md px-2 py-2"
              />
            </div>
          ))}
          <div className="col-span-2 md:col-span-4 flex items-center gap-3">
            <button
              type="submit"
              disabled={costLoading}
              className="rounded-md bg-blue-600 text-white text-xs px-3 py-2 disabled:opacity-50"
            >
              {costLoading ? 'Calculating...' : 'Calculate'}
            </button>
            {costError && <span className="text-xs text-red-600">{costError}</span>}
          </div>
        </form>

        {costResult && (
          <div className="mt-4 grid grid-cols-2 md:grid-cols-3 gap-2">
            <StatCard label="OpenAI monthly" value={`$${costResult.openai_monthly_total_usd}`} />
            <StatCard label="Local monthly" value={`$${costResult.local_monthly_total_usd}`} />
            <StatCard label="Delta" value={`$${costResult.monthly_delta_usd_openai_minus_local}`} />
            <StatCard label="Savings %" value={`${costResult.local_savings_percent_vs_openai}%`} />
            <StatCard label="OpenAI / req" value={`$${costResult.openai_cost_per_request_usd}`} />
            <StatCard label="Local / req" value={`$${costResult.local_cost_per_request_usd}`} />
          </div>
        )}
      </section>
    </div>
  )
}
