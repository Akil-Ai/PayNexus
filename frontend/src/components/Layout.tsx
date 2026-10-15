import React, { useState, useEffect } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import {
  LayoutDashboard,
  CreditCard,
  PlusCircle,
  FileCode2,
  ShieldCheck,
  GitCompare,
  AlertTriangle,
  Zap,
  History,
  Settings,
  PlaySquare,
  LogOut,
  Bell,
  Search,
  Command,
  ChevronRight,
  Sparkles,
} from 'lucide-react';

interface LayoutProps {
  children: React.ReactNode;
}

export const Layout: React.FC<LayoutProps> = ({ children }) => {
  const location = useLocation();
  const navigate = useNavigate();
  const [user, setUser] = useState<any>(null);
  const [cmdOpen, setCmdOpen] = useState(false);

  useEffect(() => {
    const stored = localStorage.getItem('paynexus_user');
    if (stored) {
      try {
        setUser(JSON.parse(stored));
      } catch (e) {
        setUser(null);
      }
    }
  }, []);

  // Keyboard shortcut Ctrl+K / Cmd+K
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        setCmdOpen((prev) => !prev);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  const handleLogout = () => {
    localStorage.removeItem('paynexus_token');
    localStorage.removeItem('paynexus_user');
    navigate('/login');
  };

  const navItems = [
    { label: 'Executive Dashboard', path: '/', icon: LayoutDashboard },
    { label: 'Payments', path: '/payments', icon: CreditCard },
    { label: 'New Payment', path: '/payments/new', icon: PlusCircle },
    { label: 'ISO 20022 Translator', path: '/messages', icon: FileCode2 },
    { label: 'Compliance Centre', path: '/compliance', icon: ShieldCheck },
    { label: 'Reconciliation', path: '/reconciliation', icon: GitCompare },
    { label: 'Exceptions & DLQ', path: '/exceptions', icon: AlertTriangle },
    { label: 'Rails & Chaos Lab', path: '/rails', icon: Zap },
    { label: 'Audit Explorer', path: '/audit', icon: History },
    { label: 'Admin & Settings', path: '/admin', icon: Settings },
    { label: 'Demo Runner', path: '/demo', icon: PlaySquare, badge: 'Live Demo' },
  ];

  return (
    <div className="flex h-screen bg-slate-950 text-slate-100 overflow-hidden">
      {/* ── Sidebar ── */}
      <aside className="w-64 flex-shrink-0 flex flex-col border-r border-slate-800/80 bg-slate-900/60 backdrop-blur-md">
        {/* Brand */}
        <div className="h-16 flex items-center px-4 border-b border-slate-800/80 gap-3">
          <img
            src="/paynexus-logo.png"
            alt="PayNexus Logo"
            className="w-10 h-10 object-contain rounded-lg shadow-md shadow-emerald-500/10"
          />
          <div>
            <span className="font-bold tracking-tight text-lg bg-gradient-to-r from-blue-400 via-sky-300 to-emerald-400 bg-clip-text text-transparent">
              PayNexus
            </span>
            <span className="block text-[9px] font-mono tracking-widest text-emerald-400 font-semibold uppercase">
              MODERNISATION
            </span>
          </div>
        </div>

        {/* Navigation list */}
        <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = location.pathname === item.path;
            return (
              <Link
                key={item.path}
                to={item.path}
                className={`flex items-center justify-between px-3 py-2.5 rounded-lg text-sm font-medium transition-all ${
                  isActive
                    ? 'bg-indigo-600 text-white shadow-md shadow-indigo-600/30 font-semibold'
                    : 'text-slate-400 hover:text-slate-100 hover:bg-slate-800/60'
                }`}
              >
                <div className="flex items-center gap-3">
                  <Icon className={`w-4 h-4 ${isActive ? 'text-white' : 'text-slate-400'}`} />
                  <span>{item.label}</span>
                </div>
                {item.badge && (
                  <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-amber-500/20 text-amber-300 border border-amber-500/30">
                    {item.badge}
                  </span>
                )}
              </Link>
            );
          })}
        </nav>

        {/* User bar & logout */}
        <div className="p-4 border-t border-slate-800/80 bg-slate-900/40">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2.5 overflow-hidden">
              <div className="w-8 h-8 rounded-full bg-indigo-500/20 text-indigo-400 border border-indigo-500/30 flex items-center justify-center font-bold text-xs uppercase">
                {user?.full_name ? user.full_name[0] : 'U'}
              </div>
              <div className="truncate">
                <p className="text-xs font-medium text-slate-200 truncate">{user?.full_name || 'Demo User'}</p>
                <span className="inline-block text-[10px] font-mono font-semibold px-1.5 py-0.2 rounded bg-indigo-500/10 text-indigo-300 border border-indigo-500/20">
                  {user?.role || 'OPERATIONS'}
                </span>
              </div>
            </div>
            <button
              onClick={handleLogout}
              title="Sign out"
              className="p-1.5 rounded-md text-slate-400 hover:text-rose-400 hover:bg-rose-500/10 transition"
            >
              <LogOut className="w-4 h-4" />
            </button>
          </div>
        </div>
      </aside>

      {/* ── Main Layout Content ── */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Top Navbar */}
        <header className="h-16 flex items-center justify-between px-8 border-b border-slate-800/80 bg-slate-900/40 backdrop-blur-md z-10">
          <div className="flex items-center gap-3">
            <button
              onClick={() => setCmdOpen(true)}
              className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-slate-800/60 border border-slate-700/60 text-slate-400 hover:text-slate-200 text-xs transition"
            >
              <Search className="w-3.5 h-3.5" />
              <span>Search actions or commands...</span>
              <kbd className="px-1.5 py-0.5 rounded bg-slate-900 border border-slate-700 text-[10px] font-mono text-slate-300">
                Ctrl K
              </kbd>
            </button>
          </div>

          <div className="flex items-center gap-4">
            {/* Live SSE status indicator */}
            <div className="flex items-center gap-2 px-2.5 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-xs">
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
              <span className="font-mono text-[11px] font-medium">LIVE STREAM ACTIVE</span>
            </div>

            <Link
              to="/payments/new"
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white font-medium text-xs shadow-md shadow-indigo-600/30 transition"
            >
              <PlusCircle className="w-3.5 h-3.5" />
              <span>New Payment</span>
            </Link>
          </div>
        </header>

        {/* Page Body Viewport */}
        <main className="flex-1 overflow-y-auto p-8">{children}</main>
      </div>

      {/* ── Command Palette Modal (Ctrl+K) ── */}
      {cmdOpen && (
        <div className="fixed inset-0 z-50 flex items-start justify-center pt-24 bg-black/60 backdrop-blur-sm">
          <div className="w-full max-w-xl bg-slate-900 border border-slate-700/80 rounded-xl shadow-2xl overflow-hidden animate-in fade-in zoom-in-95 duration-100">
            <div className="flex items-center px-4 border-b border-slate-800">
              <Search className="w-4 h-4 text-slate-400 mr-2" />
              <input
                autoFocus
                placeholder="Type a command or jump to page..."
                className="w-full h-12 bg-transparent text-sm text-slate-100 focus:outline-none"
              />
              <button
                onClick={() => setCmdOpen(false)}
                className="text-xs px-1.5 py-0.5 rounded bg-slate-800 text-slate-400 hover:text-slate-200"
              >
                ESC
              </button>
            </div>
            <div className="p-2 space-y-1 max-h-80 overflow-y-auto">
              {navItems.map((item) => (
                <button
                  key={item.path}
                  onClick={() => {
                    navigate(item.path);
                    setCmdOpen(false);
                  }}
                  className="w-full flex items-center justify-between px-3 py-2 rounded-lg text-sm text-slate-300 hover:bg-indigo-600 hover:text-white transition group"
                >
                  <div className="flex items-center gap-2.5">
                    <item.icon className="w-4 h-4 text-slate-400 group-hover:text-white" />
                    <span>{item.label}</span>
                  </div>
                  <ChevronRight className="w-3.5 h-3.5 text-slate-500 group-hover:text-white" />
                </button>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
