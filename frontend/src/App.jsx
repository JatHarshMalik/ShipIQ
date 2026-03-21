import { useEffect, useMemo, useState } from 'react';
import './index.css';

const DEFAULTS = {
  cargos: [
    { id: 'C1', volume: 1234 },
    { id: 'C2', volume: 4352 },
    { id: 'C3', volume: 3321 },
    { id: 'C4', volume: 2456 },
    { id: 'C5', volume: 5123 },
    { id: 'C6', volume: 1879 },
    { id: 'C7', volume: 4987 },
    { id: 'C8', volume: 2050 },
    { id: 'C9', volume: 3678 },
    { id: 'C10', volume: 5432 },
  ],
  tanks: [
    { id: 'T1', capacity: 1234 },
    { id: 'T2', capacity: 4352 },
    { id: 'T3', capacity: 3321 },
    { id: 'T4', capacity: 2456 },
    { id: 'T5', capacity: 5123 },
    { id: 'T6', capacity: 1879 },
    { id: 'T7', capacity: 4987 },
    { id: 'T8', capacity: 2050 },
    { id: 'T9', capacity: 3678 },
    { id: 'T10', capacity: 5432 },
  ],
};

const CARGO_COLORS = [
  '#378add',
  '#1d9e75',
  '#d85a30',
  '#d4537e',
  '#ba7517',
  '#639922',
  '#534ab7',
  '#e24b4a',
  '#5dcaa5',
  '#f09595',
];

const DEFAULT_API_URL = import.meta.env.VITE_API_URL || '/api';

function createUid() {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;
}

function getFillColor(pct) {
  if (pct >= 90) return '#378add';
  if (pct >= 50) return '#1d9e75';
  return '#ba7517';
}

function normalizeResult(rawResult, tanksInput) {
  const allocations = (rawResult.allocations || []).map((entry) => {
    const loadedVolume = Number(entry.allocated_volume || 0);
    const tankCapacity = Number(entry.tank_capacity || 0);
    const fillPct = Number(entry.utilization_pct || (tankCapacity ? (loadedVolume / tankCapacity) * 100 : 0));

    return {
      tank_id: entry.tank_id,
      cargo_id: entry.cargo_id,
      loaded_volume: loadedVolume,
      tank_capacity: tankCapacity,
      fill_pct: fillPct,
    };
  });

  const usedTankIds = new Set(allocations.map((item) => item.tank_id));
  const emptyTankAllocations = tanksInput
    .filter((tank) => !usedTankIds.has(tank.id))
    .map((tank) => ({
      tank_id: tank.id,
      cargo_id: '',
      loaded_volume: 0,
      tank_capacity: Number(tank.capacity || 0),
      fill_pct: 0,
    }));

  const allAllocations = [...allocations, ...emptyTankAllocations];

  return {
    allocations: allAllocations,
    total_loaded: Number(rawResult.total_loaded_volume || 0),
    utilization_pct: Number(rawResult.loading_efficiency_pct || 0),
    total_capacity: Number(rawResult.total_tank_capacity || 0),
    unallocated_cargo_volume: (rawResult.unallocated_cargo || []).reduce(
      (sum, cargo) => sum + Number(cargo.volume || 0),
      0,
    ),
  };
}

