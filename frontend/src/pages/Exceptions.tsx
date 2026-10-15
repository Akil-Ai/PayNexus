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
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-white">Exception Management & DLQ</h1>
        <p className="text-sm text-slate-400">
          Unified exception handling, SLA ageing timers, and Dead-Letter Queue event replay
        </p>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-slate-800 space-x-6">
        <button
          onClick={() => setTab('exceptions')}
          className={`pb-3 text-xs font-semibold tracking-wider uppercase transition flex items-center gap-2 ${
            tab === 'exceptions'
              ? 'text-indigo-400 border-b-2 border-indigo-500'
              : 'text-slate-400 hover:text-slate-200'
          }`}
        >
          <AlertTriangle className="w-4 h-4" />
          <span>Active Exceptions ({exceptions.length})</span>
        </button>

        <button
          onClick={() => setTab('dlq')}
          className={`pb-3 text-xs font-semibold tracking-wider uppercase transition flex items-center gap-2 ${
            tab === 'dlq'
              ? 'text-indigo-400 border-b-2 border-indigo-500'
              : 'text-slate-400 hover:text-slate-200'
          }`}
        >
          <RotateCcw className="w-4 h-4" />
          <span>Dead-Letter Queue ({dlqEvents.length})</span>
        </button>
      </div>

      {/* ── Active Exceptions Tab ── */}
      {tab === 'exceptions' && (
        <div className="glass-panel rounded-2xl overflow-hidden border border-slate-800">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-900/80 border-b border-slate-800 text-slate-400 font-semibold uppercase tracking-wider">
              <tr>
                <th className="py-3 px-4">Type</th>
                <th className="py-3 px-4">Description</th>
                <th className="py-3 px-4">Priority</th>
                <th className="py-3 px-4">Status</th>
                <th className="py-3 px-4">SLA Window</th>
                <th className="py-3 px-4">Suggested Fix</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 font-mono">
              {exceptions.length === 0 ? (
                <tr>
                  <td colSpan={6} className="text-center py-12 text-slate-500">
                    No open exception cases.
                  </td>
                </tr>
              ) : (
                exceptions.map((e) => (
                  <tr key={e.id} className="hover:bg-slate-800/30">
                    <td className="py-3 px-4">
                      <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-amber-500/20 text-amber-300 border border-amber-500/30">
                        {e.exception_type}
                      </span>
                    </td>
                    <td className="py-3 px-4 font-sans text-slate-200 max-w-sm">{e.description}</td>
                    <td className="py-3 px-4">
                      <span
                        className={`text-[10px] font-bold ${
                          e.priority === 'HIGH' ? 'text-rose-400' : 'text-slate-300'
                        }`}
                      >
                        {e.priority}
                      </span>
                    </td>
                    <td className="py-3 px-4 font-sans text-slate-400">{e.status}</td>
                    <td className="py-3 px-4 text-slate-400 font-sans flex items-center gap-1.5">
                      <Clock className="w-3.5 h-3.5 text-indigo-400" />
                      <span>{e.sla_hours}h SLA</span>
                    </td>
                    <td className="py-3 px-4 font-sans text-indigo-400">{e.suggested_action}</td>
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
            <span className="text-xs text-slate-400 font-mono">
              {selectedDlq.length} events selected for replay
            </span>
            <button
              onClick={handleReplayDlq}
              disabled={selectedDlq.length === 0 || replaying}
              className="flex items-center gap-2 px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-medium text-xs shadow-md transition disabled:opacity-50"
            >
              <RotateCcw className="w-3.5 h-3.5" />
              <span>{replaying ? 'Replaying...' : 'Replay Selected to Main Stream'}</span>
            </button>
          </div>

          <div className="glass-panel rounded-2xl overflow-hidden border border-slate-800">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-900/80 border-b border-slate-800 text-slate-400 font-semibold uppercase tracking-wider">
                <tr>
                  <th className="py-3 px-4 w-10">Select</th>
                  <th className="py-3 px-4">Event ID</th>
                  <th className="py-3 px-4">Payment ID</th>
                  <th className="py-3 px-4">Error Cause</th>
                  <th className="py-3 px-4">Status</th>
                  <th className="py-3 px-4">Logged At</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 font-mono">
                {dlqEvents.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="text-center py-12 text-slate-500">
                      Dead-Letter Queue is empty. No poison messages or unhandled failures.
                    </td>
                  </tr>
                ) : (
                  dlqEvents.map((item) => (
                    <tr key={item.id} className="hover:bg-slate-800/30">
                      <td className="py-3 px-4">
                        <input
                          type="checkbox"
                          checked={selectedDlq.includes(item.id)}
                          onChange={() => handleToggleSelectDlq(item.id)}
                          className="rounded bg-slate-900 border-slate-700 text-indigo-600 focus:ring-0"
                        />
                      </td>
                      <td className="py-3 px-4 text-indigo-400 font-bold">{item.id.slice(0, 8)}...</td>
                      <td className="py-3 px-4 text-slate-300">{item.payment_id?.slice(0, 8)}...</td>
                      <td className="py-3 px-4 font-sans text-rose-300 max-w-sm truncate">
                        {item.error_message}
                      </td>
                      <td className="py-3 px-4">
                        <span
                          className={`text-[10px] px-2 py-0.5 rounded font-bold ${
                            item.replayed
                              ? 'bg-emerald-500/20 text-emerald-400'
                              : 'bg-rose-500/20 text-rose-400'
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
