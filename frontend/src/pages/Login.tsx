import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../lib/api';
import {
  User,
  Lock,
  Eye,
  EyeOff,
  ArrowRight,
  ShieldCheck,
  CheckCircle2,
  PlayCircle,
  HelpCircle,
  Layers,
  Sparkles,
  Info,
} from 'lucide-react';

interface LoginProps {
  onReplayIntro?: () => void;
}

export const Login: React.FC<LoginProps> = ({ onReplayIntro }) => {
  const navigate = useNavigate();
  const [email, setEmail] = useState('admin@paynexus.io');
  const [password, setPassword] = useState('Demo@PayNexus2026!');
  const [showPassword, setShowPassword] = useState(false);
  const [agreeTerms, setAgreeTerms] = useState(true);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [socialNotice, setSocialNotice] = useState<string | null>(null);
  const [showDemoDrawer, setShowDemoDrawer] = useState(false);

  const demoAccounts = [
    { label: 'Admin', role: 'ADMIN', email: 'admin@paynexus.io', badge: 'Full Platform Access' },
    { label: 'Operations', role: 'OPERATIONS', email: 'ops@paynexus.io', badge: 'Rails & Exceptions' },
    { label: 'Compliance', role: 'COMPLIANCE_OFFICER', email: 'compliance@paynexus.io', badge: 'Sanctions & Rules' },
    { label: 'Auditor', role: 'AUDITOR', email: 'auditor@paynexus.io', badge: 'Read-Only Logs' },
    { label: 'Merchant', role: 'MERCHANT', email: 'merchant@paynexus.io', badge: 'Client Portal' },
  ];

  const handleQuickFill = (accEmail: string) => {
    setEmail(accEmail);
    setPassword('Demo@PayNexus2026!');
    setError(null);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!agreeTerms) {
      setError('Please agree to all statements in terms of service.');
      return;
    }

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
      setError(err.message || 'Authentication failed. Please verify credentials.');
    } finally {
      setLoading(false);
    }
  };

  const handleSocialClick = (provider: string) => {
    setSocialNotice(`${provider} Single Sign-On requires Enterprise SAML/OIDC directory synchronization. Please use role credentials below.`);
    setTimeout(() => setSocialNotice(null), 5000);
  };

  return (
    <div className="min-h-screen bg-slate-900 flex items-center justify-center p-3 sm:p-6 md:p-10 relative overflow-hidden font-sans">
      {/* Background ambient lighting */}
      <div className="absolute top-0 left-1/4 w-96 h-96 bg-blue-600/10 rounded-full blur-3xl pointer-events-none" />
      <div className="absolute bottom-0 right-1/4 w-[30rem] h-[30rem] bg-cyan-500/10 rounded-full blur-3xl pointer-events-none" />

      {/* Replay Intro Video Button at top right */}
      {onReplayIntro && (
        <div className="absolute top-4 right-4 z-30">
          <button
            type="button"
            onClick={onReplayIntro}
            className="flex items-center gap-1.5 text-xs font-medium text-slate-300 hover:text-white bg-slate-800/80 hover:bg-slate-700/90 border border-slate-700/80 rounded-full px-3.5 py-1.5 transition backdrop-blur-md shadow-md"
          >
            <PlayCircle className="w-4 h-4 text-cyan-400" />
            <span className="hidden sm:inline">Watch Platform Intro</span>
            <span className="sm:hidden">Intro</span>
          </button>
        </div>
      )}

      {/* Main Reference Card Container */}
      <div className="w-full max-w-5xl rounded-3xl bg-white shadow-2xl overflow-hidden border border-slate-200/40 relative z-10 flex flex-col lg:flex-row min-h-[580px] sm:min-h-[620px]">
        
        {/* ── LEFT PANEL: Clean White Form (Exact Reference Layout) ── */}
        <div className="w-full lg:w-[45%] p-8 sm:p-12 md:p-14 bg-white flex flex-col justify-between z-20 relative">
          
          {/* Top Brand & Header */}
          <div>
            <div className="flex items-center justify-between mb-8">
              <div className="flex items-center gap-2.5">
                <img
                  src="/paynexus-logo.png"
                  alt="PayNexus Logo"
                  className="w-8 h-8 rounded-lg object-contain shadow-sm"
                />
                <span className="text-lg font-extrabold tracking-tight text-[#0B1F3A]">
                  Pay<span className="text-[#2563EB]">Nexus</span>
                </span>
              </div>

              {/* Demo Mode Toggle */}
              <button
                type="button"
                onClick={() => setShowDemoDrawer(!showDemoDrawer)}
                className="text-[11px] font-semibold text-blue-600 hover:text-blue-800 bg-blue-50 hover:bg-blue-100 border border-blue-200/60 rounded-full px-2.5 py-1 flex items-center gap-1 transition"
              >
                <Sparkles className="w-3 h-3 text-blue-500" />
                <span>Demo Roles</span>
              </button>
            </div>

            {/* Reference Header: Bold uppercase SIGN IN */}
            <h1 className="text-2xl sm:text-3xl font-extrabold text-[#0B1F3A] tracking-wider mb-2">
              SIGN IN
            </h1>
            <p className="text-xs sm:text-sm text-slate-500 mb-8 font-normal">
              Sign in to manage your payment modernization platform.
            </p>

            {/* Error banner */}
            {error && (
              <div className="mb-5 p-3 rounded-xl bg-rose-50 border border-rose-200 text-rose-700 text-xs font-medium flex items-start gap-2 animate-in fade-in">
                <span className="font-bold shrink-0">!</span>
                <span>{error}</span>
              </div>
            )}

            {/* Social notice banner */}
            {socialNotice && (
              <div className="mb-5 p-3 rounded-xl bg-blue-50 border border-blue-200 text-blue-800 text-xs font-medium flex items-start gap-2 animate-in fade-in">
                <Info className="w-4 h-4 text-blue-600 shrink-0 mt-0.5" />
                <span>{socialNotice}</span>
              </div>
            )}

            {/* Demo Quick-Fill Drawer */}
            {showDemoDrawer && (
              <div className="mb-6 p-3.5 rounded-2xl bg-slate-50 border border-slate-200/80 animate-in fade-in duration-200">
                <div className="text-[11px] font-bold text-slate-700 uppercase tracking-wider mb-2 flex items-center justify-between">
                  <span>Quick-Fill Demo Credentials</span>
                  <button
                    onClick={() => setShowDemoDrawer(false)}
                    className="text-slate-400 hover:text-slate-600"
                  >
                    ×
                  </button>
                </div>
                <div className="grid grid-cols-2 gap-1.5">
                  {demoAccounts.map((acc) => (
                    <button
                      key={acc.role}
                      type="button"
                      onClick={() => handleQuickFill(acc.email)}
                      className={`text-left p-2 rounded-xl border text-xs transition flex flex-col justify-between ${
                        email === acc.email
                          ? 'bg-blue-600 text-white border-blue-600 shadow-sm'
                          : 'bg-white text-slate-700 border-slate-200 hover:border-blue-300'
                      }`}
                    >
                      <div className="font-bold">{acc.label}</div>
                      <div className={`text-[10px] truncate ${email === acc.email ? 'text-blue-100' : 'text-slate-400'}`}>
                        {acc.email}
                      </div>
                    </button>
                  ))}
                </div>
              </div>
            )}

            {/* ── Form Inputs matching Reference Pill Styling ── */}
            <form onSubmit={handleSubmit} className="space-y-4">
              
              {/* E-mail Pill Input */}
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
                  <User className="h-4 w-4 text-teal-600/70" />
                </div>
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="e-mail"
                  required
                  className="w-full pl-11 pr-4 py-3 bg-[#B2EBF2]/40 hover:bg-[#B2EBF2]/55 focus:bg-[#B2EBF2]/60 text-slate-800 placeholder-slate-500 rounded-full text-sm font-medium border-0 focus:ring-2 focus:ring-[#22D3EE] focus:outline-none transition shadow-2xs"
                />
              </div>

              {/* Password Pill Input with Visibility Toggle */}
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
                  <Lock className="h-4 w-4 text-teal-600/70" />
                </div>
                <input
                  type={showPassword ? 'text' : 'password'}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="password"
                  required
                  className="w-full pl-11 pr-11 py-3 bg-[#B2EBF2]/40 hover:bg-[#B2EBF2]/55 focus:bg-[#B2EBF2]/60 text-slate-800 placeholder-slate-500 rounded-full text-sm font-medium border-0 focus:ring-2 focus:ring-[#22D3EE] focus:outline-none transition shadow-2xs"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute inset-y-0 right-0 pr-4 flex items-center text-teal-700/60 hover:text-teal-900 transition"
                >
                  {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </button>
              </div>

              {/* Agreement checkbox (matches reference image style: "I agree all statements In terms of service.") */}
              <div className="pt-2 flex items-center justify-between">
                <label className="flex items-center gap-2 cursor-pointer select-none text-[12px] sm:text-[13px] text-slate-600">
                  <input
                    type="checkbox"
                    checked={agreeTerms}
                    onChange={(e) => setAgreeTerms(e.target.checked)}
                    className="w-4 h-4 rounded text-[#22D3EE] focus:ring-[#22D3EE] border-slate-300 rounded cursor-pointer"
                  />
                  <span>
                    I agree all statements In{' '}
                    <span className="text-[#2563EB] hover:underline font-medium">terms of service</span>.
                  </span>
                </label>
              </div>

              {/* Primary Action Button (Matches cyan pill button in reference image) */}
              <div className="pt-3">
                <button
                  type="submit"
                  disabled={loading}
                  className="w-36 sm:w-40 py-2.5 rounded-full bg-[#22D3EE] hover:bg-[#06B6D4] active:bg-[#0891B2] text-white font-bold text-xs tracking-wider uppercase shadow-md shadow-cyan-500/25 transition disabled:opacity-50 flex items-center justify-center gap-2"
                >
                  {loading ? (
                    <span className="inline-block w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  ) : (
                    <>
                      <span>SIGN IN</span>
                    </>
                  )}
                </button>
              </div>

            </form>
          </div>

          {/* Bottom Social Icons and Footer */}
          <div className="mt-8 pt-4">
            <div className="flex items-center gap-3 mb-4">
              {/* Facebook Icon Button */}
              <button
                type="button"
                onClick={() => handleSocialClick('Facebook')}
                className="w-8 h-8 rounded-full bg-[#1877F2] text-white flex items-center justify-center font-bold text-sm shadow-xs hover:opacity-90 transition active:scale-95"
                title="Sign in with Facebook"
              >
                f
              </button>

              {/* Google Icon Button */}
              <button
                type="button"
                onClick={() => handleSocialClick('Google')}
                className="w-8 h-8 rounded-full bg-white border border-slate-200 flex items-center justify-center shadow-xs hover:border-slate-300 transition active:scale-95"
                title="Sign in with Google"
              >
                <svg className="w-4 h-4" viewBox="0 0 24 24">
                  <path
                    fill="#4285F4"
                    d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
                  />
                  <path
                    fill="#34A853"
                    d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
                  />
                  <path
                    fill="#FBBC05"
                    d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z"
                  />
                  <path
                    fill="#EA4335"
                    d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z"
                  />
                </svg>
              </button>

              {/* Twitter / X Icon Button */}
              <button
                type="button"
                onClick={() => handleSocialClick('Twitter')}
                className="w-8 h-8 rounded-full bg-[#1DA1F2] text-white flex items-center justify-center font-bold text-xs shadow-xs hover:opacity-90 transition active:scale-95"
                title="Sign in with Twitter"
              >
                <svg className="w-4 h-4 fill-current" viewBox="0 0 24 24">
                  <path d="M23.953 4.57a10 10 0 01-2.825.775 4.958 4.958 0 002.163-2.723c-.951.555-2.005.959-3.127 1.184a4.92 4.92 0 00-8.384 4.482C7.69 8.095 4.067 6.13 1.64 3.162a4.822 4.822 0 00-.666 2.475c0 1.71.87 3.213 2.188 4.096a4.904 4.904 0 01-2.228-.616v.06a4.923 4.923 0 003.946 4.827 4.996 4.996 0 01-2.212.085 4.936 4.936 0 004.604 3.417 9.867 9.867 0 01-6.102 2.105c-.39 0-.779-.023-1.17-.067a13.995 13.995 0 007.557 2.209c9.053 0 13.998-7.496 13.998-13.985 0-.21 0-.42-.015-.63A9.936 9.936 0 0024 4.59z" />
                </svg>
              </button>
            </div>

            <div className="flex items-center justify-between text-[11px] text-slate-400">
              <span>PayNexus Modernisation Core</span>
              <span>ISO 20022 Engine</span>
            </div>
          </div>
        </div>

        {/* ── RIGHT PANEL: Hero Payments Visual with Torn-Paper Effect & Branding ── */}
        <div className="w-full lg:w-[55%] relative overflow-hidden min-h-[300px] lg:min-h-full flex items-end justify-end p-8 sm:p-12">
          
          {/* Background Hero Image (Replacing Boat/Ocean with Fintech Ecosystem) */}
          <img
            src="/paynexus-hero.jpg"
            alt="PayNexus Fintech Payments Ecosystem"
            className="absolute inset-0 w-full h-full object-cover object-center"
          />

          {/* Deep Navy/Cyan Gradient Overlay for readability and brand harmony */}
          <div className="absolute inset-0 bg-gradient-to-t from-[#0B1F3A]/90 via-[#0B1F3A]/30 to-transparent pointer-events-none" />
          <div className="absolute inset-0 bg-gradient-to-r from-white/20 via-transparent to-[#0B1F3A]/40 pointer-events-none" />

          {/* Reference Tear Edge Divider (Masking effect for the left border) */}
          <div
            className="hidden lg:block absolute inset-y-0 -left-1 w-12 z-20 pointer-events-none"
            style={{
              background: '#FFFFFF',
              clipPath: 'polygon(0% 0%, 100% 0%, 30% 6%, 95% 12%, 40% 18%, 100% 25%, 35% 32%, 90% 39%, 45% 46%, 98% 54%, 30% 61%, 85% 68%, 25% 75%, 95% 82%, 40% 89%, 100% 96%, 30% 100%, 0% 100%)',
            }}
          />

          {/* Floating Fintech Security Pill */}
          <div className="absolute top-6 right-6 z-20 hidden sm:flex items-center gap-2 bg-[#0B1F3A]/80 backdrop-blur-md px-3.5 py-1.5 rounded-full border border-cyan-500/30 text-white text-xs shadow-lg">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
            <span className="font-medium text-slate-200">ISO 20022 pacs.008 Compliant</span>
          </div>

          {/* ── PayNexus Branding Text (Replacing "LOREM IPSUM / DOLOR SIT AMET") ── */}
          <div className="relative z-20 text-right select-none max-w-lg">
            <div className="flex items-center justify-end gap-2 mb-1">
              <span className="px-2 py-0.5 rounded text-[10px] font-bold tracking-widest uppercase bg-cyan-400/20 text-cyan-300 border border-cyan-400/30">
                Next-Gen Rails
              </span>
            </div>
            
            <h2 className="text-3xl sm:text-4xl md:text-5xl font-black text-white tracking-wider uppercase drop-shadow-[0_4px_16px_rgba(0,0,0,0.8)]">
              PayNexus
            </h2>
            
            <p className="text-sm sm:text-base md:text-lg font-bold text-cyan-300 tracking-widest uppercase mt-1 drop-shadow-[0_2px_8px_rgba(0,0,0,0.8)]">
              Powering the Future of Payments
            </p>
          </div>

        </div>

      </div>
    </div>
  );
};
