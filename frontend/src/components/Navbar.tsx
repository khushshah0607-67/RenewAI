import React from 'react';
import { Sun, Wind, Plus, RefreshCw, Layers, MapPin, BarChart3, CloudSun, ShieldAlert, Sparkles, Sliders, Activity } from 'lucide-react';
import { Plant, TabId } from '../types';

interface NavbarProps {
  plants: Plant[];
  selectedPlant: Plant | null;
  onSelectPlant: (plant: Plant) => void;
  onOpenNewPlant: () => void;
  activeTab: TabId;
  onSelectTab: (tab: TabId) => void;
  onRefresh: () => void;
  isRefreshing: boolean;
}

export const Navbar: React.FC<NavbarProps> = ({
  plants,
  selectedPlant,
  onSelectPlant,
  onOpenNewPlant,
  activeTab,
  onSelectTab,
  onRefresh,
  isRefreshing,
}) => {
  const tabs: { id: TabId; label: string; icon: React.FC<{ className?: string }> }[] = [
    { id: 'overview', label: 'Operations Overview', icon: Activity },
    { id: 'forecast', label: 'P10/P50/P90 Forecast', icon: BarChart3 },
    { id: 'historical', label: 'Historical SCADA', icon: Layers },
    { id: 'weather', label: 'Weather Telemetry', icon: CloudSun },
    { id: 'risk', label: 'Risk & Tariff', icon: ShieldAlert },
    { id: 'recommendations', label: 'Recommendations & Explain', icon: Sparkles },
    { id: 'simulation', label: 'What-If Sandbox', icon: Sliders },
    { id: 'plants', label: 'Plant Fleet & Map', icon: MapPin },
  ];

  return (
    <header className="border-b border-slate-200 bg-white/95 backdrop-blur sticky top-0 z-30 shadow-xs">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo & Title */}
          <div className="flex items-center space-x-3">
            <div
              onClick={() => onSelectTab('overview')}
              className="h-10 w-10 rounded-xl bg-amber-50 border border-amber-200 flex items-center justify-center text-amber-600 cursor-pointer hover:bg-amber-100 transition"
              title="RenewAI Dashboard"
            >
              <Sun className="h-5 w-5 animate-pulse" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <span
                  onClick={() => onSelectTab('overview')}
                  className="font-bold text-lg text-slate-900 tracking-tight cursor-pointer"
                >
                  RenewAI
                </span>
                <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-emerald-50 border border-emerald-200 text-emerald-700 flex items-center gap-1">
                  <span className="h-1.5 w-1.5 rounded-full bg-emerald-500"></span> Live Telemetry
                </span>
              </div>
              <p className="text-xs text-slate-500 hidden sm:block">
                Solar & Wind Renewable Energy Forecasting & Risk Intelligence
              </p>
            </div>
          </div>

          {/* Plant Selector & Controls */}
          <div className="flex items-center space-x-2 sm:space-x-3">
            <div className="relative flex items-center">
              <select
                id="plant-select"
                aria-label="Select Renewable Plant"
                value={selectedPlant?.id || ''}
                onChange={(e) => {
                  const p = plants.find((plant) => plant.id === Number(e.target.value));
                  if (p) onSelectPlant(p);
                }}
                className="bg-white border border-slate-300 text-slate-800 text-xs sm:text-sm rounded-lg px-2.5 sm:px-3 py-1.5 pr-7 sm:pr-8 focus:ring-2 focus:ring-amber-500/30 focus:border-amber-500 focus:outline-none cursor-pointer shadow-xs max-w-[160px] sm:max-w-xs truncate"
              >
                {plants.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name} ({p.capacity_mw} MW - {p.plant_type})
                  </option>
                ))}
              </select>
            </div>

            <button
              id="new-plant-btn"
              onClick={onOpenNewPlant}
              className="inline-flex items-center space-x-1 bg-white hover:bg-slate-50 text-slate-700 text-xs font-semibold px-2.5 sm:px-3 py-1.5 rounded-lg border border-slate-300 shadow-xs transition cursor-pointer"
              title="Add New Plant"
            >
              <Plus className="h-3.5 w-3.5 text-amber-600" />
              <span className="hidden md:inline">Add Plant</span>
            </button>

            <button
              id="refresh-btn"
              onClick={onRefresh}
              disabled={isRefreshing}
              className="p-1.5 text-slate-600 hover:text-slate-900 bg-white hover:bg-slate-50 border border-slate-300 rounded-lg shadow-xs transition cursor-pointer disabled:opacity-50"
              title="Refresh Telemetry & Forecasts"
            >
              <RefreshCw className={`h-4 w-4 ${isRefreshing ? 'animate-spin text-amber-600' : ''}`} />
            </button>
          </div>
        </div>

        {/* Navigation Tabs */}
        <div className="flex space-x-1 sm:space-x-2 overflow-x-auto py-2 scrollbar-none border-t border-slate-100">
          {tabs.map((tab) => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                id={`tab-${tab.id}`}
                onClick={() => onSelectTab(tab.id)}
                className={`text-xs font-semibold px-3 py-1.5 rounded-lg transition flex items-center gap-1.5 whitespace-nowrap cursor-pointer ${
                  isActive
                    ? 'bg-amber-50 text-amber-800 border border-amber-300 shadow-xs'
                    : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100 border border-transparent'
                }`}
              >
                <Icon className={`h-3.5 w-3.5 ${isActive ? 'text-amber-600' : 'text-slate-400'}`} />
                <span>{tab.label}</span>
              </button>
            );
          })}
        </div>
      </div>
    </header>
  );
};
