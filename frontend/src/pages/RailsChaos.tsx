import React, { useState, useEffect } from 'react';
import { api } from '../lib/api';
import {
  Zap,
  Activity,
  AlertTriangle,
  RotateCcw,
  Sliders,
  ShieldAlert,
  Flame,
  CheckCircle2,
} from 'lucide-react';

export const RailsChaos: React.FC = () => {
  const [rails, setRails] = useState<any[]>([]);
  const [selectedRail, setSelectedRail] = useState('UPI');
  const [loading, setLoading] = useState(true);

  // Chaos controls state
  const [latencyMs, setLatencyMs] = useState(150);
  const [errorRate, setErrorRate] = useState(0.0);
  const [dropResponseRate, setDropResponseRate] = useState(0.0);
  const [isDown, setIsDown] = useState(false);
  const [chaosApplying, setChaosApplying] = useState(false);

  const fetchRails = async () => {
    try {
      const data = await api.listRails();
      setRails(data);
    } catch (err) {
      console.error('Failed to load rails:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchRails();
    const interval = setInterval(fetchRails, 3000); // 3s polling for live circuit breaker updates
    return () => clearInterval(interval);
  }, []);

  const handleApplyChaos = async () => {
    setChaosApplying(true);
    try {
      await api.configureRailChaos(selectedRail, {
        latency_ms: latencyMs,
        error_rate: errorRate,
        drop_response_rate: dropResponseRate,
        is_down: isDown,
      });
      alert(`Chaos injected into ${selectedRail} mock service!`);
      fetchRails();
    } catch (err: any) {
      alert(`Chaos error: ${err.message}`);
    } finally {
      setChaosApplying(false);
    }
  };

  const handleResetBreaker = async (railCode: string) => {
    try {
      await api.resetCircuitBreaker(railCode);
      alert(`Circuit breaker for ${railCode} reset to CLOSED!`);
      fetchRails();
    } catch (err: any) {
      alert(`Reset error: ${err.message}`);
    }
  };

  return (
    <div className="space-y-8 max-w-7xl mx-auto">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2">
          <Flame className="w-6 h-6 text-amber-400" />
          <span>Payment Rails & Chaos Engineering Lab</span>
        </h1>
        <p className="text-sm text-slate-400">
          Inject runtime latency, synthetic faults, packet drops, or simulated outages to observe circuit breaker tripping and failover
        </p>
      </div>

      {/* ── Live Rails Cards ── */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        {rails.map((r) => {
          const cb = r.circuit_breaker;
          const isOpen = cb.state === 'OPEN';
          return (
            <div
              key={r.code}
              onClick={() => setSelectedRail(r.code)}
              className={`p-5 rounded-2xl border cursor-pointer transition ${
                selectedRail === r.code
                  ? 'border-indigo-500 bg-slate-900 shadow-xl shadow-indigo-500/10'
                  : 'border-slate-800 bg-slate-900/50 hover:border-slate-700'
              }`}
            >
              <div className="flex items-center justify-between mb-3">
                <span className="font-bold text-base text-white">{r.code}</span>
                <span
                  className={`text-[10px] px-2 py-0.5 rounded font-mono font-bold ${
                    isOpen
                      ? 'bg-rose-500/20 text-rose-400 animate-pulse border border-rose-500/40'
                      : 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/40'
                  }`}
                >
                  {cb.state}
                </span>
              </div>
              <div className="text-xs text-slate-400 truncate">{r.name}</div>

              <div className="mt-4 pt-3 border-t border-slate-800 text-[11px] font-mono space-y-1">
                <div className="flex justify-between text-slate-400">
                  <span>Failures:</span>
                  <span className="text-white font-bold">{cb.failure_count || 0}</span>
                </div>
                <div className="flex justify-between text-slate-400">
                  <span>Settlement:</span>
                  <span className="text-slate-300">{r.settlement_window}</span>
                </div>
              </div>

              {isOpen && (
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    handleResetBreaker(r.code);
                  }}
                  className="mt-3 w-full py-1.5 rounded-lg bg-rose-600 hover:bg-rose-500 text-white text-[11px] font-medium transition"
                >
                  Reset Breaker
                </button>
              )}
            </div>
          );
        })}
      </div>

      {/* ── Chaos Control Dashboard ── */}
      <div className="glass-panel p-6 rounded-2xl border border-slate-800 space-y-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Sliders className="w-5 h-5 text-indigo-400" />
            <h2 className="text-base font-bold text-white">
              Chaos Injection Controls: Target Rail [{selectedRail}]
            </h2>
          </div>
          <span className="text-xs font-mono text-amber-400">Target: {selectedRail} Mock Service</span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 pt-2">
          {/* Latency Slider */}
          <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 space-y-2">
            <div className="flex items-center justify-between text-xs font-semibold text-slate-300">
              <span>Added Latency</span>
              <span className="text-indigo-400 font-mono">{latencyMs} ms</span>
            </div>
            <input
              type="range"
              min="0"
              max="5000"
              step="50"
              value={latencyMs}
              onChange={(e) => setLatencyMs(Number(e.target.value))}
              className="w-full accent-indigo-500"
            />
            <p className="text-[11px] text-slate-500">Inject artificial network lag before responding</p>
          </div>

          {/* Error Rate Slider */}
          <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 space-y-2">
            <div className="flex items-center justify-between text-xs font-semibold text-slate-300">
              <span>Error Rate</span>
              <span className="text-rose-400 font-mono">{(errorRate * 100).toFixed(0)}%</span>
            </div>
            <input
              type="range"
              min="0"
              max="1"
              step="0.05"
              value={errorRate}
              onChange={(e) => setErrorRate(Number(e.target.value))}
              className="w-full accent-rose-500"
            />
            <p className="text-[11px] text-slate-500">Probability of HTTP 500 error</p>
          </div>

          {/* Drop Response Rate Slider */}
          <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 space-y-2">
            <div className="flex items-center justify-between text-xs font-semibold text-slate-300">
              <span>Drop Response (Idempotency)</span>
              <span className="text-amber-400 font-mono">{(dropResponseRate * 100).toFixed(0)}%</span>
            </div>
            <input
              type="range"
              min="0"
              max="1"
              step="0.05"
              value={dropResponseRate}
              onChange={(e) => setDropResponseRate(Number(e.target.value))}
              className="w-full accent-amber-500"
            />
            <p className="text-[11px] text-slate-500">Processes txn at rail but drops response (tests duplicate safety)</p>
          </div>

          {/* Complete Outage Switch */}
          <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 space-y-2 flex flex-col justify-between">
            <div className="flex items-center justify-between text-xs font-semibold text-slate-300">
              <span>Total Service Down</span>
              <span className={isDown ? 'text-rose-400 font-bold' : 'text-slate-500'}>
                {isDown ? 'OFFLINE' : 'ONLINE'}
              </span>
            </div>
            <button
              type="button"
              onClick={() => setIsDown(!isDown)}
              className={`w-full py-2.5 rounded-lg text-xs font-bold transition ${
                isDown
                  ? 'bg-rose-600 text-white shadow-lg shadow-rose-600/30'
                  : 'bg-slate-800 text-slate-400 hover:text-white'
              }`}
            >
              {isDown ? 'Rail In Outage Mode' : 'Rail Healthy'}
            </button>
            <p className="text-[11px] text-slate-500">Trip circuit breaker instantly and trigger failover</p>
          </div>
        </div>

        <div className="pt-2 flex items-center justify-end">
          <button
            onClick={handleApplyChaos}
            disabled={chaosApplying}
            className="flex items-center gap-2 px-6 py-2.5 rounded-xl bg-amber-600 hover:bg-amber-500 text-white font-semibold text-xs shadow-lg shadow-amber-600/30 transition disabled:opacity-50"
          >
            <Zap className="w-4 h-4" />
            <span>{chaosApplying ? 'Injecting Chaos...' : `Apply Chaos to ${selectedRail}`}</span>
          </button>
        </div>
      </div>
    </div>
  );
};
