import React, { useState, useEffect } from 'react';
import { 
  Activity, 
  Database, 
  Terminal, 
  Shield, 
  Settings, 
  Search, 
  Bell, 
  Filter,
  RefreshCw,
  Clock,
  ExternalLink,
  Cpu,
  Layers,
  FileText
} from 'lucide-react';
import { 
  LineChart, 
  Line, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  ResponsiveContainer,
  AreaChart,
  Area
} from 'recharts';
import { motion, AnimatePresence } from 'framer-motion';

// Mock data for initial state
const INITIAL_STATS = [
  { name: '00:00', requests: 40, errors: 2 },
  { name: '04:00', requests: 30, errors: 1 },
  { name: '08:00', requests: 200, errors: 4 },
  { name: '12:00', requests: 278, errors: 5 },
  { name: '16:00', requests: 189, errors: 2 },
  { name: '20:00', requests: 239, errors: 3 },
  { name: '23:59', requests: 349, errors: 4 },
];

const App = () => {
  const [activeTab, setActiveTab] = useState('overview');
  const [telemetry, setTelemetry] = useState({ traces: [], logs: [], metrics: [] });
  const [selectedItem, setSelectedItem] = useState(null);
  const [isRefreshing, setIsRefreshing] = useState(false);

  const fetchTelemetry = async () => {
    setIsRefreshing(true);
    try {
      const response = await fetch('/api/telemetry');
      const data = await response.json();
      setTelemetry(data);
    } catch (error) {
      console.error("Failed to fetch telemetry:", error);
    } finally {
      setIsRefreshing(false);
    }
  };

  useEffect(() => {
    fetchTelemetry();
    const interval = setInterval(fetchTelemetry, 5000); // Poll every 5s
    return () => clearInterval(interval);
  }, []);

  const renderStats = () => (
    <div className="stats-grid">
      <StatCard title="Total Requests" value={telemetry.traces.length} icon={<Activity />} color="var(--accent-blue)" />
      <StatCard title="Active Errors" value={telemetry.logs.filter(l => l.severity === 'ERROR').length} icon={<Shield />} color="var(--error)" />
      <StatCard title="System Load" value="12%" icon={<Cpu />} color="var(--accent-purple)" />
      <StatCard title="Storage" value="2.4 MB" icon={<Database />} color="var(--accent-cyan)" />
    </div>
  );

  return (
    <div className="app-container">
      {/* Sidebar */}
      <nav className="sidebar glass">
        <div className="logo">
          <div className="logo-icon">R</div>
          <span>Rouge.AI</span>
        </div>
        
        <div className="nav-items">
          <NavItem active={activeTab === 'overview'} onClick={() => setActiveTab('overview')} icon={<Activity />} label="Overview" />
          <NavItem active={activeTab === 'traces'} onClick={() => setActiveTab('traces')} icon={<Layers />} label="Traces" />
          <NavItem active={activeTab === 'logs'} onClick={() => setActiveTab('logs')} icon={<Terminal />} label="Logs" />
          <NavItem active={activeTab === 'metrics'} onClick={() => setActiveTab('metrics')} icon={<Activity />} label="Metrics" />
        </div>

        <div className="nav-footer">
          <NavItem icon={<Settings />} label="Settings" />
        </div>
      </nav>

      {/* Main Content */}
      <main className="main-content">
        <header className="main-header">
          <div className="header-title">
            <h1>{activeTab.charAt(0).toUpperCase() + activeTab.slice(1)}</h1>
            <div className="status-indicator">
              <span className="status-pulse"></span>
              Live Monitoring Active
            </div>
          </div>
          
          <div className="header-actions">
            <button className="refresh-btn glass" onClick={fetchTelemetry}>
              <RefreshCw className={isRefreshing ? "spin" : ""} size={18} />
            </button>
            <div className="user-profile glass">
              <span>Local Project</span>
            </div>
          </div>
        </header>

        <AnimatePresence mode="wait">
          {activeTab === 'overview' && (
            <motion.div 
              key="overview"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              className="dashboard-view"
            >
              {renderStats()}
              
              <div className="charts-row">
                <div className="chart-container glass">
                  <h3>Throughput (Requests/sec)</h3>
                  <ResponsiveContainer width="100%" height={300}>
                    <AreaChart data={INITIAL_STATS}>
                      <defs>
                        <linearGradient id="colorRequests" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="var(--accent-blue)" stopOpacity={0.3}/>
                          <stop offset="95%" stopColor="var(--accent-blue)" stopOpacity={0}/>
                        </linearGradient>
                      </defs>
                      <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                      <XAxis dataKey="name" stroke="var(--text-secondary)" />
                      <YAxis stroke="var(--text-secondary)" />
                      <Tooltip contentStyle={{ background: '#1e293b', border: 'none', borderRadius: '8px' }} />
                      <Area type="monotone" dataKey="requests" stroke="var(--accent-blue)" fillOpacity={1} fill="url(#colorRequests)" />
                    </AreaChart>
                  </ResponsiveContainer>
                </div>
              </div>

              <div className="live-tail glass">
                <div className="section-header">
                  <h3>Recent Traces</h3>
                  <button className="view-all">View All</button>
                </div>
                <div className="tail-list">
                  {telemetry.traces.length > 0 ? (
                    telemetry.traces.slice(0, 5).map((trace, i) => (
                      <TraceItem key={i} data={trace} />
                    ))
                  ) : (
                    <div className="empty-state">No traces received yet. Send telemetry to port 10108.</div>
                  )}
                </div>
              </div>
            </motion.div>
          )}

          {activeTab === 'traces' && <TelemetryList items={telemetry.traces} type="trace" />}
          {activeTab === 'logs' && <TelemetryList items={telemetry.logs} type="log" />}
        </AnimatePresence>
      </main>
    </div>
  );
};

