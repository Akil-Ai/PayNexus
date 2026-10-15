import React, { useEffect, useState } from 'react';
import { api } from '../lib/api';
import {
  ShieldAlert,
  ShieldCheck,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Plus,
  Sliders,
  UserCheck,
  Search,
} from 'lucide-react';

export const Compliance: React.FC = () => {
  const [tab, setTab] = useState<'screening' | 'watchlists' | 'rules'>('screening');
  const [queue, setQueue] = useState<any[]>([]);
  const [watchlists, setWatchlists] = useState<any[]>([]);
  const [fraudRules, setFraudRules] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  // Approval modal state
  const [approvalModal, setApprovalModal] = useState<any>(null);
  const [approvalNotes, setApprovalNotes] = useState('');
  const [actionLoading, setActionLoading] = useState(false);

  const loadData = async () => {
    setLoading(true);
    try {
      const [q, w, r] = await Promise.all([
        api.getScreeningQueue(),
        api.listWatchlists(),
        api.listFraudRules(),
      ]);
      setQueue(q);
      setWatchlists(w);
      setFraudRules(r);
    } catch (err) {
      console.error('Failed to load compliance data:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleToggleRule = async (ruleId: string) => {
    try {
      await api.toggleFraudRule(ruleId);
      setFraudRules((prev) =>
        prev.map((r) => (r.id === ruleId ? { ...r, is_active: !r.is_active } : r))
      );
    } catch (err: any) {
      alert(`Failed to toggle rule: ${err.message}`);
    }
  };

  const handleApprovalAction = async (action: 'APPROVE' | 'REJECT') => {
    if (!approvalModal) return;
    setActionLoading(true);
    try {
      await api.processApproval(approvalModal.id, action, approvalNotes);
      alert(`Decision recorded: ${action}`);
      setApprovalModal(null);
      loadData();
    } catch (err: any) {
      alert(`Approval error: ${err.message}`);
    } finally {
      setActionLoading(false);
    }
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-white">Compliance & Risk Centre</h1>
        <p className="text-sm text-slate-400">
          Sanctions/AML fuzzy screening, runtime fraud detection rules, and four-eyes maker-checker reviews
        </p>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-slate-800 space-x-6">
        <button
          onClick={() => setTab('screening')}
          className={`pb-3 text-xs font-semibold tracking-wider uppercase transition flex items-center gap-2 ${
            tab === 'screening'
              ? 'text-indigo-400 border-b-2 border-indigo-500'
              : 'text-slate-400 hover:text-slate-200'
          }`}
        >
          <ShieldAlert className="w-4 h-4" />
          <span>Screening Queue ({queue.length})</span>
        </button>

        <button
          onClick={() => setTab('rules')}
          className={`pb-3 text-xs font-semibold tracking-wider uppercase transition flex items-center gap-2 ${
            tab === 'rules'
              ? 'text-indigo-400 border-b-2 border-indigo-500'
              : 'text-slate-400 hover:text-slate-200'
          }`}
        >
          <Sliders className="w-4 h-4" />
          <span>Fraud Rules Engine ({fraudRules.length})</span>
        </button>

        <button
          onClick={() => setTab('watchlists')}
          className={`pb-3 text-xs font-semibold tracking-wider uppercase transition flex items-center gap-2 ${
            tab === 'watchlists'
              ? 'text-indigo-400 border-b-2 border-indigo-500'
              : 'text-slate-400 hover:text-slate-200'
          }`}
        >
          <ShieldCheck className="w-4 h-4" />
          <span>Watchlists ({watchlists.length})</span>
        </button>
      </div>

      {/* ── Screening Queue Tab ── */}
      {tab === 'screening' && (
        <div className="space-y-4">
          <div className="glass-panel rounded-2xl overflow-hidden border border-slate-800">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-900/80 border-b border-slate-800 text-slate-400 font-semibold uppercase tracking-wider">
                <tr>
                  <th className="py-3 px-4">Entity Screened</th>
                  <th className="py-3 px-4">Result</th>
                  <th className="py-3 px-4">Match Score</th>
                  <th className="py-3 px-4">Matched Watchlist Name</th>
                  <th className="py-3 px-4">Review Status</th>
                  <th className="py-3 px-4">Time</th>
                  <th className="py-3 px-4 text-right">Four-Eyes Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 font-mono">
                {queue.length === 0 ? (
                  <tr>
                    <td colSpan={7} className="text-center py-12 text-slate-500">
                      Screening queue is clear. No active sanctions alerts.
                    </td>
                  </tr>
                ) : (
                  queue.map((q) => (
                    <tr key={q.id} className="hover:bg-slate-800/30">
                      <td className="py-3 px-4 font-sans font-semibold text-white">
                        {q.entity_name}
                      </td>
                      <td className="py-3 px-4">
                        <span
                          className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                            q.result === 'BLOCKED'
                              ? 'bg-rose-500/20 text-rose-400 border border-rose-500/30'
                              : 'bg-amber-500/20 text-amber-300 border border-amber-500/30'
                          }`}
                        >
                          {q.result}
                        </span>
                      </td>
                      <td className="py-3 px-4 font-bold text-slate-200">{q.match_score}%</td>
                      <td className="py-3 px-4 font-sans text-slate-300">
                        {q.matched_entry_name || 'Consolidated Watchlist'}
                      </td>
                      <td className="py-3 px-4 font-sans text-slate-400">{q.status || 'PENDING'}</td>
                      <td className="py-3 px-4 text-slate-500 text-[11px]">
                        {q.created_at ? new Date(q.created_at).toLocaleTimeString() : 'N/A'}
                      </td>
                      <td className="py-3 px-4 text-right">
                        {q.result === 'REVIEW' && (
                          <button
                            onClick={() => setApprovalModal({ id: q.payment_id, name: q.entity_name })}
                            className="px-2.5 py-1 rounded bg-indigo-600 hover:bg-indigo-500 text-white text-[11px] font-sans font-medium"
                          >
                            Review & Decide
                          </button>
                        )}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* ── Fraud Rules Tab ── */}
      {tab === 'rules' && (
        <div className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {fraudRules.map((r) => (
              <div
                key={r.id}
                className="glass-panel p-5 rounded-2xl border border-slate-800 flex flex-col justify-between space-y-4"
              >
                <div>
                  <div className="flex items-center justify-between mb-1.5">
                    <span className="font-bold text-sm text-white">{r.name}</span>
                    <button
                      onClick={() => handleToggleRule(r.id)}
                      className={`px-2.5 py-1 rounded-full text-[10px] font-mono font-semibold transition ${
                        r.is_active
                          ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                          : 'bg-slate-800 text-slate-500 border border-slate-700'
                      }`}
                    >
                      {r.is_active ? 'ENABLED' : 'DISABLED'}
                    </button>
                  </div>
                  <p className="text-xs text-slate-400 font-sans">{r.description}</p>
                </div>

                <div className="p-2.5 rounded-xl bg-slate-950 border border-slate-800 text-[11px] font-mono text-indigo-300">
                  Impact: +{r.risk_score_impact} pts • Action: {r.decision_action}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ── Watchlists Tab ── */}
      {tab === 'watchlists' && (
        <div className="glass-panel p-5 rounded-2xl space-y-4">
          {watchlists.map((w) => (
            <div key={w.id} className="p-4 rounded-xl bg-slate-900 border border-slate-800">
              <h3 className="font-bold text-sm text-white">{w.name}</h3>
              <p className="text-xs text-slate-400 mt-0.5">{w.description}</p>
              <div className="mt-2 text-[11px] font-mono text-slate-500">
                Source: {w.source} • Version: {w.version}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Four-Eyes Approval Decision Modal */}
      {approvalModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
          <div className="w-full max-w-md bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-2xl space-y-4">
            <h3 className="text-base font-bold text-white flex items-center gap-2">
              <UserCheck className="w-5 h-5 text-indigo-400" />
              <span>Four-Eyes Maker-Checker Review</span>
            </h3>
            <p className="text-xs text-slate-400">
              You are acting as the independent Checker for flagged entity:{' '}
              <span className="text-white font-semibold">{approvalModal.name}</span>.
            </p>

            <div>
              <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1.5">
                Audit Justification / Notes
              </label>
              <textarea
                rows={3}
                value={approvalNotes}
                onChange={(e) => setApprovalNotes(e.target.value)}
                placeholder="State rationale for approval or rejection..."
                className="w-full bg-slate-950 border border-slate-800 rounded-xl p-3 text-xs text-slate-200 focus:outline-none focus:border-indigo-500"
              />
            </div>

            <div className="flex items-center gap-3 pt-2">
              <button
                onClick={() => handleApprovalAction('APPROVE')}
                disabled={actionLoading}
                className="flex-1 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white font-medium text-xs shadow-md transition"
              >
                Approve & Release
              </button>
              <button
                onClick={() => handleApprovalAction('REJECT')}
                disabled={actionLoading}
                className="flex-1 py-2 rounded-xl bg-rose-600 hover:bg-rose-500 text-white font-medium text-xs shadow-md transition"
              >
                Confirm Block
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
