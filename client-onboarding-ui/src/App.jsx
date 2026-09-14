import React, { useState, useEffect, useCallback } from "react";
import { Check, Circle, Clock, AlertTriangle, Send, Plus, ArrowLeft, RefreshCw, Wifi, WifiOff } from "lucide-react";

const COLORS = {
  bg: "#0E1B2A",
  panel: "#14283F",
  panelAlt: "#101F32",
  line: "#26405C",
  text: "#DCE8F0",
  textMuted: "#7691AC",
  amber: "#E8A33D",
  green: "#4FB286",
  red: "#E2685C",
  cyan: "#5FB3D9",
};

const STAGES = [
  { key: "route", label: "Route" },
  { key: "parse", label: "Parse" },
  { key: "profile", label: "Profile" },
  { key: "config", label: "Auto-config" },
  { key: "chunk", label: "Chunk" },
  { key: "index", label: "Embed & index" },
];

function badge(status) {
  if (status === "done") return { color: COLORS.green, Icon: Check };
  if (status === "running") return { color: COLORS.amber, Icon: Clock };
  if (status === "error") return { color: COLORS.red, Icon: AlertTriangle };
  return { color: COLORS.line, Icon: Circle };
}

function useApi(apiBase) {
  const call = useCallback(
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
  return call;
}

function ConnectionIndicator({ apiBase }) {
  const [ok, setOk] = useState(null);
  const api = useApi(apiBase);

  useEffect(() => {
    let cancelled = false;
    api("/health")
      .then(() => !cancelled && setOk(true))
      .catch(() => !cancelled && setOk(false));
    return () => {
      cancelled = true;
    };
  }, [api]);

  return (
    <div className="flex items-center gap-1.5 text-xs font-mono">
      {ok === null ? (
        <span style={{ color: COLORS.textMuted }}>checking...</span>
      ) : ok ? (
        <>
          <Wifi size={12} color={COLORS.green} />
          <span style={{ color: COLORS.green }}>api connected</span>
        </>
      ) : (
        <>
          <WifiOff size={12} color={COLORS.red} />
          <span style={{ color: COLORS.red }}>api unreachable</span>
        </>
      )}
    </div>
  );
}

function ClientListView({ apiBase, onSelect, onNew }) {
  const api = useApi(apiBase);
  const [clients, setClients] = useState(null);
  const [rows, setRows] = useState({});
  const [error, setError] = useState(null);

  const load = useCallback(() => {
    setError(null);
    api("/customers")
      .then((data) => setClients(data.customers))
      .catch((e) => setError(e.message));
  }, [api]);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    if (!clients) return;
    clients.forEach((id) => {
      Promise.all([api(`/customers/${id}/profile`), api(`/customers/${id}/config`)])
        .then(([profile, config]) => {
          setRows((prev) => ({
            ...prev,
            [id]: {
              fileCount: profile.summary.total_files,
              flagged: config.flagged_for_cleaning.length,
            },
          }));
        })
        .catch(() => {});
    });
  }, [clients, api]);

  return (
    <div className="flex-1 p-6">
      <div className="flex items-center justify-between mb-1">
        <p style={{ color: COLORS.text }} className="text-lg font-mono">Client Directory</p>
        <button
          onClick={onNew}
          style={{ background: COLORS.cyan, color: COLORS.bg }}
          className="rounded px-3 py-1.5 text-sm font-mono flex items-center gap-1"
        >
          <Plus size={14} /> new client
        </button>
      </div>
      <p style={{ color: COLORS.textMuted }} className="text-sm mb-5">
        Clients with a completed pipeline build. Data pulled live from /customers, /profile, /config.
      </p>

      {error && (
        <div style={{ background: COLORS.panelAlt, border: `1px solid ${COLORS.red}`, color: COLORS.red }} className="rounded p-4 text-sm mb-4 flex items-center justify-between">
          <span>Could not reach API at {apiBase}: {error}</span>
          <button onClick={load} style={{ color: COLORS.text }} className="flex items-center gap-1 text-xs">
            <RefreshCw size={12} /> retry
          </button>
        </div>
      )}

      {clients && clients.length === 0 && !error && (
        <p style={{ color: COLORS.textMuted }} className="text-sm">No clients built yet. Click "new client" to onboard one.</p>
      )}

      {clients && clients.length > 0 && (
        <div style={{ border: `1px solid ${COLORS.line}` }} className="rounded overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr style={{ background: COLORS.panelAlt, borderBottom: `1px solid ${COLORS.line}` }}>
                <th style={{ color: COLORS.textMuted }} className="text-left font-mono font-normal px-4 py-2">Client</th>
                <th style={{ color: COLORS.textMuted }} className="text-left font-mono font-normal px-4 py-2">Files</th>
                <th style={{ color: COLORS.textMuted }} className="text-left font-mono font-normal px-4 py-2">Flagged</th>
                <th style={{ color: COLORS.textMuted }} className="text-left font-mono font-normal px-4 py-2">Status</th>
                <th className="px-4 py-2"></th>
              </tr>
            </thead>
            <tbody>
              {clients.map((id) => {
                const row = rows[id];
                return (
                  <tr key={id} style={{ borderBottom: `1px solid ${COLORS.line}` }}>
                    <td style={{ color: COLORS.cyan }} className="px-4 py-2.5 font-mono">{id}</td>
                    <td style={{ color: COLORS.text }} className="px-4 py-2.5 font-mono">{row ? row.fileCount : "…"}</td>
                    <td style={{ color: row?.flagged ? COLORS.amber : COLORS.text }} className="px-4 py-2.5 font-mono">
                      {row ? row.flagged : "…"}
                    </td>
                    <td className="px-4 py-2.5">
                      <span style={{ color: COLORS.green }} className="text-xs font-mono">● ready</span>
                    </td>
                    <td className="px-4 py-2.5 text-right">
                      <button onClick={() => onSelect(id)} style={{ color: COLORS.cyan }} className="text-xs font-mono">
                        inspect →
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

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
      api(`/customers/${clientId}/status`)
        .then(setStatus)
        .catch((e) => setError(e.message));
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
      const initial = await api(`/customers/${clientId}/status`);
      setStatus(initial);
    } catch (e) {
      setError(e.message);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="flex-1 p-6">
      <button onClick={onBack} style={{ color: COLORS.textMuted }} className="flex items-center gap-1 text-xs font-mono mb-4">
        <ArrowLeft size={12} /> back to directory
      </button>
      <p style={{ color: COLORS.text }} className="text-lg font-mono mb-1">Build a client</p>
      <p style={{ color: COLORS.textMuted }} className="text-sm mb-5">
        Uploads to POST /customers/&#123;id&#125;/build, then polls /status live. No fabricated progress — this is the real pipeline running.
      </p>

      {!status && (
        <div style={{ background: COLORS.panelAlt, border: `1px solid ${COLORS.line}` }} className="rounded p-4 max-w-md flex flex-col gap-3">
          <div>
            <label style={{ color: COLORS.textMuted }} className="text-xs font-mono block mb-1">client id</label>
            <input
              value={clientId}
              onChange={(e) => setClientId(e.target.value)}
              placeholder="e.g. acme_corp"
              style={{ background: COLORS.bg, border: `1px solid ${COLORS.line}`, color: COLORS.text }}
              className="w-full rounded px-3 py-2 text-sm font-mono outline-none"
            />
          </div>
          <div>
            <label style={{ color: COLORS.textMuted }} className="text-xs font-mono block mb-1">files (csv, xlsx, pdf, txt, md)</label>
            <input
              type="file"
              multiple
              onChange={(e) => setFiles(Array.from(e.target.files))}
              style={{ color: COLORS.text }}
              className="w-full text-xs font-mono"
            />
          </div>
          {error && <p style={{ color: COLORS.red }} className="text-xs">{error}</p>}
          <button
            onClick={handleSubmit}
            disabled={submitting || !clientId.trim() || files.length === 0}
            style={{
              background: submitting || !clientId.trim() || files.length === 0 ? COLORS.line : COLORS.cyan,
              color: COLORS.bg,
            }}
            className="rounded px-3 py-2 text-sm font-mono"
          >
            {submitting ? "starting..." : "build client"}
          </button>
        </div>
      )}

      {status && (
        <div style={{ background: COLORS.panelAlt, border: `1px solid ${COLORS.line}` }} className="rounded p-5 max-w-md">
          <p style={{ color: COLORS.cyan }} className="font-mono text-sm mb-4">{clientId}</p>
          <div className="flex flex-col gap-3">
            {STAGES.map((s) => {
              const st = status.stages?.[s.key] || "pending";
              const { color, Icon } = badge(st);
              return (
                <div key={s.key} className="flex items-center gap-3">
                  <div style={{ background: st === "done" || st === "running" ? color : "transparent", borderColor: color }} className="w-4 h-4 rounded-full border flex items-center justify-center shrink-0">
                    {st === "done" && <Check size={9} color={COLORS.bg} strokeWidth={3} />}
                  </div>
                  <div className="flex-1">
                    <span style={{ color: st === "pending" ? COLORS.textMuted : COLORS.text }} className="text-sm font-mono">{s.label}</span>
                    {status.detail?.[s.key] && (
                      <span style={{ color: COLORS.textMuted }} className="text-xs font-mono ml-2">— {status.detail[s.key]}</span>
                    )}
                  </div>
                </div>
              );
            })}
          </div>

          {status.overall === "error" && (
            <p style={{ color: COLORS.red }} className="text-sm mt-4">Build failed: {status.error}</p>
          )}

          {status.overall === "done" && (
            <button
              onClick={() => onDone(clientId)}
              style={{ background: COLORS.cyan, color: COLORS.bg }}
              className="rounded px-3 py-2 text-sm font-mono mt-4"
            >
              go to dashboard →
            </button>
          )}
        </div>
      )}
    </div>
  );
}

function ConfigTab({ apiBase, clientId }) {
  const api = useApi(apiBase);
  const [config, setConfig] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    api(`/customers/${clientId}/config`).then(setConfig).catch((e) => setError(e.message));
  }, [api, clientId]);

  if (error) return <p style={{ color: COLORS.red }} className="text-sm">{error}</p>;
  if (!config) return <p style={{ color: COLORS.textMuted }} className="text-sm">Loading...</p>;

  return (
    <div className="flex flex-col gap-3">
      {config.configs.map((cfg) => (
        <div key={cfg.filename} style={{ background: COLORS.panelAlt, border: `1px solid ${COLORS.line}` }} className="rounded p-4">
          <div className="flex items-center justify-between mb-1">
            <span style={{ color: COLORS.cyan }} className="font-mono text-sm">{cfg.filename}</span>
            {cfg.needs_cleaning && (
              <span style={{ color: COLORS.amber }} className="flex items-center gap-1 text-xs font-mono">
                <AlertTriangle size={12} /> needs cleaning
              </span>
            )}
          </div>
          <p style={{ color: COLORS.text }} className="text-sm mb-1">
            <span style={{ color: COLORS.textMuted }}>strategy:</span> {cfg.strategy}
            {cfg.chunk_size && <span style={{ color: COLORS.textMuted }}> · chunk_size={cfg.chunk_size}, overlap={cfg.chunk_overlap}</span>}
            {cfg.rows_per_chunk && <span style={{ color: COLORS.textMuted }}> · {cfg.rows_per_chunk} row(s)/chunk</span>}
          </p>
          <p style={{ color: COLORS.textMuted }} className="text-sm leading-snug">{cfg.reason}</p>
        </div>
      ))}
    </div>
  );
}

function ProfileTab({ apiBase, clientId }) {
  const api = useApi(apiBase);
  const [profile, setProfile] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    api(`/customers/${clientId}/profile`).then(setProfile).catch((e) => setError(e.message));
  }, [api, clientId]);

  if (error) return <p style={{ color: COLORS.red }} className="text-sm">{error}</p>;
  if (!profile) return <p style={{ color: COLORS.textMuted }} className="text-sm">Loading...</p>;

  return (
    <div className="flex flex-col gap-3">
      {profile.files.map((f) => (
        <div key={f.filename} style={{ background: COLORS.panelAlt, border: `1px solid ${COLORS.line}` }} className="rounded p-4">
          <p style={{ color: COLORS.cyan }} className="font-mono text-sm mb-2">{f.filename} <span style={{ color: COLORS.textMuted }}>({f.kind})</span></p>
          {f.kind === "tabular" && (
            <p style={{ color: COLORS.text }} className="text-sm font-mono">
              {f.row_count} rows · {f.column_count} cols · max null {Math.max(0, ...Object.values(f.null_pct_by_column || { x: 0 })).toFixed(1)}%
            </p>
          )}
          {f.kind === "pdf" && (
            <p style={{ color: COLORS.text }} className="text-sm font-mono">
              {f.page_count} pages · {f.avg_chars_per_page} chars/page avg · {f.text_density} · {f.tables_detected} table(s) detected
            </p>
          )}
          {f.kind === "text" && (
            <p style={{ color: COLORS.text }} className="text-sm font-mono">
              {f.char_count} chars · {f.line_count} lines
            </p>
          )}
        </div>
      ))}
    </div>
  );
}

function AskTab({ apiBase, clientId }) {
  const api = useApi(apiBase);
  const [question, setQuestion] = useState("");
  const [result, setResult] = useState(null);
  const [evalResult, setEvalResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const ask = async () => {
    if (!question.trim()) return;
    setLoading(true);
    setError(null);
    setEvalResult(null);
    try {
      const r = await api(`/customers/${clientId}/query`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question }),
      });
      setResult(r);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  const runEval = async () => {
    if (!question.trim()) return;
    try {
      const r = await api(`/customers/${clientId}/eval`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question }),
      });
      setEvalResult(r);
    } catch (e) {
      setError(e.message);
    }
  };

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center gap-2">
        <input
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && ask()}
          placeholder="Ask this client's assistant a question..."
          style={{ background: COLORS.panelAlt, border: `1px solid ${COLORS.line}`, color: COLORS.text }}
          className="flex-1 rounded px-3 py-2 text-sm font-mono outline-none"
        />
        <button onClick={ask} disabled={loading} style={{ background: COLORS.cyan, color: COLORS.bg }} className="rounded px-3 py-2">
          <Send size={16} />
        </button>
      </div>

      {error && <p style={{ color: COLORS.red }} className="text-sm">{error}</p>}

      {result && (
        <div style={{ background: COLORS.panelAlt, border: `1px solid ${COLORS.line}` }} className="rounded p-4">
          <p style={{ color: COLORS.textMuted }} className="text-xs font-mono mb-1">answer (via {result.provider})</p>
          <p style={{ color: COLORS.text }} className="text-sm mb-3">{result.answer}</p>
          {result.citations.length > 0 && (
            <div className="flex flex-col gap-1">
              {result.citations.map((c, i) => (
                <p key={i} style={{ color: COLORS.cyan }} className="text-xs font-mono">{c.source_file} · {c.locator}</p>
              ))}
            </div>
          )}
          <button onClick={runEval} style={{ color: COLORS.amber, border: `1px solid ${COLORS.amber}` }} className="mt-3 rounded px-3 py-1.5 text-xs font-mono">
            run reliability check
          </button>
        </div>
      )}

      {evalResult && (
        <div style={{ background: COLORS.panelAlt, border: `1px solid ${evalResult.overall_pass ? COLORS.green : COLORS.red}` }} className="rounded p-4">
          <p style={{ color: evalResult.overall_pass ? COLORS.green : COLORS.red }} className="text-sm font-mono mb-2">
            {evalResult.overall_pass ? "PASS" : "FAIL"}
          </p>
          {evalResult.checks.map((c) => (
            <p key={c.check} style={{ color: COLORS.text }} className="text-xs font-mono mb-1">
              {c.passed ? "✅" : "❌"} {c.check} — <span style={{ color: COLORS.textMuted }}>{c.detail}</span>
            </p>
          ))}
        </div>
      )}
    </div>
  );
}

