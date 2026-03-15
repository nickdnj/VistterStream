import React, { useState, useEffect, useMemo } from 'react';
import { api } from '../../services/api';
import type { FontInfo } from './types';

interface FontPickerProps {
  value: string;
  onChange: (family: string) => void;
}

const FontPicker: React.FC<FontPickerProps> = ({ value, onChange }) => {
  const [fonts, setFonts] = useState<FontInfo[]>([]);
  const [search, setSearch] = useState('');
  const [open, setOpen] = useState(false);

  useEffect(() => {
    api.get('/fonts').then((res) => setFonts(res.data)).catch(() => {});
  }, []);

  const filtered = useMemo(() => {
    const q = search.toLowerCase();
    return fonts.filter((f) => f.family.toLowerCase().includes(q));
  }, [fonts, search]);

  const grouped = useMemo(() => {
    const groups: Record<string, FontInfo[]> = {};
    for (const f of filtered) {
      const key = f.source === 'system' ? 'System' : f.source === 'google' ? 'Google' : 'Uploaded';
      (groups[key] ??= []).push(f);
    }
    return groups;
  }, [filtered]);

  return (
    <div className="relative">
      <label className="block text-xs text-gray-400 mb-1">Font Family</label>
      <button
        onClick={() => setOpen(!open)}
        className="w-full text-left px-3 py-2 bg-dark-700 border border-dark-600 rounded-md text-white text-sm focus:outline-none focus:ring-1 focus:ring-primary-500"
        style={{ fontFamily: value }}
      >
        {value || 'Select font...'}
      </button>

      {open && (
        <div className="absolute z-50 mt-1 w-full bg-dark-800 border border-dark-600 rounded-lg shadow-xl max-h-60 overflow-auto">
          <div className="sticky top-0 p-2 bg-dark-800 border-b border-dark-700">
            <input
              type="text"
              placeholder="Search fonts..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full px-2 py-1.5 bg-dark-700 border border-dark-600 rounded text-white text-xs focus:outline-none focus:ring-1 focus:ring-primary-500"
              autoFocus
            />
          </div>
          {Object.entries(grouped).map(([group, items]) => (
            <div key={group}>
              <div className="px-3 py-1 text-[10px] text-gray-500 uppercase tracking-wider bg-dark-750">
                {group}
              </div>
              {items.map((f) => (
                <button
                  key={`${f.id}-${f.family}`}
                  onClick={() => { onChange(f.family); setOpen(false); }}
                  className={`w-full text-left px-3 py-1.5 text-sm hover:bg-dark-700 transition-colors ${
                    f.family === value ? 'text-primary-400 bg-dark-700' : 'text-gray-300'
                  }`}
                  style={{ fontFamily: f.family }}
                >
                  {f.family}
                </button>
              ))}
            </div>
          ))}
          {filtered.length === 0 && (
            <p className="px-3 py-4 text-gray-500 text-xs text-center">No fonts found</p>
          )}
        </div>
      )}
    </div>
  );
};

export default FontPicker;
