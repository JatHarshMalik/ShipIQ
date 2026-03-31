import { useEffect, useMemo, useRef, useState } from 'react';
import './index.css';
import { api } from './services/api';
import { parseCargoCsv, parseTankCsv, exportResultsCsv, downloadTemplate } from './utils/csv';

// ─── Constants ──────────────────────────────────────────────────────────────

const DEFAULTS = {
  cargos: [
    { id: 'C1', volume: 1234, weight: 0 },
    { id: 'C2', volume: 4352, weight: 0 },
    { id: 'C3', volume: 3321, weight: 0 },
    { id: 'C4', volume: 2456, weight: 0 },
    { id: 'C5', volume: 5123, weight: 0 },
    { id: 'C6', volume: 1879, weight: 0 },
    { id: 'C7', volume: 4987, weight: 0 },
    { id: 'C8', volume: 2050, weight: 0 },
    { id: 'C9', volume: 3678, weight: 0 },
    { id: 'C10', volume: 5432, weight: 0 },
  ],
  tanks: [
    { id: 'T1', capacity: 1234, weight_limit: 0 },
    { id: 'T2', capacity: 4352, weight_limit: 0 },
    { id: 'T3', capacity: 3321, weight_limit: 0 },
    { id: 'T4', capacity: 2456, weight_limit: 0 },
    { id: 'T5', capacity: 5123, weight_limit: 0 },
    { id: 'T6', capacity: 1879, weight_limit: 0 },
    { id: 'T7', capacity: 4987, weight_limit: 0 },
    { id: 'T8', capacity: 2050, weight_limit: 0 },
    { id: 'T9', capacity: 3678, weight_limit: 0 },
    { id: 'T10', capacity: 5432, weight_limit: 0 },
  ],
};

const CARGO_COLORS = [
  '#378add','#1d9e75','#d85a30','#d4537e','#ba7517',
  '#639922','#534ab7','#e24b4a','#5dcaa5','#f09595',
];

// ─── Helpers ─────────────────────────────────────────────────────────────────

let _uid = 0;
const createUid = () => `uid-${++_uid}`;

const withUid = (row) => ({ ...row, _uid: createUid() });

function getFillColor(pct) {
  if (pct >= 90) return '#378add';
  if (pct >= 50) return '#1d9e75';
  return '#ba7517';
}

function normalizeResult(rawResult, tanksInput) {
  const allocations = (rawResult.allocations || []).map((entry) => {
    const loaded = Number(entry.allocated_volume || 0);
    const cap = Number(entry.tank_capacity || 0);
    const pct = Number(entry.utilization_pct || (cap ? (loaded / cap) * 100 : 0));
    return { tank_id: entry.tank_id, cargo_id: entry.cargo_id, loaded_volume: loaded, tank_capacity: cap, fill_pct: pct };
  });

  const usedIds = new Set(allocations.map((a) => a.tank_id));
  const emptyTanks = tanksInput
    .filter((t) => !usedIds.has(t.id))
    .map((t) => ({ tank_id: t.id, cargo_id: '', loaded_volume: 0, tank_capacity: Number(t.capacity || 0), fill_pct: 0 }));

  return {
    allocations: [...allocations, ...emptyTanks],
    total_loaded: Number(rawResult.total_loaded_volume || 0),
    utilization_pct: Number(rawResult.loading_efficiency_pct || 0),
    total_capacity: Number(rawResult.total_tank_capacity || 0),
    unallocated_cargo_volume: (rawResult.unallocated_cargo || []).reduce((s, c) => s + Number(c.volume || 0), 0),
  };
}

// ─── Validation ──────────────────────────────────────────────────────────────

function validateRows(rows, type) {
  const errors = {};
  const seenIds = new Set();
  const volumeKey = type === 'cargo' ? 'volume' : 'capacity';

  rows.forEach((row) => {
    const rowErrors = [];
    const id = (row.id || '').trim();
    if (!id) {
      rowErrors.push('ID is required');
    } else if (seenIds.has(id)) {
      rowErrors.push('Duplicate ID');
    } else {
      seenIds.add(id);
    }
    const val = Number(row[volumeKey]);
    if (!val || val <= 0) rowErrors.push(`${volumeKey} must be > 0`);
    if (rowErrors.length) errors[row._uid] = rowErrors.join(' · ');
  });
  return errors;
}

