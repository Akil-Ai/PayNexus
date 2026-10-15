import React, { useState } from 'react';
import { api } from '../lib/api';
import { FileCode, Play, CheckCircle2, AlertTriangle, ArrowRight, Copy } from 'lucide-react';

const PRESETS: Record<string, { label: string; format: string; content: string }> = {
  pain001: {
    label: 'ISO 20022 pain.001 XML',
    format: 'PAIN_001',
    content: `<?xml version="1.0" encoding="UTF-8"?>
<Document xmlns="urn:iso:std:iso:20022:tech:xsd:pain.001.001.09">
  <CstmrCdtTrfInitn>
    <GrpHdr>
      <MsgId>MSG-2026-1015-001</MsgId>
      <CreDtTm>2026-10-15T10:00:00Z</CreDtTm>
      <NbOfTxs>1</NbOfTxs>
      <InitgPty><Nm>Acme Corp</Nm></InitgPty>
    </GrpHdr>
    <PmtInf>
      <PmtInfId>PMT-INF-001</PmtInfId>
      <PmtMtd>TRF</PmtMtd>
      <Dbtr><Nm>Acme Corp India Pvt Ltd</Nm></Dbtr>
      <DbtrAcct><Id><Othr><Id>919876543210</Id></Othr></Id></DbtrAcct>
      <CdtTrfTxInf>
        <PmtId><InstrId>INS-88912</InstrId><EndToEndId>E2E-88912</EndToEndId></PmtId>
        <Amt><InstdAmt Ccy="INR">25000.00</InstdAmt></Amt>
        <Cdtr><Nm>Zenith Cloud Technologies</Nm></Cdtr>
        <CdtrAcct><Id><Othr><Id>918877665544</Id></Othr></Id></CdtrAcct>
        <RmtInf><Ustrd>Q3 Server Infrastructure Retainer</Ustrd></RmtInf>
      </CdtTrfTxInf>
    </PmtInf>
  </CstmrCdtTrfInitn>
</Document>`,
  },
  iso8583: {
    label: 'ISO 8583 JSON',
    format: 'ISO_8583',
    content: `{
  "mti": "0200",
  "fields": {
    "3": "000000",
    "4": "450000",
    "11": "892144",
    "41": "TERM0012",
    "49": "356",
    "102": "411111XXXXXX1111",
    "103": "MERCH_89211",
    "cardholder_name": "Rohan Sharma",
    "merchant_name": "Reliance Digital Store",
    "description": "Electronics POS Purchase"
  }
}`,
  },
  swift: {
    label: 'SWIFT MT103',
    format: 'SWIFT_MT103',
    content: `:20:SWIFT20261015099
:23B:CRED
:32A:261015USD12500,00
:50K:/US8899112233
Global Logistics Corp
:57A:CHASUS33XXX
:59:/IN1122334455
Apex Engineering India
:70:Cross-border software license fee
:71A:SHA`,
  },
  csv: {
    label: 'Legacy CSV Batch',
    format: 'CSV',
    content: `instruction_id,debtor_name,debtor_account,debtor_ifsc,creditor_name,creditor_account,creditor_ifsc,amount,currency,description
LEG-001,Priya Patel,9123456789,HDFC0001234,Aarav Tech,9876543210,SBIN0005678,1250.50,INR,Consulting Fee`,
  },
};

