import React from 'react';
import { Sun, Wind, MapPin, Zap, Clock, Upload, Cpu, Edit, Layers } from 'lucide-react';
import { Plant } from '../types';

interface PlantHeaderProps {
  plant: Plant;
  onOpenUpload: () => void;
  onOpenEdit: () => void;
  onRegenerateForecast: () => void;
  isGenerating: boolean;
}

export const PlantHeader: React.FC<PlantHeaderProps> = ({
  plant,
  onOpenUpload,
  onOpenEdit,
  onRegenerateForecast,
  isGenerating,
}) => {
  const isSolar = plant.plant_type === 'SOLAR';

  return (
    <div className="bg-white border border-slate-200 rounded-xl p-5 mb-6 shadow-xs">
      <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
        {/* Plant Metadata */}
        <div>
          <div className="flex items-center space-x-3 mb-1">
            <span
              className={`p-2.5 rounded-xl flex items-center justify-center ${
                isSolar
                  ? 'bg-amber-50 text-amber-600 border border-amber-200'
                  : 'bg-sky-50 text-sky-600 border border-sky-200'
              }`}
            >
              {isSolar ? <Sun className="h-5 w-5" /> : <Wind className="h-5 w-5" />}
            </span>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-xl font-bold text-slate-900">{plant.name}</h1>
                <span
                  className={`text-[10px] font-bold px-2 py-0.5 rounded-full border ${
                    isSolar
                      ? 'bg-amber-50 text-amber-800 border-amber-200'
                      : 'bg-sky-50 text-sky-800 border-sky-200'
                  }`}
                >
                  {plant.plant_type}
                </span>
              </div>

              <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-slate-500 mt-1">
                <span className="flex items-center gap-1 font-semibold text-slate-700">
                  <Zap className="h-3.5 w-3.5 text-amber-500" />
                  <span>{plant.capacity_mw.toLocaleString()} MW</span> Nameplate
                </span>
                <span className="flex items-center gap-1">
                  <MapPin className="h-3.5 w-3.5 text-slate-400" />
                  {plant.latitude.toFixed(3)}°N, {plant.longitude.toFixed(3)}°E
                </span>
                <span className="flex items-center gap-1">
                  <Clock className="h-3.5 w-3.5 text-slate-400" />
                  {plant.timezone}
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Action Controls */}
        <div className="flex flex-wrap items-center gap-2 sm:gap-2.5">
          <button
            onClick={onOpenEdit}
            className="inline-flex items-center space-x-1.5 bg-white hover:bg-slate-50 text-slate-700 text-xs font-semibold px-3 py-2 rounded-lg border border-slate-300 shadow-xs transition cursor-pointer"
            title="Edit plant configurations"
          >
            <Edit className="h-3.5 w-3.5 text-slate-500" />
            <span>Edit Asset</span>
          </button>

          <button
            id="upload-csv-btn"
            onClick={onOpenUpload}
            className="inline-flex items-center space-x-1.5 bg-white hover:bg-slate-50 text-slate-700 text-xs font-semibold px-3.5 py-2 rounded-lg border border-slate-300 shadow-xs transition cursor-pointer"
          >
            <Upload className="h-3.5 w-3.5 text-slate-500" />
            <span>Upload SCADA CSV</span>
          </button>

          <button
            id="regenerate-forecast-btn"
            onClick={onRegenerateForecast}
            disabled={isGenerating}
            className="inline-flex items-center space-x-2 bg-amber-500 hover:bg-amber-400 disabled:opacity-50 text-slate-950 text-xs font-bold px-4 py-2 rounded-lg transition shadow-xs cursor-pointer"
          >
            <Cpu className={`h-3.5 w-3.5 ${isGenerating ? 'animate-spin' : ''}`} />
            <span>{isGenerating ? 'Computing Forecast...' : 'Run Forecast Engine'}</span>
          </button>
        </div>
      </div>
    </div>
  );
};
