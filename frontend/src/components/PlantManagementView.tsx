import React, { useState } from 'react';
import { Plant, PlantType } from '../types';
import { PlantMap } from './PlantMap';
import {
  Plus,
  Edit,
  Trash2,
  Sun,
  Wind,
  MapPin,
  Clock,
  Zap,
  Search,
  CheckCircle,
  ExternalLink,
} from 'lucide-react';

interface PlantManagementViewProps {
  plants: Plant[];
  selectedPlant: Plant | null;
  onSelectPlant: (plant: Plant) => void;
  onOpenNewPlant: () => void;
  onOpenEditPlant: (plant: Plant) => void;
  onOpenDeletePlant: (plant: Plant) => void;
}

export const PlantManagementView: React.FC<PlantManagementViewProps> = ({
  plants,
  selectedPlant,
  onSelectPlant,
  onOpenNewPlant,
  onOpenEditPlant,
  onOpenDeletePlant,
}) => {
  const [filterType, setFilterType] = useState<'ALL' | PlantType>('ALL');
  const [search, setSearch] = useState('');

  const filteredPlants = plants.filter((p) => {
    const matchesType = filterType === 'ALL' || p.plant_type === filterType;
    const matchesSearch =
      p.name.toLowerCase().includes(search.toLowerCase()) ||
      p.timezone.toLowerCase().includes(search.toLowerCase());
    return matchesType && matchesSearch;
  });

  const totalCapacity = plants.reduce((sum, p) => sum + p.capacity_mw, 0);
  const solarCount = plants.filter((p) => p.plant_type === 'SOLAR').length;
  const windCount = plants.filter((p) => p.plant_type === 'WIND').length;

  return (
    <div className="space-y-6">
      {/* Top metrics */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-xs">
          <span className="text-xs text-slate-500 font-medium block mb-1">Total Monitored Plants</span>
          <div className="flex items-baseline space-x-2">
            <span className="text-2xl font-bold text-slate-900">{plants.length}</span>
            <span className="text-xs text-slate-500">assets</span>
          </div>
          <span className="text-[11px] text-slate-500 mt-1 inline-block">
            {solarCount} Solar · {windCount} Wind
          </span>
        </div>

        <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-xs">
          <span className="text-xs text-slate-500 font-medium block mb-1">Total Fleet Capacity</span>
          <div className="flex items-baseline space-x-2">
            <span className="text-2xl font-bold text-slate-900">{totalCapacity.toFixed(1)}</span>
            <span className="text-xs text-slate-500">MW</span>
          </div>
          <span className="text-[11px] text-amber-700 font-semibold mt-1 inline-block">
            {(totalCapacity / 1000).toFixed(2)} GW aggregate nameplate
          </span>
        </div>

        <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-xs">
          <span className="text-xs text-slate-500 font-medium block mb-1">Active Selected Plant</span>
          <div className="flex items-baseline space-x-2">
            <span className="text-base font-bold text-slate-900 truncate">
              {selectedPlant ? selectedPlant.name : 'None'}
            </span>
          </div>
          <span className="text-[11px] text-emerald-700 font-semibold mt-1 inline-block">
            {selectedPlant ? `${selectedPlant.capacity_mw} MW (${selectedPlant.plant_type})` : 'Select a plant'}
          </span>
        </div>

        <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-xs flex flex-col justify-between">
          <div>
            <span className="text-xs text-slate-500 font-medium block mb-1">Quick Action</span>
            <span className="text-xs text-slate-600">Register new asset</span>
          </div>
          <button
            onClick={onOpenNewPlant}
            className="mt-2 w-full py-1.5 bg-amber-500 hover:bg-amber-400 text-slate-950 text-xs font-bold rounded-lg transition flex items-center justify-center gap-1.5 shadow-xs cursor-pointer"
          >
            <Plus className="h-3.5 w-3.5" />
            <span>Add Renewable Plant</span>
          </button>
        </div>
      </div>

      {/* Geospatial Map Container */}
      <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-xs">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 mb-3">
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-base font-semibold text-slate-900">Fleet Geospatial Distribution</h2>
              <span className="px-2 py-0.5 bg-slate-100 text-slate-600 text-[10px] font-bold rounded border border-slate-200">
                Leaflet + OpenStreetMap
              </span>
            </div>
            <p className="text-xs text-slate-500">
              Interactive plant locations linked to localized Open-Meteo meteorological telemetry feeds
            </p>
          </div>
          {selectedPlant && (
            <div className="text-xs text-slate-600 flex items-center gap-1">
              <MapPin className="h-3.5 w-3.5 text-amber-500" />
              <span>
                Focused on: <strong className="text-slate-800">{selectedPlant.name}</strong> ({selectedPlant.latitude.toFixed(3)}°, {selectedPlant.longitude.toFixed(3)}°)
              </span>
            </div>
          )}
        </div>

        <PlantMap
          plant={selectedPlant}
          plants={plants}
          height="380px"
          onSelectPlant={onSelectPlant}
        />
      </div>

      {/* Plant Management Table / Cards */}
      <div className="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-xs">
        <div className="p-4 border-b border-slate-100 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
          <div className="flex items-center gap-3">
            <h3 className="text-sm font-semibold text-slate-900">Registered Plant Directory</h3>
            <div className="flex rounded-lg bg-slate-100 border border-slate-200 p-0.5 text-xs">
              {(['ALL', 'SOLAR', 'WIND'] as const).map((type) => (
                <button
                  key={type}
                  onClick={() => setFilterType(type)}
                  className={`px-2.5 py-1 rounded-md font-medium transition cursor-pointer ${
                    filterType === type
                      ? 'bg-white text-slate-900 shadow-xs'
                      : 'text-slate-600 hover:text-slate-900'
                  }`}
                >
                  {type}
                </button>
              ))}
            </div>
          </div>

          <div className="flex items-center gap-2">
            <div className="relative">
              <Search className="h-3.5 w-3.5 text-slate-400 absolute left-2.5 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                placeholder="Search by name or timezone..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="pl-8 pr-3 py-1.5 bg-slate-50 border border-slate-200 rounded-lg text-xs text-slate-800 focus:outline-none focus:ring-1 focus:ring-amber-500 w-52 sm:w-64"
              />
            </div>
          </div>
        </div>

        <div className="divide-y divide-slate-100">
          {filteredPlants.length > 0 ? (
            filteredPlants.map((plant) => {
              const isSelected = selectedPlant?.id === plant.id;
              const isSolar = plant.plant_type === 'SOLAR';

              return (
                <div
                  key={plant.id}
                  className={`p-4 transition flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 ${
                    isSelected ? 'bg-amber-50/40' : 'hover:bg-slate-50'
                  }`}
                >
                  <div className="flex items-start sm:items-center gap-3">
                    <div
                      className={`p-2.5 rounded-xl border flex items-center justify-center shrink-0 ${
                        isSolar
                          ? 'bg-amber-50 border-amber-200 text-amber-700'
                          : 'bg-sky-50 border-sky-200 text-sky-700'
                      }`}
                    >
                      {isSolar ? <Sun className="h-5 w-5" /> : <Wind className="h-5 w-5" />}
                    </div>

                    <div>
                      <div className="flex items-center gap-2">
                        <h4 className="text-sm font-bold text-slate-900">{plant.name}</h4>
                        {isSelected && (
                          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold bg-amber-100 text-amber-800 border border-amber-200">
                            <CheckCircle className="h-3 w-3" /> Active Context
                          </span>
                        )}
                      </div>

                      <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-slate-500 mt-1">
                        <span className="inline-flex items-center gap-1 font-semibold text-slate-700">
                          <Zap className="h-3.5 w-3.5 text-amber-500" />
                          {plant.capacity_mw} MW ({plant.plant_type})
                        </span>
                        <span className="inline-flex items-center gap-1">
                          <MapPin className="h-3.5 w-3.5 text-slate-400" />
                          {plant.latitude.toFixed(4)}°, {plant.longitude.toFixed(4)}°
                        </span>
                        <span className="inline-flex items-center gap-1">
                          <Clock className="h-3.5 w-3.5 text-slate-400" />
                          {plant.timezone}
                        </span>
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center gap-2 self-end sm:self-center">
                    {!isSelected ? (
                      <button
                        onClick={() => onSelectPlant(plant)}
                        className="px-3 py-1.5 border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 rounded-lg text-xs font-semibold transition cursor-pointer"
                      >
                        Switch To Plant
                      </button>
                    ) : (
                      <span className="text-xs text-amber-700 font-semibold px-2 py-1 bg-amber-100/60 rounded">
                        Currently Active
                      </span>
                    )}

                    <button
                      onClick={() => onOpenEditPlant(plant)}
                      className="p-1.5 border border-slate-200 hover:bg-slate-100 text-slate-600 rounded-lg transition cursor-pointer"
                      title="Edit plant"
                    >
                      <Edit className="h-3.5 w-3.5" />
                    </button>

                    <button
                      onClick={() => onOpenDeletePlant(plant)}
                      className="p-1.5 border border-rose-200 hover:bg-rose-50 text-rose-600 rounded-lg transition cursor-pointer"
                      title="Decommission plant"
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </button>
                  </div>
                </div>
              );
            })
          ) : (
            <div className="py-10 text-center text-xs text-slate-500">
              No renewable plants match the selected criteria.
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
