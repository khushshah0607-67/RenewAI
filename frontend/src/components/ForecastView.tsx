import React, { useMemo } from 'react';
import ReactECharts from 'echarts-for-react';
import { Plant, Forecast, HistoricalGeneration } from '../types';
import {
  TrendingUp,
  RefreshCw,
  AlertCircle,
  BarChart2,
  Calendar,
  Layers,
  CheckCircle2,
} from 'lucide-react';

interface ForecastViewProps {
  plant: Plant;
  forecasts: Forecast[];
  historical: HistoricalGeneration[];
  onRegenerate: () => void;
  isGenerating: boolean;
  isLoading?: boolean;
  error?: string | null;
}

export const ForecastView: React.FC<ForecastViewProps> = ({
  plant,
  forecasts,
  historical,
  onRegenerate,
  isGenerating,
  isLoading,
  error,
}) => {
  // Sort and process forecasts and recent historical generation
  const sortedForecasts = useMemo(() => {
    return [...forecasts].sort(
      (a, b) => new Date(a.forecast_timestamp).getTime() - new Date(b.forecast_timestamp).getTime()
    );
  }, [forecasts]);

  const recentHistory = useMemo(() => {
    return [...historical]
      .sort((a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime())
      .slice(-24);
  }, [historical]);

  // Statistics calculation
  const stats = useMemo(() => {
    if (sortedForecasts.length === 0) {
      return {
        peakP50: 0,
        totalYieldMWh: 0,
        avgCapacityFactor: 0,
        avgSpreadMW: 0,
        modelVersion: 'None',
      };
    }

    const p50s = sortedForecasts.map((f) => f.p50_mw);
    const spreads = sortedForecasts.map((f) => Math.max(0, f.p90_mw - f.p10_mw));
    const peakP50 = Math.max(...p50s);
    const intervalHours =
      sortedForecasts.length > 1
        ? Math.max(
            0.25,
            (new Date(sortedForecasts[1].forecast_timestamp).getTime() -
              new Date(sortedForecasts[0].forecast_timestamp).getTime()) /
              (1000 * 60 * 60)
          )
        : 0.25;
    const totalYieldMWh = p50s.reduce((sum, v) => sum + v * intervalHours, 0);
    const avgGen = p50s.reduce((sum, v) => sum + v, 0) / p50s.length;
    const avgCapacityFactor =
      plant.capacity_mw > 0 ? (avgGen / plant.capacity_mw) * 100 : 0;
    const avgSpreadMW = spreads.reduce((sum, v) => sum + v, 0) / spreads.length;
    const modelVersion = sortedForecasts[0]?.model_version || 'renewai-generalized-xgb-v1';

    return {
      peakP50,
      totalYieldMWh,
      avgCapacityFactor,
      avgSpreadMW,
      modelVersion,
    };
  }, [sortedForecasts, plant.capacity_mw]);

  // Build Apache ECharts Option
  const chartOption = useMemo(() => {
    const timeLabels: string[] = [];
    const fullTimestamps: string[] = [];
    const actualData: (number | null)[] = [];
    const p10BaseData: (number | null)[] = [];
    const spreadData: (number | null)[] = [];
    const p50Data: (number | null)[] = [];
    const p10Data: (number | null)[] = [];
    const p90Data: (number | null)[] = [];

    // 1. Add historical points
    recentHistory.forEach((h) => {
      const d = new Date(h.timestamp);
      timeLabels.push(d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }));
      fullTimestamps.push(d.toLocaleString());
      actualData.push(Number(h.generation_mw.toFixed(2)));
      p10BaseData.push(null);
      spreadData.push(null);
      p50Data.push(null);
      p10Data.push(null);
      p90Data.push(null);
    });

    // 2. Add forecast points
    sortedForecasts.forEach((f) => {
      const d = new Date(f.forecast_timestamp);
      timeLabels.push(d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }));
      fullTimestamps.push(d.toLocaleString());
      actualData.push(null);

      const p10 = Math.max(0, Number(f.p10_mw.toFixed(2)));
      const p50 = Math.max(0, Number(f.p50_mw.toFixed(2)));
      const p90 = Math.max(0, Number(f.p90_mw.toFixed(2)));
      const spread = Math.max(0, Number((p90 - p10).toFixed(2)));

      p10BaseData.push(p10);
      spreadData.push(spread);
      p50Data.push(p50);
      p10Data.push(p10);
      p90Data.push(p90);
    });

    return {
      title: {
        show: false,
      },
      tooltip: {
        trigger: 'axis',
        backgroundColor: '#ffffff',
        borderColor: '#e2e8f0',
        borderWidth: 1,
        textStyle: {
          color: '#0f172a',
          fontSize: 12,
        },
        formatter: (params: any[]) => {
          if (!params || params.length === 0) return '';
          const index = params[0].dataIndex;
          const fullTime = fullTimestamps[index] || timeLabels[index];

          let html = `<div style="font-weight: 600; margin-bottom: 6px; color: #1e293b;">${fullTime}</div>`;

          params.forEach((param) => {
            if (
              param.seriesName === 'Uncertainty Base' ||
              param.value === null ||
              param.value === undefined
            ) {
              return;
            }

            let marker = param.marker;
            let valText = `${param.value} MW`;

            if (param.seriesName === 'Uncertainty Band (P10-P90)') {
              valText = `±${param.value} MW spread`;
            }

            html += `<div style="display: flex; justify-content: space-between; align-items: center; gap: 14px; font-size: 11px; margin: 3px 0;">
              <span>${marker} ${param.seriesName}</span>
              <span style="font-weight: 700; color: #0f172a;">${valText}</span>
            </div>`;
          });

          return html;
        },
      },
      legend: {
        data: [
          'Actual SCADA',
          'P50 Median Forecast',
          'Uncertainty Band (P10-P90)',
          'P90 Upper Bound',
          'P10 Lower Bound',
        ],
        top: 0,
        right: 10,
        textStyle: {
          color: '#475569',
          fontSize: 11,
        },
        selected: {
          'P90 Upper Bound': false,
          'P10 Lower Bound': false,
        },
      },
      grid: {
        left: '2%',
        right: '2%',
        bottom: '12%',
        top: '12%',
        containLabel: true,
      },
      xAxis: {
        type: 'category',
        data: timeLabels,
        boundaryGap: false,
        axisLine: { lineStyle: { color: '#cbd5e1' } },
        axisLabel: { color: '#64748b', fontSize: 11 },
        splitLine: { show: false },
      },
      yAxis: {
        type: 'value',
        name: 'Generation (MW)',
        nameTextStyle: { color: '#64748b', fontSize: 11, padding: [0, 0, 0, 20] },
        axisLine: { show: false },
        axisTick: { show: false },
        axisLabel: { color: '#64748b', fontSize: 11 },
        splitLine: { lineStyle: { color: '#f1f5f9', type: 'dashed' } },
        max: plant.capacity_mw > 0 ? Math.ceil(plant.capacity_mw * 1.05) : undefined,
      },
      dataZoom: [
        {
          type: 'inside',
          start: 0,
          end: 100,
        },
        {
          type: 'slider',
          start: 0,
          end: 100,
          height: 20,
          bottom: 5,
          borderColor: '#e2e8f0',
          fillerColor: 'rgba(245, 158, 11, 0.15)',
          handleStyle: { color: '#f59e0b' },
          textStyle: { color: '#64748b', fontSize: 10 },
        },
      ],
      series: [
        // Actual SCADA Generation
        {
          name: 'Actual SCADA',
          type: 'line',
          data: actualData,
          smooth: true,
          showSymbol: false,
          itemStyle: { color: '#0284c7' },
          lineStyle: { width: 2.5, color: '#0284c7' },
        },
        // Uncertainty Base: Stack 1
        {
          name: 'Uncertainty Base',
          type: 'line',
          data: p10BaseData,
          stack: 'confidence',
          lineStyle: { opacity: 0 },
          itemStyle: { opacity: 0 },
          showSymbol: false,
        },
        // Uncertainty Band: Stack 2
        {
          name: 'Uncertainty Band (P10-P90)',
          type: 'line',
          data: spreadData,
          stack: 'confidence',
          areaStyle: {
            color: 'rgba(245, 158, 11, 0.22)',
          },
          lineStyle: { opacity: 0 },
          itemStyle: { color: '#f59e0b' },
          showSymbol: false,
        },
        // P50 Median Forecast Line
        {
          name: 'P50 Median Forecast',
          type: 'line',
          data: p50Data,
          smooth: true,
          showSymbol: false,
          itemStyle: { color: '#d97706' },
          lineStyle: { width: 3, color: '#d97706' },
        },
        // P90 Line
        {
          name: 'P90 Upper Bound',
          type: 'line',
          data: p90Data,
          smooth: true,
          showSymbol: false,
          lineStyle: { width: 1.5, type: 'dashed', color: '#ea580c' },
          itemStyle: { color: '#ea580c' },
        },
        // P10 Line
        {
          name: 'P10 Lower Bound',
          type: 'line',
          data: p10Data,
          smooth: true,
          showSymbol: false,
          lineStyle: { width: 1.5, type: 'dashed', color: '#b45309' },
          itemStyle: { color: '#b45309' },
        },
      ],
    };
  }, [recentHistory, sortedForecasts, plant.capacity_mw]);

  if (isLoading) {
    return (
      <div className="bg-white border border-slate-200 rounded-xl p-12 text-center shadow-xs">
        <RefreshCw className="h-8 w-8 text-amber-500 animate-spin mx-auto mb-3" />
        <p className="text-sm font-semibold text-slate-800">Loading Probabilistic Forecasts...</p>
        <p className="text-xs text-slate-500 mt-1">
          Retrieving 24-hour horizon P10/P50/P90 quantile curves
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Error Alert */}
      {error && (
        <div className="p-4 bg-rose-50 border border-rose-200 rounded-xl flex items-center justify-between text-xs text-rose-800">
          <div className="flex items-center space-x-2">
            <AlertCircle className="h-4 w-4 text-rose-600 shrink-0" />
            <span>{error}</span>
          </div>
          <button
            onClick={onRegenerate}
            className="px-2.5 py-1 bg-rose-100 hover:bg-rose-200 text-rose-800 rounded font-semibold transition"
          >
            Retry Generation
          </button>
        </div>
      )}

      {/* Metric Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-xs">
          <span className="text-xs text-slate-500 font-medium block mb-1">Peak Projected (P50)</span>
          <div className="flex items-baseline space-x-2">
            <span className="text-2xl font-bold text-slate-900">{stats.peakP50.toFixed(1)}</span>
            <span className="text-xs text-slate-500">MW</span>
          </div>
          <span className="text-[11px] text-amber-700 font-semibold mt-1 inline-block">
            {((stats.peakP50 / (plant.capacity_mw || 1)) * 100).toFixed(0)}% of nameplate ({plant.capacity_mw} MW)
          </span>
        </div>

        <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-xs">
          <span className="text-xs text-slate-500 font-medium block mb-1">24h Projected Yield</span>
          <div className="flex items-baseline space-x-2">
            <span className="text-2xl font-bold text-slate-900">
              {stats.totalYieldMWh > 1000
                ? `${(stats.totalYieldMWh / 1000).toFixed(2)} GWh`
                : `${stats.totalYieldMWh.toFixed(1)} MWh`}
            </span>
          </div>
          <span className="text-[11px] text-slate-500 font-medium mt-1 inline-block">
            P50 Expected integrated energy
          </span>
        </div>

        <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-xs">
          <span className="text-xs text-slate-500 font-medium block mb-1">Mean Capacity Factor</span>
          <div className="flex items-baseline space-x-2">
            <span className="text-2xl font-bold text-slate-900">
              {stats.avgCapacityFactor.toFixed(1)}%
            </span>
          </div>
          <span className="text-[11px] text-emerald-700 font-semibold mt-1 inline-block">
            Across 24-hour horizon
          </span>
        </div>

        <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-xs">
          <span className="text-xs text-slate-500 font-medium block mb-1">Uncertainty Spread</span>
          <div className="flex items-baseline space-x-2">
            <span className="text-2xl font-bold text-slate-900">±{stats.avgSpreadMW.toFixed(1)}</span>
            <span className="text-xs text-slate-500">MW</span>
          </div>
          <span className="text-[11px] text-slate-500 font-medium mt-1 inline-flex items-center gap-1">
            <Layers className="h-3 w-3 text-amber-500" /> P90 - P10 Average
          </span>
        </div>
      </div>

      {/* Main ECharts Probabilistic Forecast Container */}
      <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-xs">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 mb-4 pb-3 border-b border-slate-100">
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-base font-semibold text-slate-900">
                24-Hour Probabilistic Generation Forecast
              </h2>
              <span className="px-2 py-0.5 bg-amber-50 text-amber-800 text-[10px] font-bold rounded border border-amber-200">
                Apache ECharts
              </span>
            </div>
            <p className="text-xs text-slate-500 mt-0.5">
              Quantile regression curves: P10 (conservative lower), P50 (expected median), and P90 (high exceedance)
            </p>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={onRegenerate}
              disabled={isGenerating}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-amber-500 hover:bg-amber-400 text-slate-950 text-xs font-bold rounded-lg transition disabled:opacity-50 shadow-xs cursor-pointer"
            >
              <RefreshCw className={`h-3.5 w-3.5 ${isGenerating ? 'animate-spin' : ''}`} />
              {isGenerating ? 'Generating...' : 'Regenerate Forecast'}
            </button>
          </div>
        </div>

        {sortedForecasts.length > 0 ? (
          <div className="w-full">
            <ReactECharts
              option={chartOption}
              style={{ height: '400px', width: '100%' }}
              notMerge={true}
              lazyUpdate={true}
            />
            <div className="flex flex-wrap items-center justify-between gap-2 pt-3 border-t border-slate-100 text-[11px] text-slate-500">
              <div className="flex items-center gap-4">
                <span className="flex items-center gap-1.5">
                  <span className="w-2.5 h-2.5 rounded-full bg-sky-600 inline-block"></span> Actual SCADA
                </span>
                <span className="flex items-center gap-1.5">
                  <span className="w-2.5 h-2.5 rounded-full bg-amber-600 inline-block"></span> P50 Median
                </span>
                <span className="flex items-center gap-1.5">
                  <span className="w-2.5 h-2.5 rounded-xs bg-amber-200 inline-block"></span> P10-P90 Uncertainty
                </span>
              </div>
              <div className="flex items-center gap-1 text-slate-600">
                <CheckCircle2 className="h-3.5 w-3.5 text-emerald-600" />
                <span>Model: <strong className="font-semibold">{stats.modelVersion}</strong></span>
              </div>
            </div>
          </div>
        ) : (
          <div className="py-16 text-center">
            <BarChart2 className="h-10 w-10 text-slate-300 mx-auto mb-3" />
            <p className="text-sm font-semibold text-slate-700">No Forecast Points Available</p>
            <p className="text-xs text-slate-500 mt-1 max-w-sm mx-auto">
              Generate an initial 24-hour probabilistic forecast curve based on historical SCADA and Open-Meteo telemetry.
            </p>
            <button
              onClick={onRegenerate}
              disabled={isGenerating}
              className="mt-4 inline-flex items-center gap-1.5 px-4 py-2 bg-amber-500 hover:bg-amber-400 text-slate-950 text-xs font-bold rounded-lg transition shadow-xs"
            >
              <RefreshCw className={`h-3.5 w-3.5 ${isGenerating ? 'animate-spin' : ''}`} />
              Generate Forecast Now
            </button>
          </div>
        )}
      </div>

      {/* Uncertainty & Scheduling Guidance */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-xs">
          <h3 className="text-xs font-semibold text-slate-800 flex items-center gap-1.5 mb-1.5">
            <span className="w-2 h-2 rounded-full bg-emerald-500"></span>
            P10 Conservative Baseline
          </h3>
          <p className="text-xs text-slate-600 leading-relaxed">
            90% probability of being exceeded. Ideal for non-firm commitment schedules and minimum contracted delivery guarantees.
          </p>
        </div>

        <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-xs">
          <h3 className="text-xs font-semibold text-slate-800 flex items-center gap-1.5 mb-1.5">
            <span className="w-2 h-2 rounded-full bg-amber-500"></span>
            P50 Expected Yield
          </h3>
          <p className="text-xs text-slate-600 leading-relaxed">
            Median projected output. Standard reference point for day-ahead dispatch scheduling and standard operational baseline.
          </p>
        </div>

        <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-xs">
          <h3 className="text-xs font-semibold text-slate-800 flex items-center gap-1.5 mb-1.5">
            <span className="w-2 h-2 rounded-full bg-sky-500"></span>
            P90 High-Exceedance Bound
          </h3>
          <p className="text-xs text-slate-600 leading-relaxed">
            10% probability of generation exceeding this level. Used for curtailment contingency planning and battery storage dispatch.
          </p>
        </div>
      </div>
    </div>
  );
};
