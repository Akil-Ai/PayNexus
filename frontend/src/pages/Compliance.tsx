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
  Filter,
  Eye,
  Check,
  X,
  Clock,
  FileCheck,
} from 'lucide-react';

export const Compliance: React.FC = () => {
  const [tab, setTab] = useState<'screening' | 'rules' | 'watchlists'>('screening');
  const [queue, setQueue] = useState<any[]>([]);
  const [watchlists, setWatchlists] = useState<any[]>([]);
  const [fraudRules, setFraudRules] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  // Filters
  const [severityFilter, setSeverityFilter] = useState('ALL');
  const [statusFilter, setStatusFilter] = useState('ALL');
  const [searchQuery, setSearchQuery] = useState('');

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
      alert(`Four-Eyes Decision Recorded: ${action}`);
      setApprovalModal(null);
      loadData();
    } catch (err: any) {
      alert(`Approval error: ${err.message}`);
    } finally {
      setActionLoading(false);
    }
  };

  // Label styling helper for compliance requirements:
  // Cleared (Green), Review Required (Amber), Flagged (Red), Pending Verification (Slate/Blue)
  const getComplianceStatusBadge = (result: string, status?: string) => {
    if (result === 'CLEARED' || status === 'CLEARED' || status === 'APPROVED') {
      return (
        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-emerald-50 text-[#10A66A] border border-emerald-200">
          <CheckCircle2 className="w-3 h-3" />
          <span>Cleared</span>
        </span>
      );
    }
    if (result === 'REVIEW' || status === 'REVIEW') {
      return (
        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-amber-50 text-amber-700 border border-amber-300">
          <AlertTriangle className="w-3 h-3" />
          <span>Review Required</span>
        </span>
      );
    }
    if (result === 'BLOCKED' || result === 'FLAGGED' || status === 'FLAGGED') {
      return (
        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-red-50 text-[#DC2626] border border-red-200">
          <XCircle className="w-3 h-3" />
          <span>Flagged</span>
        </span>
      );
    }
    return (
      <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-blue-50 text-blue-700 border border-blue-200">
        <Clock className="w-3 h-3" />
        <span>Pending Verification</span>
      </span>
    );
  };

  // Filter queue
  const filteredQueue = queue.filter((item) => {
    const matchesSearch = !searchQuery || 
      (item.entity_name && item.entity_name.toLowerCase().includes(searchQuery.toLowerCase())) ||
      (item.matched_entry_name && item.matched_entry_name.toLowerCase().includes(searchQuery.toLowerCase()));

    const matchesStatus = statusFilter === 'ALL' || item.result === statusFilter || item.status === statusFilter;
    const matchesSeverity = severityFilter === 'ALL' || 
      (severityFilter === 'HIGH' && (item.match_score >= 80 || item.result === 'BLOCKED')) ||
      (severityFilter === 'MEDIUM' && item.match_score >= 50 && item.match_score < 80) ||
      (severityFilter === 'LOW' && item.match_score < 50);

    return matchesSearch && matchesStatus && matchesSeverity;
  });

  return (
    <div className="space-y-6 max-w-7xl mx-auto animate-in fade-in duration-200">
      {/* Header */}
      <div className="bg-white p-6 rounded-2xl border border-slate-200/80 shadow-sm flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <h1 className="text-2xl font-bold tracking-tight text-[#102A56]">Risk & Sanctions Screening</h1>
            <span className="px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-blue-50 text-blue-700 border border-blue-200/60">
              Deterministic Screening Sim
            </span>
          </div>
          <p className="text-sm text-slate-500">
            Real-time OFAC / UN / EU sanctions fuzzy matching, AML fraud heuristics, and four-eyes maker-checker reviews
          </p>
        </div>
      </div>

      {/* Primary Compliance Overview Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="fintech-card p-4">
          <div className="flex items-center justify-between text-slate-500 mb-2">
            <span className="text-[11px] font-bold uppercase tracking-wider text-slate-600">Screening In Queue</span>
            <div className="p-2 rounded-lg bg-blue-50 text-blue-600">
              <ShieldAlert className="w-4 h-4" />
            </div>
          </div>
          <div className="text-2xl font-extrabold text-[#102A56] font-mono">{queue.length}</div>
          <span className="text-xs text-slate-500 mt-1 block">Awaiting compliance review</span>
        </div>

        <div className="fintech-card p-4">
          <div className="flex items-center justify-between text-slate-500 mb-2">
            <span className="text-[11px] font-bold uppercase tracking-wider text-slate-600">Sanctions Flagged</span>
            <div className="p-2 rounded-lg bg-red-50 text-red-600">
              <XCircle className="w-4 h-4" />
            </div>
          </div>
          <div className="text-2xl font-extrabold text-[#DC2626] font-mono">
            {queue.filter((q) => q.result === 'BLOCKED').length}
          </div>
          <span className="text-xs text-red-600 font-semibold mt-1 block">Fuzzy match &gt; 85%</span>
        </div>

        <div className="fintech-card p-4">
          <div className="flex items-center justify-between text-slate-500 mb-2">
            <span className="text-[11px] font-bold uppercase tracking-wider text-slate-600">Active Fraud Rules</span>
            <div className="p-2 rounded-lg bg-emerald-50 text-[#10A66A]">
              <Sliders className="w-4 h-4" />
            </div>
          </div>
          <div className="text-2xl font-extrabold text-[#102A56] font-mono">
            {fraudRules.filter((r) => r.is_active).length} / {fraudRules.length}
          </div>
          <span className="text-xs text-[#10A66A] font-semibold mt-1 block">Velocity & Geolocation rules</span>
        </div>

        <div className="fintech-card p-4">
          <div className="flex items-center justify-between text-slate-500 mb-2">
            <span className="text-[11px] font-bold uppercase tracking-wider text-slate-600">Watchlist Feeds</span>
            <div className="p-2 rounded-lg bg-blue-50 text-blue-600">
              <ShieldCheck className="w-4 h-4" />
            </div>
          </div>
          <div className="text-2xl font-extrabold text-[#102A56] font-mono">{watchlists.length} lists</div>
          <span className="text-xs text-slate-500 mt-1 block">OFAC, PEP, UN consolidated</span>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-slate-200 space-x-6">
        <button
          onClick={() => setTab('screening')}
          className={`pb-3 text-xs font-bold tracking-wider uppercase transition flex items-center gap-2 ${
            tab === 'screening'
              ? 'text-blue-600 border-b-2 border-blue-600'
              : 'text-slate-500 hover:text-slate-800'
          }`}
        >
          <ShieldAlert className="w-4 h-4" />
          <span>Compliance Review Queue ({queue.length})</span>
        </button>

        <button
          onClick={() => setTab('rules')}
          className={`pb-3 text-xs font-bold tracking-wider uppercase transition flex items-center gap-2 ${
            tab === 'rules'
              ? 'text-blue-600 border-b-2 border-blue-600'
              : 'text-slate-500 hover:text-slate-800'
          }`}
        >
          <Sliders className="w-4 h-4" />
          <span>Fraud Rules Engine ({fraudRules.length})</span>
        </button>

        <button
          onClick={() => setTab('watchlists')}
          className={`pb-3 text-xs font-bold tracking-wider uppercase transition flex items-center gap-2 ${
            tab === 'watchlists'
              ? 'text-blue-600 border-b-2 border-blue-600'
              : 'text-slate-500 hover:text-slate-800'
          }`}
        >
          <ShieldCheck className="w-4 h-4" />
          <span>Sanctions Watchlists ({watchlists.length})</span>
        </button>
      </div>

      {/* ── Screening Queue Tab ── */}
      {tab === 'screening' && (
        <div className="space-y-4">
          {/* Filters Bar */}
          <div className="fintech-card p-4 flex flex-wrap items-center justify-between gap-4">
            <div className="flex flex-wrap items-center gap-3 flex-1 min-w-[280px]">
              <div className="relative flex-1 min-w-[180px]">
                <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder="Filter by entity or watchlist name..."
                  className="w-full pl-9 pr-3 py-1.5 rounded-lg bg-slate-50 border border-slate-200 text-xs text-[#102A56] placeholder-slate-400 focus:outline-none focus:border-blue-600"
                />
              </div>

              <select
                value={severityFilter}
                onChange={(e) => setSeverityFilter(e.target.value)}
                className="bg-slate-50 border border-slate-200 rounded-lg px-3 py-1.5 text-xs text-slate-700 font-semibold focus:outline-none"
              >
                <option value="ALL">All Severities</option>
                <option value="HIGH">High Risk (&ge; 80%)</option>
                <option value="MEDIUM">Medium Risk (50-79%)</option>
                <option value="LOW">Low Risk (&lt; 50%)</option>
              </select>

              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                className="bg-slate-50 border border-slate-200 rounded-lg px-3 py-1.5 text-xs text-slate-700 font-semibold focus:outline-none"
              >
                <option value="ALL">All Statuses</option>
                <option value="BLOCKED">Flagged (BLOCKED)</option>
                <option value="REVIEW">Review Required</option>
                <option value="CLEARED">Cleared</option>
              </select>
            </div>
            <span className="text-xs font-mono text-slate-500 font-medium">
              Showing {filteredQueue.length} records
            </span>
          </div>

          <div className="fintech-card overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-50 border-b border-slate-200 text-slate-600 font-semibold uppercase tracking-wider">
                  <tr>
                    <th className="py-3 px-4">Entity Screened</th>
                    <th className="py-3 px-4">Sanctions Match Result</th>
                    <th className="py-3 px-4">Confidence Score</th>
                    <th className="py-3 px-4">Matched Watchlist</th>
                    <th className="py-3 px-4">Compliance Status</th>
                    <th className="py-3 px-4">Timestamp</th>
                    <th className="py-3 px-4 text-right">Four-Eyes Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {filteredQueue.length === 0 ? (
                    <tr>
                      <td colSpan={7} className="text-center py-12 text-slate-500">
                        No screening records matching filter criteria. All entities currently cleared.
                      </td>
                    </tr>
                  ) : (
                    filteredQueue.map((q) => (
                      <tr key={q.id} className="hover:bg-slate-50/80 transition">
                        <td className="py-3 px-4 font-bold text-[#102A56]">
                          {q.entity_name}
                        </td>
                        <td className="py-3 px-4">
                          {getComplianceStatusBadge(q.result, q.status)}
                        </td>
                        <td className="py-3 px-4 font-bold font-mono text-[#102A56]">
                          {q.match_score}%
                        </td>
                        <td className="py-3 px-4 text-slate-600 font-medium">
                          {q.matched_entry_name || 'OFAC SDN Consolidated'}
                        </td>
                        <td className="py-3 px-4">
                          <span className="px-2 py-0.5 rounded text-[10px] font-bold font-mono bg-slate-100 text-slate-700">
                            {q.status || 'PENDING'}
                          </span>
                        </td>
                        <td className="py-3 px-4 text-slate-500 font-mono text-[11px]">
                          {q.created_at ? new Date(q.created_at).toLocaleTimeString() : 'Recent'}
                        </td>
                        <td className="py-3 px-4 text-right">
                          {q.result === 'REVIEW' && (
                            <button
                              onClick={() => setApprovalModal({ id: q.payment_id, name: q.entity_name })}
                              className="px-3 py-1 rounded-lg bg-blue-600 hover:bg-blue-700 text-white text-xs font-bold shadow-sm transition"
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
        </div>
      )}

      {/* ── Fraud Rules Tab ── */}
      {tab === 'rules' && (
        <div className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {fraudRules.map((r) => (
              <div
                key={r.id}
                className="fintech-card p-5 flex flex-col justify-between space-y-4"
              >
                <div>
                  <div className="flex items-center justify-between mb-1.5">
                    <span className="font-bold text-sm text-[#102A56]">{r.name}</span>
                    <button
                      onClick={() => handleToggleRule(r.id)}
                      className={`px-3 py-1 rounded-full text-[10px] font-mono font-bold transition ${
                        r.is_active
                          ? 'bg-emerald-100 text-[#10A66A] border border-emerald-200'
                          : 'bg-slate-100 text-slate-500 border border-slate-200'
                      }`}
                    >
                      {r.is_active ? 'ACTIVE' : 'DISABLED'}
                    </button>
                  </div>
                  <p className="text-xs text-slate-500">{r.description}</p>
                </div>

                <div className="p-3 rounded-xl bg-slate-50 border border-slate-200 text-xs font-mono text-slate-700 flex items-center justify-between">
                  <span>Risk Score Impact: +{r.risk_score_impact} pts</span>
                  <span className="font-bold text-blue-600">Action: {r.decision_action}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ── Watchlists Tab ── */}
      {tab === 'watchlists' && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {watchlists.map((w) => (
            <div key={w.id} className="fintech-card p-5 space-y-2">
              <div className="flex items-center justify-between">
                <h3 className="font-bold text-sm text-[#102A56]">{w.name}</h3>
                <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-blue-50 text-blue-700 border border-blue-200">
                  v{w.version}
                </span>
              </div>
              <p className="text-xs text-slate-500">{w.description}</p>
              <div className="pt-2 text-xs font-mono text-slate-400">
                Source Provider: {w.source}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Four-Eyes Approval Decision Modal */}
      {approvalModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm p-4 animate-in fade-in">
          <div className="w-full max-w-md bg-white border border-slate-200 rounded-2xl p-6 shadow-2xl space-y-4">
            <h3 className="text-base font-bold text-[#102A56] flex items-center gap-2">
              <UserCheck className="w-5 h-5 text-blue-600" />
              <span>Four-Eyes Maker-Checker Review</span>
            </h3>
            <p className="text-xs text-slate-600">
              You are acting as the independent Checker for flagged entity:{' '}
              <span className="text-[#102A56] font-bold">{approvalModal.name}</span>.
            </p>

            <div>
              <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1.5">
                Audit Justification / Case Notes
              </label>
              <textarea
                rows={3}
                value={approvalNotes}
                onChange={(e) => setApprovalNotes(e.target.value)}
                placeholder="State formal compliance rationale for approval or block..."
                className="w-full bg-slate-50 border border-slate-200 rounded-xl p-3 text-xs text-[#102A56] focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-600"
              />
            </div>

            <div className="flex items-center gap-3 pt-2">
              <button
                onClick={() => handleApprovalAction('APPROVE')}
                disabled={actionLoading}
                className="flex-1 py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white font-bold text-xs shadow-sm transition"
              >
                Approve & Release
              </button>
              <button
                onClick={() => handleApprovalAction('REJECT')}
                disabled={actionLoading}
                className="flex-1 py-2.5 rounded-xl bg-red-600 hover:bg-red-700 text-white font-bold text-xs shadow-sm transition"
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
