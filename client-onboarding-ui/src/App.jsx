import React, { useState, useEffect, useCallback } from "react";
import {
  Check, Circle, Clock, AlertTriangle, Send, Plus, ArrowLeft, RefreshCw,
  Wifi, WifiOff, Workflow, Terminal, Database, Info,
} from "lucide-react";

const STAGES = [
  { key: "route", label: "Route" },
  { key: "parse", label: "Parse" },
  { key: "profile", label: "Profile" },
  { key: "config", label: "Auto-config" },
  { key: "chunk", label: "Chunk" },
  { key: "index", label: "Embed & index" },
];

const statusStyles = {
  done: { dot: "bg-emerald-400 shadow-[0_0_10px_rgba(52,211,153,0.7)]" },
  running: { dot: "bg-amber-400 shadow-[0_0_10px_rgba(251,191,36,0.7)] animate-pulse" },
  error: { dot: "bg-rose-400 shadow-[0_0_10px_rgba(251,113,133,0.7)]" },
  pending: { dot: "bg-slate-600" },
};

function useApi(apiBase) {
  return useCallback(
    async (path, options = {}) => {
      const res = await fetch(`${apiBase}${path}`, options);
      if (!res.ok) {
        let detail = res.statusText;
        try {
          const body = await res.json();
          detail = body.detail || detail;
        } catch (_) {}
        throw new Error(detail);
      }
      return res.json();
    },
    [apiBase]
  );
}

// ---------------------------------------------------------------- Header
function ConnectionIndicator({ apiBase, simulatedOutage }) {
  const [ok, setOk] = useState(null);
  const api = useApi(apiBase);

  useEffect(() => {
    if (simulatedOutage) return;
    let cancelled = false;
    api("/health").then(() => !cancelled && setOk(true)).catch(() => !cancelled && setOk(false));
    return () => { cancelled = true; };
  }, [api, simulatedOutage]);

  const connected = !simulatedOutage && ok;
  const checking = !simulatedOutage && ok === null;

  if (checking) return <span className="text-xs font-mono text-slate-500">checking…</span>;

  return connected ? (
    <div className="flex items-center gap-1.5 rounded-full bg-emerald-400/10 border border-emerald-400/30 px-3 py-1">
      <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 shadow-[0_0_8px_rgba(52,211,153,0.8)]" />
      <span className="text-xs font-mono text-emerald-400">connected</span>
    </div>
  ) : (
    <div className="flex items-center gap-1.5 rounded-full bg-rose-400/10 border border-rose-400/30 px-3 py-1">
      <span className="w-1.5 h-1.5 rounded-full bg-rose-400 shadow-[0_0_8px_rgba(251,113,133,0.8)]" />
      <span className="text-xs font-mono text-rose-400">{simulatedOutage ? "outage (simulated)" : "unreachable"}</span>
    </div>
  );
}

function Header({ apiBase, setApiBase, simulatedOutage, setSimulatedOutage }) {
  const [editingApi, setEditingApi] = useState(false);

  return (
    <div className="flex items-center justify-between px-8 py-4 border-b border-slate-800/80 backdrop-blur-sm">
      <div className="flex items-center gap-3">
        <div className="w-9 h-9 rounded-lg bg-emerald-400/10 border border-emerald-400/30 flex items-center justify-center shrink-0">
          <Workflow size={16} className="text-emerald-400" />
        </div>
        <div>
          <div className="flex items-center gap-2">
            <span className="text-sm font-mono font-semibold text-slate-100 tracking-tight">Client Onboarding Pipeline</span>
            <span className="text-[10px] font-mono text-emerald-400 border border-emerald-400/30 rounded px-1.5 py-0.5 leading-none">
              PIPELINE
            </span>
          </div>
          <p className="text-xs text-slate-500 mt-0.5">Auto-adapting RAG builder — no mocked data</p>
        </div>
      </div>

      <div className="flex items-center gap-3">
        <div className="flex items-center gap-2 rounded-lg bg-slate-900/60 border border-slate-800 px-3 py-1.5">
          <Terminal size={13} className="text-slate-500" />
          <span className="text-xs font-mono text-slate-500">endpoint:</span>
          {editingApi ? (
            <input
              value={apiBase}
              onChange={(e) => setApiBase(e.target.value)}
              onBlur={() => setEditingApi(false)}
              onKeyDown={(e) => e.key === "Enter" && setEditingApi(false)}
              autoFocus
              className="bg-transparent text-slate-200 text-xs font-mono outline-none w-44"
            />
          ) : (
            <button onClick={() => setEditingApi(true)} className="text-xs font-mono text-slate-200 hover:text-cyan-400 transition-colors">
              {apiBase}
            </button>
          )}
          <RefreshCw size={12} className="text-slate-600 hover:text-slate-400 cursor-pointer transition-colors" onClick={() => setEditingApi(false)} />
        </div>

        <ConnectionIndicator apiBase={apiBase} simulatedOutage={simulatedOutage} />

        <button
          onClick={() => setSimulatedOutage((v) => !v)}
          className="text-xs font-mono text-slate-500 hover:text-slate-300 underline decoration-dotted underline-offset-4 transition-colors"
          title="UI-only demo toggle — does not call the API"
        >
          {simulatedOutage ? "Restore connection" : "Simulate outage"}
        </button>
      </div>
    </div>
  );
}