// ─── Toast hook ──────────────────────────────────────────────────────────────

function useToast() {
  const [toast, setToast] = useState({ msg: '', type: '' });
  const timerRef = useRef(null);

  const show = (msg, type = '') => {
    clearTimeout(timerRef.current);
    setToast({ msg, type });
    timerRef.current = setTimeout(() => setToast({ msg: '', type: '' }), 3000);
  };
  return [toast, show];
}

// ─── CSV import helper ────────────────────────────────────────────────────────

function useCsvImport(setRows, parseFn, rowTemplate, showToast) {
  const inputRef = useRef(null);

  const trigger = () => inputRef.current?.click();

  const handleFile = (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (ev) => {
      try {
        const parsed = parseFn(ev.target.result);
        if (!parsed.length) { showToast('No valid rows found in CSV', 'error'); return; }
        setRows(parsed.map((r) => ({ ...rowTemplate, ...r, _uid: createUid() })));
        showToast(`Imported ${parsed.length} rows from CSV`, 'success');
      } catch {
        showToast('Failed to parse CSV file', 'error');
      }
    };
    reader.readAsText(file);
    e.target.value = '';
  };

  const Input = () => (
    <input
      ref={inputRef}
      type="file"
      accept=".csv,text/csv"
      style={{ display: 'none' }}
      onChange={handleFile}
    />
  );

  return { trigger, Input };
}

// ─── App ─────────────────────────────────────────────────────────────────────

