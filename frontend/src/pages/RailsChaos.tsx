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
  Cpu,
  Clock,
  Wifi,
  Radio,
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

  const [notice, setNotice] = useState<string | null>(null);
  const [errorBanner, setErrorBanner] = useState<string | null>(null);

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
    setNotice(null);
    setErrorBanner(null);
    try {
      await api.configureRailChaos(selectedRail, {
        latency_ms: latencyMs,
        error_rate: errorRate,
        drop_response_rate: dropResponseRate,
        is_down: isDown,
      });
      setNotice(`Chaos injected into ${selectedRail} mock service successfully.`);
      fetchRails();
      setTimeout(() => setNotice(null), 4000);
    } catch (err: any) {
      setErrorBanner(`Chaos error: ${err.message}`);
    } finally {
      setChaosApplying(false);
    }
  };

  const handleResetBreaker = async (railCode: string) => {
    setNotice(null);
    setErrorBanner(null);
    try {
      await api.resetCircuitBreaker(railCode);
      setNotice(`Circuit breaker for ${railCode} reset to CLOSED!`);
      fetchRails();
      setTimeout(() => setNotice(null), 4000);
    } catch (err: any) {
      setErrorBanner(`Reset error: ${err.message}`);
    }
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto animate-in fade-in duration-200">
      {/* Header */}
      <div className="bg-white p-6 rounded-2xl border border-slate-200/80 shadow-sm flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <h1 className="text-2xl font-bold tracking-tight text-[#102A56] flex items-center gap-2">
              <Cpu className="w-6 h-6 text-blue-600" />
              <span>Payment Networks & Integration Adapters</span>
            </h1>
            <span className="px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200/60">
              4 Mock Adapters Online
            </span>
          </div>
          <p className="text-sm text-slate-500">
            Monitor adapter connection health, response latencies, and circuit breakers. Inject simulated faults to verify automated failover routing.
          </p>
        </div>
      </div>

      {/* Notification Toast Banners */}
      {notice && (
        <div className="p-4 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs font-semibold flex items-center justify-between shadow-xs animate-in fade-in">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
            <span>{notice}</span>
          </div>
          <button onClick={() => setNotice(null)} className="text-emerald-700 hover:text-emerald-950 font-bold">×</button>
        </div>
      )}

      {errorBanner && (
        <div className="p-4 rounded-xl bg-rose-50 border border-rose-200 text-rose-800 text-xs font-semibold flex items-center justify-between shadow-xs animate-in fade-in">
          <div className="flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 text-rose-600 shrink-0" />
            <span>{errorBanner}</span>
          </div>
          <button onClick={() => setErrorBanner(null)} className="text-rose-700 hover:text-rose-950 font-bold">×</button>
        </div>
      )}

      {/* ── Payment Network Adapter Cards (UPI, Cards, Bank Transfers/NEFT, Digital Wallets/SWIFT) ── */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {rails.map((r) => {
          const cb = r.circuit_breaker;
          const isOpen = cb.state === 'OPEN';
          const isSelected = selectedRail === r.code;
          return (
            <div
              key={r.code}
              onClick={() => setSelectedRail(r.code)}
              className={`fintech-card p-5 cursor-pointer transition ${
                isSelected
                  ? 'border-blue-600 ring-2 ring-blue-500/20 shadow-md'
                  : 'hover:border-slate-300'
              }`}
            >
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  <div className={`p-2 rounded-xl ${isOpen ? 'bg-red-50 text-red-600' : 'bg-blue-50 text-blue-600'}`}>
                    <Radio className="w-4 h-4" />
                  </div>
                  <div>
                    <span className="font-extrabold text-base text-[#102A56] block">{r.code}</span>
                    <span className="text-[11px] text-slate-500">{r.name.split('(')[0]}</span>
                  </div>
                </div>
                <span
                  className={`text-[10px] px-2.5 py-0.5 rounded-full font-bold font-mono border ${
                    isOpen
                      ? 'bg-red-50 text-[#DC2626] border-red-200'
                      : 'bg-emerald-50 text-[#10A66A] border-emerald-200'
                  }`}
                >
                  {isOpen ? 'Degraded / Open' : 'Connected (Demo)'}
                </span>
              </div>

              <div className="mt-4 pt-3 border-t border-slate-100 text-xs font-mono space-y-1.5">
                <div className="flex justify-between text-slate-500">
                  <span>Connection Status:</span>
                  <span className={isOpen ? 'text-[#DC2626] font-bold' : 'text-[#10A66A] font-semibold'}>
                    {isOpen ? 'Degraded' : 'Connected'}
                  </span>
                </div>
                <div className="flex justify-between text-slate-500">
                  <span>Demo Transactions:</span>
                  <span className="text-[#102A56] font-bold">{r.circuit_breaker?.total_calls || 128} txs</span>
                </div>
                <div className="flex justify-between text-slate-500">
                  <span>Recent Processing Errors:</span>
                  <span className="text-red-600 font-bold">{cb.failure_count || 0}</span>
                </div>
                <div className="flex justify-between text-slate-500">
                  <span>Simulated Latency:</span>
                  <span className="text-slate-700 font-semibold">{r.p95_latency_ms || 120} ms</span>
                </div>
              </div>

              {isOpen && (
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    handleResetBreaker(r.code);
                  }}
                  className="mt-3 w-full py-1.5 rounded-lg bg-red-600 hover:bg-red-700 text-white text-xs font-bold transition shadow-sm"
                >
                  Reset Circuit Breaker
                </button>
              )}
            </div>
          );
        })}
      </div>

      {/* ── Chaos Control Dashboard ── */}
      <div className="fintech-card p-6 space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-3 border-b border-slate-200 gap-2">
          <div className="flex items-center gap-2">
            <Sliders className="w-5 h-5 text-blue-600" />
            <h2 className="text-base font-bold text-[#102A56]">
              Chaos Fault Injection: Target Adapter [{selectedRail}]
            </h2>
          </div>
          <span className="text-xs font-mono font-semibold px-2.5 py-1 rounded-full bg-amber-50 text-amber-800 border border-amber-200">
            Targeting Port: {selectedRail === 'UPI' ? '8101' : selectedRail === 'NEFT' ? '8102' : selectedRail === 'SWIFT' ? '8103' : '8104'}
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 pt-2">
          {/* Latency Slider */}
          <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 space-y-2">
            <div className="flex items-center justify-between text-xs font-bold text-slate-700">
              <span>Added Latency</span>
              <span className="text-blue-600 font-mono">{latencyMs} ms</span>
            </div>
            <input
              type="range"
              min="0"
              max="5000"
              step="50"
              value={latencyMs}
              onChange={(e) => setLatencyMs(Number(e.target.value))}
              className="w-full accent-blue-600"
            />
            <p className="text-[11px] text-slate-500">Inject artificial network lag before responding</p>
          </div>

          {/* Error Rate Slider */}
          <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 space-y-2">
            <div className="flex items-center justify-between text-xs font-bold text-slate-700">
              <span>Error Rate</span>
              <span className="text-red-600 font-mono">{(errorRate * 100).toFixed(0)}%</span>
            </div>
            <input
              type="range"
              min="0"
              max="1"
              step="0.05"
              value={errorRate}
              onChange={(e) => setErrorRate(Number(e.target.value))}
              className="w-full accent-red-600"
            />
            <p className="text-[11px] text-slate-500">Probability of HTTP 500 error return</p>
          </div>

          {/* Drop Response Rate Slider */}
          <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 space-y-2">
            <div className="flex items-center justify-between text-xs font-bold text-slate-700">
              <span>Drop Response (Idempotency)</span>
              <span className="text-amber-600 font-mono">{(dropResponseRate * 100).toFixed(0)}%</span>
            </div>
            <input
              type="range"
              min="0"
              max="1"
              step="0.05"
              value={dropResponseRate}
              onChange={(e) => setDropResponseRate(Number(e.target.value))}
              className="w-full accent-amber-600"
            />
            <p className="text-[11px] text-slate-500">Rail processes payment but drops response (verifies idempotency retry safety)</p>
          </div>

          {/* Complete Outage Switch */}
          <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 space-y-2 flex flex-col justify-between">
            <div className="flex items-center justify-between text-xs font-bold text-slate-700">
              <span>Adapter Service State</span>
              <span className={isDown ? 'text-red-600 font-bold' : 'text-[#10A66A] font-bold'}>
                {isDown ? 'OUTAGE MODE' : 'ONLINE'}
              </span>
            </div>
            <button
              type="button"
              onClick={() => setIsDown(!isDown)}
              className={`w-full py-2.5 rounded-xl text-xs font-bold transition shadow-sm ${
                isDown
                  ? 'bg-red-600 text-white'
                  : 'bg-white border border-slate-200 text-slate-700 hover:bg-slate-100'
              }`}
            >
              {isDown ? 'Adapter in Outage' : 'Simulate Outage'}
            </button>
            <p className="text-[11px] text-slate-500">Trip circuit breaker instantly and test failover</p>
          </div>
        </div>

        <div className="pt-2 flex items-center justify-end">
          <button
            onClick={handleApplyChaos}
            disabled={chaosApplying}
            className="flex items-center gap-2 px-6 py-2.5 rounded-xl bg-blue-600 hover:bg-blue-700 text-white font-bold text-xs shadow-sm transition disabled:opacity-50"
          >
            <Zap className="w-4 h-4" />
            <span>{chaosApplying ? 'Injecting Chaos...' : `Apply Fault Configuration to ${selectedRail}`}</span>
          </button>
        </div>
      </div>
    </div>
  );
};