function DashboardView({ apiBase, clientId, onBack }) {
  const [tab, setTab] = useState("config");

  return (
    <div className="flex-1 p-6">
      <button onClick={onBack} style={{ color: COLORS.textMuted }} className="flex items-center gap-1 text-xs font-mono mb-4">
        <ArrowLeft size={12} /> back to directory
      </button>
      <p style={{ color: COLORS.text }} className="text-lg font-mono mb-5">{clientId}</p>

      <div style={{ borderBottom: `1px solid ${COLORS.line}` }} className="flex items-center gap-1 mb-5">
        {[
          { key: "config", label: "Config" },
          { key: "profile", label: "Profile" },
          { key: "ask", label: "Ask" },
        ].map((t) => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            style={{
              color: tab === t.key ? COLORS.text : COLORS.textMuted,
              borderBottom: tab === t.key ? `2px solid ${COLORS.cyan}` : "2px solid transparent",
            }}
            className="px-3 py-2 text-sm font-mono -mb-px"
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

export default function ClientOnboardingApp() {
  const [apiBase, setApiBase] = useState("http://localhost:8000");
  const [view, setView] = useState("list"); // list | build | dashboard
  const [selectedClient, setSelectedClient] = useState(null);
  const [editingApi, setEditingApi] = useState(false);

  return (
    <div style={{ background: COLORS.bg, minHeight: "650px" }} className="w-full flex flex-col font-sans">
      <div style={{ borderBottom: `1px solid ${COLORS.line}` }} className="flex items-center justify-between px-5 py-3">
        <div>
          <p style={{ color: COLORS.text }} className="text-sm font-mono">Client onboarding pipeline</p>
          <p style={{ color: COLORS.textMuted }} className="text-xs mt-0.5">wired to live API — no mocked data</p>
        </div>
        <div className="flex items-center gap-4">
          {editingApi ? (
            <input
              value={apiBase}
              onChange={(e) => setApiBase(e.target.value)}
              onBlur={() => setEditingApi(false)}
              onKeyDown={(e) => e.key === "Enter" && setEditingApi(false)}
              autoFocus
              style={{ background: COLORS.panelAlt, border: `1px solid ${COLORS.line}`, color: COLORS.text }}
              className="rounded px-2 py-1 text-xs font-mono outline-none w-56"
            />
          ) : (
            <button onClick={() => setEditingApi(true)} style={{ color: COLORS.textMuted }} className="text-xs font-mono">
              {apiBase}
            </button>
          )}
          <ConnectionIndicator apiBase={apiBase} />
        </div>
      </div>

      {view === "list" && (
        <ClientListView
          apiBase={apiBase}
          onSelect={(id) => {
            setSelectedClient(id);
            setView("dashboard");
          }}
          onNew={() => setView("build")}
        />
      )}

      {view === "build" && (
        <BuildView
          apiBase={apiBase}
          onBack={() => setView("list")}
          onDone={(id) => {
            setSelectedClient(id);
            setView("dashboard");
          }}
        />
      )}

      {view === "dashboard" && selectedClient && (
        <DashboardView apiBase={apiBase} clientId={selectedClient} onBack={() => setView("list")} />
      )}
    </div>
  );
}
