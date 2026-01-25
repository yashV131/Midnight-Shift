import { useState, useEffect, useRef } from 'react';

const API_BASE_URL = 'http://127.0.0.1:5000';

const StatCard = ({ title, value }: { title: string, value: string | number }) => (
  <div className="bg-[#151c3a] border-2 border-[#4a5f8f] rounded-lg p-4 transition-all hover:-translate-y-1">
    <h3 className="text-[8px] font-bold text-[#7b9cdb] uppercase tracking-wider mb-2 retro-text">{title}</h3>
    <div className="text-xl font-bold text-[#a8c0ff] retro-text">{value}</div>
  </div>
);

const EyeMetricCard = ({ title, value }: { title: string, value: string | number }) => (
  <div className="bg-[#2d3a5f] border-2 border-[#4a5f8f] rounded-lg p-4 text-center">
    <h4 className="text-[8px] font-bold text-[#7b9cdb] uppercase tracking-wider mb-2 retro-text">{title}</h4>
    <div className="text-2xl font-bold text-[#a8c0ff] retro-text">{value}</div>
  </div>
);

export default function App() {
  const [isMonitoring, setIsMonitoring] = useState(false);
  const [stats, setStats] = useState<any>({ today: {}, recent_sessions: [], top_distractions: [] });
  const [eyeStats, setEyeStats] = useState<any>({});
  const [logs, setLogs] = useState<string[]>([]);
  const [showLogs, setShowLogs] = useState(false);
  const intervalRef = useRef<NodeJS.Timeout | null>(null);

  const formatTime = (seconds: number = 0) => {
    const h = Math.floor(seconds / 3600).toString().padStart(2, '0');
    const m = Math.floor((seconds % 3600) / 60).toString().padStart(2, '0');
    const s = Math.floor(seconds % 60).toString().padStart(2, '0');
    return `${h}:${m}:${s}`;
  };

  const fetchData = async () => {
    try {
      const [statsRes, eyeRes, logsRes] = await Promise.all([
        fetch(`${API_BASE_URL}/api/stats`),
        fetch(`${API_BASE_URL}/api/eye-tracking`),
        fetch(`${API_BASE_URL}/api/logs`)
      ]);
      const [statsData, eyeData, logsData] = await Promise.all([
        statsRes.json(),
        eyeRes.json(),
        logsRes.json()
      ]);
      setStats(statsData);
      setEyeStats(eyeData);
      setLogs(logsData.logs.slice().reverse());
    } catch (error) {
      console.error("Failed to fetch data:", error);
    }
  };

  const startMonitoring = async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/api/start`, { method: 'POST' });
      if (res.ok) setIsMonitoring(true);
    } catch (error) {
      console.error("Failed to start monitoring:", error);
    }
  };

  const stopMonitoring = async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/api/stop`, { method: 'POST' });
      if (res.ok) setIsMonitoring(false);
    } catch (error) {
      console.error("Failed to stop monitoring:", error);
    }
  };

  useEffect(() => {
    const checkStatus = async () => {
      try {
        const res = await fetch(`${API_BASE_URL}/api/status`);
        const data = await res.json();
        setIsMonitoring(data.monitoring_active);
      } catch (e) {
        console.error("Cannot connect to backend.");
      }
    };
    checkStatus();
    fetchData();
  }, []);

  useEffect(() => {
    if (isMonitoring) {
      intervalRef.current = setInterval(fetchData, 3000);
    } else {
      if (intervalRef.current) clearInterval(intervalRef.current);
      fetchData();
    }
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [isMonitoring]);

  const { today, recent_sessions, top_distractions } = stats;

  return (
    <div className="min-h-screen bg-[#0a0e27] p-6 text-[#a8c0ff] relative overflow-hidden">
      <div className="max-w-7xl mx-auto relative z-10">
        <header className="text-center mb-8">
          <h1 className="text-2xl font-bold retro-text">MIDNIGHTSHIFT</h1>
          <p className="text-[50px] text-[#7b9cdb] retro-text">~ productivity monitoring for the night owls ~</p>
        </header>
        <div className="bg-[#1a2456] border-2 border-[#4a5f8f] p-6 mb-6 flex items-center justify-between">
          <span className="text-sm font-bold retro-text">
            STATUS: {isMonitoring ? '>>> ACTIVE <<<' : '>>> STOPPED <<<'}
          </span>
          <div className="flex gap-3">
            <button onClick={startMonitoring} disabled={isMonitoring} className="px-5 py-2 bg-[#4a5f8f] border-2 border-[#a8c0ff] font-bold retro-text text-[10px] disabled:opacity-30">START</button>
            <button onClick={stopMonitoring} disabled={!isMonitoring} className="px-5 py-2 bg-[#2d1a3d] border-2 border-[#d4a5c8] font-bold retro-text text-[10px] disabled:opacity-30">STOP</button>
          </div>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
          <StatCard title="TOTAL TIME TODAY" value={formatTime(today?.total_time)} />
          <StatCard title="DISTRACTED TODAY" value={formatTime(today?.distraction_time)} />
          <StatCard title="DISTRACTION RATE" value={`${today?.distraction_percentage || 0}%`} />
        </div>
        <div className="bg-[#1a2456] border-2 border-[#4a5f8f] p-6 mb-6">
          <h2 className="text-base font-bold retro-text mb-4">EYE TRACKING METRICS</h2>
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            <EyeMetricCard title="BLINKS" value={eyeStats?.blinks || 0} />
            <EyeMetricCard title="EYES OPEN" value={`${Math.round(eyeStats?.eyes_open || 0)}%`} />
            <EyeMetricCard title="AT SCREEN" value={`${Math.round(eyeStats?.looking_at_screen || 0)}%`} />
            <EyeMetricCard title="PRODUCTIVE" value={formatTime(eyeStats?.productive_time)} />
          </div>
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
          <div className="bg-[#151c3a] border-2 border-[#4a5f8f] p-6">
            <h2 className="text-base font-bold retro-text mb-4">TOP DISTRACTIONS</h2>
            <div className="space-y-2">
              {top_distractions.map((app: any, idx: number) => (
                <div key={idx} className="flex justify-between p-2 bg-[#1a2456] border border-[#4a5f8f]">
                  <span className="text-[10px] retro-text flex-1 truncate">{app.app_name}</span>
                  <span className="text-[10px] retro-text text-[#d4a5c8]">{formatTime(app.total_time)}</span>
                </div>
              ))}
            </div>
          </div>
          <div className="bg-[#151c3a] border-2 border-[#4a5f8f] p-6">
            <h2 className="text-base font-bold retro-text mb-4">RECENT SESSIONS</h2>
            <div className="space-y-2">
              {recent_sessions.map((session: any, idx: number) => (
                <div key={idx} className="p-2 bg-[#1a2456] border border-[#4a5f8f]">
                  <div className="flex justify-between text-[8px] retro-text mb-1">
                    <span>{session.start_time}</span>
                    <span className={session.distraction_percentage > 50 ? 'text-[#d4a5c8]' : 'text-green-400'}>{session.distraction_percentage}% DISTRACTED</span>
                  </div>
                  <div className="text-[8px] text-[#7b9cdb] retro-text">
                    DURATION: {formatTime(session.total_duration)}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
        <div className="bg-[#1a2456] border-2 border-[#4a5f8f] p-6">
          <h2 className="text-base font-bold retro-text mb-4">ACTIVITY LOGS</h2>
          <button
            onClick={() => setShowLogs((v) => !v)}
            className="mb-4 px-6 py-3 bg-[#4a5f8f] text-[#a8c0ff] rounded transition-all retro-text text-[10px] font-bold"
          >
            {showLogs ? 'Hide activity log' : 'Show activity log'}
          </button>
          {showLogs && (
            <div className="max-h-60 overflow-y-auto space-y-1 bg-[#0a0e27] border border-[#4a5f8f] p-2 font-mono text-[8px]">
              {logs.map((log, idx) => (
                <div key={idx}>{log}</div>
              ))}
            </div>
          )}
        </div>
      </div>
      <style>{`.retro-text { font-family: 'Press Start 2P', cursive; line-height: 1.6; }`}</style>
    </div>
  );
}