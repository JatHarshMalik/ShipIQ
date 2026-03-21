import { useState } from 'react';
import { Plus, X, Package, Container } from 'lucide-react';

function InputSection({ cargos, setCargos, tanks, setTanks }) {
  const [cargoId, setCargoId] = useState('');
  const [cargoVolume, setCargoVolume] = useState('');
  const [tankId, setTankId] = useState('');
  const [tankCapacity, setTankCapacity] = useState('');

  const addCargo = () => {
    if (!cargoId || !cargoVolume) return;
    if (cargos.find(c => c.id === cargoId)) {
      alert('Cargo ID must be unique');
      return;
    }
    const volume = parseFloat(cargoVolume);
    if (volume <= 0 || isNaN(volume)) {
      alert('Volume must be a positive number');
      return;
    }
    setCargos([...cargos, { id: cargoId, volume }]);
    setCargoId('');
    setCargoVolume('');
  };

  const removeCargo = (id) => {
    setCargos(cargos.filter(c => c.id !== id));
  };

  const addTank = () => {
    if (!tankId || !tankCapacity) return;
    if (tanks.find(t => t.id === tankId)) {
      alert('Tank ID must be unique');
      return;
    }
    const capacity = parseFloat(tankCapacity);
    if (capacity <= 0 || isNaN(capacity)) {
      alert('Capacity must be a positive number');
      return;
    }
    setTanks([...tanks, { id: tankId, capacity }]);
    setTankId('');
    setTankCapacity('');
  };

  const removeTank = (id) => {
    setTanks(tanks.filter(t => t.id !== id));
  };

  const handleKeyPress = (e, type) => {
    if (e.key === 'Enter') {
      type === 'cargo' ? addCargo() : addTank();
    }
  };

  return (
    <>
      {/* Cargo Input */}
      <div className="sidebar-section">
        <div className="sidebar-section-title">
          <Package size={16} />
          Cargos (ID · Volume m³)
        </div>
        <table className="sidebar-table">
          <thead>
            <tr>
              <th>ID</th>
              <th>Volume</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {cargos.map((cargo) => (
              <tr key={cargo.id}>
                <td className="cell-id">{cargo.id}</td>
                <td>{cargo.volume.toLocaleString()}</td>
                <td>
                  <button className="btn-remove" onClick={() => removeCargo(cargo.id)} title="Remove">
                    <X size={14} />
                  </button>
                </td>
              </tr>
            ))}
            <tr className="input-row">
              <td>
                <input
                  type="text"
                  placeholder="ID"
                  value={cargoId}
                  onChange={(e) => setCargoId(e.target.value)}
                  onKeyPress={(e) => handleKeyPress(e, 'cargo')}
                  className="table-input"
                />
              </td>
              <td>
                <input
                  type="number"
                  placeholder="Volume"
                  value={cargoVolume}
                  onChange={(e) => setCargoVolume(e.target.value)}
                  onKeyPress={(e) => handleKeyPress(e, 'cargo')}
                  min="0"
                  step="0.01"
                  className="table-input"
                />
              </td>
              <td></td>
            </tr>
          </tbody>
        </table>
        <button className="btn-add-row" onClick={addCargo}>
          <Plus size={14} />
          Add cargo
        </button>
      </div>

      {/* Tank Input */}
      <div className="sidebar-section">
        <div className="sidebar-section-title">
          <Container size={16} />
          Tanks (ID · Capacity m³)
        </div>
        <table className="sidebar-table">
          <thead>
            <tr>
              <th>ID</th>
              <th>Capacity</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {tanks.map((tank) => (
              <tr key={tank.id}>
                <td className="cell-id">{tank.id}</td>
                <td>{tank.capacity.toLocaleString()}</td>
                <td>
                  <button className="btn-remove" onClick={() => removeTank(tank.id)} title="Remove">
                    <X size={14} />
                  </button>
                </td>
              </tr>
            ))}
            <tr className="input-row">
              <td>
                <input
                  type="text"
                  placeholder="ID"
                  value={tankId}
                  onChange={(e) => setTankId(e.target.value)}
                  onKeyPress={(e) => handleKeyPress(e, 'tank')}
                  className="table-input"
                />
              </td>
              <td>
                <input
                  type="number"
                  placeholder="Capacity"
                  value={tankCapacity}
                  onChange={(e) => setTankCapacity(e.target.value)}
                  onKeyPress={(e) => handleKeyPress(e, 'tank')}
                  min="0"
                  step="0.01"
                  className="table-input"
                />
              </td>
              <td></td>
            </tr>
          </tbody>
        </table>
        <button className="btn-add-row" onClick={addTank}>
          <Plus size={14} />
          Add tank
        </button>
      </div>
    </>
  );
}

export default InputSection;
