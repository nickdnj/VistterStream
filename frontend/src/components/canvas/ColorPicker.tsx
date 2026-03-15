import React, { useState, useRef, useEffect } from 'react';
import { HexColorPicker } from 'react-colorful';

const PRESETS = [
  '#ffffff', '#000000', '#ef4444', '#f97316',
  '#eab308', '#22c55e', '#3b82f6', '#8b5cf6',
];

interface ColorPickerProps {
  color: string;
  onChange: (color: string) => void;
  label?: string;
}

const ColorPicker: React.FC<ColorPickerProps> = ({ color, onChange, label }) => {
  const [open, setOpen] = useState(false);
  const popoverRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (popoverRef.current && !popoverRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    if (open) document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [open]);

  return (
    <div className="relative">
      {label && <label className="block text-xs text-gray-400 mb-1">{label}</label>}
      <div className="flex items-center gap-2">
        <button
          onClick={() => setOpen(!open)}
          className="w-8 h-8 rounded border border-dark-600 flex-shrink-0"
          style={{ backgroundColor: color }}
        />
        <input
          type="text"
          value={color}
          onChange={(e) => onChange(e.target.value)}
          className="flex-1 px-2 py-1 bg-dark-700 border border-dark-600 rounded text-white text-xs font-mono focus:outline-none focus:ring-1 focus:ring-primary-500"
        />
      </div>

      {open && (
        <div
          ref={popoverRef}
          className="absolute z-50 mt-2 p-3 bg-dark-800 border border-dark-600 rounded-lg shadow-xl"
        >
          <HexColorPicker color={color} onChange={onChange} />
          <div className="flex gap-1.5 mt-2 flex-wrap">
            {PRESETS.map((c) => (
              <button
                key={c}
                onClick={() => onChange(c)}
                className="w-5 h-5 rounded border border-dark-600"
                style={{ backgroundColor: c }}
              />
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default ColorPicker;
