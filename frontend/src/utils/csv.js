/**
 * CSV import and export utilities for ShipIQ cargo/tank data.
 */

/** Parse a CSV string into cargo rows. Format: id,volume[,weight] */
export function parseCargoCsv(text) {
  const lines = text.trim().split(/\r?\n/).filter(Boolean);
  const rows = [];
  for (const line of lines) {
    const [id, volume, weight] = line.split(',').map((p) => p.trim());
    if (!id || id.toLowerCase() === 'id') continue;
    const vol = parseFloat(volume);
    const wt = parseFloat(weight) || 0;
    if (!id || isNaN(vol) || vol <= 0) continue;
    rows.push({ id, volume: vol, weight: wt });
  }
  return rows;
}

/** Parse a CSV string into tank rows. Format: id,capacity[,weight_limit] */
export function parseTankCsv(text) {
  const lines = text.trim().split(/\r?\n/).filter(Boolean);
  const rows = [];
  for (const line of lines) {
    const [id, capacity, weightLimit] = line.split(',').map((p) => p.trim());
    if (!id || id.toLowerCase() === 'id') continue;
    const cap = parseFloat(capacity);
    const wl = parseFloat(weightLimit) || 0;
    if (!id || isNaN(cap) || cap <= 0) continue;
    rows.push({ id, capacity: cap, weight_limit: wl });
  }
  return rows;
}

/** Download allocation results as a CSV file. */
export function exportResultsCsv(allocations) {
  const header = 'Tank,Cargo,Loaded (m3),Capacity (m3),Fill %\n';
  const rows = allocations
    .map((a) =>
      `${a.tank_id},${a.cargo_id || '-'},${a.loaded_volume},${a.tank_capacity},${a.fill_pct.toFixed(1)}`
    )
    .join('\n');
  _download(header + rows, `shipiq-results-${new Date().toISOString().slice(0, 10)}.csv`);
}

/** Download a starter template CSV. */
export function downloadTemplate(type) {
  const content =
    type === 'cargo'
      ? 'id,volume,weight\nC1,1234,500\nC2,4352,0\n'
      : 'id,capacity,weight_limit\nT1,1500,600\nT2,4000,0\n';
  _download(content, `shipiq-${type}-template.csv`);
}

function _download(content, filename) {
  const blob = new Blob([content], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}
