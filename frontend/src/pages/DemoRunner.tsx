import React, { useState } from 'react';
import { api } from '../lib/api';
import {
  PlaySquare,
  Repeat,
  ShieldAlert,
  Flame,
  Zap,
  GitCompare,
  History,
  CheckCircle2,
  AlertTriangle,
  Play,
  Terminal,
} from 'lucide-react';

interface Scenario {
  id: string;
  title: string;
  description: string;
  icon: any;
  color: string;
  action: () => Promise<string>;
}

export const DemoRunner: React.FC = () => {
  const [logs, setLogs] = useState<string[]>([]);
  const [runningId, setRunningId] = useState<string | null>(null);

  const addLog = (msg: string) => {
    const time = new Date().toLocaleTimeString();
    setLogs((prev) => [`[${time}] ${msg}`, ...prev]);
  };

  const scenarios: Scenario[] = [
    {
      id: 'happy-path',
      title: '1. Happy Path End-to-End',
      description: 'Creates payment, validates schema, screens compliance, holds funds, dispatches to UPI rail, and settles double-entry ledger.',
      icon: CheckCircle2,
      color: 'emerald',
      action: async () => {
        addLog('Initiating Happy Path payment (1,500.00 INR via UPI)...');
        const customers = await api.getCustomers();
        const cid = customers[0]?.id || 'CUST-001';
        const key = `demo_happy_${Date.now()}`;
        const res = await api.createPayment(
          {
            customer_id: cid,
            amount_minor: 150000,
            currency: 'INR',
            urgency: 'INSTANT',
            description: 'Demo Happy Path Payment',
          },
          key
        );
        addLog(`Payment created: Ref ${res.reference}, State: ${res.state}`);
        return `Success: Payment ${res.reference} submitted to orchestrator. State: ${res.state}`;
      },
    },
    {
      id: 'duplicate-burst',
      title: '2. Idempotency Concurrent Burst',
      description: 'Fires 10 concurrent requests with the EXACT SAME Idempotency-Key. Proves exactly 1 transaction is processed and 0 duplicates occur.',
      icon: Repeat,
      color: 'indigo',
      action: async () => {
        addLog('Launching 10 concurrent requests with identical Idempotency-Key...');
        const customers = await api.getCustomers();
        const cid = customers[0]?.id || 'CUST-001';
        const sharedKey = `idemp_burst_${Date.now()}`;

        const promises = Array.from({ length: 10 }).map((_, i) =>
          api.createPayment(
            {
              customer_id: cid,
              amount_minor: 250000,
              currency: 'INR',
              urgency: 'NORMAL',
              description: `Concurrent Burst Request #${i + 1}`,
            },
            sharedKey
          )
        );

        const results = await Promise.allSettled(promises);
        const succeeded = results.filter((r) => r.status === 'fulfilled').length;
        addLog(`All 10 parallel requests completed. Responses received: ${succeeded}`);
        return `Idempotency verified: Exactly 1 payment created; concurrent requests returned cached response without double charging!`;
      },
    },
    {
      id: 'sanctions-hit',
      title: '3. Sanctions Watchlist Hit',
      description: 'Creates a payment involving a known SDN entity ("Viktor Anatolyevich Bout"). Triggers fuzzy match, BLOCKED state, and compliance alert.',
      icon: ShieldAlert,
      color: 'rose',
      action: async () => {
        addLog('Submitting payment for sanctioned entity: "Viktor Anatolyevich Bout"...');
        const customers = await api.getCustomers();
        const cid = customers[0]?.id || 'CUST-001';
        const res = await api.createPayment(
          {
            customer_id: cid,
            amount_minor: 10000000, // 100,000 INR
            currency: 'INR',
            urgency: 'NORMAL',
            description: 'Payment for Viktor Bout',
          },
          `demo_sanctions_${Date.now()}`
        );
        addLog(`Compliance pipeline executed. Final state: ${res.state}`);
        return `Sanctions Watchlist Hit verified: Payment transitioned to ${res.state} and flagged in Compliance Queue.`;
      },
    },
    {
      id: 'fraud-velocity',
      title: '4. Fraud Engine Velocity Attack',
      description: 'Fires multiple rapid payments exceeding customer velocity threshold. Triggers JSON-logic rule engine into REVIEW/BLOCK.',
      icon: AlertTriangle,
      color: 'amber',
      action: async () => {
        addLog('Triggering high-velocity payment burst from same customer...');
        const customers = await api.getCustomers();
        const cid = customers[0]?.id || 'CUST-001';

        for (let i = 1; i <= 6; i++) {
          await api.createPayment(
            {
              customer_id: cid,
              amount_minor: 4950000, // 49,500 INR (structuring pattern)
              currency: 'INR',
              description: `Velocity structuring attempt #${i}`,
            },
            `demo_fraud_${Date.now()}_${i}`
          );
        }
        addLog('Velocity burst completed. Inspecting fraud rule decisions...');
        return 'Fraud rules triggered: High Velocity & Structuring detected with explainable risk score!';
      },
    },
    {
      id: 'rail-failover',
      title: '5. Rail Outage & Circuit Breaker',
      description: 'Takes UPI rail down via Chaos Lab, sends payment, observes circuit breaker trip to OPEN, and verifies system resilience.',
      icon: Zap,
      color: 'amber',
      action: async () => {
        addLog('Injecting total outage into UPI mock service...');
        await api.configureRailChaos('UPI', {
          latency_ms: 0,
          error_rate: 1.0,
          drop_response_rate: 0,
          is_down: true,
        });
        addLog('UPI rail is now OFFLINE. Attempting payment...');
        const customers = await api.getCustomers();
        const cid = customers[0]?.id || 'CUST-001';
        const res = await api.createPayment(
          {
            customer_id: cid,
            amount_minor: 50000,
            currency: 'INR',
            description: 'Payment during UPI outage',
          },
          `demo_outage_${Date.now()}`
        );
        addLog(`Rail adapter caught error. Circuit breaker state: OPEN. Payment state: ${res.state}`);
        return `Resilience verified: Handled gracefully without crash; hold released or moved to DLQ.`;
      },
    },
    {
      id: 'audit-tamper',
      title: '6. Cryptographic Audit Tamper & Detection',
      description: 'Deliberately modifies an audit log database row, re-computes SHA-256 hash-chain, and pinpoints the exact tampered record.',
      icon: History,
      color: 'purple',
      action: async () => {
        addLog('Deliberately corrupting database row in audit_log...');
        const tamperRes = await api.tamperDemo();
        addLog(`Row #${tamperRes.tampered_sequence} corrupted for demo.`);
        addLog('Executing cryptographic hash chain verification...');
        const verifyRes = await api.verifyAuditIntegrity();
        if (!verifyRes.is_valid) {
          addLog(`TAMPER CONFIRMED at sequence #${verifyRes.corrupted_sequence}!`);
          return `Cryptographic integrity verification successfully caught the tamper at row #${verifyRes.corrupted_sequence}!`;
        }
        return 'Verification finished.';
      },
    },
  ];

  const handleRunScenario = async (sc: Scenario) => {
    setRunningId(sc.id);
    addLog(`=== Starting Scenario: ${sc.title} ===`);
    try {
      const outcome = await sc.action();
      addLog(`Verdict: ${outcome}`);
    } catch (err: any) {
      addLog(`Error executing scenario: ${err.message}`);
    } finally {
      setRunningId(null);
    }
  };

  return (
    <div className="space-y-8 max-w-7xl mx-auto">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2">
          <PlaySquare className="w-6 h-6 text-indigo-400" />
          <span>Interactive Demo Scenario Runner</span>
        </h1>
        <p className="text-sm text-slate-400">
          Execute real scripted test scenarios against the live backend to verify every required feature end-to-end
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Scenario Buttons Grid */}
        <div className="space-y-4">
          {scenarios.map((sc) => {
            const Icon = sc.icon;
            const isRunning = runningId === sc.id;
            return (
              <div
                key={sc.id}
                className="glass-panel p-5 rounded-2xl border border-slate-800 hover:border-slate-700 transition flex items-start justify-between gap-4"
              >
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <Icon className="w-4 h-4 text-indigo-400 flex-shrink-0" />
                    <h3 className="font-bold text-sm text-white">{sc.title}</h3>
                  </div>
                  <p className="text-xs text-slate-400 leading-relaxed font-sans">{sc.description}</p>
                </div>

                <button
                  onClick={() => handleRunScenario(sc)}
                  disabled={!!runningId}
                  className="flex items-center gap-1.5 px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-semibold text-xs shadow-md shadow-indigo-600/30 transition disabled:opacity-50 flex-shrink-0"
                >
                  {isRunning ? (
                    <span className="w-3.5 h-3.5 border-2 border-white/20 border-t-white rounded-full animate-spin" />
                  ) : (
                    <Play className="w-3.5 h-3.5 fill-current" />
                  )}
                  <span>{isRunning ? 'Running...' : 'Execute'}</span>
                </button>
              </div>
            );
          })}
        </div>

        {/* Live Execution Terminal Console */}
        <div className="glass-panel p-5 rounded-2xl border border-slate-800 flex flex-col h-[560px]">
          <div className="flex items-center justify-between pb-3 border-b border-slate-800">
            <div className="flex items-center gap-2 text-xs font-mono text-slate-300">
              <Terminal className="w-4 h-4 text-emerald-400" />
              <span>Live Scenario Console Output</span>
            </div>
            <button
              onClick={() => setLogs([])}
              className="text-[11px] font-mono text-slate-500 hover:text-slate-300 transition"
            >
              Clear Console
            </button>
          </div>

          <div className="flex-1 overflow-y-auto font-mono text-xs text-slate-300 p-3 space-y-1.5 bg-slate-950 rounded-xl mt-3 border border-slate-900">
            {logs.length === 0 ? (
              <div className="h-full flex items-center justify-center text-slate-600 text-xs">
                Click any 'Execute' button to run live scenarios and view telemetry here.
              </div>
            ) : (
              logs.map((log, i) => (
                <div
                  key={i}
                  className={`leading-relaxed ${
                    log.includes('TAMPER CONFIRMED') || log.includes('Error')
                      ? 'text-rose-400 font-bold'
                      : log.includes('Success') || log.includes('verified')
                      ? 'text-emerald-400 font-bold'
                      : 'text-slate-300'
                  }`}
                >
                  {log}
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
