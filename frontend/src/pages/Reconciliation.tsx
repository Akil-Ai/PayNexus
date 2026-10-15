import React, { useState, useEffect } from 'react';
import { api } from '../lib/api';
import {
  GitCompare,
  Upload,
  CheckCircle2,
  AlertTriangle,
  Play,
  FileText,
  Clock,
  ArrowRight,
  ShieldCheck,
  RefreshCw,
} from 'lucide-react';

export const Reconciliation: React.FC = () => {
  const [runs, setRuns] = useState<any[]>([]);
  const [selectedRun, setSelectedRun] = useState<any>(null);
  const [exceptions, setExceptions] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [railCode, setRailCode] = useState('UPI');

  const fetchRuns = async () => {
    setLoading(true);
    try {
      const data = await api.listReconRuns();
      setRuns(data);
      if (data.length > 0 && !selectedRun) {
        handleSelectRun(data[0]);
      }
    } catch (err) {
      console.error('Failed to load recon runs:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchRuns();
  }, []);

  const handleSelectRun = async (run: any) => {
    setSelectedRun(run);
    try {
      const excs = await api.getRunExceptions(run.id);
      setExceptions(excs);
    } catch (err) {
      console.error('Failed to load exceptions for run:', err);
    }
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setUploading(true);
    const formData = new FormData();
    formData.append('file', file);
    formData.append('rail_code', railCode);
    formData.append('auto_resolve', 'true');

    try {
      const result = await api.uploadAndRunStatement(formData);
      alert(`Reconciliation Completed! Match Rate: ${result.match_rate}% (${result.matched_records}/${result.total_records})`);
      fetchRuns();
    } catch (err: any) {
      alert(`Reconciliation error: ${err.message}`);
    } finally {
      setUploading(false);
    }
  };

  const handleResolveException = async (exceptionId: string, action: string) => {
    try {
      await api.resolveException(exceptionId, action, 'Manual reconciliation override');
      setExceptions((prev) =>
        prev.map((e) => (e.id === exceptionId ? { ...e, status: 'RESOLVED' } : e))
      );
      alert(`Exception resolved via ${action}`);
    } catch (err: any) {
      alert(`Failed to resolve: ${err.message}`);
    }
  };

  return (
    <div className="space-y-8 max-w-7xl mx-auto">
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-white">Reconciliation Hub</h1>
          <p className="text-sm text-slate-400">
            Ingest camt.053 XML and bank statement CSVs, classify discrepancies, and auto-settle matched transactions
          </p>
        </div>

        {/* Upload Button with hidden input */}
        <div className="flex items-center gap-3">
          <select
            value={railCode}
            onChange={(e) => setRailCode(e.target.value)}
            className="bg-slate-900 border border-slate-700 rounded-xl px-3 py-2 text-xs text-slate-200 font-mono"
          >
            <option value="UPI">UPI Rail</option>
            <option value="NEFT">NEFT Rail</option>
            <option value="SWIFT">SWIFT Rail</option>
            <option value="CARD">CARD Clearing</option>
          </select>

          <label className="flex items-center gap-2 px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-medium text-xs shadow-md shadow-indigo-600/30 cursor-pointer transition">
            <Upload className="w-3.5 h-3.5" />
            <span>{uploading ? 'Processing Recon...' : 'Upload Statement'}</span>
            <input
              type="file"
              accept=".csv,.xml"
              onChange={handleFileUpload}
              disabled={uploading}
              className="hidden"
            />
          </label>
        </div>
      </div>

      {/* ── Active Run Breakdown Stats ── */}
      {selectedRun && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="glass-panel p-4 rounded-xl">
            <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
              Total Rail Records
            </span>
            <div className="text-xl font-bold text-white mt-1">
              {selectedRun.total_records || 0} txs
            </div>
          </div>

          <div className="glass-panel p-4 rounded-xl">
            <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
              Exact Match Rate
            </span>
            <div className="text-xl font-bold text-emerald-400 mt-1">
              {selectedRun.match_rate || 0}%
            </div>
          </div>

          <div className="glass-panel p-4 rounded-xl">
            <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
              Matched Value
            </span>
            <div className="text-xl font-bold text-white mt-1">
              ₹{((selectedRun.matched_value_minor || 0) / 100).toLocaleString('en-IN')}
            </div>
          </div>

          <div className="glass-panel p-4 rounded-xl">
            <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
              Exceptions Found
            </span>
            <div className="text-xl font-bold text-amber-400 mt-1">
              {selectedRun.unmatched_records || exceptions.length} cases
            </div>
          </div>
        </div>
      )}

      {/* ── Exceptions Drill-Down List ── */}
      <div className="glass-panel p-6 rounded-2xl space-y-4">
        <h2 className="text-base font-bold text-white flex items-center gap-2">
          <AlertTriangle className="w-4 h-4 text-amber-400" />
          <span>Classified Reconciliation Exceptions</span>
        </h2>

        {exceptions.length === 0 ? (
          <div className="p-8 text-center text-xs text-slate-500 font-mono">
            Zero exceptions in this reconciliation run! All records matched internal ledger.
          </div>
        ) : (
          <div className="space-y-3">
            {exceptions.map((exc) => (
              <div
                key={exc.id}
                className="p-4 rounded-xl bg-slate-900 border border-slate-800 space-y-3"
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="px-2 py-0.5 rounded text-[10px] font-bold font-mono bg-rose-500/20 text-rose-400 border border-rose-500/30">
                      {exc.exception_type}
                    </span>
                    <span className="text-xs font-semibold text-white">{exc.description}</span>
                  </div>
                  <span
                    className={`text-xs px-2.5 py-0.5 rounded-full font-mono ${
                      exc.status === 'RESOLVED'
                        ? 'bg-emerald-500/20 text-emerald-400'
                        : 'bg-amber-500/20 text-amber-300'
                    }`}
                  >
                    {exc.status}
                  </span>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs font-mono">
                  <div className="p-2.5 rounded-lg bg-slate-950 border border-slate-800">
                    <span className="text-slate-500 block mb-1">PayNexus Internal Record:</span>
                    <pre className="text-[11px] text-slate-300">
                      {JSON.stringify(exc.internal_record || 'None (Missing Internally)', null, 2)}
                    </pre>
                  </div>
                  <div className="p-2.5 rounded-lg bg-slate-950 border border-slate-800">
                    <span className="text-slate-500 block mb-1">Rail Statement Record:</span>
                    <pre className="text-[11px] text-slate-300">
                      {JSON.stringify(exc.rail_record || 'None (Missing at Rail)', null, 2)}
                    </pre>
                  </div>
                </div>

                {exc.status !== 'RESOLVED' && (
                  <div className="flex items-center justify-between pt-2 border-t border-slate-800/80">
                    <span className="text-xs text-indigo-400 font-sans">
                      Suggested: {exc.suggested_action}
                    </span>
                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => handleResolveException(exc.id, 'FORCE_SETTLE')}
                        className="px-3 py-1 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-medium"
                      >
                        Force Settle
                      </button>
                      <button
                        onClick={() => handleResolveException(exc.id, 'IGNORE')}
                        className="px-3 py-1 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-medium"
                      >
                        Dismiss
                      </button>
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
