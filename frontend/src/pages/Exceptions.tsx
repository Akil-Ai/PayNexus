import React, { useState, useEffect } from 'react';
import { api } from '../lib/api';
import {
  AlertTriangle,
  RotateCcw,
  CheckCircle2,
  Clock,
  User,
  Shield,
  Layers,
  Search,
} from 'lucide-react';

export const Exceptions: React.FC = () => {
  const [tab, setTab] = useState<'exceptions' | 'dlq'>('exceptions');
  const [exceptions, setExceptions] = useState<any[]>([]);
  const [dlqEvents, setDlqEvents] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedDlq, setSelectedDlq] = useState<string[]>([]);
  const [replaying, setReplaying] = useState(false);

  const loadData = async () => {
    setLoading(true);
    try {
      const [excs, dlq] = await Promise.all([api.listExceptions(), api.listDlq()]);
      setExceptions(excs);
      setDlqEvents(dlq);
    } catch (err) {
      console.error('Failed to load exceptions/dlq:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleToggleSelectDlq = (id: string) => {
    setSelectedDlq((prev) =>
      prev.includes(id) ? prev.filter((item) => item !== id) : [...prev, id]
    );
  };

  const handleReplayDlq = async () => {
    if (selectedDlq.length === 0) return;
    setReplaying(true);
    try {
      await api.replayDlq(selectedDlq);
      alert(`Successfully replayed ${selectedDlq.length} events back into the payment orchestrator stream!`);
      setSelectedDlq([]);
      loadData();
    } catch (err: any) {
      alert(`DLQ replay failed: ${err.message}`);
    } finally {
      setReplaying(false);
    }
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      <div className="bg-white p-6 rounded-2xl border border-slate-200/80 shadow-xs flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <h1 className="text-2xl font-bold tracking-tight text-[#102A56] flex items-center gap-2">
              <AlertTriangle className="w-6 h-6 text-amber-500" />
              <span>Exception Management & Dead-Letter Queue (DLQ)</span>
            </h1>
            <span className="px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-blue-50 text-blue-700 border border-blue-200/60">
              Operations Hub
            </span>
          </div>
          <p className="text-sm text-slate-500">
            Unified exception handling, SLA ageing timers, poison message isolation, and automated stream replaying
          </p>
        </div>
        <button
          onClick={loadData}
          disabled={loading}
          className="flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-slate-50 hover:bg-slate-100 text-[#102A56] font-semibold text-xs border border-slate-200 shadow-2xs transition"
        >
          <RotateCcw className={`w-3.5 h-3.5 ${loading ? 'animate-spin text-blue-600' : 'text-slate-500'}`} />
          <span>Refresh Queue</span>
        </button>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-slate-200 space-x-6">
        <button
          onClick={() => setTab('exceptions')}
          className={`pb-3 text-xs font-semibold tracking-wider uppercase transition flex items-center gap-2 ${
            tab === 'exceptions'
              ? 'text-blue-600 border-b-2 border-blue-600'
              : 'text-slate-500 hover:text-slate-800'
          }`}
        >
          <AlertTriangle className="w-4 h-4" />
          <span>Active Exceptions ({exceptions.length})</span>
        </button>

        <button
          onClick={() => setTab('dlq')}
          className={`pb-3 text-xs font-semibold tracking-wider uppercase transition flex items-center gap-2 ${
            tab === 'dlq'
              ? 'text-blue-600 border-b-2 border-blue-600'
              : 'text-slate-500 hover:text-slate-800'
          }`}
        >
          <RotateCcw className="w-4 h-4" />
          <span>Dead-Letter Queue ({dlqEvents.length})</span>
        </button>
      </div>

      {/* ── Active Exceptions Tab ── */}
      {tab === 'exceptions' && (
        <div className="fintech-card overflow-hidden">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-50/80 border-b border-slate-200 text-slate-600 font-semibold uppercase tracking-wider">
              <tr>
                <th className="py-3.5 px-4">Type</th>
                <th className="py-3.5 px-4">Description</th>
                <th className="py-3.5 px-4">Priority</th>
                <th className="py-3.5 px-4">Status</th>
                <th className="py-3.5 px-4">SLA Window</th>
                <th className="py-3.5 px-4">Suggested Fix</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {exceptions.length === 0 ? (
                <tr>
                  <td colSpan={6} className="text-center py-12 text-slate-500 font-medium">
                    No open exception cases. All payment operations healthy.
                  </td>
                </tr>
              ) : (
                exceptions.map((e) => (
                  <tr key={e.id} className="hover:bg-blue-50/40 transition">
                    <td className="py-3 px-4">
                      <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-amber-50 text-amber-800 border border-amber-200">
                        {e.exception_type}
                      </span>
                    </td>
                    <td className="py-3 px-4 font-sans text-slate-700 max-w-sm font-medium">{e.description}</td>
                    <td className="py-3 px-4">
                      <span
                        className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${
                          e.priority === 'HIGH' ? 'bg-red-50 text-red-700 border border-red-200' : 'bg-slate-100 text-slate-700'
                        }`}
                      >
                        {e.priority}
                      </span>
                    </td>
                    <td className="py-3 px-4 font-sans text-slate-600 font-medium">{e.status}</td>
                    <td className="py-3 px-4 text-slate-600 font-sans flex items-center gap-1.5 font-medium">
                      <Clock className="w-3.5 h-3.5 text-blue-600" />
                      <span>{e.sla_hours}h SLA</span>
                    </td>
                    <td className="py-3 px-4 font-sans text-blue-600 font-semibold">{e.suggested_action}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      )}

      {/* ── Dead-Letter Queue Tab ── */}
      {tab === 'dlq' && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <span className="text-xs text-slate-500 font-mono font-medium">
              {selectedDlq.length} events selected for replay
            </span>
            <button
              onClick={handleReplayDlq}
              disabled={selectedDlq.length === 0 || replaying}
              className="flex items-center gap-2 px-4 py-2 rounded-xl bg-[#2563EB] hover:bg-blue-700 text-white font-semibold text-xs shadow-xs transition disabled:opacity-50"
            >
              <RotateCcw className={`w-3.5 h-3.5 ${replaying ? 'animate-spin' : ''}`} />
              <span>{replaying ? 'Replaying...' : 'Replay Selected to Main Stream'}</span>
            </button>
          </div>

          <div className="fintech-card overflow-hidden">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50/80 border-b border-slate-200 text-slate-600 font-semibold uppercase tracking-wider">
                <tr>
                  <th className="py-3.5 px-4 w-10">Select</th>
                  <th className="py-3.5 px-4">Event ID</th>
                  <th className="py-3.5 px-4">Payment ID</th>
                  <th className="py-3.5 px-4">Error Cause</th>
                  <th className="py-3.5 px-4">Status</th>
                  <th className="py-3.5 px-4">Logged At</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 font-mono">
                {dlqEvents.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="text-center py-12 text-slate-500 font-sans font-medium">
                      Dead-Letter Queue is empty. No poison messages or unhandled failures.
                    </td>
                  </tr>
                ) : (
                  dlqEvents.map((item) => (
                    <tr key={item.id} className="hover:bg-blue-50/40 transition">
                      <td className="py-3 px-4">
                        <input
                          type="checkbox"
                          checked={selectedDlq.includes(item.id)}
                          onChange={() => handleToggleSelectDlq(item.id)}
                          className="rounded border-slate-300 text-blue-600 focus:ring-blue-500 cursor-pointer"
                        />
                      </td>
                      <td className="py-3 px-4 text-blue-600 font-bold">{item.id.slice(0, 8)}...</td>
                      <td className="py-3 px-4 text-slate-700">{item.payment_id?.slice(0, 8)}...</td>
                      <td className="py-3 px-4 font-sans text-rose-700 max-w-sm truncate font-medium">
                        {item.error_message}
                      </td>
                      <td className="py-3 px-4">
                        <span
                          className={`text-[10px] px-2 py-0.5 rounded-full font-bold border ${
                            item.replayed
                              ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                              : 'bg-rose-50 text-rose-700 border-rose-200'
                          }`}
                        >
                          {item.replayed ? 'REPLAYED' : 'DEAD_LETTER'}
                        </span>
                      </td>
                      <td className="py-3 px-4 text-slate-500 text-[11px]">
                        {new Date(item.created_at).toLocaleString()}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
};