// Helper Components
const NavItem = ({ icon, label, active, onClick }) => (
  <div className={`nav-item ${active ? 'active' : ''}`} onClick={onClick}>
    {icon}
    <span>{label}</span>
  </div>
);

const StatCard = ({ title, value, icon, color }) => (
  <div className="stat-card glass animate-fade-in">
    <div className="stat-header">
      <div className="stat-icon" style={{ backgroundColor: `${color}20`, color: color }}>
        {icon}
      </div>
      <span className="stat-title">{title}</span>
    </div>
    <div className="stat-value">{value}</div>
  </div>
);

const TraceItem = ({ data }) => {
  const firstSpan = data?.resourceSpans?.[0]?.scopeSpans?.[0]?.spans?.[0];
  const name = firstSpan?.name || "unnamed-span";
  const duration = (firstSpan?.endTimeUnixNano - firstSpan?.startTimeUnixNano) / 1000000;
  
  return (
    <div className="tail-item">
      <div className="item-main">
        <Layers size={14} className="icon-blue" />
        <span className="item-name">{name}</span>
      </div>
      <div className="item-meta">
        <Clock size={12} />
        <span>{duration.toFixed(2)}ms</span>
        <span className="status-badge success">Success</span>
      </div>
    </div>
  );
};

const TelemetryList = ({ items, type }) => (
  <motion.div 
    initial={{ opacity: 0 }}
    animate={{ opacity: 1 }}
    className="full-list-view"
  >
    <div className="list-toolbar glass">
      <div className="search-box">
        <Search size={18} />
        <input type="text" placeholder={`Search ${type}s...`} />
      </div>
      <div className="toolbar-actions">
        <button className="filter-btn glass"><Filter size={16} /> Filter</button>
      </div>
    </div>
    <div className="list-container glass">
      {items.length === 0 ? (
        <div className="empty-state">No {type}s found.</div>
      ) : (
        <table className="telemetry-table">
          <thead>
            <tr>
              <th>Timestamp</th>
              <th>Name/Content</th>
              <th>Duration/Severity</th>
              <th>Action</th>
            </tr>
          </thead>
          <tbody>
            {items.map((item, i) => (
              <tr key={i}>
                <td>{new Date().toLocaleTimeString()}</td>
                <td>{type === 'trace' ? (item.resourceSpans?.[0]?.scopeSpans?.[0]?.spans?.[0]?.name) : "Log Entry"}</td>
                <td>{type === 'trace' ? "45ms" : "INFO"}</td>
                <td><button className="icon-btn"><ExternalLink size={14} /></button></td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  </motion.div>
);

export default App;
