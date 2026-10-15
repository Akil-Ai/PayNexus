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
    { label: 'Dashboard', path: '/', icon: LayoutDashboard },
    { label: 'Payments', path: '/payments', icon: CreditCard },
    { label: 'New Payment', path: '/payments/new', icon: PlusCircle },
    { label: 'Reconciliation', path: '/reconciliation', icon: GitCompare },
    { label: 'Risk & Compliance', path: '/compliance', icon: ShieldCheck },
    { label: 'Payment Networks', path: '/rails', icon: Zap },
    { label: 'Exceptions & DLQ', path: '/exceptions', icon: AlertTriangle },
    { label: 'Audit Explorer', path: '/audit', icon: History },
    { label: 'ISO 20022 Translator', path: '/messages', icon: FileCode2 },
    { label: 'Reports & Settings', path: '/admin', icon: Settings },
    { label: 'Demo Runner', path: '/demo', icon: PlaySquare, badge: 'Live Demo' },
  ];

  const currentNav = navItems.find((item) => item.path === location.pathname) || { label: 'Payments Modernisation' };

  return (
    <div className="flex h-screen bg-[#F3F6FA] text-[#102A56] overflow-hidden font-sans">
      {/* ── Sidebar ── */}
      <aside className="w-64 flex-shrink-0 flex flex-col border-r border-[#E2E8F0] bg-white shadow-sm z-20">
        {/* Brand */}
        <div className="h-16 flex items-center px-5 border-b border-[#E2E8F0] gap-3">
          <img
            src="/paynexus-logo.png"
            alt="PayNexus Logo"
            className="w-9 h-9 object-contain rounded-lg shadow-sm"
          />
          <div>
            <span className="font-extrabold tracking-tight text-lg text-[#102A56]">
              PayNexus
            </span>
            <span className="block text-[9px] font-mono tracking-widest text-[#2563EB] font-bold uppercase">
              PAYMENTS MODERNISATION
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
                className={`flex items-center justify-between px-3.5 py-2.5 rounded-lg text-sm font-medium transition-all ${
                  isActive
                    ? 'bg-[#2563EB] text-white shadow-sm font-semibold'
                    : 'text-slate-600 hover:text-[#102A56] hover:bg-slate-100/80'
                }`}
              >
                <div className="flex items-center gap-3">
                  <Icon className={`w-4 h-4 ${isActive ? 'text-white' : 'text-slate-500'}`} />
                  <span>{item.label}</span>
                </div>
                {item.badge && (
                  <span className={`text-[10px] font-mono px-1.5 py-0.5 rounded font-semibold ${
                    isActive
                      ? 'bg-white/20 text-white'
                      : 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                  }`}>
                    {item.badge}
                  </span>
                )}
              </Link>
            );
          })}
        </nav>

        {/* User bar & logout */}
        <div className="p-3.5 border-t border-[#E2E8F0] bg-slate-50/80">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2.5 overflow-hidden">
              <div className="w-8 h-8 rounded-full bg-[#102A56] text-white flex items-center justify-center font-bold text-xs uppercase shadow-sm">
                {user?.full_name ? user.full_name[0] : 'A'}
              </div>
              <div className="truncate">
                <p className="text-xs font-semibold text-[#102A56] truncate">{user?.full_name || 'Alex Mercer'}</p>
                <span className="inline-block text-[10px] font-mono font-medium text-slate-500">
                  {user?.role || 'ADMIN'}
                </span>
              </div>
            </div>
            <button
              onClick={handleLogout}
              title="Sign out"
              className="p-1.5 rounded-md text-slate-400 hover:text-red-600 hover:bg-red-50 transition"
            >
              <LogOut className="w-4 h-4" />
            </button>
          </div>
        </div>
      </aside>

      {/* ── Main Layout Content ── */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Top Navbar */}
        <header className="h-16 flex items-center justify-between px-8 border-b border-[#E2E8F0] bg-white shadow-sm z-10">
          <div className="flex items-center gap-4">
            <h1 className="text-lg font-bold text-[#102A56] tracking-tight">{currentNav.label}</h1>
            
            <button
              onClick={() => setCmdOpen(true)}
              className="hidden md:flex items-center gap-2 px-3 py-1.5 rounded-lg bg-slate-50 border border-slate-200 text-slate-500 hover:text-slate-800 text-xs transition"
            >
              <Search className="w-3.5 h-3.5 text-slate-400" />
              <span>Search actions or commands...</span>
              <kbd className="px-1.5 py-0.5 rounded bg-white border border-slate-200 text-[10px] font-mono text-slate-500 shadow-2xs">
                Ctrl K
              </kbd>
            </button>
          </div>

          <div className="flex items-center gap-4">
            {/* Environment Indicator Chip */}
            <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-blue-50 border border-blue-200 text-blue-700 text-xs font-medium">
              <span className="w-2 h-2 rounded-full bg-blue-600 animate-pulse" />
              <span className="font-mono text-[11px] font-semibold">Demo Mode</span>
            </div>

            {/* Notification bell */}
            <button 
              className="relative p-2 rounded-lg text-slate-500 hover:text-[#102A56] hover:bg-slate-100 transition"
              title="Notifications"
            >
              <Bell className="w-4 h-4" />
              <span className="absolute top-1.5 right-1.5 w-2 h-2 rounded-full bg-red-500" />
            </button>

            {/* New Payment action */}
            <Link
              to="/payments/new"
              className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg bg-[#2563EB] hover:bg-blue-700 text-white font-medium text-xs shadow-sm transition"
            >
              <PlusCircle className="w-3.5 h-3.5" />
              <span>New Payment</span>
            </Link>
          </div>
        </header>

        {/* Page Body Viewport */}
        <main className="flex-1 overflow-y-auto p-8 bg-[#F3F6FA]">{children}</main>
      </div>

      {/* ── Command Palette Modal (Ctrl+K) ── */}
      {cmdOpen && (
        <div className="fixed inset-0 z-50 flex items-start justify-center pt-24 bg-slate-900/30 backdrop-blur-sm">
          <div className="w-full max-w-xl bg-white border border-[#E2E8F0] rounded-xl shadow-2xl overflow-hidden animate-in fade-in zoom-in-95 duration-100">
            <div className="flex items-center px-4 border-b border-[#E2E8F0]">
              <Search className="w-4 h-4 text-slate-400 mr-2" />
              <input
                autoFocus
                placeholder="Type a command or jump to page..."
                className="w-full h-12 bg-transparent text-sm text-[#102A56] focus:outline-none"
              />
              <button
                onClick={() => setCmdOpen(false)}
                className="text-xs px-2 py-0.5 rounded bg-slate-100 text-slate-500 hover:text-slate-800"
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
                  className="w-full flex items-center justify-between px-3 py-2 rounded-lg text-sm text-slate-700 hover:bg-blue-50 hover:text-[#2563EB] transition group"
                >
                  <div className="flex items-center gap-2.5">
                    <item.icon className="w-4 h-4 text-slate-400 group-hover:text-[#2563EB]" />
                    <span className="font-medium">{item.label}</span>
                  </div>
                  <ChevronRight className="w-3.5 h-3.5 text-slate-400 group-hover:text-[#2563EB]" />
                </button>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