function App() {
  const [status, setStatus] = useState('checking');
  const [statusLabel, setStatusLabel] = useState('Connecting...');
  const [toastMsg, setToastMsg] = useState('');
  const [toastType, setToastType] = useState('');
  const [isOptimizing, setIsOptimizing] = useState(false);

  const [cargoRows, setCargoRows] = useState([]);
  const [tankRows, setTankRows] = useState([]);
  const [result, setResult] = useState(null);

  const showToast = (msg, type = '') => {
    setToastMsg(msg);
    setToastType(type);
    window.clearTimeout(showToast._timer);
    showToast._timer = window.setTimeout(() => {
      setToastMsg('');
      setToastType('');
    }, 2800);
  };

  const baseUrl = useMemo(() => DEFAULT_API_URL.replace(/\/$/, ''), []);

  const checkHealth = async () => {
    setStatus('checking');
    setStatusLabel('Checking...');
    try {
      const response = await fetch(`${baseUrl}/health`);
      if (!response.ok) {
        throw new Error('API unreachable');
      }
      setStatus('online');
      setStatusLabel('API online');
    } catch {
      setStatus('error');
      setStatusLabel('Unreachable');
    }
  };

  const addRow = (type, data = {}) => {
    const row =
      type === 'cargo'
        ? { _uid: createUid(), id: data.id || '', volume: Number(data.volume || 0) }
        : { _uid: createUid(), id: data.id || '', capacity: Number(data.capacity || 0) };

    if (type === 'cargo') {
      setCargoRows((prev) => [...prev, row]);
    } else {
      setTankRows((prev) => [...prev, row]);
    }
  };

  const removeRow = (type, uid) => {
    if (type === 'cargo') {
      setCargoRows((prev) => prev.filter((row) => row._uid !== uid));
    } else {
      setTankRows((prev) => prev.filter((row) => row._uid !== uid));
    }
  };

  const updateRow = (type, uid, key, value) => {
    const updater = (rows) => rows.map((row) => (row._uid === uid ? { ...row, [key]: value } : row));
    if (type === 'cargo') {
      setCargoRows((prev) => updater(prev));
    } else {
      setTankRows((prev) => updater(prev));
    }
  };

  const clearAll = () => {
    setCargoRows([]);
    setTankRows([]);
    setResult(null);
  };

  const loadDefaults = () => {
    setResult(null);
    setCargoRows(DEFAULTS.cargos.map((cargo) => ({ ...cargo, _uid: createUid() })));
    setTankRows(DEFAULTS.tanks.map((tank) => ({ ...tank, _uid: createUid() })));
    showToast('Sample data loaded', 'success');
  };

  const runOptimize = async () => {
    const cargos = cargoRows
      .filter((row) => row.id.trim() && Number(row.volume) > 0)
      .map((row) => ({ id: row.id.trim(), volume: Number(row.volume) }));
    const tanks = tankRows
      .filter((row) => row.id.trim() && Number(row.capacity) > 0)
      .map((row) => ({ id: row.id.trim(), capacity: Number(row.capacity) }));

    if (!cargos.length || !tanks.length) {
      showToast('Add at least one cargo and one tank', 'error');
      return;
    }

    setIsOptimizing(true);

    try {
      const inputResponse = await fetch(`${baseUrl}/input`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ cargos, tanks }),
      });

      if (!inputResponse.ok) {
        const errorData = await inputResponse.json().catch(() => ({}));
        throw new Error(errorData.detail || 'Input failed');
      }

      const optimizeResponse = await fetch(`${baseUrl}/optimize`, {
        method: 'POST',
      });

      if (!optimizeResponse.ok) {
        const errorData = await optimizeResponse.json().catch(() => ({}));
        throw new Error(errorData.detail || 'Optimize failed');
      }

      const optimizationData = await optimizeResponse.json();
      setResult(normalizeResult(optimizationData, tanks));
      showToast('Optimization complete', 'success');
      setStatus('online');
      setStatusLabel('API online');
    } catch (error) {
      showToast(`Error: ${error.message}`, 'error');
      setStatus('error');
      setStatusLabel('Error');
    } finally {
      setIsOptimizing(false);
    }
  };

  useEffect(() => {
    loadDefaults();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    checkHealth();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const cargoIds = useMemo(() => {
    if (!result) return [];
    return [...new Set(result.allocations.map((a) => a.cargo_id).filter(Boolean))];
  }, [result]);

  const colorMap = useMemo(() => {
    const map = {};
    cargoIds.forEach((id, idx) => {
      map[id] = CARGO_COLORS[idx % CARGO_COLORS.length];
    });
    return map;
  }, [cargoIds]);

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
          <div className={`status-dot${status === 'online' ? ' online' : status === 'error' ? ' error' : ''}`} />
          <span>{statusLabel}</span>
        </div>
      </header>

      <div className="layout">
        <div className="panel-left">
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

          <div>
            <div className="section-title">Cargos (ID · Volume m3)</div>
            <div className="data-editor">
              <div className="data-editor-header cargo-grid">
                <span>ID</span>
                <span>Volume</span>
                <span></span>
              </div>
              <div>
                {cargoRows.map((row) => (
                  <div className="data-row cargo-grid" key={row._uid}>
                    <input
                      type="text"
                      value={row.id}
                      placeholder="C1"
                      onChange={(event) => updateRow('cargo', row._uid, 'id', event.target.value)}
                    />
                    <input
                      type="number"
                      min="0"
                      step="1"
                      value={row.volume}
                      placeholder="Volume"
                      onChange={(event) => updateRow('cargo', row._uid, 'volume', Number(event.target.value))}
                    />
                    <button
                      className="btn-icon"
                      type="button"
                      title="Remove"
                      onClick={() => removeRow('cargo', row._uid)}
                    >
                      x
                    </button>
                  </div>
                ))}
              </div>
            </div>
            <button className="btn-add" type="button" onClick={() => addRow('cargo')}>
              + Add cargo
            </button>
          </div>

          <div>
            <div className="section-title">Tanks (ID · Capacity m3)</div>
            <div className="data-editor">
              <div className="data-editor-header tank-grid">
                <span>ID</span>
                <span>Capacity</span>
                <span></span>
              </div>
              <div>
                {tankRows.map((row) => (
                  <div className="data-row tank-grid" key={row._uid}>
                    <input
                      type="text"
                      value={row.id}
                      placeholder="T1"
                      onChange={(event) => updateRow('tank', row._uid, 'id', event.target.value)}
                    />
                    <input
                      type="number"
                      min="0"
                      step="1"
                      value={row.capacity}
                      placeholder="Capacity"
                      onChange={(event) => updateRow('tank', row._uid, 'capacity', Number(event.target.value))}
                    />
                    <button
                      className="btn-icon"
                      type="button"
                      title="Remove"
                      onClick={() => removeRow('tank', row._uid)}
                    >
                      x
                    </button>
                  </div>
                ))}
              </div>
            </div>
            <button className="btn-add" type="button" onClick={() => addRow('tank')}>
              + Add tank
            </button>
          </div>
        </div>

        <div className="panel-right" id="results-panel">
          {!result && (
            <div className="empty-state" id="empty-state">
              <div className="empty-icon">⚓</div>
              <div className="empty-title">No results yet</div>
              <div className="empty-sub">
                Add cargo and tank data on the left, then click <strong>Run optimization</strong>.
              </div>
            </div>
          )}

          {result && (
            <>
              <div className="stats-grid">
                <div className="stat-card">
                  <div className="stat-label">Total loaded</div>
                  <div className="stat-value">{result.total_loaded.toLocaleString()}</div>
                  <div className="stat-sub">m3</div>
                </div>
                <div className="stat-card">
                  <div className="stat-label">Utilization</div>
                  <div className="stat-value">{result.utilization_pct.toFixed(1)}%</div>
                  <div className="stat-sub">of total capacity</div>
                </div>
                <div className="stat-card">
                  <div className="stat-label">Tank capacity</div>
                  <div className="stat-value">{result.total_capacity.toLocaleString()}</div>
                  <div className="stat-sub">m3 total</div>
                </div>
                <div className="stat-card">
                  <div className="stat-label">Unallocated</div>
                  <div className="stat-value">{result.unallocated_cargo_volume.toLocaleString()}</div>
                  <div className="stat-sub">m3 cargo excess</div>
                </div>
              </div>

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
                  {result.allocations.map((allocation) => {
                    const pct = Number(allocation.fill_pct || 0);
                    const color = allocation.cargo_id ? colorMap[allocation.cargo_id] : '#e2e1db';
                    return (
                      <div className="tank-card" key={`${allocation.tank_id}-${allocation.cargo_id || 'empty'}`}>
                        <div className="tank-label">
                          <span>{allocation.tank_id}</span>
                          <span className="tank-label-pct">{pct.toFixed(0)}%</span>
                        </div>
                        <div className="tank-bar-wrap">
                          <div
                            className="tank-bar-fill"
                            style={{
                              height: `${Math.max(pct, 2)}%`,
                              background: color,
                              opacity: 0.85,
                            }}
                          ></div>
                        </div>
                        <div className="tank-meta">
                          <span>{allocation.cargo_id || '-'}</span>
                          <span>{allocation.loaded_volume.toLocaleString()}</span>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>

              <div className="alloc-table-wrap">
                <div className="alloc-table-header">Allocation details</div>
                <table>
                  <thead>
                    <tr>
                      <th>Tank</th>
                      <th>Cargo</th>
                      <th>Loaded</th>
                      <th>Capacity</th>
                      <th>Fill</th>
                    </tr>
                  </thead>
                  <tbody>
                    {result.allocations.map((allocation) => {
                      const pct = Number(allocation.fill_pct || 0);
                      const fillColor = getFillColor(pct);
                      return (
                        <tr key={`${allocation.tank_id}-table-${allocation.cargo_id || 'empty'}`}>
                          <td>
                            <strong>{allocation.tank_id}</strong>
                          </td>
                          <td>
                            {allocation.cargo_id ? (
                              <span className="badge badge-blue">{allocation.cargo_id}</span>
                            ) : (
                              <span className="muted">-</span>
                            )}
                          </td>
                          <td>{allocation.loaded_volume.toLocaleString()} m3</td>
                          <td>{allocation.tank_capacity.toLocaleString()} m3</td>
                          <td>
                            <div className="fill-bar">
                              <div className="fill-bar-track">
                                <div
                                  className="fill-bar-fill"
                                  style={{ width: `${pct}%`, background: fillColor }}
                                ></div>
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

      <div id="toast" className={`${toastMsg ? 'show' : ''} ${toastType}`.trim()}>
        {toastMsg}
      </div>
    </>
  );
}

export default App;