export const Translator: React.FC = () => {
  const [selectedPreset, setSelectedPreset] = useState('pain001');
  const [formatType, setFormatType] = useState('PAIN_001');
  const [inputContent, setInputContent] = useState(PRESETS.pain001.content);
  const [output, setOutput] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  const handleSelectPreset = (key: string) => {
    setSelectedPreset(key);
    setFormatType(PRESETS[key].format);
    setInputContent(PRESETS[key].content);
    setOutput(null);
  };

  const handleTranslate = async () => {
    setLoading(true);
    try {
      const res = await api.translateMessage(inputContent, formatType);
      setOutput(res);
    } catch (err: any) {
      setOutput({ success: false, error: err.message, validation_errors: [err.message] });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6 max-w-6xl mx-auto">
      <div className="bg-white p-6 rounded-2xl border border-slate-200/80 shadow-xs flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <h1 className="text-2xl font-bold tracking-tight text-[#102A56] flex items-center gap-2">
              <FileCode className="w-6 h-6 text-blue-600" />
              <span>ISO 20022 Message Translator</span>
            </h1>
            <span className="px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-blue-50 text-blue-700 border border-blue-200/60">
              Syntax Normalizer
            </span>
          </div>
          <p className="text-sm text-slate-500">
            Bidirectional message transformation: pain.001, pacs.008, ISO 8583, SWIFT MT103, and Legacy CSV
          </p>
        </div>
      </div>

      {/* Preset selection bar */}
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider mr-2">
          Sample Payloads:
        </span>
        {Object.entries(PRESETS).map(([key, item]) => (
          <button
            key={key}
            onClick={() => handleSelectPreset(key)}
            className={`px-3 py-1.5 rounded-xl text-xs font-semibold border transition ${
              selectedPreset === key
                ? 'bg-blue-50 border-blue-500 text-blue-700 shadow-2xs'
                : 'bg-white border-slate-200 text-slate-600 hover:text-[#102A56] hover:bg-slate-50'
            }`}
          >
            {item.label}
          </button>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Input Panel */}
        <div className="fintech-card p-5 space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-[#102A56] uppercase tracking-wider">
              Raw Source Message
            </span>
            <select
              value={formatType}
              onChange={(e) => setFormatType(e.target.value)}
              className="bg-slate-50 border border-slate-200 rounded-lg px-2.5 py-1 text-xs text-slate-700 font-mono font-medium focus:outline-none focus:border-blue-600"
            >
              <option value="AUTO">Auto-Detect Format</option>
              <option value="PAIN_001">ISO 20022 pain.001</option>
              <option value="ISO_8583">ISO 8583 JSON</option>
              <option value="SWIFT_MT103">SWIFT MT103</option>
              <option value="CSV">Legacy CSV</option>
            </select>
          </div>

          <textarea
            rows={18}
            value={inputContent}
            onChange={(e) => setInputContent(e.target.value)}
            className="w-full bg-slate-50 border border-slate-200 rounded-xl p-3.5 text-xs font-mono text-[#102A56] focus:outline-none focus:border-blue-600 focus:bg-white transition"
          />

          <button
            onClick={handleTranslate}
            disabled={loading}
            className="w-full flex items-center justify-center gap-2 py-2.5 rounded-xl bg-[#2563EB] hover:bg-blue-700 text-white font-semibold text-xs shadow-xs transition disabled:opacity-50"
          >
            <Play className={`w-3.5 h-3.5 fill-current ${loading ? 'animate-pulse' : ''}`} />
            <span>{loading ? 'Normalizing Message...' : 'Translate to Canonical Model'}</span>
          </button>
        </div>

        {/* Canonical Output Panel */}
        <div className="fintech-card p-5 space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-[#102A56] uppercase tracking-wider">
              Canonical Internal Model (ISO 20022 standard)
            </span>
            {output?.detected_format && (
              <span className="text-[10px] font-mono px-2 py-0.5 rounded font-bold bg-blue-50 text-blue-700 border border-blue-200">
                Format: {output.detected_format}
              </span>
            )}
          </div>

          {output ? (
            <div className="space-y-3">
              {output.validation_errors?.length > 0 && (
                <div className="p-3 rounded-xl bg-red-50 border border-red-200 text-red-700 text-xs font-mono space-y-1">
                  <div className="font-bold flex items-center gap-1.5">
                    <AlertTriangle className="w-4 h-4 text-red-600" />
                    <span>Validation Errors:</span>
                  </div>
                  {output.validation_errors.map((err: string, i: number) => (
                    <div key={i}>• {err}</div>
                  ))}
                </div>
              )}

              <pre className="w-full bg-slate-50 border border-slate-200 rounded-xl p-3.5 text-xs font-mono text-[#102A56] max-h-[460px] overflow-y-auto">
                {JSON.stringify(output.canonical_model || output, null, 2)}
              </pre>
            </div>
          ) : (
            <div className="h-[440px] flex items-center justify-center border border-dashed border-slate-200 rounded-xl text-xs font-mono text-slate-400">
              Click 'Translate to Canonical Model' to view parsed normalized structure.
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
