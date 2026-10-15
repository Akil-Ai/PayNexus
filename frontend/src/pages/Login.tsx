import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../lib/api';
import { Sparkles, Shield, User, Lock, ArrowRight, CheckCircle2 } from 'lucide-react';

export const Login: React.FC = () => {
  const navigate = useNavigate();
  const [email, setEmail] = useState('admin@paynexus.io');
  const [password, setPassword] = useState('Demo@PayNexus2026!');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const demoAccounts = [
    { label: 'Admin', role: 'ADMIN', email: 'admin@paynexus.io', color: 'indigo' },
    { label: 'Operations', role: 'OPERATIONS', email: 'ops@paynexus.io', color: 'blue' },
    { label: 'Compliance Officer', role: 'COMPLIANCE_OFFICER', email: 'compliance@paynexus.io', color: 'emerald' },
    { label: 'Auditor (Read-Only)', role: 'AUDITOR', email: 'auditor@paynexus.io', color: 'amber' },
    { label: 'Merchant Client', role: 'MERCHANT', email: 'merchant@paynexus.io', color: 'purple' },
  ];

  const handleQuickFill = (accEmail: string) => {
    setEmail(accEmail);
    setPassword('Demo@PayNexus2026!');
    setError(null);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      const formData = new URLSearchParams();
      formData.append('username', email);
      formData.append('password', password);

      const tokenData = await api.login(formData);
      localStorage.setItem('paynexus_token', tokenData.access_token);

      // Fetch user profile
      const user = await api.getMe();
      localStorage.setItem('paynexus_user', JSON.stringify(user));

      navigate('/');
    } catch (err: any) {
      setError(err.message || 'Login failed. Please check credentials.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 flex flex-col justify-center items-center px-4 relative overflow-hidden">
      {/* Background glowing gradients */}
      <div className="absolute top-1/4 left-1/2 -translate-x-1/2 -translate-y-1/2 w-96 h-96 bg-indigo-600/20 rounded-full blur-3xl pointer-events-none" />
      <div className="absolute bottom-10 right-10 w-80 h-80 bg-emerald-500/10 rounded-full blur-3xl pointer-events-none" />

      <div className="w-full max-w-md z-10 space-y-6">
        {/* Logo and title */}
        <div className="text-center space-y-2">
          <div className="inline-flex w-12 h-12 rounded-2xl bg-gradient-to-tr from-indigo-600 to-emerald-400 items-center justify-center shadow-xl shadow-indigo-500/25 mb-2">
            <Sparkles className="w-6 h-6 text-white" />
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-white">PayNexus Platform</h1>
          <p className="text-sm text-slate-400">
            Next-Gen Multi-Rail Payments Modernisation & Orchestration
          </p>
        </div>

        {/* Quick-fill Role Chips */}
        <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-4 backdrop-blur-md">
          <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-2.5">
            Quick-Fill Role Credentials
          </label>
          <div className="flex flex-wrap gap-2">
            {demoAccounts.map((acc) => (
              <button
                key={acc.role}
                type="button"
                onClick={() => handleQuickFill(acc.email)}
                className={`text-xs px-2.5 py-1.5 rounded-lg border transition flex items-center gap-1.5 ${
                  email === acc.email
                    ? 'bg-indigo-600/20 border-indigo-500 text-indigo-300 font-medium'
                    : 'bg-slate-800/60 border-slate-700/60 text-slate-400 hover:text-slate-200 hover:bg-slate-800'
                }`}
              >
                {email === acc.email && <CheckCircle2 className="w-3 h-3 text-indigo-400" />}
                <span>{acc.label}</span>
              </button>
            ))}
          </div>
        </div>

        {/* Login Card */}
        <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-6 shadow-2xl backdrop-blur-xl space-y-4">
          {error && (
            <div className="p-3 rounded-lg bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1.5">Email Address</label>
              <div className="relative">
                <User className="w-4 h-4 text-slate-500 absolute left-3 top-3" />
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-9 py-2.5 text-sm text-slate-100 placeholder-slate-600 focus:outline-none focus:border-indigo-500 transition"
                  placeholder="name@paynexus.io"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1.5">Password</label>
              <div className="relative">
                <Lock className="w-4 h-4 text-slate-500 absolute left-3 top-3" />
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-9 py-2.5 text-sm text-slate-100 placeholder-slate-600 focus:outline-none focus:border-indigo-500 transition"
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full flex items-center justify-center gap-2 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-medium text-sm shadow-lg shadow-indigo-600/30 transition disabled:opacity-50"
            >
              {loading ? (
                <span className="inline-block w-4 h-4 border-2 border-white/20 border-t-white rounded-full animate-spin" />
              ) : (
                <>
                  <span>Sign In</span>
                  <ArrowRight className="w-4 h-4" />
                </>
              )}
            </button>
          </form>
        </div>

        <p className="text-center text-xs text-slate-500">
          PayNexus v1.0 • Cryptographic Audit • ISO 20022 Engine
        </p>
      </div>
    </div>
  );
};
