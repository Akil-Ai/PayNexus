import React, { useState, useEffect } from 'react';
import { api } from '../lib/api';
import {
  History,
  ShieldCheck,
  ShieldAlert,
  Search,
  CheckCircle2,
  AlertTriangle,
  Flame,
  ArrowRight,
  Lock,
} from 'lucide-react';

export const AuditExplorer: React.FC = () => {
  const [logs, setLogs] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [verificationResult, setVerificationResult] = useState<any>(null);
  const [verifying, setVerifying] = useState(false);
  const [tampering, setTampering] = useState(false);

  const fetchAuditLogs = async () => {
    setLoading(true);
    try {
      const data = await api.listAuditLogs({ limit: 40 });
      setLogs(data);
    } catch (err) {
      console.error('Failed to load audit logs:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAuditLogs();
  }, []);

  const handleVerifyIntegrity = async () => {
    setVerifying(true);
    try {
      const res = await api.verifyAuditIntegrity();
      setVerificationResult(res);
    } catch (err: any) {
      alert(`Verification error: ${err.message}`);
    } finally {
      setVerifying(false);
    }
  };

  const handleTamperDemo = async () => {
    setTampering(true);
    try {
      const res = await api.tamperDemo();
      alert(`[Tamper Injection Successful]\n${res.instructions}`);
      await fetchAuditLogs();
      // Automatically run verify to immediately highlight the tamper!
      const verifyRes = await api.verifyAuditIntegrity();
      setVerificationResult(verifyRes);
    } catch (err: any) {
      alert(`Tamper demo error: ${err.message}`);
    } finally {
      setTampering(false);
    }
  };

  return (
    <div className="space-y-8 max-w-7xl mx-auto">
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2">
            <Lock className="w-5 h-5 text-indigo-400" />
            <span>Cryptographic Audit Chain Explorer</span>
          </h1>
          <p className="text-sm text-slate-400">
            Append-only audit trail with SHA-256 forward-linked hash integrity and tamper detection
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={handleVerifyIntegrity}
            disabled={verifying}
            className="flex items-center gap-2 px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-medium text-xs shadow-md shadow-indigo-600/30 transition disabled:opacity-50"
          >
            <ShieldCheck className="w-4 h-4" />
            <span>{verifying ? 'Verifying Chain...' : 'Verify Chain Integrity'}</span>
          </button>

          <button
            onClick={handleTamperDemo}
            disabled={tampering}
            className="flex items-center gap-2 px-4 py-2 rounded-xl bg-rose-600/20 hover:bg-rose-600/30 text-rose-300 font-medium text-xs border border-rose-500/30 transition disabled:opacity-50"
            title="Deliberately corrupt a database row to prove cryptographic detection"
          >
            <Flame className="w-4 h-4 text-rose-400" />
            <span>Tamper Demo</span>
          </button>
        </div>
      </div>

      {/* ── Verification Banner ── */}
      {verificationResult && (
        <div
          className={`p-5 rounded-2xl border transition animate-in fade-in duration-200 ${
            verificationResult.is_valid
              ? 'bg-emerald-950/20 border-emerald-500/40 text-emerald-300'
              : 'bg-rose-950/30 border-rose-500/50 text-rose-300 shadow-xl shadow-rose-950/40'
          }`}
        >
          <div className="flex items-start gap-3">
            {verificationResult.is_valid ? (
              <CheckCircle2 className="w-5 h-5 text-emerald-400 flex-shrink-0 mt-0.5" />
            ) : (
              <ShieldAlert className="w-5 h-5 text-rose-400 flex-shrink-0 mt-0.5 animate-bounce" />
            )}
            <div className="space-y-1">
              <h3 className="font-bold text-sm">
                {verificationResult.is_valid
                  ? 'Audit Hash-Chain Verification Passed: 100% Intact'
                  : 'TAMPER DETECTED: Audit Hash-Chain Integrity Broken!'}
              </h3>
              <p className="text-xs opacity-90 font-mono">
                {verificationResult.is_valid
                  ? `Successfully validated ${verificationResult.total_rows_checked} sequential records. Every row matches prev_hash + SHA-256 signature.`
                  : `Chain broken at sequence #${verificationResult.corrupted_sequence}! Expected hash does not match computed hash.`}
              </p>
            </div>
          </div>
        </div>
      )}

      {/* ── Audit Hash Chain Stream Table ── */}
      <div className="glass-panel rounded-2xl overflow-hidden border border-slate-800">
        <table className="w-full text-left text-xs">
          <thead className="bg-slate-900/80 border-b border-slate-800 text-slate-400 font-semibold uppercase tracking-wider">
            <tr>
              <th className="py-3 px-4 w-16">Seq #</th>
              <th className="py-3 px-4">Entity</th>
              <th className="py-3 px-4">Action</th>
              <th className="py-3 px-4">Actor</th>
              <th className="py-3 px-4">Row SHA-256 Hash</th>
              <th className="py-3 px-4">Prev SHA-256 Hash</th>
              <th className="py-3 px-4">Timestamp</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800/60 font-mono">
            {loading ? (
              <tr>
                <td colSpan={7} className="text-center py-12 text-slate-500">
                  Loading cryptographic audit ledger...
                </td>
              </tr>
            ) : (
              logs.map((log) => (
                <tr key={log.id} className="hover:bg-slate-800/30">
                  <td className="py-3 px-4 font-bold text-indigo-400">#{log.sequence}</td>
                  <td className="py-3 px-4 font-sans text-slate-300">
                    <span className="font-semibold text-white">{log.entity_type}</span>{' '}
                    <span className="text-slate-500 text-[10px]">({log.entity_id?.slice(0, 8)})</span>
                  </td>
                  <td className="py-3 px-4">
                    <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-slate-800 text-slate-200 border border-slate-700">
                      {log.action}
                    </span>
                  </td>
                  <td className="py-3 px-4 font-sans text-slate-400">{log.actor_id || 'SYSTEM'}</td>
                  <td className="py-3 px-4 text-emerald-400 font-bold" title={log.row_hash}>
                    {log.row_hash ? `${log.row_hash.slice(0, 14)}...` : 'N/A'}
                  </td>
                  <td className="py-3 px-4 text-slate-500" title={log.prev_hash}>
                    {log.prev_hash ? `${log.prev_hash.slice(0, 14)}...` : 'ROOT_GENESIS'}
                  </td>
                  <td className="py-3 px-4 text-slate-500 text-[11px]">
                    {new Date(log.created_at).toLocaleTimeString()}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};
