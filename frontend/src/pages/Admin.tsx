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
} from 'lucide-react';

export const Admin: React.FC = () => {
  const [tab, setTab] = useState<'settings' | 'users' | 'apiclients' | 'webhooks'>('settings');
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

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2">
          <Settings className="w-5 h-5 text-indigo-400" />
          <span>Platform Administration</span>
        </h1>
        <p className="text-sm text-slate-400">
          Runtime configurable system parameters, user access control, API client credentials, and webhooks
        </p>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-slate-800 space-x-6">
        <button
          onClick={() => setTab('settings')}
          className={`pb-3 text-xs font-semibold tracking-wider uppercase transition flex items-center gap-2 ${
            tab === 'settings'
              ? 'text-indigo-400 border-b-2 border-indigo-500'
              : 'text-slate-400 hover:text-slate-200'
          }`}
        >
          <Sliders className="w-4 h-4" />
          <span>System Settings ({settingsList.length})</span>
        </button>

        <button
          onClick={() => setTab('users')}
          className={`pb-3 text-xs font-semibold tracking-wider uppercase transition flex items-center gap-2 ${
            tab === 'users'
              ? 'text-indigo-400 border-b-2 border-indigo-500'
              : 'text-slate-400 hover:text-slate-200'
          }`}
        >
          <Users className="w-4 h-4" />
          <span>Users & RBAC ({usersList.length})</span>
        </button>

        <button
          onClick={() => setTab('apiclients')}
          className={`pb-3 text-xs font-semibold tracking-wider uppercase transition flex items-center gap-2 ${
            tab === 'apiclients'
              ? 'text-indigo-400 border-b-2 border-indigo-500'
              : 'text-slate-400 hover:text-slate-200'
          }`}
        >
          <Key className="w-4 h-4" />
          <span>API Credentials ({apiClients.length})</span>
        </button>

        <button
          onClick={() => setTab('webhooks')}
          className={`pb-3 text-xs font-semibold tracking-wider uppercase transition flex items-center gap-2 ${
            tab === 'webhooks'
              ? 'text-indigo-400 border-b-2 border-indigo-500'
              : 'text-slate-400 hover:text-slate-200'
          }`}
        >
          <Webhook className="w-4 h-4" />
          <span>Webhooks ({webhooks.length})</span>
        </button>
      </div>

      {/* ── System Settings Tab ── */}
      {tab === 'settings' && (
        <div className="glass-panel p-6 rounded-2xl border border-slate-800 space-y-4">
          <p className="text-xs text-slate-400">
            Non-negotiable rule: No hardcoded business logic in code. Modify any threshold or policy at runtime below:
          </p>

          <div className="divide-y divide-slate-800 font-mono text-xs">
            {settingsList.map((st) => (
              <div key={st.key} className="py-3.5 flex items-center justify-between">
                <div>
                  <span className="font-bold text-white text-sm">{st.key}</span>
                  <p className="text-[11px] text-slate-400 font-sans mt-0.5">{st.description}</p>
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
                    className="bg-slate-950 border border-slate-700 rounded-lg px-3 py-1.5 text-xs text-indigo-400 text-right w-40 focus:outline-none focus:border-indigo-500"
                  />
                  <span className="text-[10px] text-slate-500">Auto-saves on blur</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ── Users Tab ── */}
      {tab === 'users' && (
        <div className="glass-panel rounded-2xl overflow-hidden border border-slate-800">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-900/80 border-b border-slate-800 text-slate-400 font-semibold uppercase tracking-wider">
              <tr>
                <th className="py-3 px-4">Full Name</th>
                <th className="py-3 px-4">Email</th>
                <th className="py-3 px-4">Role</th>
                <th className="py-3 px-4">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 font-mono">
              {usersList.map((u) => (
                <tr key={u.id} className="hover:bg-slate-800/30">
                  <td className="py-3 px-4 font-sans font-semibold text-white">{u.full_name}</td>
                  <td className="py-3 px-4 text-slate-300">{u.email}</td>
                  <td className="py-3 px-4">
                    <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">
                      {u.role}
                    </span>
                  </td>
                  <td className="py-3 px-4 text-emerald-400 font-sans">Active</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* ── API Clients Tab ── */}
      {tab === 'apiclients' && (
        <div className="space-y-6">
          <div className="glass-panel p-5 rounded-2xl border border-slate-800 space-y-4">
            <h3 className="text-sm font-bold text-white">Generate New Machine API Key</h3>
            <form onSubmit={handleCreateApiKey} className="flex gap-3">
              <input
                type="text"
                placeholder="Client application name (e.g. ERP Gateway)"
                value={newKeyName}
                onChange={(e) => setNewKeyName(e.target.value)}
                className="flex-1 bg-slate-950 border border-slate-800 rounded-xl px-4 py-2 text-xs text-slate-200 focus:outline-none focus:border-indigo-500"
              />
              <button
                type="submit"
                className="px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold transition"
              >
                Generate Key
              </button>
            </form>

            {generatedKey && (
              <div className="p-4 rounded-xl bg-amber-500/10 border border-amber-500/30 text-amber-200 text-xs font-mono space-y-1">
                <div className="font-bold">Save this API key now; it will not be shown again:</div>
                <div className="p-2 bg-slate-950 rounded border border-slate-800 select-all text-white">
                  {generatedKey}
                </div>
              </div>
            )}
          </div>

          <div className="glass-panel rounded-2xl overflow-hidden border border-slate-800">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-900/80 border-b border-slate-800 text-slate-400 font-semibold uppercase tracking-wider">
                <tr>
                  <th className="py-3 px-4">Client Name</th>
                  <th className="py-3 px-4">Key Prefix</th>
                  <th className="py-3 px-4">Rate Limit</th>
                  <th className="py-3 px-4">Created</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 font-mono">
                {apiClients.map((c) => (
                  <tr key={c.id}>
                    <td className="py-3 px-4 font-sans font-semibold text-white">{c.name}</td>
                    <td className="py-3 px-4 text-indigo-400">{c.key_prefix}...</td>
                    <td className="py-3 px-4 text-slate-300">{c.rate_limit_per_minute}/min</td>
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
        <div className="glass-panel p-6 rounded-2xl border border-slate-800 space-y-4">
          <h3 className="text-sm font-bold text-white">HMAC Signed Webhook Endpoints</h3>
          <p className="text-xs text-slate-400">
            Every delivery includes an HMAC-SHA256 signature in X-PayNexus-Signature header.
          </p>
          <div className="space-y-3 font-mono text-xs">
            {webhooks.length === 0 ? (
              <p className="text-slate-500 py-6 text-center">No active webhook subscriptions.</p>
            ) : (
              webhooks.map((w) => (
                <div key={w.id} className="p-3.5 rounded-xl bg-slate-950 border border-slate-800 flex justify-between">
                  <div>
                    <span className="text-indigo-400 font-bold">{w.url}</span>
                    <span className="text-slate-500 block text-[11px] mt-0.5">Events: {(w.events || []).join(', ')}</span>
                  </div>
                  <span className="text-emerald-400 text-[10px]">ACTIVE</span>
                </div>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  );
};
