import { BarChart3, TrendingUp, Package, AlertCircle } from 'lucide-react';

function ResultsSection({ results }) {
  const {
    allocations,
    total_cargo_volume,
    total_tank_capacity,
    total_loaded_volume,
    loading_efficiency_pct,
    unallocated_cargo,
    unused_tank_capacity,
  } = results;

  const getUtilizationColor = (utilization) => {
    if (utilization >= 90) return 'success';
    if (utilization >= 70) return 'warning';
    return 'danger';
  };

  return (
    <>
      {/* Statistics Cards */}
      <div className="stats-grid">
        <div className="stat-card">
          <h3>Total Cargo Volume</h3>
          <div className="value">{total_cargo_volume.toLocaleString()}</div>
          <div className="label">cubic meters</div>
        </div>

        <div className="stat-card">
          <h3>Total Tank Capacity</h3>
          <div className="value">{total_tank_capacity.toLocaleString()}</div>
          <div className="label">cubic meters</div>
        </div>

        <div className="stat-card success">
          <h3>Loaded Volume</h3>
          <div className="value">{total_loaded_volume.toLocaleString()}</div>
          <div className="label">cubic meters</div>
        </div>

        <div className={`stat-card ${loading_efficiency_pct >= 90 ? 'success' : 'warning'}`}>
          <h3>Loading Efficiency</h3>
          <div className="value">{loading_efficiency_pct.toFixed(2)}%</div>
          <div className="label">utilization rate</div>
        </div>
      </div>

      {/* Allocation Details */}
      <div className="card">
        <div className="card-header">
          <BarChart3 size={24} />
          <h2>Allocation Details</h2>
        </div>

        {allocations.length > 0 ? (
          <div style={{ overflowX: 'auto' }}>
            <table className="allocation-table">
              <thead>
                <tr>
                  <th>Tank ID</th>
                  <th>Cargo ID</th>
                  <th>Allocated Volume</th>
                  <th>Tank Capacity</th>
                  <th>Utilization</th>
                </tr>
              </thead>
              <tbody>
                {allocations.map((alloc, idx) => (
                  <tr key={idx}>
                    <td style={{ fontWeight: 600 }}>{alloc.tank_id}</td>
                    <td>
                      <span className="cargo-badge">{alloc.cargo_id}</span>
                    </td>
                    <td>{alloc.allocated_volume.toLocaleString()} m³</td>
                    <td>{alloc.tank_capacity.toLocaleString()} m³</td>
                    <td>
                      <div className="progress-bar">
                        <div
                          className={`progress-fill ${alloc.utilization_pct < 90 ? 'warning' : ''}`}
                          style={{ width: `${alloc.utilization_pct}%` }}
                        >
                          <span className="progress-text">{alloc.utilization_pct.toFixed(1)}%</span>
                        </div>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="empty-state">
            <Package />
            <h3>No Allocations</h3>
            <p>No cargo was allocated to tanks</p>
          </div>
        )}
      </div>

      {/* Visual Representation */}
      <div className="card">
        <div className="card-header">
          <TrendingUp size={24} />
          <h2>Tank Visualization</h2>
        </div>

        <div className="tank-grid">
          {allocations.map((alloc, idx) => (
            <div key={idx} className="tank-visual">
              <div className="tank-header">
                <span className="tank-id">{alloc.tank_id}</span>
                <span className="cargo-badge">{alloc.cargo_id}</span>
              </div>
              <div className="tank-capacity">
                Capacity: {alloc.tank_capacity.toLocaleString()} m³
              </div>
              <div className="progress-bar">
                <div
                  className={`progress-fill ${alloc.utilization_pct < 90 ? 'warning' : ''}`}
                  style={{ width: `${alloc.utilization_pct}%` }}
                >
                  <span className="progress-text">{alloc.utilization_pct.toFixed(1)}%</span>
                </div>
              </div>
              <div style={{ marginTop: '0.5rem', fontSize: '0.875rem', color: 'var(--gray)' }}>
                Loaded: {alloc.allocated_volume.toLocaleString()} m³
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Warnings and Unallocated */}
      {(unallocated_cargo.length > 0 || unused_tank_capacity.length > 0) && (
        <div className="card">
          <div className="card-header">
            <AlertCircle size={24} />
            <h2>Warnings & Unused Resources</h2>
          </div>

          {unallocated_cargo.length > 0 && (
            <div className="alert alert-warning">
              <AlertCircle size={20} />
              <div>
                <strong>Unallocated Cargo:</strong>{' '}
                {unallocated_cargo.map((c) => `${c.id} (${c.volume} m³)`).join(', ')}
              </div>
            </div>
          )}

          {unused_tank_capacity.length > 0 && (
            <div className="alert alert-info">
              <AlertCircle size={20} />
              <div>
                <strong>Unused Tanks:</strong>{' '}
                {unused_tank_capacity.map((t) => `${t.id} (${t.capacity} m³)`).join(', ')}
              </div>
            </div>
          )}
        </div>
      )}
    </>
  );
}

export default ResultsSection;
