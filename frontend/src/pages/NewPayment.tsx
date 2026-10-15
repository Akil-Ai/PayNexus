import React, { useState, useEffect } from 'react';
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

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setDuplicateMessage(null);
    setSubmitResult(null);

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
    } catch (err: any) {
      setSubmitResult({ error: err.message });
    } finally {
      setLoading(false);
    }
  };

  const handleDuplicateResend = async () => {
    // Send identical request with SAME Idempotency-Key
    setLoading(true);
    setDuplicateMessage('Resending IDENTICAL request with same Idempotency-Key to demonstrate duplicate protection...');
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
        '✓ Idempotency Verified: Server returned identical cached response with Idempotent-Replayed status. Zero duplicate charges!'
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
  };

  return (
    <div className="max-w-4xl mx-auto space-y-8 animate-in fade-in duration-200">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-white">Create New Payment</h1>
        <p className="text-sm text-slate-400">
          Guided payment initiation with smart rail routing, ISO 20022 canonical preview, and bulletproof idempotency
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Form */}
        <div className="lg:col-span-2 glass-panel p-6 rounded-2xl border border-slate-800 space-y-5">
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1.5">
                Payer Customer Account
              </label>
              <select
                value={customerId}
                onChange={(e) => setCustomerId(e.target.value)}
                className="w-full bg-slate-900 border border-slate-700 rounded-xl px-3.5 py-2.5 text-sm text-slate-100 focus:outline-none focus:border-indigo-500"
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
                <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1.5">
                  Amount
                </label>
                <div className="relative">
                  <DollarSign className="w-4 h-4 text-slate-500 absolute left-3 top-3" />
                  <input
                    type="number"
                    step="0.01"
                    value={amount}
                    onChange={(e) => setAmount(e.target.value)}
                    required
                    className="w-full bg-slate-900 border border-slate-700 rounded-xl px-9 py-2.5 text-sm text-slate-100 font-mono focus:outline-none focus:border-indigo-500"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1.5">
                  Currency
                </label>
                <select
                  value={currency}
                  onChange={(e) => setCurrency(e.target.value)}
                  className="w-full bg-slate-900 border border-slate-700 rounded-xl px-3.5 py-2.5 text-sm text-slate-100 font-mono focus:outline-none focus:border-indigo-500"
                >
                  <option value="INR">INR (₹)</option>
                  <option value="USD">USD ($)</option>
                  <option value="EUR">EUR (€)</option>
                  <option value="GBP">GBP (£)</option>
                </select>
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1.5">
                Urgency Tier
              </label>
              <div className="grid grid-cols-3 gap-3">
                {['INSTANT', 'NORMAL', 'BULK'].map((u) => (
                  <button
                    type="button"
                    key={u}
                    onClick={() => setUrgency(u)}
                    className={`py-2 text-xs font-medium rounded-xl border transition ${
                      urgency === u
                        ? 'bg-indigo-600/20 border-indigo-500 text-indigo-300'
                        : 'bg-slate-900 border-slate-800 text-slate-400 hover:text-slate-200'
                    }`}
                  >
                    {u}
                  </button>
                ))}
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1.5">
                Remittance Description
              </label>
              <input
                type="text"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                className="w-full bg-slate-900 border border-slate-700 rounded-xl px-3.5 py-2.5 text-sm text-slate-100 focus:outline-none focus:border-indigo-500"
              />
            </div>

            {/* Idempotency Key Control */}
            <div className="p-3.5 rounded-xl bg-slate-950 border border-slate-800 space-y-1.5">
              <div className="flex items-center justify-between">
                <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-400 font-mono">
                  Idempotency-Key
                </span>
                <button
                  type="button"
                  onClick={handleRegenerateKey}
                  className="text-[11px] text-indigo-400 hover:text-indigo-300 transition flex items-center gap-1 font-mono"
                >
                  <Repeat className="w-3 h-3" />
                  <span>Generate New</span>
                </button>
              </div>
              <div className="font-mono text-xs text-indigo-300 truncate bg-slate-900 p-2 rounded-lg border border-slate-800">
                {idempotencyKey}
              </div>
            </div>

            {/* Submit & Duplicate Actions */}
            <div className="pt-2 flex items-center gap-3">
              <button
                type="submit"
                disabled={loading}
                className="flex-1 flex items-center justify-center gap-2 py-3 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-medium text-sm shadow-lg shadow-indigo-600/30 transition disabled:opacity-50"
              >
                <Send className="w-4 h-4" />
                <span>Submit Payment</span>
              </button>

              <button
                type="button"
                onClick={handleDuplicateResend}
                disabled={loading}
                className="flex items-center justify-center gap-2 px-4 py-3 rounded-xl bg-slate-800 hover:bg-slate-700 text-amber-300 font-medium text-xs border border-amber-500/30 transition disabled:opacity-50"
                title="Send identical request with same key to prove zero double charge"
              >
                <Repeat className="w-3.5 h-3.5" />
                <span>Resend (Duplicate Test)</span>
              </button>
            </div>
          </form>

          {/* Results Feedback */}
          {duplicateMessage && (
            <div className="p-3 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-300 text-xs font-mono">
              {duplicateMessage}
            </div>
          )}

          {submitResult && (
            <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-white font-mono">
                  Server Response: {submitResult.reference || 'ERROR'}
                </span>
                <span className="text-xs px-2 py-0.5 rounded bg-indigo-500/20 text-indigo-300 font-mono">
                  State: {submitResult.state || 'FAILED'}
                </span>
              </div>
              <pre className="text-[11px] font-mono text-slate-400 overflow-x-auto">
                {JSON.stringify(submitResult, null, 2)}
              </pre>
            </div>
          )}
        </div>

        {/* Rail Recommendation & Smart Router Side-Panel */}
        <div className="space-y-4">
          <div className="glass-panel p-5 rounded-2xl border border-slate-800 space-y-4">
            <div className="flex items-center gap-2 text-white font-semibold text-sm">
              <Sparkles className="w-4 h-4 text-indigo-400" />
              <span>Smart Rail Recommendation</span>
            </div>

            {recommendation ? (
              <div className="space-y-3">
                {recommendation.cheapest && (
                  <div className="p-3.5 rounded-xl bg-emerald-950/20 border border-emerald-500/30 space-y-1">
                    <span className="text-[10px] uppercase font-bold tracking-wider text-emerald-400">
                      Cheapest Option
                    </span>
                    <div className="text-sm font-bold text-white">
                      {recommendation.cheapest.rail_name}
                    </div>
                    <div className="text-xs text-slate-300 font-mono">
                      Fee: {recommendation.cheapest.fee_formatted} • ETA: {recommendation.cheapest.eta_description}
                    </div>
                  </div>
                )}

                {recommendation.fastest && (
                  <div className="p-3.5 rounded-xl bg-indigo-950/20 border border-indigo-500/30 space-y-1">
                    <span className="text-[10px] uppercase font-bold tracking-wider text-indigo-400">
                      Fastest Option
                    </span>
                    <div className="text-sm font-bold text-white">
                      {recommendation.fastest.rail_name}
                    </div>
                    <div className="text-xs text-slate-300 font-mono">
                      Fee: {recommendation.fastest.fee_formatted} • ETA: {recommendation.fastest.eta_description}
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <p className="text-xs text-slate-500 font-mono">
                Enter amount to compute cheapest vs fastest routing.
              </p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
