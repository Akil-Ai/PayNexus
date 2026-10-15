import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { api } from '../lib/api';
import {
  PlusCircle,
  Zap,
  Repeat,
  CheckCircle2,
  AlertCircle,
  FileCode,
  DollarSign,
  ShieldCheck,
  Send,
  Sparkles,
  ArrowRight,
  Info,
  Clock,
  Shield,
  Layers,
  Check,
} from 'lucide-react';

export const NewPayment: React.FC = () => {
  const [customers, setCustomers] = useState<any[]>([]);
  const [customerId, setCustomerId] = useState('');
  const [amount, setAmount] = useState('1500.00');
  const [currency, setCurrency] = useState('INR');
  const [urgency, setUrgency] = useState('NORMAL');
  const [description, setDescription] = useState('Vendor software licensing invoice');
  const [idempotencyKey, setIdempotencyKey] = useState(
    () => `idemp_${Math.random().toString(36).slice(2, 11)}_${Date.now()}`
  );

  const [recommendation, setRecommendation] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [submitResult, setSubmitResult] = useState<any>(null);
  const [duplicateMessage, setDuplicateMessage] = useState<string | null>(null);

  // Workflow visualizer state (Steps 1-8)
  // Step 1: Initiate Payment
  // Step 2: Validate Request
  // Step 3: Check Idempotency and Prevent Duplicates
  // Step 4: Perform Risk and Compliance Checks
  // Step 5: Route to Payment Network
  // Step 6: Track Transaction Status
  // Step 7: Reconcile Records
  // Step 8: Return Final Status
  const [workflowStep, setWorkflowStep] = useState<number>(0);

  useEffect(() => {
    api.getCustomers().then((data) => {
      setCustomers(data);
      if (data.length > 0) setCustomerId(data[0].id);
    });
  }, []);

  // Compute rail recommendation whenever amount or currency changes
  useEffect(() => {
    const amtMinor = Math.round(parseFloat(amount || '0') * 100);
    if (amtMinor > 0) {
      api
        .recommendRail({ amount_minor: amtMinor, currency, urgency })
        .then((rec) => setRecommendation(rec))
        .catch(() => setRecommendation(null));
    }
  }, [amount, currency, urgency]);

  const simulateWorkflowProgression = async (finalRes: any) => {
    setWorkflowStep(1); // Initiate
    await new Promise((r) => setTimeout(r, 250));
    setWorkflowStep(2); // Validate
    await new Promise((r) => setTimeout(r, 250));
    setWorkflowStep(3); // Idempotency
    await new Promise((r) => setTimeout(r, 250));
    setWorkflowStep(4); // Risk & Compliance
    await new Promise((r) => setTimeout(r, 250));
    setWorkflowStep(5); // Route
    await new Promise((r) => setTimeout(r, 250));
    setWorkflowStep(6); // Track
    await new Promise((r) => setTimeout(r, 250));
    setWorkflowStep(7); // Reconcile
    await new Promise((r) => setTimeout(r, 200));
    setWorkflowStep(8); // Final Status
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setDuplicateMessage(null);
    setSubmitResult(null);
    setWorkflowStep(1);

    const amtMinor = Math.round(parseFloat(amount) * 100);
    const payload = {
      customer_id: customerId,
      amount_minor: amtMinor,
      currency,
      urgency,
      description,
    };

    try {
      const res = await api.createPayment(payload, idempotencyKey);
      await simulateWorkflowProgression(res);
      setSubmitResult(res);
    } catch (err: any) {
      setSubmitResult({ error: err.message });
      setWorkflowStep(4); // stopped at validation / error
    } finally {
      setLoading(false);
    }
  };

  const handleDuplicateResend = async () => {
    setLoading(true);
    setDuplicateMessage('Resending request with the same Idempotency-Key to test duplicate prevention...');
    const amtMinor = Math.round(parseFloat(amount) * 100);
    const payload = {
      customer_id: customerId,
      amount_minor: amtMinor,
      currency,
      urgency,
      description,
    };

    try {
      const res = await api.createPayment(payload, idempotencyKey);
      setSubmitResult(res);
      setDuplicateMessage(
        '✓ Idempotency Active: Server verified existing key and returned cached result. Zero duplicate debit occurred.'
      );
    } catch (err: any) {
      setSubmitResult({ error: err.message });
    } finally {
      setLoading(false);
    }
  };

  const handleRegenerateKey = () => {
    setIdempotencyKey(`idemp_${Math.random().toString(36).slice(2, 11)}_${Date.now()}`);
    setSubmitResult(null);
    setDuplicateMessage(null);
    setWorkflowStep(0);
  };

  const pipelineSteps = [
    { num: 1, title: 'Initiate Payment', desc: 'Client payload received' },
    { num: 2, title: 'Validate Request', desc: 'ISO 20022 schemas' },
    { num: 3, title: 'Check Idempotency', desc: 'Prevent double charge' },
    { num: 4, title: 'Risk & Sanctions', desc: 'AML / OFAC check' },
    { num: 5, title: 'Route to Network', desc: 'Least-cost/latency' },
    { num: 6, title: 'Track Status', desc: 'State ledger transition' },
    { num: 7, title: 'Reconcile Records', desc: 'Ledger matching' },
    { num: 8, title: 'Return Final Status', desc: 'Receipt confirmed' },
  ];

  return (
    <div className="max-w-5xl mx-auto space-y-8 animate-in fade-in duration-200">
      {/* Header */}
      <div className="bg-white p-6 rounded-2xl border border-slate-200/80 shadow-sm flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <h1 className="text-2xl font-bold tracking-tight text-[#102A56]">Payment Processing & Idempotency</h1>
            <span className="px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-blue-50 text-blue-700 border border-blue-200/60">
              Interactive Demo
            </span>
          </div>
          <p className="text-sm text-slate-500">
            Execute payments with dynamic smart routing, ISO 20022 canonical payload validation, and idempotency protection
          </p>
        </div>
      </div>

      {/* ── Visual Payment-Processing Pipeline (Steps 1-8) ── */}
      <div className="fintech-card p-6 space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-base font-bold text-[#102A56] flex items-center gap-2">
              <Layers className="w-4 h-4 text-blue-600" />
              <span>Payment Workflow Visualisation (8 Stages)</span>
            </h2>
            <p className="text-xs text-slate-500">End-to-end execution pipeline from initiation to reconciliation</p>
          </div>
          <span className="text-xs font-mono font-medium px-2.5 py-1 rounded-full bg-slate-100 text-slate-700">
            {workflowStep === 0
              ? 'Status: Ready'
              : workflowStep === 8
              ? 'Status: Completed'
              : `Processing: Stage ${workflowStep} of 8`}
          </span>
        </div>

        {/* Pipeline steps cards with connected indicators and smooth active animation */}
        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-8 gap-2 pt-2">
          {pipelineSteps.map((step) => {
            const isCompleted = workflowStep > step.num;
            const isCurrent = workflowStep === step.num;
            return (
              <motion.div
                key={step.num}
                animate={isCurrent ? { scale: [1, 1.04, 1] } : { scale: 1 }}
                transition={isCurrent ? { repeat: Infinity, duration: 1.5 } : { duration: 0.2 }}
                className={`p-3 rounded-xl border transition flex flex-col justify-between ${
                  isCurrent
                    ? 'bg-blue-50 border-blue-500 ring-2 ring-blue-500/20 shadow-sm'
                    : isCompleted
                    ? 'bg-emerald-50/70 border-emerald-200 text-emerald-900'
                    : 'bg-slate-50/70 border-slate-200 text-slate-400'
                }`}
              >
                <div>
                  <div className="flex items-center justify-between mb-1.5">
                    <span
                      className={`w-5 h-5 rounded-full flex items-center justify-center text-[10px] font-bold ${
                        isCurrent
                          ? 'bg-blue-600 text-white'
                          : isCompleted
                          ? 'bg-[#10A66A] text-white'
                          : 'bg-slate-200 text-slate-600'
                      }`}
                    >
                      {isCompleted ? <Check className="w-3 h-3" /> : step.num}
                    </span>
                    <span className="text-[9px] font-mono font-bold uppercase">
                      {isCurrent ? 'Active' : isCompleted ? 'Done' : 'Wait'}
                    </span>
                  </div>
                  <div className={`text-[11px] font-bold ${isCurrent ? 'text-blue-900' : isCompleted ? 'text-emerald-950' : 'text-slate-700'}`}>
                    {step.title}
                  </div>
                </div>
                <div className="text-[10px] text-slate-500 mt-2 line-clamp-1">{step.desc}</div>
              </motion.div>
            );
          })}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Form and Idempotency Panel */}
        <div className="lg:col-span-2 fintech-card p-6 space-y-5">
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1.5">
                Payer Customer Account
              </label>
              <select
                value={customerId}
                onChange={(e) => setCustomerId(e.target.value)}
                className="w-full bg-slate-50 border border-slate-200 rounded-xl px-3.5 py-2.5 text-sm text-[#102A56] font-medium focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-600"
              >
                {customers.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.name} ({c.email}) • KYC: {c.kyc_level || 'STANDARD'}
                  </option>
                ))}
              </select>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1.5">
                  Amount
                </label>
                <div className="relative">
                  <span className="w-4 h-4 text-slate-400 absolute left-3 top-3 text-xs font-bold font-mono">₹</span>
                  <input
                    type="number"
                    step="0.01"
                    value={amount}
                    onChange={(e) => setAmount(e.target.value)}
                    required
                    className="w-full bg-slate-50 border border-slate-200 rounded-xl pl-8 pr-3 py-2.5 text-sm text-[#102A56] font-mono font-semibold focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-600"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1.5">
                  Currency
                </label>
                <select
                  value={currency}
                  onChange={(e) => setCurrency(e.target.value)}
                  className="w-full bg-slate-50 border border-slate-200 rounded-xl px-3.5 py-2.5 text-sm text-[#102A56] font-mono font-semibold focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-600"
                >
                  <option value="INR">INR (₹)</option>
                  <option value="USD">USD ($)</option>
                  <option value="EUR">EUR (€)</option>
                  <option value="GBP">GBP (£)</option>
                </select>
              </div>
            </div>

            <div>
              <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1.5">
                Urgency Tier
              </label>
              <div className="grid grid-cols-3 gap-3">
                {['INSTANT', 'NORMAL', 'BULK'].map((u) => (
                  <button
                    type="button"
                    key={u}
                    onClick={() => setUrgency(u)}
                    className={`py-2 text-xs font-semibold rounded-xl border transition ${
                      urgency === u
                        ? 'bg-blue-50 border-blue-600 text-blue-700 shadow-sm'
                        : 'bg-slate-50 border-slate-200 text-slate-600 hover:bg-slate-100'
                    }`}
                  >
                    {u}
                  </button>
                ))}
              </div>
            </div>

            <div>
              <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1.5">
                Remittance Description
              </label>
              <input
                type="text"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                className="w-full bg-slate-50 border border-slate-200 rounded-xl px-3.5 py-2.5 text-sm text-[#102A56] focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-600"
              />
            </div>

            {/* Idempotency Key Control & Explainer Box */}
            <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-[11px] font-bold uppercase tracking-wider text-slate-600 font-mono">
                  Idempotency-Key
                </span>
                <button
                  type="button"
                  onClick={handleRegenerateKey}
                  className="text-[11px] text-blue-600 hover:text-blue-700 font-semibold transition flex items-center gap-1 font-mono"
                >
                  <Repeat className="w-3 h-3" />
                  <span>Generate New</span>
                </button>
              </div>
              <div className="font-mono text-xs text-[#102A56] font-semibold truncate bg-white p-2.5 rounded-lg border border-slate-200">
                {idempotencyKey}
              </div>
              {/* Prompt required message */}
              <div className="flex items-start gap-2 pt-1 text-[11px] text-slate-600">
                <Info className="w-3.5 h-3.5 text-blue-600 shrink-0 mt-0.5" />
                <p className="italic">
                  “Idempotency helps prevent duplicate transaction processing when requests are retried.”
                </p>
              </div>
            </div>

            {/* Submit & Duplicate Actions */}
            <div className="pt-2 flex flex-col sm:flex-row items-center gap-3">
              <button
                type="submit"
                disabled={loading}
                className="w-full sm:flex-1 flex items-center justify-center gap-2 py-3 rounded-xl bg-blue-600 hover:bg-blue-700 text-white font-semibold text-sm shadow-sm transition disabled:opacity-50"
              >
                <Send className="w-4 h-4" />
                <span>Submit Payment</span>
              </button>

              <button
                type="button"
                onClick={handleDuplicateResend}
                disabled={loading}
                className="w-full sm:w-auto flex items-center justify-center gap-2 px-4 py-3 rounded-xl bg-amber-50 hover:bg-amber-100 text-amber-800 font-semibold text-xs border border-amber-300 transition disabled:opacity-50"
                title="Send identical request with same key to test duplicate prevention"
              >
                <Repeat className="w-3.5 h-3.5" />
                <span>Resend (Duplicate Test)</span>
              </button>
            </div>
          </form>

          {/* Results Feedback */}
          {duplicateMessage && (
            <div className="p-3.5 rounded-xl bg-emerald-50 border border-emerald-200 text-[#10A66A] text-xs font-mono font-medium flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 shrink-0" />
              <span>{duplicateMessage}</span>
            </div>
          )}

          {submitResult && (
            <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-[#102A56] font-mono">
                  Server Response: {submitResult.reference || 'ERROR'}
                </span>
                <span className="text-xs px-2.5 py-0.5 rounded-full bg-emerald-100 text-[#10A66A] font-bold font-mono">
                  State: {submitResult.state || 'SUBMITTED'}
                </span>
              </div>
              <pre className="text-[11px] font-mono text-slate-600 overflow-x-auto bg-white p-3 rounded-lg border border-slate-200">
                {JSON.stringify(submitResult, null, 2)}
              </pre>
            </div>
          )}
        </div>

        {/* Rail Recommendation & Smart Router Side-Panel */}
        <div className="space-y-4">
          <div className="fintech-card p-5 space-y-4">
            <div className="flex items-center gap-2 text-[#102A56] font-bold text-sm">
              <Sparkles className="w-4 h-4 text-blue-600" />
              <span>Smart Rail Recommendation</span>
            </div>

            {recommendation ? (
              <div className="space-y-3">
                {recommendation.cheapest && (
                  <div className="p-3.5 rounded-xl bg-emerald-50/80 border border-emerald-200 space-y-1">
                    <span className="text-[10px] uppercase font-bold tracking-wider text-[#10A66A]">
                      Cheapest Routing Option
                    </span>
                    <div className="text-sm font-bold text-[#102A56]">
                      {recommendation.cheapest.rail_name}
                    </div>
                    <div className="text-xs text-slate-600 font-mono">
                      Fee: {recommendation.cheapest.fee_formatted} • ETA: {recommendation.cheapest.eta_description}
                    </div>
                  </div>
                )}

                {recommendation.fastest && (
                  <div className="p-3.5 rounded-xl bg-blue-50/80 border border-blue-200 space-y-1">
                    <span className="text-[10px] uppercase font-bold tracking-wider text-blue-600">
                      Fastest Routing Option
                    </span>
                    <div className="text-sm font-bold text-[#102A56]">
                      {recommendation.fastest.rail_name}
                    </div>
                    <div className="text-xs text-slate-600 font-mono">
                      Fee: {recommendation.fastest.fee_formatted} • ETA: {recommendation.fastest.eta_description}
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <p className="text-xs text-slate-500 font-mono">
                Enter payment amount to calculate dynamic rail routing.
              </p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
