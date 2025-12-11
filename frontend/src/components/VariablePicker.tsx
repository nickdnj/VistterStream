/**
 * VariablePicker Component
 * 
 * A drag-and-drop variable picker for ReelForge templates.
 * Shows available template variables with their current live values,
 * grouped by category. Users can drag variables into text fields.
 */

import React, { useState, useEffect } from 'react';
import { api } from '../services/api';

interface Variable {
  key: string;
  description: string;
  value: string;
  category: string;
}

interface LiveVariablesResponse {
  variables: Variable[];
  weather_connected: boolean;
  usage: string;
  error?: string;
}

interface VariablePickerProps {
  onRefresh?: () => void;
}

const CATEGORY_LABELS: Record<string, string> = {
  time: 'Time & Date',
  weather: 'Weather',
  tides: 'Tides & Water',
  astronomy: 'Moon & Solunar',
  forecast: 'Forecast',
  other: 'Other'
};

const CATEGORY_ICONS: Record<string, string> = {
  time: '🕐',
  weather: '🌤️',
  tides: '🌊',
  astronomy: '🌙',
  forecast: '📅',
  other: '📋'
};

export const VariablePicker: React.FC<VariablePickerProps> = ({ onRefresh }) => {
  const [variables, setVariables] = useState<Variable[]>([]);
  const [loading, setLoading] = useState(true);
  const [weatherConnected, setWeatherConnected] = useState(false);
  const [expandedCategories, setExpandedCategories] = useState<Set<string>>(
    new Set(['time', 'weather', 'tides', 'astronomy'])
  );
  const [draggedVar, setDraggedVar] = useState<string | null>(null);

  const loadVariables = async () => {
    setLoading(true);
    try {
      const response = await api.get<LiveVariablesResponse>('/reelforge/settings/variables/live');
      setVariables(response.data.variables);
      setWeatherConnected(response.data.weather_connected);
    } catch (err) {
      console.error('Failed to load variables:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadVariables();
  }, []);

  const handleRefresh = () => {
    loadVariables();
    onRefresh?.();
  };

  const toggleCategory = (category: string) => {
    setExpandedCategories(prev => {
      const next = new Set(prev);
      if (next.has(category)) {
        next.delete(category);
      } else {
        next.add(category);
      }
      return next;
    });
  };

  const handleDragStart = (e: React.DragEvent, variable: Variable) => {
    e.dataTransfer.setData('text/plain', `{${variable.key}}`);
    e.dataTransfer.effectAllowed = 'copy';
    setDraggedVar(variable.key);
  };

  const handleDragEnd = () => {
    setDraggedVar(null);
  };

  // Group variables by category
  const groupedVariables = variables.reduce((acc, variable) => {
    const category = variable.category || 'other';
    if (!acc[category]) {
      acc[category] = [];
    }
    acc[category].push(variable);
    return acc;
  }, {} as Record<string, Variable[]>);

  // Order categories
  const categoryOrder = ['time', 'weather', 'tides', 'astronomy', 'forecast', 'other'];
  const orderedCategories = categoryOrder.filter(cat => groupedVariables[cat]?.length > 0);

  if (loading) {
    return (
      <div className="bg-dark-900 rounded-lg border border-dark-600 p-4">
        <div className="animate-pulse space-y-2">
          <div className="h-4 bg-dark-700 rounded w-3/4"></div>
          <div className="h-4 bg-dark-700 rounded w-1/2"></div>
          <div className="h-4 bg-dark-700 rounded w-2/3"></div>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-dark-900 rounded-lg border border-dark-600 flex flex-col h-full">
      {/* Header */}
      <div className="p-3 border-b border-dark-600 flex-shrink-0">
        <div className="flex items-center justify-between mb-2">
          <h3 className="text-sm font-semibold text-white">Variables</h3>
          <button
            onClick={handleRefresh}
            className="p-1 text-gray-400 hover:text-white transition-colors"
            title="Refresh values"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} 
                d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
          </button>
        </div>
        <div className="flex items-center gap-2 text-xs">
          <span className={`w-2 h-2 rounded-full ${weatherConnected ? 'bg-green-500' : 'bg-red-500'}`}></span>
          <span className="text-gray-400">
            {weatherConnected ? 'Live values' : 'Weather offline'}
          </span>
        </div>
        <p className="text-xs text-gray-500 mt-1">Drag into text fields</p>
      </div>

      {/* Variable List */}
      <div className="flex-1 overflow-y-auto p-2 space-y-1">
        {orderedCategories.map(category => (
          <div key={category} className="mb-2">
            {/* Category Header */}
            <button
              onClick={() => toggleCategory(category)}
              className="w-full flex items-center gap-2 px-2 py-1.5 text-xs font-medium text-gray-300 hover:bg-dark-700 rounded transition-colors"
            >
              <span className="text-sm">{CATEGORY_ICONS[category] || '📋'}</span>
              <span className="flex-1 text-left">{CATEGORY_LABELS[category] || category}</span>
              <svg
                className={`w-3 h-3 transition-transform ${expandedCategories.has(category) ? 'rotate-90' : ''}`}
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
              </svg>
            </button>

            {/* Variables in Category */}
            {expandedCategories.has(category) && (
              <div className="ml-2 mt-1 space-y-0.5">
                {groupedVariables[category].map(variable => (
                  <div
                    key={variable.key}
                    draggable
                    onDragStart={(e) => handleDragStart(e, variable)}
                    onDragEnd={handleDragEnd}
                    className={`
                      flex items-center gap-2 px-2 py-1.5 rounded cursor-grab
                      bg-dark-800 hover:bg-dark-700 border border-transparent
                      hover:border-primary-500/50 transition-all
                      ${draggedVar === variable.key ? 'opacity-50 border-primary-500' : ''}
                    `}
                    title={variable.description}
                  >
                    {/* Drag Handle */}
                    <svg className="w-3 h-3 text-gray-500 flex-shrink-0" fill="currentColor" viewBox="0 0 24 24">
                      <circle cx="9" cy="5" r="1.5" />
                      <circle cx="15" cy="5" r="1.5" />
                      <circle cx="9" cy="12" r="1.5" />
                      <circle cx="15" cy="12" r="1.5" />
                      <circle cx="9" cy="19" r="1.5" />
                      <circle cx="15" cy="19" r="1.5" />
                    </svg>
                    
                    {/* Variable Name */}
                    <code className="text-xs text-primary-400 font-mono flex-shrink-0">
                      {variable.key}
                    </code>
                    
                    {/* Current Value */}
                    <span className="text-xs text-gray-400 truncate flex-1 text-right">
                      {variable.value}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
};

export default VariablePicker;
