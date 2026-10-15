import React, { useEffect, useState } from 'react';
import { api } from '../lib/api';
import {
  CreditCard,
  Search,
  Filter,
  Download,
  X,
  CheckCircle2,
  AlertCircle,
  Clock,
  ArrowRight,
  Shield,
  Layers,
  ChevronRight,
  RefreshCw,
} from 'lucide-react';

export const Payments: React.FC = () => {
  const [payments, setPayments] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [stateFilter, setStateFilter] = useState('');
  const [railFilter, setRailFilter] = useState('');
  const [selectedPayment, setSelectedPayment] = useState<any>(null);
  const [detailLoading, setDetailLoading] = useState(false);

  const fetchPayments = async () => {
    setLoading(true);
    try {
      const res = await api.listPayments({
        state: stateFilter || undefined,
        rail: railFilter || undefined,
        limit: 50,
      });
      setPayments(Array.isArray(res) ? res : res?.items || []);
    } catch (err) {
      console.error('Failed to fetch payments:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchPayments();
  }, [stateFilter, railFilter]);

  const openDetailDrawer = async (p: any) => {
    setDetailLoading(true);
    try {
      const full = await api.getPaymentById(p.id);
      setSelectedPayment(full);
    } catch (err) {
      console.error('Failed to load payment detail:', err);
      setSelectedPayment(p);
    } finally {
      setDetailLoading(false);
    }
  };

  const handleExportCsv = () => {
    if (!payments.length) return;
    const headers = ['ID', 'Reference', 'State', 'Amount_Minor', 'Currency', 'Rail', 'Created_At'];
    const rows = payments.map((p) => [
      p.id,
      p.reference,
      p.state,
      p.amount_minor,
      p.currency,
      p.rail || '',
      p.created_at,
    ]);
    const csvContent =
      'data:text/csv;charset=utf-8,' +
      [headers.join(','), ...rows.map((e) => e.join(','))].join('\n');
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement('a');
    link.setAttribute('href', encodedUri);
    link.setAttribute('download', `paynexus_payments_${new Date().toISOString().slice(0, 10)}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const getBadgeColor = (state: string) => {
    switch (state) {
      case 'SETTLED':
        return 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30';
      case 'SUBMITTED':
      case 'AUTHORISED':
        return 'bg-indigo-500/10 text-indigo-400 border-indigo-500/30';
      case 'REVIEW':
        return 'bg-amber-500/10 text-amber-400 border-amber-500/30';
      case 'BLOCKED':
      case 'FAILED':
        return 'bg-rose-500/10 text-rose-400 border-rose-500/30';
      default:
        return 'bg-slate-800 text-slate-300 border-slate-700';
    }
  };

  return (
    <div className="space-y-6 relative">
      {/* Page Title & Actions */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-white">Payment Operations</h1>
          <p className="text-sm text-slate-400">
            Real-time transaction state ledger, message inspection, and compliance trace
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={fetchPayments}
            className="p-2 rounded-xl bg-slate-800/80 hover:bg-slate-700 text-slate-300 border border-slate-700/60 transition"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          </button>
          <button
            onClick={handleExportCsv}
            className="flex items-center gap-2 px-3 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium border border-slate-700 transition"
          >
            <Download className="w-3.5 h-3.5" />
            <span>Export CSV</span>
          </button>
        </div>
      </div>

      {/* Filters Bar */}
      <div className="glass-panel p-4 rounded-xl flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <Filter className="w-4 h-4 text-slate-400" />
          <select
            value={stateFilter}
            onChange={(e) => setStateFilter(e.target.value)}
            className="bg-slate-900 border border-slate-700 rounded-lg px-3 py-1.5 text-xs text-slate-200 focus:outline-none"
          >
            <option value="">All States</option>
            <option value="CREATED">CREATED</option>
            <option value="VALIDATED">VALIDATED</option>
            <option value="SCREENING">SCREENING</option>
            <option value="AUTHORISED">AUTHORISED</option>
            <option value="SUBMITTED">SUBMITTED</option>
            <option value="SETTLED">SETTLED</option>
            <option value="REVIEW">REVIEW</option>
            <option value="BLOCKED">BLOCKED</option>
            <option value="FAILED">FAILED</option>
          </select>

          <select
            value={railFilter}
            onChange={(e) => setRailFilter(e.target.value)}
            className="bg-slate-900 border border-slate-700 rounded-lg px-3 py-1.5 text-xs text-slate-200 focus:outline-none"
          >
            <option value="">All Rails</option>
            <option value="UPI">UPI</option>
            <option value="NEFT">NEFT</option>
            <option value="SWIFT">SWIFT</option>
            <option value="CARD">CARD</option>
          </select>
        </div>

        <span className="text-xs font-mono text-slate-400">
          Showing {payments.length} payments
        </span>
      </div>

      {/* Table */}
      <div className="glass-panel rounded-2xl overflow-hidden border border-slate-800">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-900/80 border-b border-slate-800 text-slate-400 font-semibold uppercase tracking-wider">
              <tr>
                <th className="py-3.5 px-4">Reference</th>
                <th className="py-3.5 px-4">Amount</th>
                <th className="py-3.5 px-4">Rail</th>
                <th className="py-3.5 px-4">State</th>
                <th className="py-3.5 px-4">Customer</th>
                <th className="py-3.5 px-4">Created</th>
                <th className="py-3.5 px-4 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 font-mono">
              {loading ? (
                <tr>
                  <td colSpan={7} className="text-center py-12 text-slate-500">
                    Loading payments...
                  </td>
                </tr>
              ) : payments.length === 0 ? (
                <tr>
                  <td colSpan={7} className="text-center py-12 text-slate-500">
                    No payments found matching filter criteria.
                  </td>
                </tr>
              ) : (
                payments.map((p) => (
                  <tr
                    key={p.id}
                    onClick={() => openDetailDrawer(p)}
                    className="hover:bg-slate-800/40 cursor-pointer transition"
                  >
                    <td className="py-3 px-4 font-semibold text-slate-100 flex items-center gap-2">
                      <CreditCard className="w-3.5 h-3.5 text-indigo-400" />
                      <span>{p.reference}</span>
                    </td>
                    <td className="py-3 px-4 text-white font-bold">
                      {(p.amount_minor / 100).toLocaleString('en-IN', {
                        minimumFractionDigits: 2,
                      })}{' '}
                      <span className="text-slate-400 text-[10px]">{p.currency}</span>
                    </td>
                    <td className="py-3 px-4 text-slate-300 font-sans font-medium">{p.rail || 'AUTO'}</td>
                    <td className="py-3 px-4">
                      <span
                        className={`inline-block px-2 py-0.5 rounded-full text-[10px] font-semibold border ${getBadgeColor(
                          p.state
                        )}`}
                      >
                        {p.state}
                      </span>
                    </td>
                    <td className="py-3 px-4 text-slate-400 font-sans truncate max-w-xs">
                      {p.customer_id?.slice(0, 8)}...
                    </td>
                    <td className="py-3 px-4 text-slate-500 text-[11px]">
                      {new Date(p.created_at).toLocaleString()}
                    </td>
                    <td className="py-3 px-4 text-right">
                      <ChevronRight className="w-4 h-4 text-slate-500 inline-block" />
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* ── Payment Detail Drawer ── */}
      {selectedPayment && (
        <div className="fixed inset-y-0 right-0 w-full max-w-xl bg-slate-900/95 border-l border-slate-800 shadow-2xl p-6 overflow-y-auto z-50 backdrop-blur-xl animate-in slide-in-from-right duration-200">
          <div className="flex items-center justify-between pb-4 border-b border-slate-800">
            <div>
              <span className="text-xs font-mono text-indigo-400 font-semibold uppercase tracking-wider">
                Transaction Detail
              </span>
              <h2 className="text-lg font-bold text-white">{selectedPayment.reference}</h2>
            </div>
            <button
              onClick={() => setSelectedPayment(null)}
              className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          <div className="mt-6 space-y-6">
            {/* Amount & State Card */}
            <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 flex items-center justify-between">
              <div>
                <span className="text-xs text-slate-500">Gross Settlement Amount</span>
                <div className="text-2xl font-bold text-white font-mono mt-0.5">
                  {(selectedPayment.amount_minor / 100).toLocaleString('en-IN', {
                    minimumFractionDigits: 2,
                  })}{' '}
                  <span className="text-indigo-400 text-sm">{selectedPayment.currency}</span>
                </div>
              </div>
              <span
                className={`px-3 py-1 rounded-full text-xs font-bold font-mono border ${getBadgeColor(
                  selectedPayment.state
                )}`}
              >
                {selectedPayment.state}
              </span>
            </div>

            {/* State Machine Timeline */}
            <div>
              <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-3 flex items-center gap-1.5">
                <Clock className="w-3.5 h-3.5 text-indigo-400" />
                <span>State Machine Transition Audit</span>
              </h3>
              <div className="border-l-2 border-slate-800 ml-3 space-y-4 py-1">
                {(selectedPayment.state_history || [
                  { to_state: selectedPayment.state, actor: 'SYSTEM', reason: 'Initial submission' },
                ]).map((hist: any, idx: number) => (
                  <div key={idx} className="relative pl-5">
                    <span className="absolute -left-[9px] top-1 w-4 h-4 rounded-full bg-slate-900 border-2 border-indigo-500 flex items-center justify-center">
                      <span className="w-1.5 h-1.5 rounded-full bg-indigo-400" />
                    </span>
                    <div className="text-xs font-semibold text-white font-mono">{hist.to_state}</div>
                    <div className="text-[11px] text-slate-400 font-sans mt-0.5">
                      {hist.reason || 'Normal transition'}
                    </div>
                    <div className="text-[10px] text-slate-500 font-mono mt-0.5">
                      Actor: {hist.actor || 'ORCHESTRATOR'}
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Raw vs Canonical Message Preview */}
            <div>
              <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-2">
                Canonical ISO 20022 Representation
              </h3>
              <pre className="p-3 rounded-xl bg-slate-950 border border-slate-800 text-[11px] font-mono text-slate-300 overflow-x-auto max-h-48">
                {JSON.stringify(
                  {
                    id: selectedPayment.id,
                    reference: selectedPayment.reference,
                    end_to_end_id: selectedPayment.end_to_end_id || selectedPayment.reference,
                    amount_minor: selectedPayment.amount_minor,
                    currency: selectedPayment.currency,
                    rail: selectedPayment.rail,
                    state: selectedPayment.state,
                    customer_id: selectedPayment.customer_id,
                  },
                  null,
                  2
                )}
              </pre>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