// ------------------------------------------------------------ Client List
function ClientListView({ apiBase, simulatedOutage, onSelect, onNew }) {
  const api = useApi(apiBase);
  const [clients, setClients] = useState(null);
  const [rows, setRows] = useState({});
  const [error, setError] = useState(null);

  const load = useCallback(() => {
    if (simulatedOutage) {
      setError("Simulated outage — connection intentionally disabled.");
      setClients(null);
      return;
    }
    setError(null);
    api("/customers").then((data) => setClients(data.customers)).catch((e) => setError(e.message));
  }, [api, simulatedOutage]);

  useEffect(() => { load(); }, [load]);

  useEffect(() => {
    if (!clients) return;
    clients.forEach((id) => {
      Promise.all([api(`/customers/${id}/profile`), api(`/customers/${id}/config`)])
        .then(([profile, config]) => {
          setRows((prev) => ({ ...prev, [id]: { fileCount: profile.summary.total_files, flagged: config.flagged_for_cleaning.length } }));
        })
        .catch(() => {});
    });
  }, [clients, api]);

  return (
    <div className="flex-1 p-8">
      <div className="flex items-center justify-between mb-1">
        <div className="flex items-center gap-3">
          <h1 className="text-xl font-semibold text-slate-100 tracking-tight">Client Directory</h1>
          <span className="text-xs font-mono text-slate-400 bg-slate-800/80 border border-slate-700 rounded-full px-2.5 py-1">
            {clients ? clients.length : "…"} clients
          </span>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={load}
            className="flex items-center gap-1.5 rounded-lg bg-slate-900/60 border border-slate-700 hover:border-slate-600 text-slate-300 font-mono text-sm px-3.5 py-2 transition-colors"
          >
            <RefreshCw size={13} /> Fetch clients
          </button>
          <button
            onClick={onNew}
            className="flex items-center gap-1.5 rounded-lg bg-gradient-to-b from-cyan-400 to-cyan-500 text-slate-950 font-mono text-sm font-medium px-4 py-2 shadow-[0_4px_14px_rgba(56,189,248,0.35)] hover:shadow-[0_6px_20px_rgba(56,189,248,0.5)] hover:-translate-y-0.5 transition-all"
          >
            <Plus size={15} strokeWidth={2.5} /> New client
          </button>
        </div>
      </div>
      <p className="text-sm text-slate-500 mb-6">Clients with a completed pipeline build.</p>

      {error && (
        <div className="rounded-xl bg-rose-500/10 border border-rose-500/30 p-4 mb-5 flex items-center justify-between backdrop-blur-sm">
          <span className="text-sm text-rose-300">{error}</span>
          <button onClick={load} className="flex items-center gap-1 text-xs text-slate-300 hover:text-white transition-colors">
            <RefreshCw size={12} /> retry
          </button>
        </div>
      )}

      {clients && clients.length === 0 && !error && (
        <div className="rounded-xl border border-dashed border-slate-700 p-10 text-center">
          <p className="text-sm text-slate-500">No clients built yet.</p>
        </div>
      )}

      {clients && clients.length > 0 && (
        <div className="rounded-xl border border-slate-800 overflow-hidden shadow-[0_8px_30px_rgba(0,0,0,0.4)]">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-slate-900/70 border-b border-slate-800">
                <th className="text-left font-mono font-medium text-xs uppercase tracking-wider text-slate-500 px-5 py-3">Client identifier</th>
                <th className="text-left font-mono font-medium text-xs uppercase tracking-wider text-slate-500 px-5 py-3">Files ingested</th>
                <th className="text-left font-mono font-medium text-xs uppercase tracking-wider text-slate-500 px-5 py-3">Cleaning flagged</th>
                <th className="text-left font-mono font-medium text-xs uppercase tracking-wider text-slate-500 px-5 py-3">Pipeline status</th>
                <th className="text-right font-mono font-medium text-xs uppercase tracking-wider text-slate-500 px-5 py-3">Action</th>
              </tr>
            </thead>
            <tbody>
              {clients.map((id, i) => {
                const row = rows[id];
                return (
                  <tr key={id} className={`${i % 2 === 0 ? "bg-slate-900/20" : "bg-transparent"} border-b border-slate-800/60 last:border-0 hover:bg-cyan-400/5 transition-colors group`}>
                    <td className="px-5 py-4">
                      <div className="flex items-center gap-3">
                        <div className="w-8 h-8 rounded-lg bg-slate-800/80 border border-slate-700 flex items-center justify-center shrink-0">
                          <Database size={14} className="text-slate-400" />
                        </div>
                        <div>
                          <p className="font-mono text-sm text-slate-100 font-medium">{id}</p>
                          <p className="text-xs text-slate-500">Build completed · Indexed</p>
                        </div>
                      </div>
                    </td>
                    <td className="px-5 py-4">
                      <span className="inline-block font-mono text-xs text-slate-300 bg-slate-800/60 border border-slate-700 rounded-md px-2.5 py-1">
                        {row ? `${row.fileCount} file${row.fileCount === 1 ? "" : "s"}` : "…"}
                      </span>
                    </td>
                    <td className="px-5 py-4">
                      {row && row.flagged > 0 ? (
                        <span className="inline-flex items-center gap-1.5 font-mono text-xs text-amber-400 bg-amber-400/10 border border-amber-400/30 rounded-md px-2.5 py-1">
                          <AlertTriangle size={11} /> {row.flagged} flagged
                        </span>
                      ) : (
                        <span className="font-mono text-xs text-slate-500">{row ? "0 flagged" : "…"}</span>
                      )}
                    </td>
                    <td className="px-5 py-4">
                      <span className="inline-flex items-center gap-1.5 text-xs font-mono text-emerald-400">
                        <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 shadow-[0_0_8px_rgba(52,211,153,0.8)]" /> ready
                      </span>
                    </td>
                    <td className="px-5 py-4 text-right">
                      <button onClick={() => onSelect(id)} className="text-xs font-mono text-emerald-400 group-hover:text-emerald-300 transition-colors">
                        Open Dashboard →
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
          <div className="flex items-center justify-between px-5 py-3 bg-slate-900/50 border-t border-slate-800">
            <span className="flex items-center gap-1.5 text-xs text-slate-500">
              <Info size={12} /> Click any row to open that client's Config, Profile, and Ask workspace.
            </span>
            <span className="text-xs font-mono text-slate-600">GET /customers</span>
          </div>
        </div>
      )}
    </div>
  );
}

// ------------------------------------------------------------------ Build
function BuildView({ apiBase, onDone, onBack }) {
  const api = useApi(apiBase);
  const [clientId, setClientId] = useState("");
  const [files, setFiles] = useState([]);
  const [status, setStatus] = useState(null);
  const [error, setError] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (!status || status.overall === "done" || status.overall === "error") return;
    const t = setTimeout(() => {
      api(`/customers/${clientId}/status`).then(setStatus).catch((e) => setError(e.message));
    }, 1200);
    return () => clearTimeout(t);
  }, [status, clientId, api]);

  const handleSubmit = async () => {
    if (!clientId.trim() || files.length === 0) return;
    setError(null);
    setSubmitting(true);
    const formData = new FormData();
    for (const f of files) formData.append("files", f);
    try {
      await api(`/customers/${clientId}/build`, { method: "POST", body: formData });
      setStatus(await api(`/customers/${clientId}/status`));
    } catch (e) {
      setError(e.message);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="flex-1 p-8">
      <button onClick={onBack} className="flex items-center gap-1 text-xs font-mono text-slate-500 hover:text-slate-300 transition-colors mb-5">
        <ArrowLeft size={12} /> back to directory
      </button>
      <h1 className="text-xl font-semibold text-slate-100 tracking-tight mb-2">Build a client</h1>
      <p className="text-sm text-slate-500 mb-6">Real pipeline run — polls <code className="text-slate-400">/status</code> live, no simulated progress.</p>

      {!status && (
        <div className="rounded-xl bg-slate-900/60 border border-slate-800 p-6 max-w-md shadow-[0_8px_30px_rgba(0,0,0,0.4)] flex flex-col gap-4">
          <div>
            <label className="text-xs font-mono uppercase tracking-wider text-slate-500 block mb-1.5">Client ID</label>
            <input
              value={clientId}
              onChange={(e) => setClientId(e.target.value)}
              placeholder="e.g. acme-corp"
              className="w-full rounded-lg bg-slate-950 border border-slate-700 focus:border-cyan-400 text-slate-100 px-3.5 py-2.5 text-sm font-mono outline-none transition-colors"
            />
          </div>
          <div>
            <label className="text-xs font-mono uppercase tracking-wider text-slate-500 block mb-1.5">Files</label>
            <input
              type="file"
              multiple
              onChange={(e) => setFiles(Array.from(e.target.files))}
              className="w-full text-xs font-mono text-slate-400 file:mr-3 file:rounded-lg file:border-0 file:bg-slate-800 file:text-slate-300 file:px-3 file:py-1.5 file:text-xs hover:file:bg-slate-700 file:transition-colors"
            />
          </div>
          {error && <p className="text-xs text-rose-400">{error}</p>}
          <button
            onClick={handleSubmit}
            disabled={submitting || !clientId.trim() || files.length === 0}
            className="rounded-lg bg-gradient-to-b from-cyan-400 to-cyan-500 disabled:from-slate-700 disabled:to-slate-700 disabled:cursor-not-allowed text-slate-950 disabled:text-slate-500 font-mono text-sm font-medium px-4 py-2.5 shadow-[0_4px_14px_rgba(56,189,248,0.35)] disabled:shadow-none hover:not-disabled:-translate-y-0.5 transition-all"
          >
            {submitting ? "starting…" : "Build client"}
          </button>
        </div>
      )}

      {status && (
        <div className="rounded-xl bg-slate-900/60 border border-slate-800 p-6 max-w-md shadow-[0_8px_30px_rgba(0,0,0,0.4)]">
          <p className="font-mono text-sm text-cyan-400 font-medium mb-5">{clientId}</p>
          <div className="flex flex-col gap-4">
            {STAGES.map((s) => {
              const st = status.stages?.[s.key] || "pending";
              const sty = statusStyles[st];
              return (
                <div key={s.key} className="flex items-start gap-3">
                  <div className={`w-2.5 h-2.5 rounded-full mt-1 shrink-0 ${sty.dot}`} />
                  <div className="flex-1">
                    <span className={`text-sm font-mono ${st === "pending" ? "text-slate-500" : "text-slate-200"}`}>{s.label}</span>
                    {status.detail?.[s.key] && (
                      <p className="text-xs font-mono text-slate-500 mt-0.5">{status.detail[s.key]}</p>
                    )}
                  </div>
                </div>
              );
            })}
          </div>

          {status.overall === "error" && (
            <p className="text-sm text-rose-400 mt-5 pt-4 border-t border-slate-800">Build failed: {status.error}</p>
          )}

          {status.overall === "done" && (
            <button
              onClick={() => onDone(clientId)}
              className="rounded-lg bg-gradient-to-b from-cyan-400 to-cyan-500 text-slate-950 font-mono text-sm font-medium px-4 py-2.5 mt-5 shadow-[0_4px_14px_rgba(56,189,248,0.35)] hover:-translate-y-0.5 transition-all"
            >
              Go to dashboard →
            </button>
          )}
        </div>
      )}
    </div>
  );
}

// ----------------------------------------------------------------- Config
function ConfigTab({ apiBase, clientId }) {
  const api = useApi(apiBase);
  const [config, setConfig] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => { api(`/customers/${clientId}/config`).then(setConfig).catch((e) => setError(e.message)); }, [api, clientId]);

  if (error) return <p className="text-sm text-rose-400">{error}</p>;
  if (!config) return <p className="text-sm text-slate-500">Loading…</p>;

  return (
    <div className="flex flex-col gap-3">
      {config.configs.map((cfg) => (
        <div key={cfg.filename} className="rounded-xl bg-slate-900/60 border border-slate-800 p-5 hover:border-slate-700 transition-colors">
          <div className="flex items-center justify-between mb-2">
            <span className="font-mono text-sm text-cyan-400 font-medium">{cfg.filename}</span>
            {cfg.needs_cleaning && (
              <span className="flex items-center gap-1 text-xs font-mono text-amber-400 bg-amber-400/10 border border-amber-400/30 rounded-full px-2.5 py-1">
                <AlertTriangle size={11} /> needs cleaning
              </span>
            )}
          </div>
          <p className="text-sm text-slate-300 mb-1.5">
            <span className="text-slate-500">strategy:</span> <span className="font-mono">{cfg.strategy}</span>
            {cfg.chunk_size && <span className="text-slate-500 font-mono"> · chunk_size={cfg.chunk_size}, overlap={cfg.chunk_overlap}</span>}
            {cfg.rows_per_chunk && <span className="text-slate-500 font-mono"> · {cfg.rows_per_chunk} row(s)/chunk</span>}
          </p>
          <p className="text-sm text-slate-500 leading-relaxed">{cfg.reason}</p>
        </div>
      ))}
    </div>
  );
}

// ---------------------------------------------------------------- Profile
function ProfileTab({ apiBase, clientId }) {
  const api = useApi(apiBase);
  const [profile, setProfile] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => { api(`/customers/${clientId}/profile`).then(setProfile).catch((e) => setError(e.message)); }, [api, clientId]);

  if (error) return <p className="text-sm text-rose-400">{error}</p>;
  if (!profile) return <p className="text-sm text-slate-500">Loading…</p>;

  return (
    <div className="flex flex-col gap-3">
      {profile.files.map((f) => (
        <div key={f.filename} className="rounded-xl bg-slate-900/60 border border-slate-800 p-5 hover:border-slate-700 transition-colors">
          <p className="font-mono text-sm text-cyan-400 font-medium mb-2">{f.filename} <span className="text-slate-500 font-normal">({f.kind})</span></p>
          {f.kind === "tabular" && (
            <p className="text-sm font-mono text-slate-300">
              {f.row_count} rows · {f.column_count} cols · max null {Math.max(0, ...Object.values(f.null_pct_by_column || { x: 0 })).toFixed(1)}%
            </p>
          )}
          {f.kind === "pdf" && (
            <p className="text-sm font-mono text-slate-300">
              {f.page_count} pages · {f.avg_chars_per_page} chars/page avg · {f.text_density} · {f.tables_detected} table(s) detected
            </p>
          )}
          {f.kind === "text" && (
            <p className="text-sm font-mono text-slate-300">{f.char_count} chars · {f.line_count} lines</p>
          )}
        </div>
      ))}
    </div>
  );
}

// -------------------------------------------------------------------- Ask
function AskTab({ apiBase, clientId }) {
  const api = useApi(apiBase);
  const [question, setQuestion] = useState("");
  const [result, setResult] = useState(null);
  const [evalResult, setEvalResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const ask = async () => {
    if (!question.trim()) return;
    setLoading(true); setError(null); setEvalResult(null);
    try {
      setResult(await api(`/customers/${clientId}/query`, {
        method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ question }),
      }));
    } catch (e) { setError(e.message); } finally { setLoading(false); }
  };

  const runEval = async () => {
    if (!question.trim()) return;
    try {
      setEvalResult(await api(`/customers/${clientId}/eval`, {
        method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ question }),
      }));
    } catch (e) { setError(e.message); }
  };

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center gap-2">
        <input
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && ask()}
          placeholder="Ask this client's assistant a question…"
          className="flex-1 rounded-lg bg-slate-900/60 border border-slate-800 focus:border-cyan-400 text-slate-100 px-3.5 py-2.5 text-sm font-mono outline-none transition-colors"
        />
        <button onClick={ask} disabled={loading} className="rounded-lg bg-gradient-to-b from-cyan-400 to-cyan-500 text-slate-950 p-2.5 shadow-[0_4px_14px_rgba(56,189,248,0.35)] hover:-translate-y-0.5 transition-all disabled:opacity-50">
          <Send size={16} />
        </button>
      </div>

      {error && <p className="text-sm text-rose-400">{error}</p>}

      {result && (
        <div className="rounded-xl bg-slate-900/60 border border-slate-800 p-5">
          <p className="text-xs font-mono uppercase tracking-wider text-slate-500 mb-1.5">answer <span className="text-slate-600">· via {result.provider}</span></p>
          <p className="text-sm text-slate-200 mb-4 leading-relaxed">{result.answer}</p>
          {result.citations.length > 0 && (
            <div className="flex flex-col gap-1 mb-4">
              {result.citations.map((c, i) => (
                <p key={i} className="text-xs font-mono text-cyan-400/80">{c.source_file} · {c.locator}</p>
              ))}
            </div>
          )}
          <button onClick={runEval} className="rounded-lg border border-amber-400/40 text-amber-400 hover:bg-amber-400/10 font-mono text-xs px-3.5 py-1.5 transition-colors">
            Run reliability check
          </button>
        </div>
      )}

      {evalResult && (
        <div className={`rounded-xl bg-slate-900/60 border p-5 ${evalResult.overall_pass ? "border-emerald-400/40" : "border-rose-400/40"}`}>
          <p className={`text-sm font-mono font-semibold mb-3 ${evalResult.overall_pass ? "text-emerald-400" : "text-rose-400"}`}>
            {evalResult.overall_pass ? "PASS" : "FAIL"}
          </p>
          <div className="flex flex-col gap-1.5">
            {evalResult.checks.map((c) => (
              <p key={c.check} className="text-xs font-mono text-slate-300">
                {c.passed ? "✅" : "❌"} <span className="text-slate-200">{c.check}</span> — <span className="text-slate-500">{c.detail}</span>
              </p>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// ------------------------------------------------------------- Dashboard
function DashboardView({ apiBase, clientId, onBack }) {
  const [tab, setTab] = useState("config");
  const tabs = [{ key: "config", label: "Config" }, { key: "profile", label: "Profile" }, { key: "ask", label: "Ask" }];

  return (
    <div className="flex-1 p-8">
      <button onClick={onBack} className="flex items-center gap-1 text-xs font-mono text-slate-500 hover:text-slate-300 transition-colors mb-5">
        <ArrowLeft size={12} /> back to directory
      </button>
      <h1 className="text-xl font-semibold text-slate-100 tracking-tight mb-6">{clientId}</h1>

      <div className="flex items-center gap-1 mb-6 border-b border-slate-800">
        {tabs.map((t) => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={`px-4 py-2.5 text-sm font-mono -mb-px border-b-2 transition-colors ${
              tab === t.key ? "text-slate-100 border-cyan-400" : "text-slate-500 border-transparent hover:text-slate-300"
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {tab === "config" && <ConfigTab apiBase={apiBase} clientId={clientId} />}
      {tab === "profile" && <ProfileTab apiBase={apiBase} clientId={clientId} />}
      {tab === "ask" && <AskTab apiBase={apiBase} clientId={clientId} />}
    </div>
  );
}

// ------------------------------------------------------------------- App
export default function ClientOnboardingApp() {
  const [apiBase, setApiBase] = useState("http://localhost:8000");
  const [view, setView] = useState("list");
  const [selectedClient, setSelectedClient] = useState(null);
  const [simulatedOutage, setSimulatedOutage] = useState(false);

  return (
    <div className="w-full min-h-screen flex flex-col bg-[#0A0F1A] bg-[radial-gradient(circle_at_top,rgba(56,189,248,0.06),transparent_55%)]">
      <Header apiBase={apiBase} setApiBase={setApiBase} simulatedOutage={simulatedOutage} setSimulatedOutage={setSimulatedOutage} />

      {view === "list" && (
        <ClientListView
          apiBase={apiBase}
          simulatedOutage={simulatedOutage}
          onSelect={(id) => { setSelectedClient(id); setView("dashboard"); }}
          onNew={() => setView("build")}
        />
      )}
      {view === "build" && (
        <BuildView apiBase={apiBase} onBack={() => setView("list")} onDone={(id) => { setSelectedClient(id); setView("dashboard"); }} />
      )}
      {view === "dashboard" && selectedClient && (
        <DashboardView apiBase={apiBase} clientId={selectedClient} onBack={() => setView("list")} />
      )}
    </div>
  );
}
