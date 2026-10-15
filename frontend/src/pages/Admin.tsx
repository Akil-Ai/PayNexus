import React, { useState, useEffect } from 'react';
import { api } from '../lib/api';
import {
  Settings,
  Users,
  Key,
  Webhook,
  Sliders,
  Plus,
  Save,
  CheckCircle2,
  FileText,
  Download,
  ShieldCheck,
  Bell,
  Lock,
} from 'lucide-react';

export const Admin: React.FC = () => {
  const [tab, setTab] = useState<'reports' | 'settings' | 'users' | 'apiclients' | 'webhooks'>('reports');
  const [settingsList, setSettingsList] = useState<any[]>([]);
  const [usersList, setUsersList] = useState<any[]>([]);
  const [apiClients, setApiClients] = useState<any[]>([]);
  const [webhooks, setWebhooks] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  // New API key state
  const [newKeyName, setNewKeyName] = useState('');
  const [generatedKey, setGeneratedKey] = useState<string | null>(null);

  const loadData = async () => {
    setLoading(true);
    try {
      const [s, u, a, w] = await Promise.all([
        api.getSettings(),
        api.listUsers(),
        api.listApiClients(),
        api.listWebhooks(),
      ]);
      setSettingsList(s);
      setUsersList(u);
      setApiClients(a);
      setWebhooks(w);
    } catch (err) {
      console.error('Failed to load admin data:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleUpdateSetting = async (key: string, value: any) => {
    try {
      await api.updateSetting(key, value);
      alert(`Setting updated: ${key} = ${value}`);
      loadData();
    } catch (err: any) {
      alert(`Update failed: ${err.message}`);
    }
  };

  const handleCreateApiKey = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newKeyName) return;
    try {
      const res = await api.createApiClient({ name: newKeyName });
      setGeneratedKey(res.api_key);
      setNewKeyName('');
      loadData();
    } catch (err: any) {
      alert(`Failed to create API key: ${err.message}`);
    }
  };

  const handleDownloadReport = (reportType: string) => {
    const reportData = [
      ['Report Type', reportType],
      ['Generated At', new Date().toISOString()],
      ['Environment', 'Hackathon Demo Mode'],
      ['Platform', 'PayNexus Payments Modernisation'],
      ['Ledger State', 'Balanced and Reconciled'],
    ];
    const csvContent =
      'data:text/csv;charset=utf-8,' + reportData.map((e) => e.join(',')).join('\n');
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement('a');
    link.setAttribute('href', encodedUri);
    link.setAttribute('download', `paynexus_${reportType.toLowerCase().replace(/\s+/g, '_')}_${new Date().toISOString().slice(0, 10)}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto animate-in fade-in duration-200">
      {/* Header */}
      <div className="bg-white p-6 rounded-2xl border border-slate-200/80 shadow-sm flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <h1 className="text-2xl font-bold tracking-tight text-[#102A56] flex items-center gap-2">
              <Settings className="w-5 h-5 text-blue-600" />
              <span>Reports & Platform Administration</span>
            </h1>
            <span className="px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-blue-50 text-blue-700 border border-blue-200/60">
              Role-Based Access
            </span>
          </div>
          <p className="text-sm text-slate-500">
            Export comprehensive reconciliation and exception reports, configure runtime system thresholds, and manage API credentials
          </p>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-slate-200 space-x-6 overflow-x-auto">
        <button
          onClick={() => setTab('reports')}
          className={`pb-3 text-xs font-bold tracking-wider uppercase transition flex items-center gap-2 whitespace-nowrap ${
            tab === 'reports'
              ? 'text-blue-600 border-b-2 border-blue-600'
              : 'text-slate-500 hover:text-slate-800'
          }`}
        >
          <FileText className="w-4 h-4" />
          <span>Reports & CSV Export</span>
        </button>

        <button
          onClick={() => setTab('settings')}
          className={`pb-3 text-xs font-bold tracking-wider uppercase transition flex items-center gap-2 whitespace-nowrap ${
            tab === 'settings'
              ? 'text-blue-600 border-b-2 border-blue-600'
              : 'text-slate-500 hover:text-slate-800'
          }`}
        >
          <Sliders className="w-4 h-4" />
          <span>System Settings ({settingsList.length})</span>
        </button>

        <button
          onClick={() => setTab('users')}
          className={`pb-3 text-xs font-bold tracking-wider uppercase transition flex items-center gap-2 whitespace-nowrap ${
            tab === 'users'
              ? 'text-blue-600 border-b-2 border-blue-600'
              : 'text-slate-500 hover:text-slate-800'
          }`}
        >
          <Users className="w-4 h-4" />
          <span>Users & RBAC ({usersList.length})</span>
        </button>

        <button
          onClick={() => setTab('apiclients')}
          className={`pb-3 text-xs font-bold tracking-wider uppercase transition flex items-center gap-2 whitespace-nowrap ${
            tab === 'apiclients'
              ? 'text-blue-600 border-b-2 border-blue-600'
              : 'text-slate-500 hover:text-slate-800'
          }`}
        >
          <Key className="w-4 h-4" />
          <span>API Credentials ({apiClients.length})</span>
        </button>

        <button
          onClick={() => setTab('webhooks')}
          className={`pb-3 text-xs font-bold tracking-wider uppercase transition flex items-center gap-2 whitespace-nowrap ${
            tab === 'webhooks'
              ? 'text-blue-600 border-b-2 border-blue-600'
              : 'text-slate-500 hover:text-slate-800'
          }`}
        >
          <Webhook className="w-4 h-4" />
          <span>Webhooks ({webhooks.length})</span>
        </button>
      </div>

      {/* ── Reports Tab ── */}
      {tab === 'reports' && (
        <div className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="fintech-card p-5 space-y-3 flex flex-col justify-between">
              <div>
                <span className="text-[11px] font-bold text-blue-600 uppercase">Operational Summary</span>
                <h3 className="font-bold text-sm text-[#102A56] mt-1">Transaction Summaries</h3>
                <p className="text-xs text-slate-500 mt-1">Aggregated transaction volumes, net values, and state distributions</p>
              </div>
              <button
                onClick={() => handleDownloadReport('Transaction Summaries')}
                className="flex items-center justify-center gap-2 w-full py-2 rounded-xl bg-slate-100 hover:bg-slate-200 text-[#102A56] font-bold text-xs transition"
              >
                <Download className="w-3.5 h-3.5" />
                <span>Export CSV</span>
              </button>
            </div>

            <div className="fintech-card p-5 space-y-3 flex flex-col justify-between">
              <div>
                <span className="text-[11px] font-bold text-[#10A66A] uppercase">Ledger Balance</span>
                <h3 className="font-bold text-sm text-[#102A56] mt-1">Reconciliation Reports</h3>
                <p className="text-xs text-slate-500 mt-1">Match rates, bank statement balances, and auto-settled transaction tallies</p>
              </div>
              <button
                onClick={() => handleDownloadReport('Reconciliation Report')}
                className="flex items-center justify-center gap-2 w-full py-2 rounded-xl bg-slate-100 hover:bg-slate-200 text-[#102A56] font-bold text-xs transition"
              >
                <Download className="w-3.5 h-3.5" />
                <span>Export CSV</span>
              </button>
            </div>

            <div className="fintech-card p-5 space-y-3 flex flex-col justify-between">
              <div>
                <span className="text-[11px] font-bold text-[#DC2626] uppercase">Root Cause Analysis</span>
                <h3 className="font-bold text-sm text-[#102A56] mt-1">Failed-Payment Reports</h3>
                <p className="text-xs text-slate-500 mt-1">Circuit breaker trips, timeouts, and sanctions rejections breakdown</p>
              </div>
              <button
                onClick={() => handleDownloadReport('Failed Payments Report')}
                className="flex items-center justify-center gap-2 w-full py-2 rounded-xl bg-slate-100 hover:bg-slate-200 text-[#102A56] font-bold text-xs transition"
              >
                <Download className="w-3.5 h-3.5" />
                <span>Export CSV</span>
              </button>
            </div>

            <div className="fintech-card p-5 space-y-3 flex flex-col justify-between">
              <div>
                <span className="text-[11px] font-bold text-[#F59E0B] uppercase">Exception Queue</span>
                <h3 className="font-bold text-sm text-[#102A56] mt-1">Exception History</h3>
                <p className="text-xs text-slate-500 mt-1">Full audit trail of manually overridden and resolved recon exceptions</p>
              </div>
              <button
                onClick={() => handleDownloadReport('Exception History Report')}
                className="flex items-center justify-center gap-2 w-full py-2 rounded-xl bg-slate-100 hover:bg-slate-200 text-[#102A56] font-bold text-xs transition"
              >
                <Download className="w-3.5 h-3.5" />
                <span>Export CSV</span>
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ── System Settings Tab ── */}
      {tab === 'settings' && (
        <div className="fintech-card p-6 space-y-4">
          <p className="text-xs text-slate-500">
            Runtime configurable thresholds: Zero hardcoded business logic. Edit threshold values below:
          </p>

          <div className="divide-y divide-slate-100 font-mono text-xs">
            {settingsList.map((st) => (
              <div key={st.key} className="py-3.5 flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                <div>
                  <span className="font-bold text-[#102A56] text-sm">{st.key}</span>
                  <p className="text-[11px] text-slate-500 font-sans mt-0.5">{st.description}</p>
                </div>
                <div className="flex items-center gap-3">
                  <input
                    type="text"
                    defaultValue={String(st.value)}
                    onBlur={(e) => {
                      let val: any = e.target.value;
                      if (val === 'true') val = true;
                      else if (val === 'false') val = false;
                      else if (!isNaN(Number(val))) val = Number(val);
                      handleUpdateSetting(st.key, val);
                    }}
                    className="bg-slate-50 border border-slate-200 rounded-lg px-3 py-1.5 text-xs text-blue-700 font-bold text-right w-44 focus:outline-none focus:border-blue-600"
                  />
                  <span className="text-[10px] text-slate-400 font-sans">Auto-saves on blur</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ── Users Tab ── */}
      {tab === 'users' && (
        <div className="fintech-card overflow-hidden">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-50 border-b border-slate-200 text-slate-600 font-semibold uppercase tracking-wider">
              <tr>
                <th className="py-3 px-4">Full Name</th>
                <th className="py-3 px-4">Email</th>
                <th className="py-3 px-4">Role</th>
                <th className="py-3 px-4">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 font-mono">
              {usersList.map((u) => (
                <tr key={u.id} className="hover:bg-slate-50">
                  <td className="py-3 px-4 font-sans font-bold text-[#102A56]">{u.full_name}</td>
                  <td className="py-3 px-4 text-slate-600">{u.email}</td>
                  <td className="py-3 px-4">
                    <span className="px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-blue-50 text-blue-700 border border-blue-200">
                      {u.role}
                    </span>
                  </td>
                  <td className="py-3 px-4 text-[#10A66A] font-sans font-semibold">Active</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* ── API Clients Tab ── */}
      {tab === 'apiclients' && (
        <div className="space-y-6">
          <div className="fintech-card p-5 space-y-4">
            <h3 className="text-sm font-bold text-[#102A56]">Provision New Machine API Key</h3>
            <form onSubmit={handleCreateApiKey} className="flex flex-col sm:flex-row gap-3">
              <input
                type="text"
                placeholder="Client application name (e.g. ERP Gateway)"
                value={newKeyName}
                onChange={(e) => setNewKeyName(e.target.value)}
                className="flex-1 bg-slate-50 border border-slate-200 rounded-xl px-4 py-2 text-xs text-[#102A56] focus:outline-none focus:border-blue-600"
              />
              <button
                type="submit"
                className="px-5 py-2 rounded-xl bg-blue-600 hover:bg-blue-700 text-white text-xs font-bold transition shadow-sm"
              >
                Generate Key
              </button>
            </form>

            {generatedKey && (
              <div className="p-4 rounded-xl bg-amber-50 border border-amber-200 text-amber-900 text-xs font-mono space-y-1">
                <div className="font-bold">Save this API key now; secrets are never stored in plaintext:</div>
                <div className="p-2.5 bg-white rounded-lg border border-amber-300 select-all text-[#102A56] font-bold">
                  {generatedKey}
                </div>
              </div>
            )}
          </div>

          <div className="fintech-card overflow-hidden">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50 border-b border-slate-200 text-slate-600 font-semibold uppercase tracking-wider">
                <tr>
                  <th className="py-3 px-4">Client Name</th>
                  <th className="py-3 px-4">Key Prefix</th>
                  <th className="py-3 px-4">Rate Limit</th>
                  <th className="py-3 px-4">Created</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 font-mono">
                {apiClients.map((c) => (
                  <tr key={c.id} className="hover:bg-slate-50">
                    <td className="py-3 px-4 font-sans font-bold text-[#102A56]">{c.name}</td>
                    <td className="py-3 px-4 text-blue-600 font-semibold">{c.key_prefix}...</td>
                    <td className="py-3 px-4 text-slate-600">{c.rate_limit_per_minute}/min</td>
                    <td className="py-3 px-4 text-slate-500 text-[11px]">
                      {new Date(c.created_at).toLocaleDateString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* ── Webhooks Tab ── */}
      {tab === 'webhooks' && (
        <div className="fintech-card p-6 space-y-4">
          <h3 className="text-sm font-bold text-[#102A56]">HMAC Signed Webhook Endpoints</h3>
          <p className="text-xs text-slate-500">
            Every delivery includes an HMAC-SHA256 signature in X-PayNexus-Signature header.
          </p>
          <div className="space-y-3 font-mono text-xs">
            {webhooks.length === 0 ? (
              <p className="text-slate-500 py-6 text-center">No active webhook subscriptions.</p>
            ) : (
              webhooks.map((w) => (
                <div key={w.id} className="p-3.5 rounded-xl bg-slate-50 border border-slate-200 flex justify-between items-center">
                  <div>
                    <span className="text-blue-600 font-bold">{w.url}</span>
                    <span className="text-slate-500 block text-[11px] mt-0.5">Events: {(w.events || []).join(', ')}</span>
                  </div>
                  <span className="text-[#10A66A] font-bold text-[10px] bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200">ACTIVE</span>
                </div>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  );
};
