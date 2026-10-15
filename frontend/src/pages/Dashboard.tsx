import React, { useEffect, useState } from 'react';
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
} from 'lucide-react';
import {
  PieChart,
  Pie,
  Cell,
  ResponsiveContainer,
  Tooltip,
} from 'recharts';

export const Dashboard: React.FC = () => {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [liveStreamEvents, setLiveStreamEvents] = useState<any[]>([]);

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
          <div className="w-8 h-8 border-4 border-indigo-500/20 border-t-indigo-500 rounded-full animate-spin" />
          <p className="text-xs text-slate-400">Loading live platform metrics...</p>
        </div>
      </div>
    );
  }

  const { kpis, state_distribution, rail_health, compliance_summary } = data;
  const STATE_COLORS: Record<string, string> = {
    SETTLED: '#10b981',
    SUBMITTED: '#3b82f6',
    AUTHORISED: '#6366f1',
    SCREENING: '#8b5cf6',
    VALIDATED: '#06b6d4',
    CREATED: '#94a3b8',
    REVIEW: '#f59e0b',
    BLOCKED: '#ef4444',
    FAILED: '#f43f5e',
  };

  return (
    <div className="space-y-8 animate-in fade-in duration-300">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-white">Executive Command Centre</h1>
          <p className="text-sm text-slate-400">
            Real-time multi-rail payment telemetry, compliance status, and rail health
          </p>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs text-slate-400 font-mono">Auto-refreshed live (5s)</span>
        </div>
      </div>

      {/* ── KPI Cards ── */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Total Volume */}
        <div className="glass-panel p-5 rounded-2xl relative overflow-hidden group">
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-xs font-semibold uppercase tracking-wider">Processed Volume</span>
            <div className="p-2 rounded-lg bg-indigo-500/10 text-indigo-400">
              <CreditCard className="w-4 h-4" />
            </div>
          </div>
          <div className="text-2xl font-bold text-white tracking-tight">
            {kpis.total_volume.toLocaleString()} txs
          </div>
          <div className="mt-2 flex items-center text-xs text-emerald-400 gap-1">
            <TrendingUp className="w-3.5 h-3.5" />
            <span>Success rate {kpis.success_rate_pct}%</span>
          </div>
        </div>

        {/* Processed Value */}
        <div className="glass-panel p-5 rounded-2xl relative overflow-hidden group">
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-xs font-semibold uppercase tracking-wider">Total Value (INR)</span>
            <div className="p-2 rounded-lg bg-emerald-500/10 text-emerald-400">
              <DollarSign className="w-4 h-4" />
            </div>
          </div>
          <div className="text-2xl font-bold text-white tracking-tight">
            ₹{(kpis.total_value_minor / 100).toLocaleString('en-IN', { maximumFractionDigits: 0 })}
          </div>
          <div className="mt-2 flex items-center text-xs text-slate-400 gap-1 font-mono">
            <span>Avg Settlement: {kpis.avg_settlement_seconds}s</span>
          </div>
        </div>

        {/* Fraud & Sanctions Blocked */}
        <div className="glass-panel p-5 rounded-2xl relative overflow-hidden group">
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-xs font-semibold uppercase tracking-wider">Fraud Blocked</span>
            <div className="p-2 rounded-lg bg-rose-500/10 text-rose-400">
              <ShieldAlert className="w-4 h-4" />
            </div>
          </div>
          <div className="text-2xl font-bold text-rose-400 tracking-tight">
            ₹{(kpis.fraud_blocked_value_minor / 100).toLocaleString('en-IN', { maximumFractionDigits: 0 })}
          </div>
          <div className="mt-2 flex items-center text-xs text-slate-400 gap-1">
            <span>{compliance_summary.sanctions_blocked} sanctions hits stopped</span>
          </div>
        </div>

        {/* Reconciliation Match Rate */}
        <div className="glass-panel p-5 rounded-2xl relative overflow-hidden group">
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-xs font-semibold uppercase tracking-wider">Recon Match Rate</span>
            <div className="p-2 rounded-lg bg-cyan-500/10 text-cyan-400">
              <Activity className="w-4 h-4" />
            </div>
          </div>
          <div className="text-2xl font-bold text-white tracking-tight">
            {kpis.recon_match_rate_pct}%
          </div>
          <div className="mt-2 flex items-center text-xs text-emerald-400 gap-1">
            <CheckCircle className="w-3.5 h-3.5" />
            <span>Automated ledger sync</span>
          </div>
        </div>
      </div>

      {/* ── Rail Health Grid & State Distribution ── */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Rail Health Status Tiles */}
        <div className="lg:col-span-2 glass-panel p-6 rounded-2xl space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-base font-semibold text-white flex items-center gap-2">
              <Zap className="w-4 h-4 text-amber-400" />
              <span>Payment Rails Health & Circuit Breakers</span>
            </h2>
            <span className="text-xs font-mono text-emerald-400">4 Active Adapters</span>
          </div>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 pt-2">
            {rail_health.map((r: any) => {
              const isClosed = r.circuit_breaker_state === 'CLOSED';
              return (
                <div
                  key={r.code}
                  className={`p-4 rounded-xl border transition ${
                    isClosed
                      ? 'bg-slate-900/50 border-slate-800'
                      : 'bg-rose-950/30 border-rose-800/80 shadow-lg shadow-rose-900/20'
                  }`}
                >
                  <div className="flex items-center justify-between mb-2">
                    <span className="font-bold text-sm text-white">{r.code}</span>
                    <span
                      className={`w-2.5 h-2.5 rounded-full ${
                        isClosed ? 'bg-emerald-400 shadow-sm shadow-emerald-400' : 'bg-rose-500 animate-ping'
                      }`}
                    />
                  </div>
                  <div className="text-xs text-slate-400">{r.name.split('(')[0]}</div>
                  <div className="mt-3 flex items-center justify-between text-[11px] font-mono">
                    <span className="text-slate-500">Latency:</span>
                    <span className="text-slate-300">{r.p95_latency_ms}ms</span>
                  </div>
                  <div className="mt-1 flex items-center justify-between text-[11px] font-mono">
                    <span className="text-slate-500">Breaker:</span>
                    <span className={isClosed ? 'text-emerald-400' : 'text-rose-400 font-bold'}>
                      {r.circuit_breaker_state}
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* State Distribution Donut */}
        <div className="glass-panel p-6 rounded-2xl flex flex-col justify-between">
          <h2 className="text-base font-semibold text-white flex items-center gap-2 mb-2">
            <Layers className="w-4 h-4 text-indigo-400" />
            <span>Transaction State Distribution</span>
          </h2>
          <div className="h-44 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={state_distribution}
                  dataKey="count"
                  nameKey="state"
                  cx="50%"
                  cy="50%"
                  innerRadius={45}
                  outerRadius={65}
                  paddingAngle={3}
                >
                  {state_distribution.map((entry: any) => (
                    <Cell
                      key={`cell-${entry.state}`}
                      fill={STATE_COLORS[entry.state] || '#64748b'}
                    />
                  ))}
                </Pie>
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#0f172a',
                    borderColor: '#334155',
                    borderRadius: '0.5rem',
                    color: '#f8fafc',
                  }}
                />
              </PieChart>
            </ResponsiveContainer>
          </div>
          <div className="flex flex-wrap gap-2 text-[11px] text-slate-400 font-mono mt-2 justify-center">
            {state_distribution.slice(0, 5).map((s: any) => (
              <span key={s.state} className="flex items-center gap-1">
                <span
                  className="w-2 h-2 rounded-full"
                  style={{ backgroundColor: STATE_COLORS[s.state] || '#64748b' }}
                />
                <span>{s.state}: {s.count}</span>
              </span>
            ))}
          </div>
        </div>
      </div>

      {/* ── Real-Time Event Stream Viewport ── */}
      <div className="glass-panel p-6 rounded-2xl space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-emerald-400 animate-pulse" />
            <h2 className="text-base font-semibold text-white">Live Payment Stream (Redis Events)</h2>
          </div>
          <span className="text-xs font-mono text-slate-500">Listening to payment_events</span>
        </div>

        <div className="space-y-2">
          {liveStreamEvents.length === 0 ? (
            <div className="p-8 text-center text-xs text-slate-500 font-mono">
              Waiting for new payment events... Create a payment to watch it stream live!
            </div>
          ) : (
            liveStreamEvents.map((ev, idx) => (
              <div
                key={idx}
                className="flex items-center justify-between p-3 rounded-xl bg-slate-900/60 border border-slate-800 text-xs font-mono transition animate-in fade-in slide-in-from-top-2"
              >
                <div className="flex items-center gap-3">
                  <span className="text-indigo-400 font-bold">{ev.event_type || 'PAYMENT_EVENT'}</span>
                  <span className="text-slate-400">ID: {ev.aggregate_id || ev.payment_id || 'N/A'}</span>
                </div>
                <div className="flex items-center gap-4 text-slate-500">
                  <span>{ev.created_at || 'Just now'}</span>
                  <span className="text-emerald-400">CONFIRMED</span>
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
};
