import { useState, useEffect } from 'react';
import { AlertCircle, Cpu, HardDrive, Trash2, X, RefreshCw } from 'lucide-react';

interface ProcessInfo {
  pid: number;
  name: string;
  cmdline: string;
  project_dir: string | null;
  cpu_percent: number;
  memory_mb: number;
  status: string;
  create_time: number;
}

interface ProcessListResponse {
  processes: ProcessInfo[];
  total: number;
}

export function ProcessManager() {
  const [isOpen, setIsOpen] = useState(false);
  const [processes, setProcesses] = useState<ProcessInfo[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchProcesses = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch('http://127.0.0.1:8888/api/processes');
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }
      const data: ProcessListResponse = await response.json();
      setProcesses(data.processes);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch processes');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (isOpen) {
      fetchProcesses();
      // Auto-refresh every 2 seconds
      const interval = setInterval(fetchProcesses, 2000);
      return () => clearInterval(interval);
    }
  }, [isOpen]);

  const killProcess = async (pid: number) => {
    try {
      const response = await fetch('http://127.0.0.1:8888/api/processes/kill', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ pid }),
      });

      if (!response.ok) {
        throw new Error(`Failed to kill process ${pid}`);
      }

      // Refresh the list
      await fetchProcesses();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to kill process');
    }
  };

  const killAllProcesses = async () => {
    if (!confirm('Kill all agent processes? This will stop all running agents.')) {
      return;
    }

    try {
      const response = await fetch('http://127.0.0.1:8888/api/processes/kill-all', {
        method: 'POST',
      });

      if (!response.ok) {
        throw new Error('Failed to kill all processes');
      }

      const data = await response.json();
      alert(`Killed ${data.total_killed} processes. Failed: ${data.total_failed}`);

      // Refresh the list
      await fetchProcesses();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to kill all processes');
    }
  };

  const formatUptime = (createTime: number) => {
    const now = Date.now() / 1000;
    const uptime = now - createTime;

    if (uptime < 60) return `${Math.floor(uptime)}s`;
    if (uptime < 3600) return `${Math.floor(uptime / 60)}m`;
    if (uptime < 86400) return `${Math.floor(uptime / 3600)}h`;
    return `${Math.floor(uptime / 86400)}d`;
  };

  const extractProjectName = (projectDir: string | null) => {
    if (!projectDir) return 'Unknown';
    const parts = projectDir.split('/');
    return parts[parts.length - 1] || 'Unknown';
  };

  return (
    <>
      {/* Floating Button */}
      <button
        onClick={() => setIsOpen(true)}
        className="fixed bottom-6 right-24 z-50 bg-black text-white p-4 rounded-full border-4 border-white shadow-neo-brutal hover:translate-x-1 hover:translate-y-1 hover:shadow-none transition-all"
        title="Process Manager"
      >
        <Cpu className="w-6 h-6" />
        {processes.length > 0 && (
          <span className="absolute -top-2 -right-2 bg-red-500 text-white text-xs font-bold rounded-full w-6 h-6 flex items-center justify-center border-2 border-black">
            {processes.length}
          </span>
        )}
      </button>

      {/* Modal */}
      {isOpen && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
          <div className="bg-white border-4 border-black rounded-xl shadow-neo-brutal max-w-5xl w-full max-h-[80vh] overflow-hidden flex flex-col">
            {/* Header */}
            <div className="bg-black text-white p-4 flex items-center justify-between border-b-4 border-white">
              <div className="flex items-center gap-3">
                <Cpu className="w-6 h-6" />
                <h2 className="text-xl font-bold">Process Manager</h2>
                <span className="bg-white text-black px-3 py-1 rounded-full text-sm font-bold">
                  {processes.length} running
                </span>
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={fetchProcesses}
                  disabled={loading}
                  className="p-2 hover:bg-white/20 rounded-lg transition-colors disabled:opacity-50"
                  title="Refresh"
                >
                  <RefreshCw className={`w-5 h-5 ${loading ? 'animate-spin' : ''}`} />
                </button>
                <button
                  onClick={() => setIsOpen(false)}
                  className="bg-red-500 hover:bg-red-600 p-2 rounded-lg transition-colors border-2 border-white"
                  title="Fechar"
                >
                  <X className="w-6 h-6 stroke-[3]" />
                </button>
              </div>
            </div>

            {/* Error Alert */}
            {error && (
              <div className="bg-red-100 border-b-4 border-red-500 p-4 flex items-center gap-3">
                <AlertCircle className="w-5 h-5 text-red-600" />
                <span className="text-red-700 font-medium">{error}</span>
              </div>
            )}

            {/* Action Bar */}
            {processes.length > 0 && (
              <div className="bg-gray-50 border-b-4 border-black p-4">
                <button
                  onClick={killAllProcesses}
                  className="bg-red-500 text-white px-4 py-2 rounded-lg border-2 border-black font-bold hover:bg-red-600 transition-colors flex items-center gap-2"
                >
                  <Trash2 className="w-4 h-4" />
                  Kill All Processes
                </button>
              </div>
            )}

            {/* Process List */}
            <div className="flex-1 overflow-y-auto p-4">
              {loading && processes.length === 0 ? (
                <div className="text-center py-12 text-gray-500">
                  <RefreshCw className="w-8 h-8 animate-spin mx-auto mb-3" />
                  Loading processes...
                </div>
              ) : processes.length === 0 ? (
                <div className="text-center py-12 text-gray-500">
                  <Cpu className="w-12 h-12 mx-auto mb-3 opacity-50" />
                  <p className="text-lg font-medium">No agent processes running</p>
                  <p className="text-sm">All agents have been stopped</p>
                </div>
              ) : (
                <div className="space-y-3">
                  {processes.map((proc) => (
                    <div
                      key={proc.pid}
                      className="bg-white border-4 border-black rounded-xl p-4 shadow-neo-sm hover:shadow-neo-brutal transition-shadow"
                    >
                      <div className="flex items-start justify-between gap-4">
                        <div className="flex-1 min-w-0">
                          {/* Header */}
                          <div className="flex items-start gap-3 mb-3">
                            <div className="flex-1">
                              <h3 className="text-lg font-bold text-black mb-2">
                                {proc.name}
                              </h3>
                              <div className="flex items-center gap-2 flex-wrap">
                                <span className="bg-neo-dark text-white px-3 py-1 rounded-full text-sm font-bold">
                                  PID {proc.pid}
                                </span>
                                <span className="bg-blue-500 text-white px-3 py-1 rounded-full text-xs font-bold">
                                  {proc.status}
                                </span>
                                <span className="text-gray-600 text-sm font-medium">
                                  Uptime: {formatUptime(proc.create_time)}
                                </span>
                              </div>
                            </div>
                          </div>

                          {/* Project */}
                          {proc.project_dir && (
                            <div className="mb-2">
                              <span className="text-sm font-medium text-gray-600">Project:</span>
                              <span className="ml-2 font-bold text-black">
                                {extractProjectName(proc.project_dir)}
                              </span>
                              <span className="ml-2 text-xs text-gray-500 font-mono">
                                {proc.project_dir}
                              </span>
                            </div>
                          )}

                          {/* Resources */}
                          <div className="flex items-center gap-4 text-sm">
                            <div className="flex items-center gap-2">
                              <Cpu className="w-4 h-4 text-blue-500" />
                              <span className="font-medium">{proc.cpu_percent.toFixed(1)}%</span>
                            </div>
                            <div className="flex items-center gap-2">
                              <HardDrive className="w-4 h-4 text-green-500" />
                              <span className="font-medium">{proc.memory_mb.toFixed(0)} MB</span>
                            </div>
                          </div>

                          {/* Command Line */}
                          <div className="mt-2 text-xs text-gray-600 font-mono bg-gray-50 p-2 rounded border border-gray-200 overflow-hidden text-ellipsis">
                            {proc.cmdline}
                          </div>
                        </div>

                        {/* Kill Button */}
                        <button
                          onClick={() => killProcess(proc.pid)}
                          className="bg-red-500 text-white p-2 rounded-lg border-2 border-black font-bold hover:bg-red-600 transition-colors flex-shrink-0"
                          title="Kill Process"
                        >
                          <Trash2 className="w-5 h-5" />
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Footer */}
            <div className="bg-gray-50 border-t-4 border-black p-4 text-center text-sm text-gray-600">
              Auto-refreshes every 2 seconds • Only shows agent-related processes
            </div>
          </div>
        </div>
      )}
    </>
  );
}