function App() {
  const [apiStatus, setApiStatus] = useState('checking');
  const [statusLabel, setStatusLabel] = useState('Connecting...');
  const [isOptimizing, setIsOptimizing] = useState(false);
  const [toast, showToast] = useToast();

  const [cargoRows, setCargoRows] = useState([]);
  const [tankRows, setTankRows] = useState([]);
  const [cargoErrors, setCargoErrors] = useState({});
  const [tankErrors, setTankErrors] = useState({});
  const [result, setResult] = useState(null);

  // CSV import hooks
  const cargoImport = useCsvImport(
    setCargoRows, parseCargoCsv, { id: '', volume: 0, weight: 0 }, showToast
  );
  const tankImport = useCsvImport(
    setTankRows, parseTankCsv, { id: '', capacity: 0, weight_limit: 0 }, showToast
  );

  // ── Health check ────────────────────────────────────────────────────────
  const checkHealth = async () => {
    setApiStatus('checking');
    setStatusLabel('Checking...');
    try {
      await api.health();
      setApiStatus('online');
      setStatusLabel('API online');
    } catch {
      setApiStatus('error');
      setStatusLabel('Unreachable');
    }
  };

  // ── Row management ─────────────────────────────────────────────────────
  const addRow = (type) => {
    const row = type === 'cargo'
      ? withUid({ id: '', volume: 0, weight: 0 })
      : withUid({ id: '', capacity: 0, weight_limit: 0 });
    if (type === 'cargo') setCargoRows((p) => [...p, row]);
    else setTankRows((p) => [...p, row]);
  };

  const removeRow = (type, uid) => {
    if (type === 'cargo') setCargoRows((p) => p.filter((r) => r._uid !== uid));
    else setTankRows((p) => p.filter((r) => r._uid !== uid));
  };

  const updateRow = (type, uid, key, value) => {
    const upd = (rows) => rows.map((r) => (r._uid === uid ? { ...r, [key]: value } : r));
    if (type === 'cargo') {
      setCargoRows((p) => {
        const next = upd(p);
        setCargoErrors(validateRows(next, 'cargo'));
        return next;
      });
    } else {
      setTankRows((p) => {
        const next = upd(p);
        setTankErrors(validateRows(next, 'tank'));
        return next;
      });
    }
  };

  const clearAll = () => { setCargoRows([]); setTankRows([]); setResult(null); setCargoErrors({}); setTankErrors({}); };

  const loadDefaults = () => {
    setResult(null);
    setCargoErrors({});
    setTankErrors({});
    setCargoRows(DEFAULTS.cargos.map(withUid));
    setTankRows(DEFAULTS.tanks.map(withUid));
    showToast('Sample data loaded', 'success');
  };

  // ── Optimize ────────────────────────────────────────────────────────────
  const runOptimize = async () => {
    const cargos = cargoRows
      .filter((r) => r.id.trim() && Number(r.volume) > 0)
      .map((r) => ({ id: r.id.trim(), volume: Number(r.volume), weight: Number(r.weight || 0) }));
    const tanks = tankRows
      .filter((r) => r.id.trim() && Number(r.capacity) > 0)
      .map((r) => ({ id: r.id.trim(), capacity: Number(r.capacity), weight_limit: Number(r.weight_limit || 0) }));

    const cErrs = validateRows(cargoRows, 'cargo');
    const tErrs = validateRows(tankRows, 'tank');
    setCargoErrors(cErrs);
    setTankErrors(tErrs);

    if (Object.keys(cErrs).length || Object.keys(tErrs).length) {
      showToast('Fix validation errors before optimizing', 'error');
      return;
    }
    if (!cargos.length || !tanks.length) {
      showToast('Add at least one cargo and one tank', 'error');
      return;
    }

    setIsOptimizing(true);
    try {
      await api.submitInput(cargos, tanks);
      const data = await api.optimize();
      setResult(normalizeResult(data, tanks));
      showToast('Optimization complete', 'success');
      setApiStatus('online');
      setStatusLabel('API online');
    } catch (err) {
      showToast(`Error: ${err.message}`, 'error');
      setApiStatus('error');
      setStatusLabel('Error');
    } finally {
      setIsOptimizing(false);
    }
  };

  // ── Effects ────────────────────────────────────────────────────────────
  useEffect(() => { loadDefaults(); checkHealth(); }, []); // eslint-disable-line

  // ── Derived ────────────────────────────────────────────────────────────
  const cargoIds = useMemo(
    () => [...new Set((result?.allocations || []).map((a) => a.cargo_id).filter(Boolean))],
    [result]
  );
  const colorMap = useMemo(() => {
    const m = {};
    cargoIds.forEach((id, i) => { m[id] = CARGO_COLORS[i % CARGO_COLORS.length]; });
    return m;
  }, [cargoIds]);

  // ── Render ─────────────────────────────────────────────────────────────
  return (
    <>
      <header>
        <div className="logo">
          <div className="logo-icon" aria-hidden="true">
            <svg viewBox="0 0 17 17" fill="none" xmlns="http://www.w3.org/2000/svg">
              <rect x="1" y="8" width="15" height="7" rx="2" fill="white" opacity="0.9" />
              <rect x="3" y="5" width="11" height="4" rx="1.5" fill="white" opacity="0.7" />
              <rect x="6" y="2" width="5" height="4" rx="1" fill="white" opacity="0.5" />
            </svg>
          </div>
          ShipIQ Cargo Optimizer
        </div>
        <span className="header-sub">Maritime Logistics Platform</span>
        <div className="api-status">
          <div className={`status-dot${apiStatus === 'online' ? ' online' : apiStatus === 'error' ? ' error' : ''}`} />
          <span>{statusLabel}</span>
        </div>
      </header>

      <div className="layout">
        {/* ── LEFT PANEL ── */}
        <div className="panel-left">
          {/* Actions */}
          <div>
            <div className="section-title">Actions</div>
            <div className="actions">
              <button className="btn btn-primary" type="button" onClick={runOptimize} disabled={isOptimizing}>
                <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
                  <path d="M7 1v5.5L10 4" stroke="white" strokeWidth="1.5" strokeLinecap="round" />
                  <path d="M1.5 9A5.5 5.5 0 1 0 7 1.5" stroke="white" strokeWidth="1.5" strokeLinecap="round" />
                </svg>
                {isOptimizing ? 'Running...' : 'Run optimization'}
              </button>
              <button className="btn btn-secondary" type="button" onClick={loadDefaults}>
                Load sample data
              </button>
              <button className="btn btn-secondary" type="button" onClick={clearAll}>
                Clear
              </button>
            </div>
          </div>

          {/* Cargo editor */}
          <div>
            <div className="section-title-row">
              <span className="section-title" style={{ margin: 0 }}>Cargos (m³)</span>
              <div className="section-actions">
                <button className="btn-text" type="button" onClick={cargoImport.trigger} title="Import CSV">
                  ↑ Import CSV
                </button>
                <button className="btn-text" type="button" onClick={() => downloadTemplate('cargo')} title="Download template">
                  ↓ Template
                </button>
              </div>
            </div>
            <cargoImport.Input />

            <div className="data-editor">
              <div className="data-editor-header" style={{ gridTemplateColumns: '1fr 1fr 1fr auto' }}>
                <span>ID</span><span>Volume</span><span>Weight (t)</span><span></span>
              </div>
              <div>
                {cargoRows.map((row) => (
                  <div key={row._uid}>
                    <div className="data-row" style={{ gridTemplateColumns: '1fr 1fr 1fr auto' }}>
                      <input
                        type="text" value={row.id} placeholder="C1"
                        className={cargoErrors[row._uid] ? 'input-error' : ''}
                        onChange={(e) => updateRow('cargo', row._uid, 'id', e.target.value)}
                      />
                      <input
                        type="number" min="0" step="1" value={row.volume || ''} placeholder="Volume"
                        className={cargoErrors[row._uid] ? 'input-error' : ''}
                        onChange={(e) => updateRow('cargo', row._uid, 'volume', Number(e.target.value))}
                      />
                      <input
                        type="number" min="0" step="0.1" value={row.weight || ''} placeholder="0 = none"
                        onChange={(e) => updateRow('cargo', row._uid, 'weight', Number(e.target.value))}
                      />
                      <button className="btn-icon" type="button" onClick={() => removeRow('cargo', row._uid)}>×</button>
                    </div>
                    {cargoErrors[row._uid] && (
                      <div className="row-error">{cargoErrors[row._uid]}</div>
                    )}
                  </div>
                ))}
              </div>
            </div>
            <button className="btn-add" type="button" onClick={() => addRow('cargo')}>+ Add cargo</button>
          </div>

          {/* Tank editor */}
          <div>
            <div className="section-title-row">
              <span className="section-title" style={{ margin: 0 }}>Tanks (m³)</span>
              <div className="section-actions">
                <button className="btn-text" type="button" onClick={tankImport.trigger} title="Import CSV">
                  ↑ Import CSV
                </button>
                <button className="btn-text" type="button" onClick={() => downloadTemplate('tank')} title="Download template">
                  ↓ Template
                </button>
              </div>
            </div>
            <tankImport.Input />

            <div className="data-editor">
              <div className="data-editor-header" style={{ gridTemplateColumns: '1fr 1fr 1fr auto' }}>
                <span>ID</span><span>Capacity</span><span>Wt. limit (t)</span><span></span>
              </div>
              <div>
                {tankRows.map((row) => (
                  <div key={row._uid}>
                    <div className="data-row" style={{ gridTemplateColumns: '1fr 1fr 1fr auto' }}>
                      <input
                        type="text" value={row.id} placeholder="T1"
                        className={tankErrors[row._uid] ? 'input-error' : ''}
                        onChange={(e) => updateRow('tank', row._uid, 'id', e.target.value)}
                      />
                      <input
                        type="number" min="0" step="1" value={row.capacity || ''} placeholder="Capacity"
                        className={tankErrors[row._uid] ? 'input-error' : ''}
                        onChange={(e) => updateRow('tank', row._uid, 'capacity', Number(e.target.value))}
                      />
                      <input
                        type="number" min="0" step="0.1" value={row.weight_limit || ''} placeholder="0 = none"
                        onChange={(e) => updateRow('tank', row._uid, 'weight_limit', Number(e.target.value))}
                      />
                      <button className="btn-icon" type="button" onClick={() => removeRow('tank', row._uid)}>×</button>
                    </div>
                    {tankErrors[row._uid] && (
                      <div className="row-error">{tankErrors[row._uid]}</div>
                    )}
                  </div>
                ))}
              </div>
            </div>
            <button className="btn-add" type="button" onClick={() => addRow('tank')}>+ Add tank</button>
          </div>
        </div>

        {/* ── RIGHT PANEL ── */}
        <div className="panel-right" id="results-panel">
          {!result && (
            <div className="empty-state" id="empty-state">
              <div className="empty-icon">⚓</div>
              <div className="empty-title">No results yet</div>
              <div className="empty-sub">
                Add cargo and tank data, then click <strong>Run optimization</strong>.
              </div>
            </div>
          )}

          {result && (
            <>
              {/* Stats */}
              <div className="stats-grid">
                <div className="stat-card">
                  <div className="stat-label">Total loaded</div>
                  <div className="stat-value">{result.total_loaded.toLocaleString()}</div>
                  <div className="stat-sub">m³</div>
                </div>
                <div className="stat-card">
                  <div className="stat-label">Utilization</div>
                  <div className="stat-value">{result.utilization_pct.toFixed(1)}%</div>
                  <div className="stat-sub">of total capacity</div>
                </div>
                <div className="stat-card">
                  <div className="stat-label">Tank capacity</div>
                  <div className="stat-value">{result.total_capacity.toLocaleString()}</div>
                  <div className="stat-sub">m³ total</div>
                </div>
                <div className="stat-card">
                  <div className="stat-label">Unallocated</div>
                  <div className="stat-value">{result.unallocated_cargo_volume.toLocaleString()}</div>
                  <div className="stat-sub">m³ cargo excess</div>
                </div>
              </div>

              {/* Tank fill visualisation */}
              <div className="tanks-section">
                <div className="tanks-section-header">
                  <span className="section-heading">Tank fill visualisation</span>
                  <div className="legend" id="legend">
                    {cargoIds.map((id) => (
                      <div className="legend-item" key={id}>
                        <div className="legend-dot" style={{ background: colorMap[id] }}></div>
                        {id}
                      </div>
                    ))}
                  </div>
                </div>
                <div className="tanks-grid" id="tanks-grid">
                  {result.allocations.map((a) => {
                    const pct = Number(a.fill_pct || 0);
                    const color = a.cargo_id ? colorMap[a.cargo_id] : '#e2e1db';
                    return (
                      <div className="tank-card" key={`${a.tank_id}-${a.cargo_id || 'empty'}`}>
                        <div className="tank-label">
                          <span>{a.tank_id}</span>
                          <span className="tank-label-pct">{pct.toFixed(0)}%</span>
                        </div>
                        <div className="tank-bar-wrap">
                          <div className="tank-bar-fill" style={{ height: `${Math.max(pct, 2)}%`, background: color, opacity: 0.85 }} />
                        </div>
                        <div className="tank-meta">
                          <span>{a.cargo_id || '-'}</span>
                          <span>{a.loaded_volume.toLocaleString()}</span>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* Allocation table */}
              <div className="alloc-table-wrap">
                <div className="alloc-table-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span>Allocation details</span>
                  <button
                    className="btn btn-secondary"
                    style={{ fontSize: '12px', padding: '4px 10px' }}
                    type="button"
                    onClick={() => exportResultsCsv(result.allocations)}
                  >
                    ↓ Export CSV
                  </button>
                </div>
                <table>
                  <thead>
                    <tr>
                      <th>Tank</th><th>Cargo</th><th>Loaded</th><th>Capacity</th><th>Fill</th>
                    </tr>
                  </thead>
                  <tbody>
                    {result.allocations.map((a) => {
                      const pct = Number(a.fill_pct || 0);
                      const fillColor = getFillColor(pct);
                      return (
                        <tr key={`${a.tank_id}-table-${a.cargo_id || 'empty'}`}>
                          <td><strong>{a.tank_id}</strong></td>
                          <td>
                            {a.cargo_id
                              ? <span className="badge badge-blue">{a.cargo_id}</span>
                              : <span className="muted">-</span>}
                          </td>
                          <td>{a.loaded_volume.toLocaleString()} m³</td>
                          <td>{a.tank_capacity.toLocaleString()} m³</td>
                          <td>
                            <div className="fill-bar">
                              <div className="fill-bar-track">
                                <div className="fill-bar-fill" style={{ width: `${pct}%`, background: fillColor }} />
                              </div>
                              <span className="fill-bar-pct">{pct.toFixed(1)}%</span>
                            </div>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </>
          )}
        </div>
      </div>

      {/* Toast */}
      <div id="toast" className={`${toast.msg ? 'show' : ''} ${toast.type}`.trim()}>
        {toast.msg}
      </div>
    </>
  );
}

export default App;
