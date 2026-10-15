import React, { useState, useEffect } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
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
  Menu,
  X,
} from 'lucide-react';

interface LayoutProps {
  children: React.ReactNode;
}

export const Layout: React.FC<LayoutProps> = ({ children }) => {
  const location = useLocation();
  const navigate = useNavigate();
  const [user, setUser] = useState<any>(null);
  const [cmdOpen, setCmdOpen] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [notificationOpen, setNotificationOpen] = useState(false);

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

  // Close mobile sidebar on route change
  useEffect(() => {
    setMobileMenuOpen(false);
    setNotificationOpen(false);
  }, [location.pathname]);

  // Keyboard shortcut Ctrl+K / Cmd+K
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        setCmdOpen((prev) => !prev);
      } else if (e.key === 'Escape') {
        setCmdOpen(false);
        setNotificationOpen(false);
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
      {/* ── Mobile Sidebar Backdrop ── */}
      <AnimatePresence>
        {mobileMenuOpen && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            onClick={() => setMobileMenuOpen(false)}
            className="fixed inset-0 bg-slate-900/40 backdrop-blur-xs z-40 lg:hidden"
          />
        )}
      </AnimatePresence>

      {/* ── Sidebar (Desktop & Mobile Drawer) ── */}
      <aside
        className={`fixed lg:static top-0 bottom-0 left-0 w-64 flex-shrink-0 flex flex-col border-r border-[#E2E8F0] bg-white shadow-sm z-50 transition-transform duration-300 ease-in-out ${
          mobileMenuOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'
        }`}
      >
        {/* Brand */}
        <div className="h-16 flex items-center justify-between px-5 border-b border-[#E2E8F0]">
          <div className="flex items-center gap-3">
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
          <button
            onClick={() => setMobileMenuOpen(false)}
            className="lg:hidden p-1.5 rounded-lg text-slate-400 hover:text-slate-600 hover:bg-slate-100"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Navigation list with animated active pill indicator */}
        <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = location.pathname === item.path;
            return (
              <Link
                key={item.path}
                to={item.path}
                className={`relative flex items-center justify-between px-3.5 py-2.5 rounded-xl text-sm font-medium transition-colors duration-150 group ${
                  isActive
                    ? 'text-white font-semibold'
                    : 'text-slate-600 hover:text-[#102A56] hover:bg-slate-100/80'
                }`}
              >
                {/* Framer motion layoutId for smooth sliding active background */}
                {isActive && (
                  <motion.div
                    layoutId="activeNavIndicator"
                    className="absolute inset-0 bg-[#2563EB] rounded-xl shadow-xs"
                    transition={{ type: 'spring', stiffness: 380, damping: 30 }}
                  />
                )}

                <div className="relative z-10 flex items-center gap-3">
                  <Icon
                    className={`w-4 h-4 transition-colors ${
                      isActive ? 'text-white' : 'text-slate-400 group-hover:text-blue-600'
                    }`}
                  />
                  <span>{item.label}</span>
                </div>
                {item.badge && (
                  <span
                    className={`relative z-10 text-[10px] font-mono px-2 py-0.5 rounded-full font-semibold transition-colors ${
                      isActive
                        ? 'bg-white/20 text-white'
                        : 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                    }`}
                  >
                    {item.badge}
                  </span>
                )}
              </Link>
            );
          })}
        </nav>

        {/* User profile & logout bar */}
        <div className="p-3.5 border-t border-[#E2E8F0] bg-slate-50/80">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2.5 overflow-hidden">
              <div className="w-8 h-8 rounded-full bg-[#102A56] text-white flex items-center justify-center font-bold text-xs uppercase shadow-xs">
                {user?.full_name ? user.full_name[0] : 'A'}
              </div>
              <div className="truncate">
                <p className="text-xs font-bold text-[#102A56] truncate">{user?.full_name || 'Alex Mercer'}</p>
                <span className="inline-block text-[10px] font-mono font-medium text-slate-500">
                  {user?.role || 'ADMIN'} • System Verified
                </span>
              </div>
            </div>
            <button
              onClick={handleLogout}
              title="Sign out"
              className="p-1.5 rounded-lg text-slate-400 hover:text-red-600 hover:bg-red-50 transition"
            >
              <LogOut className="w-4 h-4" />
            </button>
          </div>
        </div>
      </aside>

      {/* ── Main Layout Content ── */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Top Navbar */}
        <header className="h-16 flex items-center justify-between px-4 sm:px-8 border-b border-[#E2E8F0] bg-white shadow-xs z-10">
          <div className="flex items-center gap-3">
            <button
              onClick={() => setMobileMenuOpen(true)}
              className="lg:hidden p-2 rounded-lg text-slate-600 hover:bg-slate-100"
            >
              <Menu className="w-5 h-5" />
            </button>

            <h1 className="text-lg font-bold text-[#102A56] tracking-tight">{currentNav.label}</h1>
            
            <button
              onClick={() => setCmdOpen(true)}
              className="hidden md:flex items-center gap-2 px-3 py-1.5 rounded-xl bg-slate-50 border border-slate-200 text-slate-500 hover:text-slate-800 text-xs transition shadow-2xs hover:border-slate-300"
            >
              <Search className="w-3.5 h-3.5 text-slate-400" />
              <span>Search actions or commands...</span>
              <kbd className="px-1.5 py-0.5 rounded bg-white border border-slate-200 text-[10px] font-mono text-slate-500 shadow-2xs">
                Ctrl K
              </kbd>
            </button>
          </div>

          <div className="flex items-center gap-3">
            {/* Environment Indicator Chip */}
            <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-blue-50 border border-blue-200 text-blue-700 text-xs font-medium">
              <span className="w-2 h-2 rounded-full bg-blue-600 animate-pulse" />
              <span className="font-mono text-[11px] font-semibold">Demo Mode</span>
            </div>

            {/* Notification bell dropdown toggle */}
            <div className="relative">
              <button 
                onClick={() => setNotificationOpen(!notificationOpen)}
                className="relative p-2 rounded-xl text-slate-500 hover:text-[#102A56] hover:bg-slate-100 transition"
                title="Notifications"
              >
                <Bell className="w-4 h-4" />
                <span className="absolute top-1.5 right-1.5 w-2 h-2 rounded-full bg-red-500" />
              </button>

              <AnimatePresence>
                {notificationOpen && (
                  <motion.div
                    initial={{ opacity: 0, y: 8, scale: 0.95 }}
                    animate={{ opacity: 1, y: 0, scale: 1 }}
                    exit={{ opacity: 0, y: 8, scale: 0.95 }}
                    transition={{ duration: 0.15 }}
                    className="absolute right-0 mt-2 w-80 bg-white border border-slate-200 rounded-2xl shadow-xl p-4 z-50 space-y-3"
                  >
                    <div className="flex items-center justify-between pb-2 border-b border-slate-100">
                      <span className="text-xs font-bold text-[#102A56]">System Notifications</span>
                      <span className="text-[10px] font-semibold text-blue-600 bg-blue-50 px-2 py-0.5 rounded-full">2 New</span>
                    </div>
                    <div className="space-y-2 text-xs">
                      <div className="p-2.5 rounded-xl bg-slate-50 border border-slate-100">
                        <p className="font-semibold text-[#102A56]">Reconciliation Completed</p>
                        <p className="text-slate-500 text-[11px]">46 transactions settled via UPI clearing.</p>
                      </div>
                      <div className="p-2.5 rounded-xl bg-amber-50/70 border border-amber-200">
                        <p className="font-semibold text-amber-800">OFAC Screening Alert</p>
                        <p className="text-amber-700 text-[11px]">1 flagged entity queued for Four-Eyes review.</p>
                      </div>
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>

            {/* New Payment action button with interactive active press */}
            <Link
              to="/payments/new"
              className="flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-[#2563EB] hover:bg-blue-700 text-white font-semibold text-xs shadow-xs transition"
            >
              <PlusCircle className="w-3.5 h-3.5" />
              <span>New Payment</span>
            </Link>
          </div>
        </header>

        {/* Page Body Viewport */}
        <main className="flex-1 overflow-y-auto p-4 sm:p-8 bg-[#F3F6FA] relative">
          {children}
        </main>
      </div>

      {/* ── Command Palette Modal (Ctrl+K) ── */}
      <AnimatePresence>
        {cmdOpen && (
          <div className="fixed inset-0 z-50 flex items-start justify-center pt-24 bg-slate-900/30 backdrop-blur-xs p-4">
            <motion.div
              initial={{ opacity: 0, scale: 0.95, y: -8 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.95, y: -8 }}
              transition={{ duration: 0.18, ease: 'easeOut' }}
              className="w-full max-w-xl bg-white border border-[#E2E8F0] rounded-2xl shadow-2xl overflow-hidden"
            >
              <div className="flex items-center px-4 border-b border-[#E2E8F0]">
                <Search className="w-4 h-4 text-slate-400 mr-2" />
                <input
                  autoFocus
                  placeholder="Type a command or jump to page..."
                  className="w-full h-12 bg-transparent text-sm text-[#102A56] focus:outline-none placeholder-slate-400"
                />
                <button
                  onClick={() => setCmdOpen(false)}
                  className="text-xs px-2 py-0.5 rounded-lg bg-slate-100 text-slate-500 hover:text-slate-800"
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
                    className="w-full flex items-center justify-between px-3 py-2 rounded-xl text-sm text-slate-700 hover:bg-blue-50 hover:text-[#2563EB] transition group"
                  >
                    <div className="flex items-center gap-2.5">
                      <item.icon className="w-4 h-4 text-slate-400 group-hover:text-[#2563EB] transition-colors" />
                      <span className="font-semibold">{item.label}</span>
                    </div>
                    <ChevronRight className="w-3.5 h-3.5 text-slate-400 group-hover:text-[#2563EB] transition-colors" />
                  </button>
                ))}
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </div>
  );
};
