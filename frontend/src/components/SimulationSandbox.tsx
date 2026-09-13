import React, { useState } from 'react';
import { Plant, SimulationResult } from '../types';
import { api } from '../services/api';
import { Sliders, Play, RotateCcw, BatteryCharging, Zap, ArrowRight, ShieldCheck, IndianRupee } from 'lucide-react';

interface SimulationSandboxProps {
  plant: Plant;
}

export const SimulationSandbox: React.FC<SimulationSandboxProps> = ({ plant }) => {
  const [batteryTarget, setBatteryTarget] = useState<number>(0);
  const [backupAvailable, setBackupAvailable] = useState<boolean>(false);
  const [flexibleLoadAvailable, setFlexibleLoadAvailable] = useState<boolean>(false);
  const [curtailmentAllowed, setCurtailmentAllowed] = useState<boolean>(false);
  const [customPrice, setCustomPrice] = useState<number>(4500);

  const [loading, setLoading] = useState<boolean>(false);
  const [result, setResult] = useState<SimulationResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleSimulate = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.runSimulation(plant.id, {
        battery_reserve_target: batteryTarget,
        backup_availability: backupAvailable,
        flexible_load_availability: flexibleLoadAvailable,
        curtailment_allowance: curtailmentAllowed,
        energy_price_inr_per_mwh: customPrice,
      });
      setResult(res);
    } catch (err: any) {
      setError(err.message || 'Simulation failed');
    } finally {
      setLoading(false);
    }
  };

  const handleReset = () => {
    setBatteryTarget(0);
    setBackupAvailable(false);
    setFlexibleLoadAvailable(false);
    setCurtailmentAllowed(false);
    setCustomPrice(4500);
    setResult(null);
  };

  return (
    <div className="space-y-6">
      <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-xs">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 mb-6">
          <div>
            <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
              <Sliders className="h-5 w-5 text-amber-500" />
              What-If Dispatch & Storage Simulation Sandbox
            </h2>
            <p className="text-xs text-slate-500">
              Evaluate how storage buffers, flexible demand, and auxiliary generation alter risk scores and financial exposure
            </p>
          </div>
          <button
            onClick={handleReset}
            className="inline-flex items-center space-x-1.5 text-xs text-slate-600 hover:text-slate-900 bg-white hover:bg-slate-50 px-3 py-1.5 rounded-lg border border-slate-300 shadow-xs transition w-fit"
          >
            <RotateCcw className="h-3.5 w-3.5" />
            <span>Reset Scenario</span>
          </button>
        </div>

        {/* Controls Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 pb-6 border-b border-slate-200">
          {/* Battery Reserve Slider */}
          <div className="space-y-2">
            <div className="flex justify-between text-xs">
              <span className="font-semibold text-slate-800 flex items-center gap-1.5">
                <BatteryCharging className="h-4 w-4 text-amber-500" />
                Battery Storage Reserve Target
              </span>
              <span className="font-mono text-amber-700 font-bold">{batteryTarget} MWh</span>
            </div>
            <input
              type="range"
              min="0"
              max={Math.round(plant.capacity_mw * 0.5)}
              step="5"
              value={batteryTarget}
              onChange={(e) => setBatteryTarget(Number(e.target.value))}
              className="w-full accent-amber-500 cursor-pointer"
            />
            <div className="flex justify-between text-[10px] text-slate-500">
              <span>0 MWh (No BESS)</span>
              <span>{Math.round(plant.capacity_mw * 0.25)} MWh (25%)</span>
              <span>{Math.round(plant.capacity_mw * 0.5)} MWh (50% max)</span>
            </div>
          </div>

          {/* Energy Tariff Slider */}
          <div className="space-y-2">
            <div className="flex justify-between text-xs">
              <span className="font-semibold text-slate-800 flex items-center gap-1.5">
                <IndianRupee className="h-4 w-4 text-amber-500" />
                Assumed Energy Price
              </span>
              <span className="font-mono text-amber-700 font-bold">₹{customPrice.toLocaleString()} / MWh</span>
            </div>
            <input
              type="range"
              min="2000"
              max="10000"
              step="250"
              value={customPrice}
              onChange={(e) => setCustomPrice(Number(e.target.value))}
              className="w-full accent-amber-500 cursor-pointer"
            />
            <div className="flex justify-between text-[10px] text-slate-500">
              <span>₹2,000 / MWh</span>
              <span>₹4,500 / MWh</span>
              <span>₹10,000 / MWh</span>
            </div>
          </div>

          {/* Toggles */}
          <div className="md:col-span-2 grid grid-cols-1 sm:grid-cols-3 gap-3">
            <label className="flex items-center space-x-3 bg-slate-50 border border-slate-200 rounded-lg p-3 cursor-pointer hover:bg-slate-100/70 transition">
              <input
                type="checkbox"
                checked={backupAvailable}
                onChange={(e) => setBackupAvailable(e.target.checked)}
                className="h-4 w-4 accent-amber-500 rounded cursor-pointer"
              />
              <span className="text-xs text-slate-700 font-medium">Backup Ready (12% risk cut)</span>
            </label>

            <label className="flex items-center space-x-3 bg-slate-50 border border-slate-200 rounded-lg p-3 cursor-pointer hover:bg-slate-100/70 transition">
              <input
                type="checkbox"
                checked={flexibleLoadAvailable}
                onChange={(e) => setFlexibleLoadAvailable(e.target.checked)}
                className="h-4 w-4 accent-amber-500 rounded cursor-pointer"
              />
              <span className="text-xs text-slate-700 font-medium">Flexible Load (10% risk cut)</span>
            </label>

            <label className="flex items-center space-x-3 bg-slate-50 border border-slate-200 rounded-lg p-3 cursor-pointer hover:bg-slate-100/70 transition">
              <input
                type="checkbox"
                checked={curtailmentAllowed}
                onChange={(e) => setCurtailmentAllowed(e.target.checked)}
                className="h-4 w-4 accent-amber-500 rounded cursor-pointer"
              />
              <span className="text-xs text-slate-700 font-medium">Curtailment Allowed (4% cut)</span>
            </label>
          </div>
        </div>

        {/* Action Button */}
        <div className="pt-4 flex items-center justify-between">
          <span className="text-xs text-slate-500">
            In-memory simulation operates safely without affecting active dispatch schedules.
          </span>
          <button
            id="run-simulation-btn"
            onClick={handleSimulate}
            disabled={loading}
            className="inline-flex items-center space-x-2 bg-amber-500 hover:bg-amber-400 disabled:opacity-50 text-slate-950 text-xs font-bold px-5 py-2.5 rounded-lg transition shadow-xs"
          >
            <Play className={`h-3.5 w-3.5 fill-current ${loading ? 'animate-spin' : ''}`} />
            <span>{loading ? 'Evaluating Scenario...' : 'Execute What-If Simulation'}</span>
          </button>
        </div>

        {error && (
          <div className="mt-4 p-3 bg-rose-50 border border-rose-200 rounded-lg text-xs text-rose-700">
            {error}
          </div>
        )}
      </div>

      {/* Simulation Results Output */}
      {result && (
        <div className="bg-white border border-slate-200 rounded-xl p-6 space-y-6 shadow-xs">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
              <ShieldCheck className="h-5 w-5 text-emerald-600" />
              Scenario Impact Analysis
            </h3>
            <span className="text-xs text-slate-500 font-mono">
              Simulated at {new Date(result.generated_at).toLocaleTimeString()}
            </span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {/* Risk Score Delta */}
            <div className="bg-slate-50 border border-slate-200 rounded-xl p-4">
              <span className="text-xs text-slate-500 block mb-2 font-medium">Overall Risk Score Delta</span>
              <div className="flex items-center space-x-3">
                <div className="text-xl font-bold text-slate-400">
                  {result.baseline_risk_score.toFixed(1)}
                  <span className="text-[10px] block font-normal text-slate-500">{result.baseline_risk_level}</span>
                </div>
                <ArrowRight className="h-4 w-4 text-slate-400 shrink-0" />
                <div className="text-2xl font-bold text-emerald-600">
                  {result.simulated_risk_score.toFixed(1)}
                  <span className="text-[10px] block font-semibold text-emerald-700">{result.simulated_risk_level}</span>
                </div>
              </div>
              <div className="text-xs font-semibold text-emerald-700 mt-2">
                {result.risk_change <= 0 ? `${result.risk_change} points reduction` : `+${result.risk_change} points`}
              </div>
            </div>

            {/* Financial Exposure Delta */}
            <div className="bg-slate-50 border border-slate-200 rounded-xl p-4">
              <span className="text-xs text-slate-500 block mb-2 font-medium">Financial Exposure Delta</span>
              <div className="flex items-center space-x-3">
                <div className="text-xl font-bold text-slate-400">
                  ₹{(result.baseline_estimated_exposure_inr / 100000).toFixed(2)}L
                </div>
                <ArrowRight className="h-4 w-4 text-slate-400 shrink-0" />
                <div className="text-2xl font-bold text-amber-600">
                  ₹{(result.simulated_estimated_exposure_inr / 100000).toFixed(2)}L
                </div>
              </div>
              <div className="text-xs font-semibold text-emerald-700 mt-2">
                ₹{Math.abs(result.exposure_change).toLocaleString()} savings under scenario
              </div>
            </div>
          </div>

          {/* Scenario Recommendations */}
          <div>
            <h4 className="text-xs font-semibold text-slate-700 uppercase tracking-wider mb-3">
              Scenario-Adjusted Recommendations
            </h4>
            <div className="space-y-2">
              {result.recommendations.map((rec, i) => (
                <div
                  key={i}
                  className="bg-slate-50 border border-slate-200 rounded-lg p-3 text-xs text-slate-700"
                >
                  <div className="flex items-center space-x-2 mb-1">
                    <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-amber-50 text-amber-800 border border-amber-200">
                      {rec.priority}
                    </span>
                    <span className="font-semibold text-slate-900">{rec.action}</span>
                  </div>
                  <p className="text-slate-500 text-[11px]">{rec.explanation}</p>
                </div>
              ))}
            </div>
          </div>

          {result.simulation_note && (
            <div className="pt-2 border-t border-slate-100 text-[11px] text-slate-500 italic">
              * {result.simulation_note}
            </div>
          )}
        </div>
      )}
    </div>
  );
};
