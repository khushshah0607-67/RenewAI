import React, { useState } from 'react';
import { PlantRisk, FinancialExposure, Plant } from '../types';
import { ShieldAlert, AlertTriangle, CheckCircle, IndianRupee, TrendingDown, Scale } from 'lucide-react';

interface RiskFinancialViewProps {
  plant: Plant;
  risk: PlantRisk | null;
  financial: FinancialExposure | null;
  onPriceChange: (newPrice: number) => void;
}

export const RiskFinancialView: React.FC<RiskFinancialViewProps> = ({
  plant,
  risk,
  financial,
  onPriceChange,
}) => {
  const [tariff, setTariff] = useState(financial?.energy_price_inr_per_mwh || 4500);

  const handleTariffChange = (val: number) => {
    setTariff(val);
    onPriceChange(val);
  };

  const getRiskColor = (level: string) => {
    switch (level) {
      case 'HIGH':
        return 'text-rose-700 bg-rose-50 border-rose-200';
      case 'MEDIUM':
        return 'text-amber-700 bg-amber-50 border-amber-200';
      default:
        return 'text-emerald-700 bg-emerald-50 border-emerald-200';
    }
  };

  const getBarColor = (score: number) => {
    if (score >= 60) return 'bg-rose-500';
    if (score >= 25) return 'bg-amber-500';
    return 'bg-emerald-500';
  };

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Risk Assessment Panel */}
        <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-xs">
          <div className="flex items-center justify-between mb-5">
            <div>
              <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
                <ShieldAlert className="h-5 w-5 text-amber-500" />
                Operational Risk Index
              </h2>
              <p className="text-xs text-slate-500">Rule-based multi-factor dispatch risk scoring</p>
            </div>
            {risk && (
              <span
                className={`text-xs font-bold px-3 py-1 rounded-full border ${getRiskColor(
                  risk.risk_level
                )}`}
              >
                {risk.risk_level} RISK ({risk.overall_score.toFixed(1)}/100)
              </span>
            )}
          </div>

          {risk ? (
            <div className="space-y-5">
              {/* Under-generation */}
              <div>
                <div className="flex justify-between text-xs mb-1.5">
                  <span className="font-semibold text-slate-800">Under-Generation Risk (45% weight)</span>
                  <span className="text-slate-600 font-mono">{risk.under_generation_risk.score.toFixed(1)} / 100</span>
                </div>
                <div className="w-full bg-slate-100 rounded-full h-2 overflow-hidden border border-slate-200/60">
                  <div
                    className={`h-2 rounded-full transition-all duration-500 ${getBarColor(
                      risk.under_generation_risk.score
                    )}`}
                    style={{ width: `${Math.min(100, risk.under_generation_risk.score)}%` }}
                  />
                </div>
                <p className="text-[11px] text-slate-500 mt-1">{risk.under_generation_risk.description}</p>
              </div>

              {/* Uncertainty Spread */}
              <div>
                <div className="flex justify-between text-xs mb-1.5">
                  <span className="font-semibold text-slate-800">Forecast Uncertainty Spread (35% weight)</span>
                  <span className="text-slate-600 font-mono">{risk.forecast_uncertainty_risk.score.toFixed(1)} / 100</span>
                </div>
                <div className="w-full bg-slate-100 rounded-full h-2 overflow-hidden border border-slate-200/60">
                  <div
                    className={`h-2 rounded-full transition-all duration-500 ${getBarColor(
                      risk.forecast_uncertainty_risk.score
                    )}`}
                    style={{ width: `${Math.min(100, risk.forecast_uncertainty_risk.score)}%` }}
                  />
                </div>
                <p className="text-[11px] text-slate-500 mt-1">{risk.forecast_uncertainty_risk.description}</p>
              </div>

              {/* Ramp Change */}
              <div>
                <div className="flex justify-between text-xs mb-1.5">
                  <span className="font-semibold text-slate-800">Ramp-Rate Step Risk (20% weight)</span>
                  <span className="text-slate-600 font-mono">{risk.ramp_change_risk.score.toFixed(1)} / 100</span>
                </div>
                <div className="w-full bg-slate-100 rounded-full h-2 overflow-hidden border border-slate-200/60">
                  <div
                    className={`h-2 rounded-full transition-all duration-500 ${getBarColor(
                      risk.ramp_change_risk.score
                    )}`}
                    style={{ width: `${Math.min(100, risk.ramp_change_risk.score)}%` }}
                  />
                </div>
                <p className="text-[11px] text-slate-500 mt-1">{risk.ramp_change_risk.description}</p>
              </div>
            </div>
          ) : (
            <div className="text-xs text-slate-500">Loading risk assessment...</div>
          )}
        </div>

        {/* Financial Exposure Panel */}
        <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-xs">
          <div className="flex items-center justify-between mb-5">
            <div>
              <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
                <IndianRupee className="h-5 w-5 text-amber-500" />
                Estimated Deviation Exposure
              </h2>
              <p className="text-xs text-slate-500">Financial exposure under Deviation Settlement Mechanism (DSM)</p>
            </div>
            <span className="text-xs font-semibold px-2.5 py-0.5 rounded bg-slate-100 text-slate-700 border border-slate-200">
              {financial?.exposure_label || 'ESTIMATED'}
            </span>
          </div>

          {financial ? (
            <div className="space-y-5">
              <div className="grid grid-cols-2 gap-4">
                <div className="bg-slate-50 border border-slate-200 rounded-lg p-4">
                  <span className="text-xs text-slate-500 block mb-1">Estimated Exposure</span>
                  <div className="text-2xl font-bold text-amber-600">
                    ₹{(financial.estimated_exposure_inr / 100000).toFixed(2)}
                    <span className="text-xs text-slate-500 font-normal ml-1">Lakh INR</span>
                  </div>
                  <span className="text-[11px] text-slate-500 mt-1 block">
                    (₹{financial.estimated_exposure_inr.toLocaleString()})
                  </span>
                </div>

                <div className="bg-slate-50 border border-slate-200 rounded-lg p-4">
                  <span className="text-xs text-slate-500 block mb-1">Estimated Deviation Volume</span>
                  <div className="text-2xl font-bold text-slate-900">
                    {financial.estimated_deviation_mwh.toFixed(1)}
                    <span className="text-xs text-slate-500 font-normal ml-1">MWh</span>
                  </div>
                  <span className="text-[11px] text-slate-500 mt-1 block">
                    Over 24-hour horizon
                  </span>
                </div>
              </div>

              {/* Interactive Tariff Setting */}
              <div className="pt-2 border-t border-slate-200">
                <div className="flex items-center justify-between text-xs mb-2">
                  <span className="font-semibold text-slate-700 flex items-center gap-1.5">
                    <Scale className="h-3.5 w-3.5 text-amber-500" />
                    DSM Tariff Rate (INR / MWh)
                  </span>
                  <span className="font-mono text-amber-700 font-bold">₹{tariff.toLocaleString()}</span>
                </div>
                <input
                  type="range"
                  min="2000"
                  max="10000"
                  step="250"
                  value={tariff}
                  onChange={(e) => handleTariffChange(Number(e.target.value))}
                  className="w-full accent-amber-500 cursor-pointer"
                />
                <div className="flex justify-between text-[10px] text-slate-500 mt-1">
                  <span>₹2,000 (Base)</span>
                  <span>₹4,500 (Regulated CERC)</span>
                  <span>₹10,000 (Peak Penalty)</span>
                </div>
              </div>

              <div className="bg-slate-50 rounded-lg p-3 text-[11px] text-slate-600 border border-slate-200">
                <span className="font-semibold text-slate-800">Methodology: </span>
                Exposure = (Shortfall MW + 0.5 × Spread MW) × 24h × Energy Price. Calculated using the CERC Renewable DSM framework.
              </div>
            </div>
          ) : (
            <div className="text-xs text-slate-500">Loading financial exposure...</div>
          )}
        </div>
      </div>
    </div>
  );
};
