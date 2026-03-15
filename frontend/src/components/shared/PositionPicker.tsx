import React from 'react';

interface PositionPickerProps {
  positionX: number;
  positionY: number;
  onChange: (x: number, y: number) => void;
  showRawInputs?: boolean;
}

// 3x3 grid mapping to normalized 0-1 coordinates
const POSITIONS = [
  { label: 'TL', x: 0.02, y: 0.02 },
  { label: 'TC', x: 0.50, y: 0.02 },
  { label: 'TR', x: 0.90, y: 0.02 },
  { label: 'ML', x: 0.02, y: 0.45 },
  { label: 'MC', x: 0.50, y: 0.45 },
  { label: 'MR', x: 0.90, y: 0.45 },
  { label: 'BL', x: 0.02, y: 0.85 },
  { label: 'BC', x: 0.50, y: 0.85 },
  { label: 'BR', x: 0.90, y: 0.85 },
];

const POSITION_LABELS: Record<string, string> = {
  TL: 'Top Left',
  TC: 'Top Center',
  TR: 'Top Right',
  ML: 'Middle Left',
  MC: 'Center',
  MR: 'Middle Right',
  BL: 'Bottom Left',
  BC: 'Bottom Center',
  BR: 'Bottom Right',
};

function findClosestPosition(x: number, y: number): string {
  let closest = POSITIONS[0];
  let minDist = Infinity;
  for (const pos of POSITIONS) {
    const dist = Math.hypot(pos.x - x, pos.y - y);
    if (dist < minDist) {
      minDist = dist;
      closest = pos;
    }
  }
  return closest.label;
}

const PositionPicker: React.FC<PositionPickerProps> = ({
  positionX,
  positionY,
  onChange,
  showRawInputs = false,
}) => {
  const activeLabel = findClosestPosition(positionX, positionY);

  return (
    <div className="space-y-3">
      <div className="grid grid-cols-3 gap-1.5 w-fit">
        {POSITIONS.map((pos) => {
          const isActive = pos.label === activeLabel;
          return (
            <button
              key={pos.label}
              type="button"
              onClick={() => onChange(pos.x, pos.y)}
              title={POSITION_LABELS[pos.label]}
              className={`w-10 h-10 rounded-md text-xs font-medium transition-colors ${
                isActive
                  ? 'bg-primary-600 text-white ring-2 ring-primary-400'
                  : 'bg-dark-700 text-gray-400 hover:bg-dark-600 hover:text-gray-300'
              }`}
            >
              {pos.label}
            </button>
          );
        })}
      </div>
      <p className="text-xs text-gray-500">
        {POSITION_LABELS[activeLabel]} ({positionX.toFixed(2)}, {positionY.toFixed(2)})
      </p>

      {showRawInputs && (
        <div className="flex gap-3">
          <div>
            <label className="block text-xs text-gray-500 mb-1">X</label>
            <input
              type="number"
              min={0}
              max={1}
              step={0.01}
              value={positionX}
              onChange={(e) => onChange(parseFloat(e.target.value) || 0, positionY)}
              className="w-20 px-2 py-1 bg-dark-700 border border-dark-600 rounded text-white text-sm"
            />
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-1">Y</label>
            <input
              type="number"
              min={0}
              max={1}
              step={0.01}
              value={positionY}
              onChange={(e) => onChange(positionX, parseFloat(e.target.value) || 0)}
              className="w-20 px-2 py-1 bg-dark-700 border border-dark-600 rounded text-white text-sm"
            />
          </div>
        </div>
      )}
    </div>
  );
};

export default PositionPicker;
