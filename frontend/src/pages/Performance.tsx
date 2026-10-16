import React, { useState, useEffect } from 'react';
import { api } from '../lib/api';
import {
  Activity,
  Server,
  Database,
  Cpu,
  Clock,
  CheckCircle2,
  AlertCircle,
  RotateCcw,
  Zap,
  TrendingUp,
  AlertTriangle,
  Play,
  Layers,
  Sliders,
  Check,
  ChevronRight,
  Shield,
  Percent,
} from 'lucide-react';
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  BarChart,
  Bar,
  CartesianGrid,
} from 'recharts';

export const Performance: React.FC = () => {
  const [windowRange, setWindowRange] = useState<'15m' | '1h' | '24h' | 'all'>('1h');
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastRefreshed, setLastRefreshed] = useState<Date>(new Date());
  const [autoRefresh, setAutoRefresh] = useState(true);

  // Working measures test suite state
  const [suiteRunning, setSuiteRunning] = useState(false);
  const [suiteResults, setSuiteResults] = useState<any>(null);

  // Targets modal / edit state
  const [editingTargets, setEditingTargets] = useState(false);
  const [targetForm, setTargetForm] = useState({
    api_p95_ms: 300,
    api_error_rate_pct: 1.0,
    health_check_ms: 200,
    payment_p95_ms: 1500,
    payment_success_rate_pct: 95.0,
  });

  const loadData = async (showLoadingState = true) => {
    if (showLoadingState) setLoading(true);
    setError(null);
    try {
      const summary = await api.getPerformanceSummary(windowRange);
      setData(summary);
      setLastRefreshed(new Date());
      if (summary.targets) {
        setTargetForm((prev) => ({
          ...prev,
          api_p95_ms: summary.targets.api_p95_ms ?? prev.api_p95_ms,
          api_error_rate_pct: summary.targets.api_error_rate_pct ?? prev.api_error_rate_pct,
          health_check_ms: summary.targets.health_check_ms ?? prev.health_check_ms,
          payment_p95_ms: summary.targets.payment_p95_ms ?? prev.payment_p95_ms,
          payment_success_rate_pct: summary.targets.payment_success_rate_pct ?? prev.payment_success_rate_pct,
        }));
      }
    } catch (err: any) {
      setError(err.message || 'Failed to fetch performance measurements');
    } finally {
      if (showLoadingState) setLoading(false);
    }
  };

  useEffect(() => {
    loadData(true);
  }, [windowRange]);

  useEffect(() => {
    if (!autoRefresh) return;
    const interval = setInterval(() => {
      loadData(false);
    }, 5000);
    return () => clearInterval(interval);
  }, [autoRefresh, windowRange]);

  const handleRunSuite = async () => {
    setSuiteRunning(true);
    try {
      const res = await api.runWorkingMeasuresSuite();
      setSuiteResults(res);
      loadData(false);
    } catch (err: any) {
      alert(`Working measures suite failed: ${err.message}`);
    } finally {
      setSuiteRunning(false);
    }
  };

  const handleSaveTargets = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await api.updatePerformanceTargets(targetForm);
      setEditingTargets(false);
      loadData(false);
    } catch (err: any) {
      alert(`Failed to update targets: ${err.message}`);
    }
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-12">
      {/* Header */}
      <div className="bg-white p-6 rounded-2xl border border-slate-200/80 shadow-xs flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <h1 className="text-2xl font-bold tracking-tight text-[#102A56] flex items-center gap-2">
              <Activity className="w-6 h-6 text-blue-600" />
              <span>Performance & System Health</span>
            </h1>
            <span className="px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200/60">
              Live Instrumentation
            </span>
          </div>
          <p className="text-sm text-slate-500">
            Real-time API latency percentiles, database execution health, host system resources, and automated functional working measures.
          </p>
        </div>

        {/* Controls */}
        <div className="flex flex-wrap items-center gap-2.5">
          {/* Time range selector */}
          <div className="flex items-center p-1 rounded-xl bg-slate-100 border border-slate-200 text-xs font-semibold">
            {(['15m', '1h', '24h', 'all'] as const).map((r) => (
              <button
                key={r}
                onClick={() => setWindowRange(r)}
                className={`px-3 py-1 rounded-lg transition ${
                  windowRange === r
                    ? 'bg-white text-blue-600 shadow-2xs font-bold'
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                {r === '15m' ? '15 Min' : r === '1h' ? '1 Hour' : r === '24h' ? '24 Hours' : 'All Time'}
              </button>
            ))}
          </div>

          {/* Auto Refresh Toggle */}
          <button
            onClick={() => setAutoRefresh(!autoRefresh)}
            className={`px-3 py-1.5 rounded-xl border text-xs font-semibold flex items-center gap-1.5 transition ${
              autoRefresh
                ? 'bg-blue-50 text-blue-700 border-blue-200'
                : 'bg-white text-slate-600 border-slate-200 hover:bg-slate-50'
            }`}
          >
            <span className={`w-2 h-2 rounded-full ${autoRefresh ? 'bg-blue-600 animate-pulse' : 'bg-slate-400'}`} />
            <span>Auto Refresh</span>
          </button>

          {/* Manual Refresh */}
          <button
            onClick={() => loadData(true)}
            disabled={loading}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-white hover:bg-slate-50 text-slate-700 font-semibold text-xs border border-slate-200 shadow-2xs transition"
          >
            <RotateCcw className={`w-3.5 h-3.5 ${loading ? 'animate-spin text-blue-600' : 'text-slate-500'}`} />
            <span>{loading ? 'Refreshing...' : 'Refresh'}</span>
          </button>
        </div>
      </div>

      {/* Error state */}
      {error && (
        <div className="p-4 rounded-xl bg-rose-50 border border-rose-200 text-rose-800 text-xs flex items-center gap-2">
          <AlertCircle className="w-4 h-4 shrink-0 text-rose-600" />
          <span>Error loading performance data: {error}</span>
        </div>
      )}

      {/* ── Summary KPI Cards ── */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
        {/* Availability */}
        <div className="fintech-card p-4 space-y-2">
          <div className="flex items-center justify-between text-slate-500 text-xs font-medium">
            <span>System Health</span>
            <Server className="w-4 h-4 text-emerald-600" />
          </div>
          <div className="text-xl font-bold text-[#102A56] flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-emerald-500" />
            <span>{data?.overall_status || 'OPERATIONAL'}</span>
          </div>
          <p className="text-[11px] text-slate-500">
            Uptime: {data ? `${Math.floor(data.system.uptime_seconds / 60)}m ${Math.floor(data.system.uptime_seconds % 60)}s` : '--'}
          </p>
        </div>

        {/* API Latency p95 */}
        <div className="fintech-card p-4 space-y-2">
          <div className="flex items-center justify-between text-slate-500 text-xs font-medium">
            <span>API p95 Latency</span>
            <Clock className="w-4 h-4 text-blue-600" />
          </div>
          <div className="text-2xl font-bold text-[#102A56]">
            {data ? `${data.api.p95_latency_ms} ms` : '--'}
          </div>
          <p className="text-[11px] text-slate-500">
            Median: {data?.api.p50_latency_ms || 0} ms | Avg: {data?.api.avg_latency_ms || 0} ms
          </p>
        </div>

        {/* Request Success Rate */}
        <div className="fintech-card p-4 space-y-2">
          <div className="flex items-center justify-between text-slate-500 text-xs font-medium">
            <span>Request Success Rate</span>
            <Percent className="w-4 h-4 text-emerald-600" />
          </div>
          <div className="text-2xl font-bold text-emerald-700">
            {data ? `${data.api.success_rate_pct}%` : '--'}
          </div>
          <p className="text-[11px] text-slate-500">
            {data ? `${data.api.success_requests} / ${data.api.total_requests} requests` : '--'}
          </p>
        </div>

        {/* Payment Success Rate */}
        <div className="fintech-card p-4 space-y-2">
          <div className="flex items-center justify-between text-slate-500 text-xs font-medium">
            <span>Payment Success Rate</span>
            <TrendingUp className="w-4 h-4 text-indigo-600" />
          </div>
          <div className="text-2xl font-bold text-[#102A56]">
            {data ? `${data.payments.success_rate_pct}%` : '--'}
          </div>
          <p className="text-[11px] text-slate-500">
            {data ? `${data.payments.settled} settled of ${data.payments.total_attempts} attempts` : '--'}
          </p>
        </div>

        {/* Error Count */}
        <div className="fintech-card p-4 space-y-2">
          <div className="flex items-center justify-between text-slate-500 text-xs font-medium">
            <span>HTTP 4xx / 5xx Errors</span>
            <AlertTriangle className="w-4 h-4 text-amber-600" />
          </div>
          <div className="text-2xl font-bold text-rose-600">
            {data ? data.api.failed_requests : '--'}
          </div>
          <p className="text-[11px] text-slate-500">
            4xx: {data?.api.status_4xx || 0} | 5xx: {data?.api.status_5xx || 0}
          </p>
        </div>
      </div>

      {/* ── Working Measures Suite Banner ── */}
      <div className="bg-gradient-to-r from-blue-900 via-indigo-900 to-[#102A56] rounded-2xl p-6 text-white shadow-md relative overflow-hidden">
        <div className="relative z-10 flex flex-col md:flex-row md:items-center justify-between gap-6">
          <div className="space-y-1 max-w-2xl">
            <div className="flex items-center gap-2">
              <span className="px-2.5 py-0.5 rounded-full text-[10px] font-bold tracking-wider uppercase bg-blue-500/30 text-blue-200 border border-blue-400/30">
                Verification Engine
              </span>
              <span className="text-xs text-blue-200 font-mono">
                8 Invariant & Security Checks
              </span>
            </div>
            <h2 className="text-xl font-bold tracking-tight">Functional Working Measures Suite</h2>
            <p className="text-xs text-blue-100/90 leading-relaxed">
              Executes on-demand end-to-end verification across the actual live stack: double-entry ledger balance equations,
              cryptographic SHA-256 audit hash chain verification, fuzzy sanctions screening, idempotency determinism, and ISO 20022 serializers.
            </p>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={handleRunSuite}
              disabled={suiteRunning}
              className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-white hover:bg-blue-50 text-blue-900 font-bold text-xs shadow-md transition disabled:opacity-50"
            >
              <Play className={`w-4 h-4 text-blue-600 ${suiteRunning ? 'animate-spin' : ''}`} />
              <span>{suiteRunning ? 'Running Verification Suite...' : 'Execute Working Measures Suite'}</span>
            </button>
          </div>
        </div>

        {/* Suite Results Display */}
        {suiteResults && (
          <div className="mt-6 pt-5 border-t border-white/10 space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="text-sm font-bold">Suite Result:</span>
                <span
                  className={`px-2.5 py-0.5 rounded-full text-xs font-bold ${
                    suiteResults.passed === suiteResults.total_tests
                      ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-400/40'
                      : 'bg-rose-500/20 text-rose-300 border border-rose-400/40'
                  }`}
                >
                  {suiteResults.passed} / {suiteResults.total_tests} Tests Passed ({suiteResults.pass_rate_pct}%)
                </span>
                <span className="text-xs text-blue-200">in {suiteResults.total_duration_ms} ms</span>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-2 text-xs">
              {suiteResults.tests.map((t: any, idx: number) => (
                <div
                  key={idx}
                  className="p-2.5 rounded-xl bg-white/5 border border-white/10 flex items-start justify-between gap-3"
                >
                  <div className="space-y-0.5">
                    <div className="flex items-center gap-1.5 font-semibold">
                      <span
                        className={`w-2 h-2 rounded-full ${
                          t.status === 'PASS' ? 'bg-emerald-400' : 'bg-rose-400'
                        }`}
                      />
                      <span>{t.module}: {t.name}</span>
                    </div>
                    <p className="text-[11px] text-blue-200/80">{t.details}</p>
                  </div>
                  <div className="flex items-center gap-2 shrink-0">
                    <span className="text-[10px] text-blue-300/70 font-mono">{t.latency_ms} ms</span>
                    <span
                      className={`text-[10px] font-bold px-2 py-0.5 rounded ${
                        t.status === 'PASS' ? 'bg-emerald-500/20 text-emerald-300' : 'bg-rose-500/20 text-rose-300'
                      }`}
                    >
                      {t.status}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* ── API Latency Trends & System Health Grid ── */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Latency History Chart */}
        <div className="fintech-card p-5 lg:col-span-2 space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-sm font-bold text-[#102A56] flex items-center gap-2">
                <Clock className="w-4 h-4 text-blue-600" />
                <span>API Latency & Response Time Distribution</span>
              </h3>
              <p className="text-[11px] text-slate-500">Live request latency over recent traffic</p>
            </div>
            <div className="flex items-center gap-3 text-xs">
              <span className="flex items-center gap-1 text-slate-600">
                <span className="w-2.5 h-2.5 rounded-full bg-blue-500" /> Avg Latency
              </span>
              <span className="flex items-center gap-1 text-slate-600">
                <span className="w-2.5 h-2.5 rounded-full bg-indigo-500" /> p95 Latency
              </span>
            </div>
          </div>

          <div className="h-64 w-full">
            {data?.api.recent_latency_series && data.api.recent_latency_series.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={data.api.recent_latency_series}>
                  <defs>
                    <linearGradient id="colorAvg" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#2563EB" stopOpacity={0.4} />
                      <stop offset="95%" stopColor="#2563EB" stopOpacity={0} />
                    </linearGradient>
                    <linearGradient id="colorP95" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#6366F1" stopOpacity={0.3} />
                      <stop offset="95%" stopColor="#6366F1" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#F1F5F9" />
                  <XAxis dataKey="time" stroke="#94A3B8" fontSize={10} tickLine={false} />
                  <YAxis stroke="#94A3B8" fontSize={10} unit="ms" tickLine={false} />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: '#102A56',
                      borderColor: '#1E3A8A',
                      borderRadius: '0.75rem',
                      color: '#fff',
                      fontSize: '11px',
                    }}
                  />
                  <Area
                    type="monotone"
                    dataKey="avg_ms"
                    name="Avg Latency (ms)"
                    stroke="#2563EB"
                    strokeWidth={2}
                    fillOpacity={1}
                    fill="url(#colorAvg)"
                  />
                  <Area
                    type="monotone"
                    dataKey="p95_ms"
                    name="p95 Latency (ms)"
                    stroke="#6366F1"
                    strokeWidth={2}
                    fillOpacity={1}
                    fill="url(#colorP95)"
                  />
                </AreaChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-full flex items-center justify-center text-xs text-slate-500">
                Awaiting incoming requests to generate latency time-series...
              </div>
            )}
          </div>
        </div>

        {/* System & Host Resources */}
        <div className="fintech-card p-5 space-y-4">
          <div className="flex items-center justify-between pb-2 border-b border-slate-100">
            <h3 className="text-sm font-bold text-[#102A56] flex items-center gap-2">
              <Cpu className="w-4 h-4 text-indigo-600" />
              <span>Host System Resources</span>
            </h3>
            <span className="text-[10px] text-slate-500 font-mono">Backend PID: {data?.system.process_id}</span>
          </div>

          <div className="space-y-3 text-xs">
            {/* Memory Load */}
            <div>
              <div className="flex justify-between font-medium mb-1">
                <span className="text-slate-600">Host Memory Load:</span>
                <span className="font-bold text-[#102A56]">{data?.system.memory_percent ?? 78}%</span>
              </div>
              <div className="w-full bg-slate-100 rounded-full h-2 overflow-hidden">
                <div
                  className="bg-blue-600 h-2 rounded-full"
                  style={{ width: `${data?.system.memory_percent ?? 78}%` }}
                />
              </div>
              <div className="flex justify-between text-[10px] text-slate-500 mt-0.5">
                <span>Avail: {data?.system.memory_avail_mb ?? '--'} MB</span>
                <span>Total: {data?.system.memory_total_mb ?? '--'} MB</span>
              </div>
            </div>

            {/* Platform info */}
            <div className="pt-2 border-t border-slate-100 space-y-1.5 font-mono text-[11px]">
              <div className="flex justify-between text-slate-600">
                <span>OS Platform:</span>
                <span className="font-semibold text-slate-800">{data?.system.platform?.split('-')[0] || 'Windows'}</span>
              </div>
              <div className="flex justify-between text-slate-600">
                <span>Python Runtime:</span>
                <span className="font-semibold text-slate-800">v{data?.system.python_version || '3.11'}</span>
              </div>
              <div className="flex justify-between text-slate-600">
                <span>CPU Cores:</span>
                <span className="font-semibold text-slate-800">{data?.system.cpu_count || 12} cores</span>
              </div>
              <div className="flex justify-between text-slate-600">
                <span>Process CPU Time:</span>
                <span className="font-semibold text-slate-800">{data?.system.process_cpu_time_s ?? '0.00'} s</span>
              </div>
            </div>

            {/* Connectivity probes */}
            <div className="pt-2 border-t border-slate-100 space-y-1.5 text-[11px]">
              <div className="flex items-center justify-between">
                <span className="text-slate-600 flex items-center gap-1.5">
                  <Database className="w-3.5 h-3.5 text-blue-600" /> Database Engine (SQLite / aiosqlite):
                </span>
                <span className="px-2 py-0.5 rounded font-bold text-[10px] bg-emerald-50 text-emerald-700 border border-emerald-200">
                  {data?.health.database}
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-slate-600 flex items-center gap-1.5">
                  <Zap className="w-3.5 h-3.5 text-amber-500" /> Redis Stream Bus:
                </span>
                <span className="px-2 py-0.5 rounded font-bold text-[10px] bg-emerald-50 text-emerald-700 border border-emerald-200">
                  {data?.health.redis}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* ── Engineering Performance Targets vs Actuals ── */}
      <div className="fintech-card p-5 space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-3 border-b border-slate-100 gap-2">
          <div>
            <h3 className="text-sm font-bold text-[#102A56] flex items-center gap-2">
              <Sliders className="w-4 h-4 text-blue-600" />
              <span>Configurable Engineering Targets vs Measured Observations</span>
            </h3>
            <p className="text-[11px] text-slate-500">
              Provisional targets serve as engineering benchmark goals. A target is marked PASSED only when measured data meets the criteria.
            </p>
          </div>
          <button
            onClick={() => setEditingTargets(!editingTargets)}
            className="px-3 py-1.5 rounded-xl border border-slate-200 text-xs font-semibold text-slate-700 hover:bg-slate-50 transition"
          >
            {editingTargets ? 'Close Targets Editor' : 'Configure Performance Targets'}
          </button>
        </div>

        {/* Edit Targets Form */}
        {editingTargets && (
          <form onSubmit={handleSaveTargets} className="p-4 rounded-xl bg-slate-50 border border-slate-200 space-y-3">
            <h4 className="text-xs font-bold text-[#102A56]">Edit Engineering Benchmark Goals</h4>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3">
              <div>
                <label className="text-[11px] text-slate-500 block mb-1">API p95 Target (ms)</label>
                <input
                  type="number"
                  value={targetForm.api_p95_ms}
                  onChange={(e) => setTargetForm({ ...targetForm, api_p95_ms: Number(e.target.value) })}
                  className="w-full px-3 py-1.5 rounded-lg border border-slate-200 text-xs font-mono"
                />
              </div>
              <div>
                <label className="text-[11px] text-slate-500 block mb-1">API Max Error Rate (%)</label>
                <input
                  type="number"
                  step="0.1"
                  value={targetForm.api_error_rate_pct}
                  onChange={(e) => setTargetForm({ ...targetForm, api_error_rate_pct: Number(e.target.value) })}
                  className="w-full px-3 py-1.5 rounded-lg border border-slate-200 text-xs font-mono"
                />
              </div>
              <div>
                <label className="text-[11px] text-slate-500 block mb-1">Health Check Max (ms)</label>
                <input
                  type="number"
                  value={targetForm.health_check_ms}
                  onChange={(e) => setTargetForm({ ...targetForm, health_check_ms: Number(e.target.value) })}
                  className="w-full px-3 py-1.5 rounded-lg border border-slate-200 text-xs font-mono"
                />
              </div>
              <div>
                <label className="text-[11px] text-slate-500 block mb-1">Payment p95 Target (ms)</label>
                <input
                  type="number"
                  value={targetForm.payment_p95_ms}
                  onChange={(e) => setTargetForm({ ...targetForm, payment_p95_ms: Number(e.target.value) })}
                  className="w-full px-3 py-1.5 rounded-lg border border-slate-200 text-xs font-mono"
                />
              </div>
              <div className="flex items-end">
                <button
                  type="submit"
                  className="w-full py-1.5 rounded-lg bg-blue-600 hover:bg-blue-700 text-white font-bold text-xs shadow-xs transition"
                >
                  Save Targets
                </button>
              </div>
            </div>
          </form>
        )}

        {/* Targets Table */}
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-50/80 border-b border-slate-200 text-slate-600 font-semibold uppercase tracking-wider">
              <tr>
                <th className="py-2.5 px-4">Category</th>
                <th className="py-2.5 px-4">Metric / Invariant</th>
                <th className="py-2.5 px-4">Configured Engineering Target</th>
                <th className="py-2.5 px-4">Measured Observation</th>
                <th className="py-2.5 px-4">Outcome</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 font-mono text-xs">
              {data?.targets_evaluation?.map((t: any, idx: number) => (
                <tr key={idx} className="hover:bg-slate-50/50 transition">
                  <td className="py-2.5 px-4 font-sans text-slate-500 font-medium">{t.category}</td>
                  <td className="py-2.5 px-4 font-sans text-[#102A56] font-semibold">{t.name}</td>
                  <td className="py-2.5 px-4 text-blue-600 font-bold">{t.target}</td>
                  <td className="py-2.5 px-4 text-slate-700">{t.actual}</td>
                  <td className="py-2.5 px-4">
                    <span
                      className={`text-[10px] font-bold px-2 py-0.5 rounded-full border ${
                        t.passed
                          ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                          : 'bg-rose-50 text-rose-700 border-rose-200'
                      }`}
                    >
                      {t.passed ? 'TARGET MET' : 'CRITERIA UNMET'}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* ── Slowest Endpoints Table & Recent Errors ── */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Slow Endpoints */}
        <div className="fintech-card p-5 space-y-3">
          <h3 className="text-sm font-bold text-[#102A56] flex items-center gap-2">
            <Layers className="w-4 h-4 text-blue-600" />
            <span>Endpoint Latency Rankings (Normalized Paths)</span>
          </h3>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50/80 border-b border-slate-200 text-slate-600 font-semibold uppercase tracking-wider">
                <tr>
                  <th className="py-2 px-3">Method & Path</th>
                  <th className="py-2 px-3">Calls</th>
                  <th className="py-2 px-3">Avg Latency</th>
                  <th className="py-2 px-3">p95 Latency</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 font-mono text-[11px]">
                {data?.api.slowest_endpoints?.length > 0 ? (
                  data.api.slowest_endpoints.map((ep: any, idx: number) => (
                    <tr key={idx} className="hover:bg-slate-50/50">
                      <td className="py-2 px-3 font-sans font-medium text-slate-800 flex items-center gap-1.5">
                        <span className="px-1.5 py-0.5 rounded text-[9px] font-bold bg-slate-100 text-slate-700">
                          {ep.method}
                        </span>
                        <span className="truncate max-w-xs">{ep.endpoint}</span>
                      </td>
                      <td className="py-2 px-3 text-slate-600">{ep.total_calls}</td>
                      <td className="py-2 px-3 text-slate-700 font-semibold">{ep.avg_duration_ms} ms</td>
                      <td className="py-2 px-3 text-blue-600 font-bold">{ep.p95_duration_ms} ms</td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan={4} className="py-6 text-center text-slate-400 font-sans">
                      Awaiting endpoint traffic...
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* Redacted Error Logs */}
        <div className="fintech-card p-5 space-y-3">
          <h3 className="text-sm font-bold text-[#102A56] flex items-center gap-2">
            <AlertCircle className="w-4 h-4 text-rose-600" />
            <span>Telemetry Error Inspector (Sensitive Data Redacted)</span>
          </h3>
          <div className="space-y-2 max-h-72 overflow-y-auto">
            {data?.api.recent_errors?.length > 0 ? (
              data.api.recent_errors.map((err: any, idx: number) => (
                <div key={idx} className="p-3 rounded-xl bg-slate-50 border border-slate-200 text-xs space-y-1">
                  <div className="flex items-center justify-between text-slate-500 text-[10px] font-mono">
                    <span className="font-bold text-rose-600">{err.type} (HTTP {err.status_code})</span>
                    <span>{new Date(err.time).toLocaleTimeString()}</span>
                  </div>
                  <p className="font-sans text-slate-700 text-[11px] font-medium break-all">{err.message}</p>
                  {err.endpoint && (
                    <span className="text-[10px] font-mono text-slate-400 block">Path: {err.endpoint}</span>
                  )}
                </div>
              ))
            ) : (
              <div className="py-12 text-center text-xs text-slate-400">
                Zero application errors logged in the current window!
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
