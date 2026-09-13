import React, { useState, useMemo } from 'react';
import { Plant, HistoricalGeneration } from '../types';
import {
  UploadCloud,
  FileSpreadsheet,
  AlertCircle,
  CheckCircle2,
  TrendingUp,
  Clock,
  Zap,
  ArrowUpDown,
  Download,
  Loader2,
  Search,
} from 'lucide-react';
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
} from 'recharts';

interface HistoricalViewProps {
  plant: Plant;
  historical: HistoricalGeneration[];
  onOpenUpload: () => void;
  isLoading?: boolean;
  onRefresh?: () => void;
}

export const HistoricalView: React.FC<HistoricalViewProps> = ({
  plant,
  historical,
  onOpenUpload,
  isLoading,
  onRefresh,
}) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [pageSize, setPageSize] = useState(15);
  const [currentPage, setCurrentPage] = useState(1);
  const [sortOrder, setSortOrder] = useState<'desc' | 'asc'>('desc');

  // Sorted and filtered generation records
  const sortedRecords = useMemo(() => {
    return [...historical].sort((a, b) => {
      const timeA = new Date(a.timestamp).getTime();
      const timeB = new Date(b.timestamp).getTime();
      return sortOrder === 'desc' ? timeB - timeA : timeA - timeB;
    });
  }, [historical, sortOrder]);

  const filteredRecords = useMemo(() => {
    if (!searchTerm) return sortedRecords;
    const term = searchTerm.toLowerCase();
    return sortedRecords.filter(
      (r) =>
        r.timestamp.toLowerCase().includes(term) ||
        r.generation_mw.toString().includes(term)
    );
  }, [sortedRecords, searchTerm]);

  // Pagination
  const totalPages = Math.max(1, Math.ceil(filteredRecords.length / pageSize));
  const paginatedRecords = useMemo(() => {
    const start = (currentPage - 1) * pageSize;
    return filteredRecords.slice(start, start + pageSize);
  }, [filteredRecords, currentPage, pageSize]);

  // Metrics
  const metrics = useMemo(() => {
    if (historical.length === 0) {
      return { total: 0, avgMw: 0, maxMw: 0, totalMwh: 0, capFactor: 0 };
    }
    const values = historical.map((h) => h.generation_mw);
    const maxMw = Math.max(...values);
    const sum = values.reduce((a, b) => a + b, 0);
    const avgMw = sum / values.length;
    const capFactor = plant.capacity_mw > 0 ? (avgMw / plant.capacity_mw) * 100 : 0;
    return {
      total: historical.length,
      avgMw,
      maxMw,
      totalMwh: sum,
      capFactor,
    };
  }, [historical, plant.capacity_mw]);

  // Chart data (chronological)
  const chartData = useMemo(() => {
    return [...historical]
      .sort((a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime())
      .map((h) => {
        const d = new Date(h.timestamp);
        return {
          time: d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
          date: d.toLocaleDateString([], { month: 'short', day: 'numeric' }),
          mw: Number(h.generation_mw.toFixed(2)),
          capacity: plant.capacity_mw,
        };
      });
  }, [historical, plant.capacity_mw]);

  // Sample CSV template download for operator format guidance
  const handleDownloadSampleCsv = () => {
    const rows = [
      'timestamp,generation_mw',
      '2026-09-01T06:00:00Z,0.00',
      '2026-09-01T07:00:00Z,1.25',
      '2026-09-01T08:00:00Z,3.50',
      '2026-09-01T09:00:00Z,5.80',
      '2026-09-01T10:00:00Z,7.40',
      '2026-09-01T11:00:00Z,8.60',
      '2026-09-01T12:00:00Z,9.10',
    ];
    const blob = new Blob([rows.join('\n')], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${plant.name.replace(/\s+/g, '_')}_template_generation.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="space-y-6">
      {/* Metric Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-xs">
          <span className="text-xs text-slate-500 font-medium block mb-1">SCADA Records</span>
          <div className="flex items-baseline space-x-2">
            <span className="text-2xl font-bold text-slate-900">{metrics.total}</span>
            <span className="text-xs text-slate-500">intervals</span>
          </div>
          <span className="text-[11px] text-slate-500 mt-1 inline-flex items-center gap-1">
            <Clock className="h-3 w-3 text-sky-500" /> Granular telemetry
          </span>
        </div>

        <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-xs">
          <span className="text-xs text-slate-500 font-medium block mb-1">Max Recorded</span>
          <div className="flex items-baseline space-x-2">
            <span className="text-2xl font-bold text-slate-900">{metrics.maxMw.toFixed(1)}</span>
            <span className="text-xs text-slate-500">MW</span>
          </div>
          <span className="text-[11px] text-amber-700 font-semibold mt-1 inline-block">
            {((metrics.maxMw / (plant.capacity_mw || 1)) * 100).toFixed(0)}% of nameplate
          </span>
        </div>

        <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-xs">
          <span className="text-xs text-slate-500 font-medium block mb-1">Mean Generation</span>
          <div className="flex items-baseline space-x-2">
            <span className="text-2xl font-bold text-slate-900">{metrics.avgMw.toFixed(1)}</span>
            <span className="text-xs text-slate-500">MW</span>
          </div>
          <span className="text-[11px] text-emerald-700 font-semibold mt-1 inline-block">
            {metrics.capFactor.toFixed(1)}% Capacity factor
          </span>
        </div>

        <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-xs">
          <span className="text-xs text-slate-500 font-medium block mb-1">Total Yield Captured</span>
          <div className="flex items-baseline space-x-2">
            <span className="text-2xl font-bold text-slate-900">
              {metrics.totalMwh > 1000
                ? `${(metrics.totalMwh / 1000).toFixed(2)} GWh`
                : `${metrics.totalMwh.toFixed(1)} MWh`}
            </span>
          </div>
          <span className="text-[11px] text-slate-500 mt-1 inline-flex items-center gap-1">
            <Zap className="h-3 w-3 text-amber-500" /> Recorded output
          </span>
        </div>
      </div>

      {/* Historical Generation Trend Chart */}
      <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-xs">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 mb-4">
          <div>
            <h2 className="text-base font-semibold text-slate-900">
              Historical Generation Profile
            </h2>
            <p className="text-xs text-slate-500">
              Chronological time-series of recorded inverter / feeder generation telemetry
            </p>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={handleDownloadSampleCsv}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-semibold rounded-lg transition"
              title="Download sample CSV formatted for this plant"
            >
              <Download className="h-3.5 w-3.5" /> Sample CSV
            </button>
            <button
              onClick={onOpenUpload}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-amber-500 hover:bg-amber-400 text-slate-950 text-xs font-bold rounded-lg transition shadow-xs cursor-pointer"
            >
              <UploadCloud className="h-3.5 w-3.5" /> Upload CSV
            </button>
          </div>
        </div>

        {chartData.length > 0 ? (
          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={chartData} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
                <defs>
                  <linearGradient id="histGen" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#0284c7" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#0284c7" stopOpacity={0.02} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" vertical={false} />
                <XAxis
                  dataKey="time"
                  stroke="#94a3b8"
                  fontSize={11}
                  tickLine={false}
                  axisLine={{ stroke: '#cbd5e1' }}
                />
                <YAxis
                  stroke="#94a3b8"
                  fontSize={11}
                  tickLine={false}
                  axisLine={false}
                  unit=" MW"
                  domain={[0, plant.capacity_mw > 0 ? Math.ceil(plant.capacity_mw * 1.05) : 'auto']}
                />
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#ffffff',
                    border: '1px solid #e2e8f0',
                    borderRadius: '8px',
                    fontSize: '12px',
                    color: '#0f172a',
                    boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)',
                  }}
                  formatter={(val: any) => [`${val} MW`, 'Generation']}
                  labelFormatter={(label, items) => {
                    const item = items[0]?.payload;
                    return item ? `${item.date} ${label}` : label;
                  }}
                />
                <Area
                  type="monotone"
                  dataKey="mw"
                  stroke="#0284c7"
                  strokeWidth={2}
                  fillOpacity={1}
                  fill="url(#histGen)"
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        ) : (
          <div className="py-12 text-center">
            <FileSpreadsheet className="h-10 w-10 text-slate-300 mx-auto mb-2" />
            <p className="text-sm font-medium text-slate-700">No Generation Data Uploaded Yet</p>
            <p className="text-xs text-slate-500 mt-1 max-w-sm mx-auto">
              Upload standard generation CSV files containing timestamp and generation_mw columns to view historical curves.
            </p>
          </div>
        )}
      </div>

      {/* Historical Telemetry Table */}
      <div className="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-xs">
        <div className="p-4 border-b border-slate-100 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
          <div className="flex items-center gap-2">
            <h3 className="text-sm font-semibold text-slate-900">Recorded Telemetry Logs</h3>
            <span className="px-2 py-0.5 bg-slate-100 text-slate-600 text-xs rounded-full font-medium">
              {filteredRecords.length} records
            </span>
          </div>

          <div className="flex items-center gap-2">
            <div className="relative">
              <Search className="h-3.5 w-3.5 text-slate-400 absolute left-2.5 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                value={searchTerm}
                onChange={(e) => {
                  setSearchTerm(e.target.value);
                  setCurrentPage(1);
                }}
                placeholder="Search timestamp or MW..."
                className="pl-8 pr-3 py-1.5 bg-slate-50 border border-slate-200 rounded-lg text-xs text-slate-800 focus:outline-none focus:ring-1 focus:ring-amber-500 w-48 sm:w-60"
              />
            </div>
            <button
              onClick={() => setSortOrder((prev) => (prev === 'desc' ? 'asc' : 'desc'))}
              className="px-2.5 py-1.5 border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 rounded-lg text-xs font-medium flex items-center gap-1 transition cursor-pointer"
              title="Toggle Sort Order"
            >
              <ArrowUpDown className="h-3 w-3" />
              {sortOrder === 'desc' ? 'Newest' : 'Oldest'}
            </button>
          </div>
        </div>

        {paginatedRecords.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50 text-slate-500 border-b border-slate-200 uppercase font-semibold">
                <tr>
                  <th className="py-3 px-4">Timestamp (UTC/Local)</th>
                  <th className="py-3 px-4">Generation (MW)</th>
                  <th className="py-3 px-4">% Nameplate</th>
                  <th className="py-3 px-4">Status</th>
                  <th className="py-3 px-4">Logged At</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {paginatedRecords.map((record) => {
                  const d = new Date(record.timestamp);
                  const pct =
                    plant.capacity_mw > 0
                      ? ((record.generation_mw / plant.capacity_mw) * 100).toFixed(1)
                      : '0';
                  const pctNum = parseFloat(pct);

                  return (
                    <tr key={record.id} className="hover:bg-slate-50 transition">
                      <td className="py-3 px-4 font-medium text-slate-900">
                        {d.toLocaleString([], {
                          year: 'numeric',
                          month: 'short',
                          day: 'numeric',
                          hour: '2-digit',
                          minute: '2-digit',
                        })}
                      </td>
                      <td className="py-3 px-4 font-bold text-slate-800">
                        {record.generation_mw.toFixed(2)} MW
                      </td>
                      <td className="py-3 px-4">
                        <div className="flex items-center gap-2">
                          <div className="w-16 bg-slate-200 rounded-full h-1.5 overflow-hidden">
                            <div
                              className={`h-1.5 rounded-full ${
                                pctNum > 70
                                  ? 'bg-amber-500'
                                  : pctNum > 20
                                  ? 'bg-sky-500'
                                  : 'bg-slate-400'
                              }`}
                              style={{ width: `${Math.min(100, pctNum)}%` }}
                            />
                          </div>
                          <span className="text-[11px] text-slate-600 font-medium">{pct}%</span>
                        </div>
                      </td>
                      <td className="py-3 px-4">
                        {record.generation_mw > 0.05 ? (
                          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
                            <span className="w-1.5 h-1.5 rounded-full bg-emerald-500"></span> Active
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-slate-100 text-slate-600 border border-slate-200">
                            <span className="w-1.5 h-1.5 rounded-full bg-slate-400"></span> Idle / Night
                          </span>
                        )}
                      </td>
                      <td className="py-3 px-4 text-slate-500 text-[11px]">
                        {new Date(record.created_at).toLocaleTimeString([], {
                          hour: '2-digit',
                          minute: '2-digit',
                        })}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="p-8 text-center text-xs text-slate-500">
            {searchTerm ? 'No records match search filter' : 'No records logged'}
          </div>
        )}

        {/* Pagination controls */}
        {totalPages > 1 && (
          <div className="p-3 border-t border-slate-100 flex items-center justify-between text-xs text-slate-500">
            <div>
              Showing page <strong className="font-semibold text-slate-700">{currentPage}</strong> of{' '}
              <strong className="font-semibold text-slate-700">{totalPages}</strong>
            </div>
            <div className="flex items-center gap-1.5">
              <button
                onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                disabled={currentPage === 1}
                className="px-2.5 py-1 border border-slate-200 rounded hover:bg-slate-50 disabled:opacity-40 transition font-medium"
              >
                Previous
              </button>
              <button
                onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
                disabled={currentPage === totalPages}
                className="px-2.5 py-1 border border-slate-200 rounded hover:bg-slate-50 disabled:opacity-40 transition font-medium"
              >
                Next
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
