import React, { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
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
  ChevronLeft,
  Calendar,
  Building,
  User,
  Check,
  RotateCcw,
} from 'lucide-react';

export const Payments: React.FC = () => {
  const [payments, setPayments] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [stateFilter, setStateFilter] = useState('');
  const [railFilter, setRailFilter] = useState('');
  const [dateFilter, setDateFilter] = useState('');
  const [selectedPayment, setSelectedPayment] = useState<any>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [currentPage, setCurrentPage] = useState(1);
  const itemsPerPage = 10;

  const fetchPayments = async () => {
    setLoading(true);
    try {
      const res = await api.listPayments({
        state: stateFilter || undefined,
        rail: railFilter || undefined,
        limit: 100,
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
    if (!filteredPayments.length) return;
    const headers = ['Transaction_ID', 'Reference', 'Customer_Merchant', 'Amount_INR', 'Payment_Method', 'Payment_Network', 'Status', 'Date_Time'];
    const rows = filteredPayments.map((p) => [
      p.id,
      p.reference,
      p.customer_id || 'Retail Client',
      (p.amount_minor / 100).toFixed(2),
      p.payment_method || 'Digital Direct',
      p.rail || 'AUTO',
      p.state,
      p.created_at,
    ]);
    const csvContent =
      'data:text/csv;charset=utf-8,' +
      [headers.join(','), ...rows.map((e) => e.join(','))].join('\n');
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement('a');
    link.setAttribute('href', encodedUri);
    link.setAttribute('download', `paynexus_transactions_${new Date().toISOString().slice(0, 10)}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  // Status badges: Success: green, Pending: amber, Failed: red, Reversed: grey
  const getBadgeStyle = (state: string) => {
    switch (state) {
      case 'SETTLED':
      case 'SUCCESS':
        return 'bg-emerald-50 text-[#10A66A] border-emerald-200';
      case 'AUTHORISED':
      case 'SUBMITTED':
      case 'SCREENING':
      case 'VALIDATED':
      case 'CREATED':
      case 'PENDING':
        return 'bg-amber-50 text-[#F59E0B] border-amber-200';
      case 'REVIEW':
        return 'bg-amber-100 text-amber-800 border-amber-300';
      case 'BLOCKED':
      case 'FAILED':
        return 'bg-red-50 text-[#DC2626] border-red-200';
      case 'REVERSED':
      case 'CANCELLED':
        return 'bg-slate-100 text-slate-600 border-slate-300';
      default:
        return 'bg-slate-50 text-slate-600 border-slate-200';
    }
  };

  // Filtering
  const filteredPayments = payments.filter((p) => {
    const q = searchQuery.toLowerCase().trim();
    const matchesSearch = !q || 
      (p.reference && p.reference.toLowerCase().includes(q)) ||
      (p.id && p.id.toLowerCase().includes(q)) ||
      (p.customer_id && p.customer_id.toLowerCase().includes(q)) ||
      (p.rail && p.rail.toLowerCase().includes(q));

    const matchesDate = !dateFilter || (p.created_at && p.created_at.startsWith(dateFilter));
    return matchesSearch && matchesDate;
  });

  // Pagination
  const totalPages = Math.ceil(filteredPayments.length / itemsPerPage) || 1;
  const paginatedPayments = filteredPayments.slice(
    (currentPage - 1) * itemsPerPage,
    currentPage * itemsPerPage
  );

  return (
    <div className="space-y-6 relative">
      {/* Page Title & Actions */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 bg-white p-6 rounded-2xl border border-slate-200/80 shadow-sm">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <h1 className="text-2xl font-bold tracking-tight text-[#102A56]">Transactions Operations</h1>
            <span className="px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-blue-50 text-blue-700 border border-blue-200/60">
              ISO 20022 Ledger
            </span>
          </div>
          <p className="text-sm text-slate-500">
            Real-time transaction state ledger, multi-column search, audit history, and validation traces
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={fetchPayments}
            className="p-2 rounded-xl bg-white hover:bg-slate-50 text-slate-600 border border-slate-200 transition shadow-sm"
            title="Refresh transactions"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          </button>
          <button
            onClick={handleExportCsv}
            className="flex items-center gap-2 px-3.5 py-2 rounded-xl bg-white hover:bg-slate-50 text-[#102A56] text-xs font-semibold border border-slate-200 transition shadow-sm"
          >
            <Download className="w-3.5 h-3.5 text-blue-600" />
            <span>Export CSV</span>
          </button>
        </div>
      </div>

      {/* Filters Bar */}
      <div className="fintech-card p-4 flex flex-wrap items-center justify-between gap-4">
        <div className="flex flex-wrap items-center gap-3 flex-1 min-w-[280px]">
          {/* Search by transaction ID or merchant */}
          <div className="relative flex-1 min-w-[200px]">
            <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => {
                setSearchQuery(e.target.value);
                setCurrentPage(1);
              }}
              placeholder="Search by transaction ID, reference, or merchant..."
              className="w-full pl-9 pr-3 py-1.5 rounded-lg bg-slate-50 border border-slate-200 text-xs text-[#102A56] placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-600 transition"
            />
          </div>

          {/* Status filter */}
          <select
            value={stateFilter}
            onChange={(e) => {
              setStateFilter(e.target.value);
              setCurrentPage(1);
            }}
            className="bg-slate-50 border border-slate-200 rounded-lg px-3 py-1.5 text-xs text-slate-700 font-medium focus:outline-none focus:border-blue-600"
          >
            <option value="">All Statuses</option>
            <option value="SETTLED">Success (SETTLED)</option>
            <option value="AUTHORISED">Pending (AUTHORISED)</option>
            <option value="SUBMITTED">Pending (SUBMITTED)</option>
            <option value="SCREENING">Pending (SCREENING)</option>
            <option value="REVIEW">Review Required</option>
            <option value="FAILED">Failed (FAILED)</option>
            <option value="BLOCKED">Failed (BLOCKED)</option>
            <option value="REVERSED">Reversed</option>
          </select>

          {/* Rail filter */}
          <select
            value={railFilter}
            onChange={(e) => {
              setRailFilter(e.target.value);
              setCurrentPage(1);
            }}
            className="bg-slate-50 border border-slate-200 rounded-lg px-3 py-1.5 text-xs text-slate-700 font-medium focus:outline-none focus:border-blue-600"
          >
            <option value="">All Networks</option>
            <option value="UPI">UPI</option>
            <option value="NEFT">NEFT</option>
            <option value="SWIFT">SWIFT</option>
            <option value="CARD">CARD</option>
          </select>

          {/* Date filter */}
          <input
            type="date"
            value={dateFilter}
            onChange={(e) => {
              setDateFilter(e.target.value);
              setCurrentPage(1);
            }}
            className="bg-slate-50 border border-slate-200 rounded-lg px-3 py-1.5 text-xs text-slate-700 font-medium focus:outline-none focus:border-blue-600"
          />
          {dateFilter && (
            <button
              onClick={() => setDateFilter('')}
              className="text-xs text-slate-400 hover:text-slate-600"
            >
              Clear date
            </button>
          )}
        </div>

        <span className="text-xs font-mono text-slate-500 font-medium">
          Showing {filteredPayments.length} of {payments.length} transactions
        </span>
      </div>

      {/* Table */}
      <div className="fintech-card overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-50/80 border-b border-slate-200 text-slate-600 font-semibold uppercase tracking-wider">
              <tr>
                <th className="py-3.5 px-4">Transaction ID</th>
                <th className="py-3.5 px-4">Date & Time</th>
                <th className="py-3.5 px-4">Customer / Merchant</th>
                <th className="py-3.5 px-4">Amount</th>
                <th className="py-3.5 px-4">Payment Method</th>
                <th className="py-3.5 px-4">Network</th>
                <th className="py-3.5 px-4">Status</th>
                <th className="py-3.5 px-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {loading ? (
                <tr>
                  <td colSpan={8} className="text-center py-12 text-slate-400 font-medium">
                    Loading transactions ledger...
                  </td>
                </tr>
              ) : paginatedPayments.length === 0 ? (
                <tr>
                  <td colSpan={8} className="text-center py-12 text-slate-500">
                    No transactions found matching your criteria.
                  </td>
                </tr>
              ) : (
                paginatedPayments.map((p) => (
                  <tr
                    key={p.id}
                    onClick={() => openDetailDrawer(p)}
                    className="hover:bg-blue-50/30 cursor-pointer transition"
                  >
                    <td className="py-3 px-4 font-mono font-semibold text-[#102A56] flex items-center gap-2">
                      <CreditCard className="w-3.5 h-3.5 text-blue-600 shrink-0" />
                      <span className="truncate max-w-[130px]" title={p.reference || p.id}>
                        {p.reference || p.id.slice(0, 12)}
                      </span>
                    </td>
                    <td className="py-3 px-4 text-slate-500 font-mono text-[11px] whitespace-nowrap">
                      {new Date(p.created_at).toLocaleString([], { dateStyle: 'short', timeStyle: 'short' })}
                    </td>
                    <td className="py-3 px-4 text-slate-700 font-medium">
                      <div className="flex items-center gap-1.5">
                        <User className="w-3 h-3 text-slate-400 shrink-0" />
                        <span className="truncate max-w-[140px]" title={p.customer_id || 'Retail Customer'}>
                          {p.customer_id || 'Retail Customer'}
                        </span>
                      </div>
                    </td>
                    <td className="py-3 px-4 font-bold text-[#102A56] font-mono">
                      ₹{(p.amount_minor / 100).toLocaleString('en-IN', {
                        minimumFractionDigits: 2,
                      })}{' '}
                      <span className="text-slate-400 text-[10px] font-normal">{p.currency}</span>
                    </td>
                    <td className="py-3 px-4 text-slate-600 font-medium">
                      {p.rail === 'UPI' ? 'Virtual Payment (VPA)' : p.rail === 'CARD' ? 'Credit/Debit Card' : p.rail === 'NEFT' ? 'National Electronic Fund' : 'SWIFT Wire'}
                    </td>
                    <td className="py-3 px-4">
                      <span className="px-2 py-0.5 rounded text-[10px] font-bold font-mono bg-slate-100 text-slate-700 border border-slate-200">
                        {p.rail || 'AUTO'}
                      </span>
                    </td>
                    <td className="py-3 px-4">
                      <span
                        className={`inline-block px-2.5 py-0.5 rounded-full text-[11px] font-semibold border ${getBadgeStyle(
                          p.state
                        )}`}
                      >
                        {p.state === 'SETTLED' ? 'Success' : p.state === 'FAILED' ? 'Failed' : p.state}
                      </span>
                    </td>
                    <td className="py-3 px-4 text-right">
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          openDetailDrawer(p);
                        }}
                        className="px-2 py-1 rounded bg-slate-100 hover:bg-blue-50 text-slate-600 hover:text-blue-600 text-xs font-semibold border border-slate-200 transition"
                      >
                        Details
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination Bar */}
        {filteredPayments.length > itemsPerPage && (
          <div className="flex items-center justify-between px-4 py-3 border-t border-slate-200 bg-slate-50/50">
            <span className="text-xs text-slate-500">
              Page {currentPage} of {totalPages}
            </span>
            <div className="flex items-center gap-2">
              <button
                onClick={() => setCurrentPage((prev) => Math.max(prev - 1, 1))}
                disabled={currentPage === 1}
                className="p-1.5 rounded-lg border border-slate-200 bg-white text-slate-600 disabled:opacity-40 hover:bg-slate-50 transition"
              >
                <ChevronLeft className="w-4 h-4" />
              </button>
              <button
                onClick={() => setCurrentPage((prev) => Math.min(prev + 1, totalPages))}
                disabled={currentPage === totalPages}
                className="p-1.5 rounded-lg border border-slate-200 bg-white text-slate-600 disabled:opacity-40 hover:bg-slate-50 transition"
              >
                <ChevronRight className="w-4 h-4" />
              </button>
            </div>
          </div>
        )}
      </div>

      {/* ── Transaction Detail Drawer (Animated Slide-in) ── */}
      <AnimatePresence>
        {selectedPayment && (
          <>
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.18 }}
              onClick={() => setSelectedPayment(null)}
              className="fixed inset-0 bg-slate-900/30 backdrop-blur-2xs z-40"
            />
            <motion.div
              initial={{ x: '100%', opacity: 0.8 }}
              animate={{ x: 0, opacity: 1 }}
              exit={{ x: '100%', opacity: 0.8 }}
              transition={{ type: 'spring', damping: 28, stiffness: 300 }}
              className="fixed inset-y-0 right-0 w-full max-w-xl bg-white border-l border-slate-200 shadow-2xl p-6 overflow-y-auto z-50"
            >
              <div className="flex items-center justify-between pb-4 border-b border-slate-200">
                <div>
                  <span className="text-xs font-mono text-blue-600 font-semibold uppercase tracking-wider">
                    Transaction Audit Profile
                  </span>
                  <h2 className="text-lg font-bold text-[#102A56]">{selectedPayment.reference}</h2>
                </div>
                <button
                  onClick={() => setSelectedPayment(null)}
                  className="p-1.5 rounded-lg text-slate-400 hover:text-slate-700 hover:bg-slate-100 transition"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>

              <div className="mt-6 space-y-6">
                {/* Amount & State Card */}
                <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 flex items-center justify-between">
                  <div>
                    <span className="text-xs text-slate-500 font-medium">Gross Settlement Amount</span>
                    <div className="text-2xl font-extrabold text-[#102A56] font-mono mt-0.5">
                      ₹{(selectedPayment.amount_minor / 100).toLocaleString('en-IN', {
                        minimumFractionDigits: 2,
                      })}{' '}
                      <span className="text-blue-600 text-sm font-semibold">{selectedPayment.currency}</span>
                    </div>
                  </div>
                  <span
                    className={`px-3 py-1 rounded-full text-xs font-bold border ${getBadgeStyle(
                      selectedPayment.state
                    )}`}
                  >
                    {selectedPayment.state}
                  </span>
                </div>

                {/* Validation & Idempotency Metadata */}
                <div className="p-4 rounded-xl bg-white border border-slate-200 space-y-2 text-xs">
                  <div className="flex justify-between py-1 border-b border-slate-100">
                    <span className="text-slate-500">Internal UUID:</span>
                    <span className="font-mono text-[#102A56] select-all font-semibold">{selectedPayment.id}</span>
                  </div>
                  <div className="flex justify-between py-1 border-b border-slate-100">
                    <span className="text-slate-500">Payment Network Rail:</span>
                    <span className="font-bold text-[#102A56]">{selectedPayment.rail || 'AUTO ROUTED'}</span>
                  </div>
                  <div className="flex justify-between py-1 border-b border-slate-100">
                    <span className="text-slate-500">Customer Identifier:</span>
                    <span className="font-mono text-slate-700">{selectedPayment.customer_id || 'N/A'}</span>
                  </div>
                  <div className="flex justify-between py-1">
                    <span className="text-slate-500">Timestamp:</span>
                    <span className="text-slate-700 font-mono">{new Date(selectedPayment.created_at).toLocaleString()}</span>
                  </div>
                </div>

                {/* State Machine Transition Audit */}
                <div>
                  <h3 className="text-xs font-bold uppercase tracking-wider text-[#102A56] mb-3 flex items-center gap-1.5">
                    <Clock className="w-3.5 h-3.5 text-blue-600" />
                    <span>State Machine Transition Audit</span>
                  </h3>
                  <div className="border-l-2 border-blue-200 ml-3 space-y-4 py-1">
                    {(selectedPayment.state_history || [
                      { to_state: selectedPayment.state, actor: 'SYSTEM', reason: 'Initial submission' },
                    ]).map((hist: any, idx: number) => (
                      <div key={idx} className="relative pl-5">
                        <span className="absolute -left-[9px] top-1 w-4 h-4 rounded-full bg-white border-2 border-blue-600 flex items-center justify-center">
                          <span className="w-1.5 h-1.5 rounded-full bg-blue-600" />
                        </span>
                        <div className="text-xs font-bold text-[#102A56] font-mono">{hist.to_state}</div>
                        <div className="text-[11px] text-slate-600 font-sans mt-0.5">
                          {hist.reason || 'State verified & processed'}
                        </div>
                        <div className="text-[10px] text-slate-400 font-mono mt-0.5">
                          Actor: {hist.actor || 'ORCHESTRATOR'}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Canonical ISO 20022 Representation */}
                <div>
                  <h3 className="text-xs font-bold uppercase tracking-wider text-[#102A56] mb-2">
                    Canonical ISO 20022 Representation (JSON)
                  </h3>
                  <pre className="p-3.5 rounded-xl bg-slate-50 border border-slate-200 text-[11px] font-mono text-slate-700 overflow-x-auto max-h-48">
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
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </div>
  );
};
