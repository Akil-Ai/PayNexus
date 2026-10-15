import React, { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { api } from '../lib/api';
import {
  TrendingUp,
  CreditCard,
  ShieldAlert,
  Clock,
  DollarSign,
  CheckCircle,
  Activity,
  ArrowUpRight,
  Layers,
  Zap,
  Bot,
  Send,
  Sparkles,
  AlertTriangle,
  XCircle,
  RefreshCw,
  Search,
} from 'lucide-react';
import {
  PieChart,
  Pie,
  Cell,
  ResponsiveContainer,
  Tooltip,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
} from 'recharts';

export const Dashboard: React.FC = () => {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [liveStreamEvents, setLiveStreamEvents] = useState<any[]>([]);

  // Payment Investigation Assistant (AI Feature)
  const [queryInput, setQueryInput] = useState('');
  const [investigating, setInvestigating] = useState(false);
  const [investigationResult, setInvestigationResult] = useState<any>(null);

  const fetchMetrics = async () => {
    try {
      const res = await api.getDashboardMetrics();
      setData(res);
    } catch (err) {
      console.error('Failed to load dashboard metrics:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleInvestigate = async (e?: React.FormEvent, presetQuery?: string) => {
    if (e) e.preventDefault();
    const query = presetQuery || queryInput;
    if (!query.trim()) return;

    setInvestigating(true);
    setInvestigationResult(null);
    try {
      const res = await api.investigateTransaction(query);
      setInvestigationResult(res);
    } catch (err: any) {
      setInvestigationResult({
        summary: `Investigation query failed: ${err.message}`,
        recommended_action: 'Verify server health and try again.',
      });
    } finally {
      setInvestigating(false);
    }
  };

  useEffect(() => {
    fetchMetrics();
    const interval = setInterval(fetchMetrics, 5000);
    return () => clearInterval(interval);
  }, []);

  // Real-time SSE stream
  useEffect(() => {
    const sseUrl = `${import.meta.env.VITE_API_URL ? import.meta.env.VITE_API_URL : ''}/api/v1/stream/payments`;
    let eventSource: EventSource | null = null;
    try {
      eventSource = new EventSource(sseUrl);
      eventSource.addEventListener('payment_update', (event) => {
        try {
          const payload = JSON.parse(event.data);
          setLiveStreamEvents((prev) => [payload, ...prev].slice(0, 8));
        } catch (e) {
          console.error('SSE parse error:', e);
        }
      });
    } catch (e) {
      console.warn('SSE connection failed:', e);
    }

    return () => {
      if (eventSource) eventSource.close();
    };
  }, []);

  if (loading || !data) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="flex flex-col items-center gap-3">
          <div className="w-9 h-9 border-4 border-blue-200 border-t-blue-600 rounded-full animate-spin" />
          <p className="text-xs text-slate-500 font-medium">Loading live platform metrics...</p>
        </div>
      </div>
    );
  }

  const { kpis, state_distribution, rail_health, compliance_summary } = data;
  
  // Calculate the 4 primary transaction metrics required by prompt:
  // 1. Total Transactions, 2. Successful Payments, 3. Pending Payments, 4. Failed Payments
  const stateCounts: Record<string, number> = {};
  state_distribution?.forEach((item: any) => {
    stateCounts[item.state] = item.count;
  });

  const totalTransactions = kpis.total_volume || 0;
  const successfulPayments = (stateCounts['SETTLED'] || 0) + (stateCounts['AUTHORISED'] || 0);
  const pendingPayments = (stateCounts['SUBMITTED'] || 0) + (stateCounts['SCREENING'] || 0) + (stateCounts['VALIDATED'] || 0) + (stateCounts['CREATED'] || 0);
  const failedPayments = (stateCounts['FAILED'] || 0) + (stateCounts['BLOCKED'] || 0) + (stateCounts['REVIEW'] || 0);

  const STATE_COLORS: Record<string, string> = {
    SETTLED: '#10A66A',    // Emerald Green
    SUBMITTED: '#2563EB',  // Electric Blue
    AUTHORISED: '#3B82F6',
    SCREENING: '#8B5CF6',
    VALIDATED: '#06B6D4',
    CREATED: '#94A3B8',
    REVIEW: '#F59E0B',     // Amber
    BLOCKED: '#DC2626',    // Red
    FAILED: '#EF4444',     // Red
  };

  // Mock trend data for volume over time line chart
  const volumeTrend = [
    { time: '09:00', volume: Math.max(12, Math.round(totalTransactions * 0.1)), settled: Math.max(10, Math.round(totalTransactions * 0.09)) },
    { time: '11:00', volume: Math.max(28, Math.round(totalTransactions * 0.25)), settled: Math.max(26, Math.round(totalTransactions * 0.23)) },
    { time: '13:00', volume: Math.max(45, Math.round(totalTransactions * 0.45)), settled: Math.max(41, Math.round(totalTransactions * 0.41)) },
    { time: '15:00', volume: Math.max(68, Math.round(totalTransactions * 0.70)), settled: Math.max(62, Math.round(totalTransactions * 0.64)) },
    { time: '17:00', volume: Math.max(90, Math.round(totalTransactions * 0.88)), settled: Math.max(84, Math.round(totalTransactions * 0.82)) },
    { time: 'Current', volume: totalTransactions, settled: successfulPayments },
  ];

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.25 }}
        className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-white p-6 rounded-2xl border border-slate-200/80 shadow-xs"
      >
        <div>
          <div className="flex items-center gap-2 mb-1">
            <h1 className="text-2xl font-bold tracking-tight text-[#102A56]">Executive Payment Operations</h1>
            <span className="px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-blue-50 text-blue-700 border border-blue-200/60">
              Live Operations
            </span>
          </div>
          <p className="text-sm text-slate-500">
            Real-time multi-rail telemetry, circuit breakers, idempotency, and automated reconciliation
          </p>
        </div>
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-xl bg-slate-50 border border-slate-200 text-xs text-slate-600 font-medium">
            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
            <span>Auto-refreshed live (5s)</span>
          </div>
          <button
            onClick={fetchMetrics}
            className="p-2 rounded-xl bg-white hover:bg-slate-50 border border-slate-200 text-slate-600 transition shadow-2xs hover:text-[#102A56]"
            title="Refresh metrics"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>
      </motion.div>

      {/* ── 4 Primary Dashboard Summary Cards (Staggered Animation) ── */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* 1. Total Transactions */}
        <motion.div
          initial={{ opacity: 0, y: 14 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.25, delay: 0.04 }}
          whileHover={{ y: -3, transition: { duration: 0.15 } }}
          className="fintech-card p-5 relative overflow-hidden group"
        >
          <div className="flex items-center justify-between text-slate-500 mb-3">
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-600">Total Transactions</span>
            <div className="p-2.5 rounded-xl bg-blue-50 text-blue-600 border border-blue-100">
              <CreditCard className="w-4 h-4" />
            </div>
          </div>
          <div className="text-3xl font-extrabold text-[#102A56] tracking-tight">
            {totalTransactions.toLocaleString()}
          </div>
          <div className="mt-2.5 flex items-center justify-between text-xs">
            <span className="text-emerald-600 font-semibold flex items-center gap-1">
              <TrendingUp className="w-3.5 h-3.5" />
              {kpis.success_rate_pct}% success rate
            </span>
            <span className="text-slate-400 font-mono text-[11px]">Vol: ₹{(kpis.total_value_minor / 100).toLocaleString('en-IN', { maximumFractionDigits: 0 })}</span>
          </div>
        </motion.div>

        {/* 2. Successful Payments */}
        <motion.div
          initial={{ opacity: 0, y: 14 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.25, delay: 0.08 }}
          whileHover={{ y: -3, transition: { duration: 0.15 } }}
          className="fintech-card p-5 relative overflow-hidden group"
        >
          <div className="flex items-center justify-between text-slate-500 mb-3">
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-600">Successful Payments</span>
            <div className="p-2.5 rounded-xl bg-emerald-50 text-[#10A66A] border border-emerald-100">
              <CheckCircle className="w-4 h-4" />
            </div>
          </div>
          <div className="text-3xl font-extrabold text-[#10A66A] tracking-tight">
            {successfulPayments.toLocaleString()}
          </div>
          <div className="mt-2.5 flex items-center justify-between text-xs">
            <span className="text-slate-500 font-medium">Settled & Authorised</span>
            <span className="text-slate-400 font-mono text-[11px]">Avg: {kpis.avg_settlement_seconds}s</span>
          </div>
        </motion.div>

        {/* 3. Pending Payments */}
        <motion.div
          initial={{ opacity: 0, y: 14 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.25, delay: 0.12 }}
          whileHover={{ y: -3, transition: { duration: 0.15 } }}
          className="fintech-card p-5 relative overflow-hidden group"
        >
          <div className="flex items-center justify-between text-slate-500 mb-3">
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-600">Pending Payments</span>
            <div className="p-2.5 rounded-xl bg-amber-50 text-amber-600 border border-amber-100">
              <Clock className="w-4 h-4" />
            </div>
          </div>
          <div className="text-3xl font-extrabold text-[#F59E0B] tracking-tight">
            {pendingPayments.toLocaleString()}
          </div>
          <div className="mt-2.5 flex items-center justify-between text-xs">
            <span className="text-slate-500 font-medium">In transit / screening</span>
            <span className="text-amber-700 bg-amber-50 px-2 py-0.5 rounded text-[10px] font-bold">Active</span>
          </div>
        </motion.div>

        {/* 4. Failed Payments */}
        <motion.div
          initial={{ opacity: 0, y: 14 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.25, delay: 0.16 }}
          whileHover={{ y: -3, transition: { duration: 0.15 } }}
          className="fintech-card p-5 relative overflow-hidden group"
        >
          <div className="flex items-center justify-between text-slate-500 mb-3">
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-600">Failed / Blocked</span>
            <div className="p-2.5 rounded-xl bg-red-50 text-red-600 border border-red-100">
              <XCircle className="w-4 h-4" />
            </div>
          </div>
          <div className="text-3xl font-extrabold text-[#DC2626] tracking-tight">
            {failedPayments.toLocaleString()}
          </div>
          <div className="mt-2.5 flex items-center justify-between text-xs">
            <span className="text-red-600 font-medium">{compliance_summary.sanctions_blocked} sanctions blocked</span>
            <span className="text-slate-400 font-mono text-[11px]">₹{(kpis.fraud_blocked_value_minor / 100).toLocaleString('en-IN', { maximumFractionDigits: 0 })}</span>
          </div>
        </motion.div>
      </div>

      {/* ── Charts: Payment Volume Over Time & Status Distribution Donut ── */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Line Chart: Payment Volume Over Time */}
        <div className="lg:col-span-2 fintech-card p-6">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h2 className="text-base font-bold text-[#102A56] flex items-center gap-2">
                <TrendingUp className="w-4 h-4 text-blue-600" />
                <span>Payment Volume Over Time</span>
              </h2>
              <p className="text-xs text-slate-500">Hourly throughput and settlement rate</p>
            </div>
            <div className="flex items-center gap-3 text-xs font-medium">
              <span className="flex items-center gap-1.5 text-slate-600">
                <span className="w-2.5 h-2.5 rounded-full bg-blue-600" />
                Total Volume
              </span>
              <span className="flex items-center gap-1.5 text-slate-600">
                <span className="w-2.5 h-2.5 rounded-full bg-[#10A66A]" />
                Settled
              </span>
            </div>
          </div>
          <div className="h-56 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={volumeTrend}>
                <CartesianGrid strokeDasharray="3 3" stroke="#F1F5F9" />
                <XAxis dataKey="time" stroke="#94A3B8" fontSize={11} tickLine={false} />
                <YAxis stroke="#94A3B8" fontSize={11} tickLine={false} axisLine={false} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#FFFFFF',
                    borderColor: '#E2E8F0',
                    borderRadius: '0.75rem',
                    color: '#102A56',
                    boxShadow: '0 4px 12px rgba(16, 42, 86, 0.08)',
                  }}
                />
                <Line
                  type="monotone"
                  dataKey="volume"
                  name="Total Volume"
                  stroke="#2563EB"
                  strokeWidth={2.5}
                  dot={{ r: 3, fill: '#2563EB' }}
                  activeDot={{ r: 5 }}
                />
                <Line
                  type="monotone"
                  dataKey="settled"
                  name="Settled"
                  stroke="#10A66A"
                  strokeWidth={2.5}
                  dot={{ r: 3, fill: '#10A66A' }}
                  activeDot={{ r: 5 }}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Donut Chart: Transaction Status Distribution */}
        <div className="fintech-card p-6 flex flex-col justify-between">
          <div>
            <h2 className="text-base font-bold text-[#102A56] flex items-center gap-2 mb-1">
              <Layers className="w-4 h-4 text-blue-600" />
              <span>Status Distribution</span>
            </h2>
            <p className="text-xs text-slate-500 mb-3">Live transaction states</p>
          </div>
          <div className="h-44 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={state_distribution}
                  dataKey="count"
                  nameKey="state"
                  cx="50%"
                  cy="50%"
                  innerRadius={46}
                  outerRadius={68}
                  paddingAngle={3}
                >
                  {state_distribution.map((entry: any) => (
                    <Cell
                      key={`cell-${entry.state}`}
                      fill={STATE_COLORS[entry.state] || '#94A3B8'}
                    />
                  ))}
                </Pie>
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#FFFFFF',
                    borderColor: '#E2E8F0',
                    borderRadius: '0.5rem',
                    color: '#102A56',
                    boxShadow: '0 4px 12px rgba(16, 42, 86, 0.08)',
                  }}
                />
              </PieChart>
            </ResponsiveContainer>
          </div>
          <div className="flex flex-wrap gap-2 text-[11px] text-slate-600 font-medium mt-2 justify-center">
            {state_distribution.slice(0, 5).map((s: any) => (
              <span key={s.state} className="flex items-center gap-1.5 px-2 py-0.5 rounded-md bg-slate-50 border border-slate-200/60">
                <span
                  className="w-2 h-2 rounded-full"
                  style={{ backgroundColor: STATE_COLORS[s.state] || '#94A3B8' }}
                />
                <span className="font-mono">{s.state}:</span>
                <span className="font-bold text-[#102A56]">{s.count}</span>
              </span>
            ))}
          </div>
        </div>
      </div>

      {/* ── Payment Network Health Panel ── */}
      <div className="fintech-card p-6 space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-base font-bold text-[#102A56] flex items-center gap-2">
              <Zap className="w-4 h-4 text-amber-500" />
              <span>Payment Network Health & Circuit Breakers</span>
            </h2>
            <p className="text-xs text-slate-500">Real-time status of payment integration adapters</p>
          </div>
          <span className="text-xs font-semibold px-2.5 py-1 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200">
            {rail_health.length} Active Rails
          </span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4 pt-1">
          {rail_health.map((r: any) => {
            const isClosed = r.circuit_breaker_state === 'CLOSED';
            return (
              <div
                key={r.code}
                className={`p-4 rounded-xl border transition ${
                  isClosed
                    ? 'bg-slate-50/70 border-slate-200 hover:border-slate-300'
                    : 'bg-red-50/50 border-red-200'
                }`}
              >
                <div className="flex items-center justify-between mb-2">
                  <span className="font-bold text-sm text-[#102A56]">{r.code}</span>
                  <span
                    className={`inline-flex items-center gap-1 text-[11px] font-semibold px-2 py-0.5 rounded-full ${
                      isClosed
                        ? 'bg-emerald-100 text-[#10A66A]'
                        : 'bg-red-100 text-[#DC2626]'
                    }`}
                  >
                    <span className={`w-1.5 h-1.5 rounded-full ${isClosed ? 'bg-[#10A66A]' : 'bg-[#DC2626]'}`} />
                    {isClosed ? 'Healthy' : 'Open'}
                  </span>
                </div>
                <div className="text-xs text-slate-500 font-medium">{r.name.split('(')[0]}</div>
                <div className="mt-3 flex items-center justify-between text-xs font-mono">
                  <span className="text-slate-500">Latency:</span>
                  <span className="text-slate-700 font-bold">{r.p95_latency_ms}ms</span>
                </div>
                <div className="mt-1 flex items-center justify-between text-xs font-mono">
                  <span className="text-slate-500">Breaker:</span>
                  <span className={isClosed ? 'text-emerald-700 font-semibold' : 'text-red-600 font-bold'}>
                    {r.circuit_breaker_state}
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* ── Payment Investigation Assistant (AI Feature) ── */}
      <div className="fintech-card p-6 border-blue-200/80 bg-gradient-to-br from-white via-blue-50/20 to-slate-50 relative overflow-hidden">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-blue-600 flex items-center justify-center text-white shadow-md shadow-blue-500/20">
              <Bot className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-base font-bold text-[#102A56] flex items-center gap-2">
                <span>Payment Investigation Assistant</span>
                <span className="text-[10px] font-mono font-semibold uppercase px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-800 border border-emerald-200">
                  Deterministic & Evidence-Based
                </span>
              </h2>
              <p className="text-xs text-slate-500">
                Ask operational questions, diagnose stuck payments, inspect reconciliation exceptions, or analyze rail failure rates.
              </p>
            </div>
          </div>

          {/* Quick presets */}
          <div className="flex flex-wrap items-center gap-1.5 text-xs">
            <span className="text-slate-500 text-[11px] font-semibold">Suggestions:</span>
            <button
              type="button"
              onClick={() => {
                setQueryInput('Which simulated payment rail has the highest failure rate?');
                handleInvestigate(undefined, 'Which simulated payment rail has the highest failure rate?');
              }}
              className="px-2.5 py-1 rounded-lg bg-white hover:bg-slate-100 text-slate-700 text-[11px] font-medium border border-slate-200 transition shadow-sm"
            >
              Highest rail failure?
            </button>
            <button
              type="button"
              onClick={() => {
                setQueryInput('Show all reconciliation exceptions and suggested fixes');
                handleInvestigate(undefined, 'Show all reconciliation exceptions and suggested fixes');
              }}
              className="px-2.5 py-1 rounded-lg bg-white hover:bg-slate-100 text-slate-700 text-[11px] font-medium border border-slate-200 transition shadow-sm"
            >
              Recon exceptions?
            </button>
          </div>
        </div>

        {/* Search input form */}
        <form onSubmit={handleInvestigate} className="flex gap-2">
          <div className="relative flex-1">
            <Search className="w-4 h-4 absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400" />
            <input
              type="text"
              value={queryInput}
              onChange={(e) => setQueryInput(e.target.value)}
              placeholder="e.g. Why is transaction in review? Or: Which rail has highest errors?"
              className="w-full pl-10 pr-4 py-2.5 rounded-xl bg-white border border-slate-300 text-sm text-[#102A56] placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-600 transition"
            />
          </div>
          <button
            type="submit"
            disabled={investigating}
            className="px-5 py-2.5 rounded-xl bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white font-medium text-xs flex items-center gap-2 shadow-sm transition"
          >
            {investigating ? (
              <RefreshCw className="w-4 h-4 animate-spin" />
            ) : (
              <Send className="w-4 h-4" />
            )}
            <span>Investigate</span>
          </button>
        </form>

        {/* Investigation Results Display */}
        {investigationResult && (
          <div className="mt-4 p-4 rounded-xl bg-white border border-slate-200 text-xs space-y-3 shadow-sm">
            <div className="flex items-start justify-between gap-4">
              <div>
                <span className="text-[10px] font-mono font-bold text-blue-600 uppercase tracking-wider block mb-1">
                  Findings & Diagnosis
                </span>
                <p className="text-[#102A56] text-sm font-semibold">{investigationResult.summary}</p>
              </div>
              {investigationResult.confidence && (
                <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-blue-50 text-blue-700 border border-blue-200">
                  Confidence: {Math.round(investigationResult.confidence * 100)}%
                </span>
              )}
            </div>

            {investigationResult.recommended_action && (
              <div className="p-3 rounded-lg bg-emerald-50 border border-emerald-200 text-emerald-900">
                <span className="font-bold block text-[11px] uppercase tracking-wide text-[#10A66A]">
                  Recommended Operational Action:
                </span>
                <span>{investigationResult.recommended_action}</span>
              </div>
            )}

            {investigationResult.retry_recommendation && (
              <div className="p-3 rounded-lg bg-blue-50 border border-blue-200 text-blue-900">
                <span className="font-bold block text-[11px] uppercase tracking-wide text-blue-700">
                  Intelligent Retry Recommendation:
                </span>
                <span>
                  {investigationResult.retry_recommendation.policy} — {investigationResult.retry_recommendation.reason}
                </span>
              </div>
            )}

            {investigationResult.evidence && (
              <div className="mt-2">
                <span className="text-[10px] font-mono text-slate-500 uppercase block mb-1">
                  Structured Evidence:
                </span>
                <pre className="p-3 rounded-lg bg-slate-50 border border-slate-200 text-[11px] text-slate-700 font-mono overflow-x-auto">
                  {JSON.stringify(investigationResult.evidence, null, 2)}
                </pre>
              </div>
            )}
          </div>
        )}
      </div>

      {/* ── Real-Time Event Stream Viewport ── */}
      <div className="fintech-card p-6 space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-[#10A66A] animate-pulse" />
            <h2 className="text-base font-bold text-[#102A56]">Live Payment Stream (Telemetry Events)</h2>
          </div>
          <span className="text-xs font-mono text-slate-500">Listening to payment_events</span>
        </div>

        <div className="space-y-2">
          {liveStreamEvents.length === 0 ? (
            <div className="p-8 text-center text-xs text-slate-500 font-mono bg-slate-50/50 rounded-xl border border-slate-100">
              Waiting for new payment events... Initiate a payment to watch it stream live!
            </div>
          ) : (
            liveStreamEvents.map((ev, idx) => (
              <div
                key={idx}
                className="flex items-center justify-between p-3 rounded-xl bg-slate-50 hover:bg-slate-100/80 border border-slate-200 text-xs font-mono transition"
              >
                <div className="flex items-center gap-3">
                  <span className="text-blue-600 font-bold">{ev.event_type || 'PAYMENT_EVENT'}</span>
                  <span className="text-slate-600">ID: {ev.aggregate_id || ev.payment_id || 'N/A'}</span>
                </div>
                <div className="flex items-center gap-4 text-slate-500">
                  <span>{ev.created_at || 'Just now'}</span>
                  <span className="px-2 py-0.5 rounded bg-emerald-100 text-[#10A66A] font-semibold text-[10px]">CONFIRMED</span>
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
};
