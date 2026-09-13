import React from 'react';
import { DecisionRecommendations, PlantExplanation, Plant } from '../types';
import {
  Lightbulb,
  Info,
  AlertCircle,
  Sparkles,
  TrendingUp,
  TrendingDown,
  ShieldCheck,
  HelpCircle,
  Clock,
  Layers,
} from 'lucide-react';

interface RecommendationExplainViewProps {
  plant: Plant;
  recommendations: DecisionRecommendations | null;
  explanation: PlantExplanation | null;
}

export const RecommendationExplainView: React.FC<RecommendationExplainViewProps> = ({
  plant,
  recommendations,
  explanation,
}) => {
  const getPriorityBadge = (priority: string) => {
    switch (priority) {
      case 'HIGH':
        return 'bg-rose-50 text-rose-700 border-rose-200';
      case 'MEDIUM':
        return 'bg-amber-50 text-amber-700 border-amber-200';
      default:
        return 'bg-emerald-50 text-emerald-700 border-emerald-200';
    }
  };

  return (
    <div className="space-y-6">
      {/* Operator Advisory Authority Banner */}
      <div className="p-4 bg-amber-50/70 border border-amber-200 rounded-xl flex items-start gap-3">
        <ShieldCheck className="h-5 w-5 text-amber-600 shrink-0 mt-0.5" />
        <div className="text-xs text-amber-900">
          <p className="font-bold">Licensed Operator Authority Notice</p>
          <p className="mt-0.5 text-amber-800 leading-relaxed">
            RenewAI operational recommendations and attribution metrics provide algorithmic decision support for day-ahead scheduling and real-time deviation mitigation. Licensed dispatch operators and scheduling managers retain ultimate authority and operational responsibility under regional grid codes (CERC/SLDC).
          </p>
        </div>
      </div>

      {/* Operational Recommendations Section */}
      <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-xs">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 mb-4">
          <div>
            <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
              <Lightbulb className="h-5 w-5 text-amber-500" />
              Operational Decision Support Recommendations
            </h2>
            <p className="text-xs text-slate-500">
              Targeted mitigation actions derived from probabilistic shortfall risk, ramp delta, and financial exposure
            </p>
          </div>
          <span className="text-xs font-semibold px-2.5 py-1 rounded bg-slate-100 text-slate-700 border border-slate-200 w-fit">
            {recommendations?.recommendations.length || 0} Actionable Advisories
          </span>
        </div>

        {recommendations && recommendations.recommendations.length > 0 ? (
          <div className="space-y-3">
            {recommendations.recommendations.map((rec, index) => (
              <div
                key={index}
                className="bg-slate-50 border border-slate-200 rounded-xl p-4 hover:border-slate-300 transition"
              >
                <div className="flex flex-wrap items-center justify-between gap-2 mb-2">
                  <div className="flex items-center space-x-2">
                    <span
                      className={`text-[10px] font-bold px-2 py-0.5 rounded border uppercase tracking-wider ${getPriorityBadge(
                        rec.priority
                      )}`}
                    >
                      {rec.priority} Priority
                    </span>
                    <h3 className="text-sm font-bold text-slate-900">{rec.action}</h3>
                  </div>
                  <span className="text-xs text-slate-500 font-medium">
                    Severity: <strong className="text-slate-700">{rec.severity}</strong>
                  </span>
                </div>

                <p className="text-xs text-slate-700 mb-2.5 leading-relaxed">{rec.explanation}</p>

                {rec.rationale && (
                  <div className="flex items-start gap-1.5 text-[11px] text-amber-900 bg-amber-50/80 rounded-lg p-2.5 border border-amber-200">
                    <Info className="h-3.5 w-3.5 mt-0.5 shrink-0 text-amber-600" />
                    <span>
                      <strong className="text-amber-900 font-semibold">Operational Rationale:</strong>{' '}
                      {rec.rationale}
                    </span>
                  </div>
                )}
              </div>
            ))}
          </div>
        ) : (
          <div className="py-8 text-center text-xs text-slate-500">
            No critical operational interventions required at current forecast risk levels.
          </div>
        )}
      </div>

      {/* Model Explainability & Factor Attribution */}
      <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-xs">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 mb-4">
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
                <Sparkles className="h-5 w-5 text-amber-500" />
                Forecast Factor Attribution & Explainability
              </h2>
              <span className="px-2 py-0.5 bg-slate-100 text-slate-600 text-[10px] font-bold rounded border border-slate-200">
                Decision Support Attribution
              </span>
            </div>
            <p className="text-xs text-slate-500 mt-0.5">
              Quantifies how meteorological telemetry and historical patterns contribute to current forecast variance
            </p>
          </div>
          {explanation && (
            <div className="flex items-center gap-2">
              <span className="text-xs font-mono px-2.5 py-1 rounded bg-slate-100 text-slate-600 border border-slate-200">
                Layer: {explanation.explanation_version}
              </span>
            </div>
          )}
        </div>

        {explanation ? (
          <div>
            {/* Forecast Summary Card */}
            <div className="bg-slate-50 rounded-xl p-4 mb-4 border border-slate-200 text-xs text-slate-700">
              <div className="flex items-center gap-1.5 font-bold text-slate-900 mb-1">
                <Info className="h-4 w-4 text-amber-500" />
                <span>Forecast Synthesis Summary:</span>
              </div>
              <p className="leading-relaxed text-slate-700">{explanation.forecast_summary}</p>
            </div>

            {/* Non-ML Prototype Disclaimer Note */}
            {explanation.prototype_note && (
              <div className="mb-5 p-3 bg-sky-50/60 border border-sky-200 rounded-lg flex items-start gap-2 text-xs text-sky-900">
                <Info className="h-4 w-4 text-sky-600 shrink-0 mt-0.5" />
                <div>
                  <span className="font-semibold">Attribution Framework Note: </span>
                  <span className="text-sky-800">{explanation.prototype_note}</span>
                </div>
              </div>
            )}

            {/* Factors List */}
            <div className="space-y-4">
              {explanation.factors.map((factor, idx) => {
                const importancePct =
                  factor.importance != null ? Math.round(factor.importance * 100) : null;
                const isPositive = factor.direction === 'positive';

                return (
                  <div
                    key={idx}
                    className="bg-slate-50 border border-slate-200 rounded-xl p-4 hover:border-slate-300 transition"
                  >
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-2">
                      <div className="flex items-center space-x-2">
                        <div
                          className={`p-1.5 rounded-lg border ${
                            isPositive
                              ? 'bg-emerald-50 border-emerald-200 text-emerald-600'
                              : 'bg-rose-50 border-rose-200 text-rose-600'
                          }`}
                        >
                          {isPositive ? (
                            <TrendingUp className="h-4 w-4" />
                          ) : (
                            <TrendingDown className="h-4 w-4" />
                          )}
                        </div>
                        <div>
                          <span className="text-xs font-bold text-slate-900 capitalize block">
                            {factor.factor_name.replace(/_/g, ' ')}
                          </span>
                          <span className="text-[10px] text-slate-500">
                            Influence: {isPositive ? 'Increasing generation' : 'Suppressing generation'}
                          </span>
                        </div>
                      </div>

                      <div className="flex items-center gap-3 text-xs">
                        {importancePct != null && (
                          <div className="text-right">
                            <span className="text-[10px] text-slate-500 block">Relative Weight</span>
                            <span className="font-mono font-bold text-slate-800">
                              {importancePct}%
                            </span>
                          </div>
                        )}
                        {factor.contribution != null && (
                          <div className="text-right">
                            <span className="text-[10px] text-slate-500 block">Contribution</span>
                            <span
                              className={`font-mono font-bold px-2 py-0.5 rounded text-[11px] border inline-block ${
                                isPositive
                                  ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                                  : 'bg-rose-50 text-rose-700 border-rose-200'
                              }`}
                            >
                              {factor.contribution > 0
                                ? `+${factor.contribution.toFixed(2)}`
                                : factor.contribution.toFixed(2)}
                            </span>
                          </div>
                        )}
                        <span className="text-[10px] uppercase font-bold px-2 py-0.5 bg-slate-200 text-slate-700 rounded">
                          {factor.source}
                        </span>
                      </div>
                    </div>

                    {importancePct != null && (
                      <div className="w-full bg-slate-200 rounded-full h-1.5 mb-2 overflow-hidden">
                        <div
                          className={`h-1.5 rounded-full ${
                            isPositive ? 'bg-emerald-500' : 'bg-rose-500'
                          }`}
                          style={{ width: `${Math.min(100, Math.max(5, importancePct))}%` }}
                        />
                      </div>
                    )}

                    <p className="text-xs text-slate-600 leading-relaxed">{factor.explanation}</p>
                  </div>
                );
              })}
            </div>
          </div>
        ) : (
          <div className="py-8 text-center text-xs text-slate-500">
            Awaiting model explainability attribution run...
          </div>
        )}
      </div>
    </div>
  );
};
