import React, { useEffect, useState } from 'react';
import { api } from '../services/api';

interface Timeline {
  id: number;
  name: string;
  duration: number;
}

interface ScheduleItem {
  id?: number;
  name: string;
  is_enabled: boolean;
  timezone: string;
  days_of_week: number[];
  window_start: string;
  window_end: string;
  destination_ids: number[];
  timelines: { timeline_id: number; order_index: number }[];
}

const Scheduler: React.FC = () => {
  const [timelines, setTimelines] = useState<Timeline[]>([]);
  const [schedules, setSchedules] = useState<ScheduleItem[]>([]);
  const [runningSchedules, setRunningSchedules] = useState<number[]>([]);
  const [name, setName] = useState('New Schedule');
  const [days, setDays] = useState<number[]>([0, 1, 2, 3, 4, 5, 6]);
  const [start, setStart] = useState('06:00');
  const [end, setEnd] = useState('23:00');
  const [selectedTimelineIds, setSelectedTimelineIds] = useState<number[]>([]);

  const dayLabels = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];

  const fetchRunning = async () => {
    try {
      const response = await api.get('/scheduler/running');
      setRunningSchedules(response.data.map((item: any) => item.schedule_id));
    } catch (error) {
      console.error('Failed to load running schedules', error);
    }
  };

  const refreshSchedules = async () => {
    const sch = await api.get('/scheduler');
    setSchedules(sch.data);
  };

  useEffect(() => {
    (async () => {
      try {
        const [tl, sch] = await Promise.all([
          api.get('/timelines'),
          api.get('/scheduler'),
        ]);
        setTimelines(tl.data.map((t: any) => ({ id: t.id, name: t.name, duration: t.duration })));
        setSchedules(sch.data);
        await fetchRunning();
      } catch (e) {
        console.error('Failed to load scheduler data', e);
      }
    })();
  }, []);

  const toggleDay = (d: number) => {
    setDays(prev => prev.includes(d) ? prev.filter(x => x !== d) : [...prev, d].sort());
  };

  const toggleTimeline = (id: number) => {
    setSelectedTimelineIds(prev => prev.includes(id) ? prev.filter(x => x !== id) : [...prev, id]);
  };

  const isRunning = (scheduleId?: number) => {
    if (!scheduleId) return false;
    return runningSchedules.includes(scheduleId);
  };

  const createSchedule = async () => {
    const overlaps = (a: ScheduleItem, b: ScheduleItem) => {
      const daySet = new Set(a.days_of_week);
      const hasDay = (b.days_of_week || []).some((d) => daySet.has(d));
      if (!hasDay) return false;
      const toMin = (t: string) => {
        const [h, m] = t.split(':').map(Number);
        return h * 60 + m;
      };
      const aS = toMin(a.window_start), aE = toMin(a.window_end);
      const bS = toMin(b.window_start), bE = toMin(b.window_end);
      const normOverlap = (s1: number, e1: number, s2: number, e2: number) => (s1 < e2 && s2 < e1);
      const ranges = (s: number, e: number) => s <= e ? [[s, e]] : [[s, 1440], [0, e]];
      const aR = ranges(aS, aE), bR = ranges(bS, bE);
      for (const [as, ae] of aR) {
        for (const [bs, be] of bR) {
          if (normOverlap(as, ae, bs, be)) return true;
        }
      }
      return false;
    };

    const payload: ScheduleItem = {
      name,
      is_enabled: true,
      timezone: 'UTC',
      days_of_week: days,
      window_start: start,
      window_end: end,
      destination_ids: [],
      timelines: selectedTimelineIds.map((id, idx) => ({ timeline_id: id, order_index: idx })),
    };

    const conflicting = schedules.filter((s) => overlaps(payload, s));
    if (conflicting.length > 0) {
      const list = conflicting
        .map((s) => `• ${s.name} (${s.window_start}–${s.window_end}, days ${s.days_of_week.join(',')})`)
        .join('\n');
      const proceed = window.confirm(`⚠️ Overlapping schedule detected:\n\n${list}\n\nCreate anyway?`);
      if (!proceed) return;
    }

    try {
      await api.post('/scheduler', payload);
      await refreshSchedules();
      await fetchRunning();
      alert('✅ Schedule created');
    } catch (e: any) {
      alert(`❌ Failed to create schedule: ${e.response?.data?.detail || e.message}`);
    }
  };

  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold text-white mb-4">Scheduler</h1>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-dark-800 rounded-lg border border-dark-700 p-4">
          <h2 className="text-white font-semibold mb-3">Create Schedule</h2>
          <div className="space-y-3">
            <div>
              <label className="block text-sm text-gray-300 mb-1">Name</label>
              <input
                value={name}
                onChange={e => setName(e.target.value)}
                className="w-full px-3 py-2 bg-dark-700 border border-dark-600 rounded-md text-white"
              />
            </div>
            <div className="flex gap-3">
              <div className="flex-1">
                <label className="block text-sm text-gray-300 mb-1">Start</label>
                <input
                  type="time"
                  value={start}
                  onChange={e => setStart(e.target.value)}
                  className="w-full px-3 py-2 bg-dark-700 border border-dark-600 rounded-md text-white"
                />
              </div>
              <div className="flex-1">
                <label className="block text-sm text-gray-300 mb-1">End</label>
                <input
                  type="time"
                  value={end}
                  onChange={e => setEnd(e.target.value)}
                  className="w-full px-3 py-2 bg-dark-700 border border-dark-600 rounded-md text-white"
                />
              </div>
            </div>
            <div>
              <label className="block text-sm text-gray-300 mb-2">Days</label>
              <div className="flex gap-2 flex-wrap">
                {dayLabels.map((lbl, idx) => (
                  <button
                    key={idx}
                    onClick={() => toggleDay(idx)}
                    className={`px-2 py-1 rounded text-sm ${days.includes(idx) ? 'bg-primary-600 text-white' : 'bg-dark-700 text-gray-300'}`}
                  >
                    {lbl}
                  </button>
                ))}
              </div>
            </div>
            <div>
              <label className="block text-sm text-gray-300 mb-2">Timelines</label>
              <div className="space-y-1 max-h-48 overflow-auto">
                {timelines.map(t => (
                  <label key={t.id} className="flex items-center gap-2 p-2 hover:bg-dark-700 rounded">
                    <input type="checkbox" checked={selectedTimelineIds.includes(t.id)} onChange={() => toggleTimeline(t.id)} />
                    <span className="text-gray-200 text-sm">{t.name}</span>
                  </label>
                ))}
              </div>
            </div>
            <div className="pt-2">
              <button
                onClick={createSchedule}
                className="px-4 py-2 bg-primary-600 hover:bg-primary-700 text-white rounded-md"
              >
                Save Schedule
              </button>
            </div>
          </div>
        </div>
        <div className="bg-dark-800 rounded-lg border border-dark-700 p-4">
          <h2 className="text-white font-semibold mb-3">Existing Schedules</h2>
          <div className="space-y-2">
            {schedules.length === 0 && <div className="text-gray-400 text-sm">No schedules yet</div>}
            {schedules.map((s, i) => (
              <div key={i} className="p-3 bg-dark-700 rounded flex items-start justify-between gap-3">
                <div>
                  <div className="text-white font-medium">
                    {s.name} {s.is_enabled ? '' : '(disabled)'}
                  </div>
                  <div className="text-gray-400 text-sm">
                    {s.window_start}–{s.window_end} • Days: {s.days_of_week.join(',')}
                  </div>
                  <div className={`text-sm ${isRunning(s.id) ? 'text-green-400' : 'text-gray-500'}`}>
                    {isRunning(s.id) ? 'Running now' : 'Idle'}
                  </div>
                  <div className="text-gray-400 text-sm">
                    Timelines: {s.timelines.map(t => t.timeline_id).join(', ') || '—'}
                  </div>
                </div>
                <div className="flex-shrink-0 flex flex-col gap-2">
                  <button
                    onClick={async () => {
                      if (!s.id) return;
                      try {
                        await api.post(`/scheduler/${s.id}/run`, { force: true });
                        await fetchRunning();
                        alert('✅ Schedule started');
                      } catch (e: any) {
                        alert(`❌ Failed to start schedule: ${e.response?.data?.detail || e.message}`);
                      }
                    }}
                    className="px-3 py-1 bg-primary-600 hover:bg-primary-700 text-white text-xs rounded"
                  >
                    Start Now
                  </button>
                  <button
                    onClick={async () => {
                      if (!s.id) return;
                      try {
                        await api.post(`/scheduler/${s.id}/stop`, {});
                        await fetchRunning();
                        alert('🛑 Schedule stopped');
                      } catch (e: any) {
                        alert(`Failed to stop schedule: ${e.response?.data?.detail || e.message}`);
                      }
                    }}
                    className={`px-3 py-1 text-xs rounded ${isRunning(s.id) ? 'bg-yellow-600 hover:bg-yellow-700 text-white' : 'bg-dark-600 text-gray-400 cursor-not-allowed'}`}
                    disabled={!isRunning(s.id)}
                  >
                    Stop
                  </button>
                  <button
                    onClick={async () => {
                      if (!s.id) return;
                      if (!window.confirm(`Delete schedule "${s.name}"?`)) return;
                      try {
                        await api.delete(`/scheduler/${s.id}`);
                        await refreshSchedules();
                        await fetchRunning();
                      } catch (e: any) {
                        alert(`❌ Failed to delete: ${e.response?.data?.detail || e.message}`);
                      }
                    }}
                    className="px-3 py-1 bg-red-600 hover:bg-red-700 text-white text-xs rounded"
                  >
                    Delete
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};

export default Scheduler;
