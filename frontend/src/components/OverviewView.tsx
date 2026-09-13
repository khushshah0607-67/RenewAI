import React from 'react';
import {
  Plant,
  Forecast,
  HistoricalGeneration,
  WeatherData,
  PlantRisk,
  FinancialExposure,
  DecisionRecommendations,
  PlantExplanation,
  TabId,
} from '../types';
import {
  Zap,
  Sun,
  Wind,
  TrendingUp,
  ShieldAlert,
  IndianRupee,
  Layers,
  ArrowRight,
  Sliders,
  Clock,
  Sparkles,
  Info,
  CheckCircle2,
  AlertTriangle,
} from 'lucide-react';

interface OverviewViewProps {
  plant: Plant;
  forecasts: Forecast[];
  historical: HistoricalGeneration[];
  weather: WeatherData[];
  risk: PlantRisk | null;
  financial: FinancialExposure | null;
  recommendations: DecisionRecommendations | null;
  explanation: PlantExplanation | null;
  onNavigateTab: (tab: TabId) => void;
  onRegenerateForecast: () => void;
  isGenerating: boolean;
}

export const OverviewView: React.FC<OverviewViewProps> = ({
  plant,
  forecasts,
  historical,
  weather,
  risk,
  financial,
  recommendations,
  explanation,
  onNavigateTab,
  onRegenerateForecast,
  isGenerating,
}) => {
  const isSolar = plant.plant_type === 'SOLAR';
  const latestWeather = weather.length > 0 ? weather[weather.length - 1] : null;
  const latestGeneration = historical.length > 0 ? historical[historical.length - 1] : null;

  // Forecast summaries
  const p50s = forecasts.map((f) => f.p50_mw);
  const peakForecast = p50s.length > 0 ? Math.max(...p50s) : 0;
  const intervalHours =
    forecasts.length > 1
      ? Math.max(
          0.25,
          (new Date(forecasts[1].forecast_timestamp).getTime() -
            new Date(forecasts[0].forecast_timestamp).getTime()) /
            (1000 * 60 * 60)
        )
      : 0.25;
  const totalForecastMWh = p50s.reduce((a, b) => a + b * intervalHours, 0);

  // Top recommendations
  const topRecs = recommendations?.recommendations.slice(0, 3) || [];

  // Top factors
  const topFactors = explanation?.factors.slice(0, 3) || [];

  // Risk color mapping
  const getRiskBadge = (level: string) => {
    switch (level) {
      case 'HIGH':
        return 'bg-rose-100 text-rose-800 border-rose-200';
      case 'MEDIUM':
        return 'bg-amber-100 text-amber-800 border-amber-200';
      default:
        return 'bg-emerald-100 text-emerald-800 border-emerald-200';
    }
  };

  return (
    <div className="space-y-6">
      {/* Workflow Navigation Banner */}
      <div className="bg-gradient-to-r from-amber-500/10 via-sky-500/10 to-emerald-500/10 border border-slate-200 rounded-xl p-4 shadow-xs">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-3">
          <div>
            <div className="flex items-center gap-2">
              <span className="flex h-2 w-2 rounded-full bg-emerald-500"></span>
              <span className="text-xs font-bold uppercase tracking-wider text-slate-700">
                End-to-End Renewable Operations Workflow
              </span>
            </div>
            <p className="text-xs text-slate-600 mt-1">
              Integrated real-time pipeline: Plant → Weather → Historical SCADA → Forecast → Uncertainty → Risk → Financials → Actions → What-If
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-2 text-xs">
            <button
              onClick={() => onNavigateTab('forecast')}
              className="px-2.5 py-1 bg-white hover:bg-slate-50 border border-slate-200 rounded-md font-semibold text-slate-700 transition"
            >
              P10/P50/P90 Curve
            </button>
            <button
              onClick={() => onNavigateTab('risk')}
              className="px-2.5 py-1 bg-white hover:bg-slate-50 border border-slate-200 rounded-md font-semibold text-slate-700 transition"
            >
              Risk & Tariff
            </button>
            <button
              onClick={() => onNavigateTab('simulation')}
              className="px-2.5 py-1 bg-amber-500 hover:bg-amber-400 font-bold text-slate-950 rounded-md transition shadow-xs"
            >
              Run What-If
            </button>
          </div>
        </div>
      </div>

      {/* Grid: 1. Weather & Telemetry | 2. Historical & Forecast */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Step 1 & 2: Plant Context & Weather Telemetry */}
        <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-xs flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <div
                  className={`p-2 rounded-lg border ${
                    isSolar ? 'bg-amber-50 border-amber-200 text-amber-700' : 'bg-sky-50 border-sky-200 text-sky-700'
                  }`}
                >
                  {isSolar ? <Sun className="h-4 w-4" /> : <Wind className="h-4 w-4" />}
                </div>
                <div>
                  <h3 className="text-sm font-bold text-slate-900">Weather & Asset Telemetry</h3>
                  <span className="text-[11px] text-slate-500">
                    Open-Meteo feeds at ({plant.latitude.toFixed(2)}°, {plant.longitude.toFixed(2)}°)
                  </span>
                </div>
              </div>
              <button
                onClick={() => onNavigateTab('weather')}
                className="text-xs font-semibold text-amber-700 hover:text-amber-800 flex items-center gap-1"
              >
                Full telemetry <ArrowRight className="h-3 w-3" />
              </button>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5 mt-4">
              <div className="bg-slate-50 border border-slate-200 rounded-lg p-2.5">
                <span className="text-[10px] text-slate-500 uppercase font-semibold block">Solar Irradiance</span>
                <span className="text-base font-bold text-slate-900">
                  {latestWeather?.radiation_w_m2 != null ? `${latestWeather.radiation_w_m2.toFixed(0)}` : '--'}
                </span>
                <span className="text-[10px] text-slate-500 block">W/m² GHI</span>
              </div>

              <div className="bg-slate-50 border border-slate-200 rounded-lg p-2.5">
                <span className="text-[10px] text-slate-500 uppercase font-semibold block">Wind Velocity</span>
                <span className="text-base font-bold text-slate-900">
                  {latestWeather?.wind_speed_mps != null ? `${latestWeather.wind_speed_mps.toFixed(1)}` : '--'}
                </span>
                <span className="text-[10px] text-slate-500 block">m/s speed</span>
              </div>

              <div className="bg-slate-50 border border-slate-200 rounded-lg p-2.5">
                <span className="text-[10px] text-slate-500 uppercase font-semibold block">Ambient Temp</span>
                <span className="text-base font-bold text-slate-900">
                  {latestWeather?.temperature_c != null ? `${latestWeather.temperature_c.toFixed(1)}` : '--'}
                </span>
                <span className="text-[10px] text-slate-500 block">°C sensor</span>
              </div>

              <div className="bg-slate-50 border border-slate-200 rounded-lg p-2.5">
                <span className="text-[10px] text-slate-500 uppercase font-semibold block">Cloud Coverage</span>
                <span className="text-base font-bold text-slate-900">
                  {latestWeather?.cloud_cover_percent != null ? `${latestWeather.cloud_cover_percent}%` : '--'}
                </span>
                <span className="text-[10px] text-slate-500 block">attenuation</span>
              </div>
            </div>
          </div>

          <div className="mt-4 pt-3 border-t border-slate-100 flex items-center justify-between text-xs text-slate-600">
            <span className="flex items-center gap-1.5">
              <Clock className="h-3.5 w-3.5 text-slate-400" />
              Last telemetry point: {latestWeather ? new Date(latestWeather.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : 'Pending sync'}
            </span>
            <span className="font-semibold text-emerald-700 flex items-center gap-1">
              <CheckCircle2 className="h-3.5 w-3.5" /> Synchronized
            </span>
          </div>
        </div>

        {/* Step 3 & 4: Historical SCADA & Probabilistic Forecast */}
        <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-xs flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <div className="p-2 rounded-lg border bg-amber-50 border-amber-200 text-amber-700">
                  <TrendingUp className="h-4 w-4" />
                </div>
                <div>
                  <h3 className="text-sm font-bold text-slate-900">SCADA & 24h Horizon Forecast</h3>
                  <span className="text-[11px] text-slate-500">
                    Probabilistic P10/P50/P90 Quantiles
                  </span>
                </div>
              </div>
              <button
                onClick={() => onNavigateTab('forecast')}
                className="text-xs font-semibold text-amber-700 hover:text-amber-800 flex items-center gap-1"
              >
                Forecast charts <ArrowRight className="h-3 w-3" />
              </button>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-3 gap-2.5 mt-4">
              <div className="bg-slate-50 border border-slate-200 rounded-lg p-2.5">
                <span className="text-[10px] text-slate-500 uppercase font-semibold block">Last SCADA Output</span>
                <span className="text-base font-bold text-slate-900">
                  {latestGeneration ? `${latestGeneration.generation_mw.toFixed(1)} MW` : '0 MW'}
                </span>
                <span className="text-[10px] text-slate-500 block">
                  {plant.capacity_mw > 0 && latestGeneration
                    ? `${((latestGeneration.generation_mw / plant.capacity_mw) * 100).toFixed(0)}% nameplate`
                    : 'Awaiting data'}
                </span>
              </div>

              <div className="bg-slate-50 border border-slate-200 rounded-lg p-2.5">
                <span className="text-[10px] text-slate-500 uppercase font-semibold block">P50 Peak Forecast</span>
                <span className="text-base font-bold text-amber-600">
                  {peakForecast.toFixed(1)} MW
                </span>
                <span className="text-[10px] text-slate-500 block">
                  {((peakForecast / (plant.capacity_mw || 1)) * 100).toFixed(0)}% nameplate
                </span>
              </div>

              <div className="bg-slate-50 border border-slate-200 rounded-lg p-2.5 col-span-2 sm:col-span-1">
                <span className="text-[10px] text-slate-500 uppercase font-semibold block">Expected 24h Yield</span>
                <span className="text-base font-bold text-slate-900">
                  {totalForecastMWh > 1000
                    ? `${(totalForecastMWh / 1000).toFixed(2)} GWh`
                    : `${totalForecastMWh.toFixed(1)} MWh`}
                </span>
                <span className="text-[10px] text-emerald-700 font-semibold block">
                  {forecasts.length} time points
                </span>
              </div>
            </div>
          </div>

          <div className="mt-4 pt-3 border-t border-slate-100 flex items-center justify-between text-xs text-slate-600">
            <span className="flex items-center gap-1.5">
              <Layers className="h-3.5 w-3.5 text-slate-400" />
              Model: <strong className="font-semibold text-slate-800">{forecasts[0]?.model_version || 'persistence-baseline'}</strong>
            </span>
            <button
              onClick={onRegenerateForecast}
              disabled={isGenerating}
              className="text-xs text-amber-700 hover:text-amber-800 font-semibold cursor-pointer disabled:opacity-50"
            >
              {isGenerating ? 'Updating...' : 'Regenerate'}
            </button>
          </div>
        </div>
      </div>

      {/* Grid: 3. Risk & Financial | 4. Recommendations & Explainability */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Step 5 & 6: Risk & Financial Exposure */}
        <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-xs flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <div className="p-2 rounded-lg border bg-rose-50 border-rose-200 text-rose-700">
                  <ShieldAlert className="h-4 w-4" />
                </div>
                <div>
                  <h3 className="text-sm font-bold text-slate-900">Operational Risk & Financial Exposure</h3>
                  <span className="text-[11px] text-slate-500">
                    CERC Deviation Settlement Mechanism (DSM) Exposure
                  </span>
                </div>
              </div>
              <button
                onClick={() => onNavigateTab('risk')}
                className="text-xs font-semibold text-amber-700 hover:text-amber-800 flex items-center gap-1"
              >
                Deep-dive <ArrowRight className="h-3 w-3" />
              </button>
            </div>

            {risk && financial ? (
              <div className="space-y-3 mt-4">
                <div className="flex items-center justify-between p-3 bg-slate-50 border border-slate-200 rounded-lg">
                  <div>
                    <span className="text-xs text-slate-500 font-medium block">Overall Risk Index</span>
                    <div className="flex items-center gap-2 mt-0.5">
                      <span className="text-2xl font-black text-slate-900">
                        {risk.overall_score.toFixed(0)}
                      </span>
                      <span className="text-xs text-slate-500">/ 100</span>
                      <span
                        className={`px-2 py-0.5 rounded text-[10px] font-bold border ${getRiskBadge(
                          risk.risk_level
                        )}`}
                      >
                        {risk.risk_level} RISK
                      </span>
                    </div>
                  </div>

                  <div className="text-right">
                    <span className="text-xs text-slate-500 font-medium block">Est. Financial Exposure</span>
                    <div className="flex items-baseline justify-end gap-1 mt-0.5">
                      <span className="text-2xl font-black text-slate-900">
                        ₹{(financial.estimated_exposure_inr / 100000).toFixed(2)}
                      </span>
                      <span className="text-xs text-slate-500 font-semibold">Lakh</span>
                    </div>
                    <span className="text-[10px] text-amber-700 font-bold">
                      {financial.exposure_label || 'ESTIMATED'}
                    </span>
                  </div>
                </div>

                {/* Risk Components Progress */}
                <div className="grid grid-cols-3 gap-2 text-xs">
                  <div className="p-2 border border-slate-200 rounded-md">
                    <span className="text-[10px] text-slate-500 block truncate">Undergeneration</span>
                    <span className="font-bold text-slate-800">
                      {risk.under_generation_risk.score.toFixed(0)} ({risk.under_generation_risk.level})
                    </span>
                  </div>
                  <div className="p-2 border border-slate-200 rounded-md">
                    <span className="text-[10px] text-slate-500 block truncate">Uncertainty</span>
                    <span className="font-bold text-slate-800">
                      {risk.forecast_uncertainty_risk.score.toFixed(0)} ({risk.forecast_uncertainty_risk.level})
                    </span>
                  </div>
                  <div className="p-2 border border-slate-200 rounded-md">
                    <span className="text-[10px] text-slate-500 block truncate">Ramp Delta</span>
                    <span className="font-bold text-slate-800">
                      {risk.ramp_change_risk.score.toFixed(0)} ({risk.ramp_change_risk.level})
                    </span>
                  </div>
                </div>
              </div>
            ) : (
              <div className="p-6 text-center text-xs text-slate-500">
                Awaiting risk score calculation...
              </div>
            )}
          </div>

          <div className="mt-4 pt-3 border-t border-slate-100 text-[11px] text-slate-500 flex items-center gap-1.5">
            <Info className="h-3.5 w-3.5 text-slate-400 shrink-0" />
            <span>Tariff basis: ₹{financial?.energy_price_inr_per_mwh || 4500}/MWh · Incurred on schedule imbalance</span>
          </div>
        </div>

        {/* Step 7 & 8: Recommendations & Explainability */}
        <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-xs flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <div className="p-2 rounded-lg border bg-emerald-50 border-emerald-200 text-emerald-700">
                  <Sparkles className="h-4 w-4" />
                </div>
                <div>
                  <h3 className="text-sm font-bold text-slate-900">Decision Recommendations & Attribution</h3>
                  <span className="text-[11px] text-slate-500">
                    Operator Decision Support & Model Factor Attribution
                  </span>
                </div>
              </div>
              <button
                onClick={() => onNavigateTab('recommendations')}
                className="text-xs font-semibold text-amber-700 hover:text-amber-800 flex items-center gap-1"
              >
                View all <ArrowRight className="h-3 w-3" />
              </button>
            </div>

            <div className="space-y-2 mt-4">
              {topRecs.length > 0 ? (
                topRecs.map((rec, i) => (
                  <div
                    key={i}
                    className="p-2.5 bg-slate-50 border border-slate-200 rounded-lg flex items-start gap-2.5"
                  >
                    <span
                      className={`px-1.5 py-0.5 rounded text-[9px] font-bold mt-0.5 ${
                        rec.priority === 'HIGH'
                          ? 'bg-rose-100 text-rose-800'
                          : rec.priority === 'MEDIUM'
                          ? 'bg-amber-100 text-amber-800'
                          : 'bg-slate-200 text-slate-700'
                      }`}
                    >
                      {rec.priority}
                    </span>
                    <div className="flex-1 min-w-0">
                      <p className="text-xs font-bold text-slate-900 truncate">{rec.action}</p>
                      <p className="text-[11px] text-slate-600 line-clamp-1">{rec.explanation}</p>
                    </div>
                  </div>
                ))
              ) : (
                <p className="text-xs text-slate-500 py-3">No active operational alerts.</p>
              )}
            </div>

            {/* Explainability highlight */}
            {topFactors.length > 0 && (
              <div className="mt-3 pt-3 border-t border-slate-100">
                <span className="text-[11px] font-semibold text-slate-700 block mb-1">
                  Primary Drivers:
                </span>
                <div className="flex flex-wrap gap-1.5">
                  {topFactors.map((f, i) => (
                    <span
                      key={i}
                      className="px-2 py-0.5 bg-slate-100 text-slate-700 text-[10px] font-medium rounded border border-slate-200"
                    >
                      {f.factor_name}: {f.direction === 'positive' ? '↑' : '↓'} {f.importance != null ? `${(f.importance * 100).toFixed(0)}%` : ''}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>

          <div className="mt-4 pt-3 border-t border-slate-100 text-[11px] text-slate-500 flex items-center justify-between">
            <span>Operator retains final dispatch authority</span>
            <span className="text-slate-400 font-mono text-[10px]">
              {explanation?.explanation_version || 'prototype-v1'}
            </span>
          </div>
        </div>
      </div>

      {/* Step 9: What-If Simulation Sandbox Banner */}
      <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-xs flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="flex items-start sm:items-center gap-3">
          <div className="p-3 bg-amber-50 border border-amber-200 text-amber-700 rounded-xl">
            <Sliders className="h-6 w-6" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-slate-900">What-If Dispatch & Storage Simulation Sandbox</h3>
            <p className="text-xs text-slate-600 mt-0.5 max-w-2xl">
              Simulate operational counter-measures: adjust battery reserve target (MWh), toggle spinning backup, flexible industrial demand-response, and curtailment buffers to mitigate DSM penalties.
            </p>
          </div>
        </div>

        <button
          onClick={() => onNavigateTab('simulation')}
          className="px-4 py-2 bg-amber-500 hover:bg-amber-400 text-slate-950 text-xs font-bold rounded-lg transition shadow-xs flex items-center justify-center gap-2 shrink-0 cursor-pointer"
        >
          <span>Open Simulation Sandbox</span>
          <ArrowRight className="h-3.5 w-3.5" />
        </button>
      </div>
    </div>
  );
};
