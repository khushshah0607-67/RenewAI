import React, { useState } from 'react';
import { X, Plus, Sun, Wind } from 'lucide-react';
import { Plant, PlantType } from '../types';
import { api } from '../services/api';

interface NewPlantModalProps {
  isOpen: boolean;
  onClose: () => void;
  onPlantCreated: (plant: Plant) => void;
}

export const NewPlantModal: React.FC<NewPlantModalProps> = ({
  isOpen,
  onClose,
  onPlantCreated,
}) => {
  const [name, setName] = useState('');
  const [plantType, setPlantType] = useState<PlantType>('SOLAR');
  const [capacity, setCapacity] = useState<number>(500);
  const [latitude, setLatitude] = useState<number>(26.9);
  const [longitude, setLongitude] = useState<number>(71.5);
  const [timezone, setTimezone] = useState('Asia/Kolkata');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) {
      setError('Plant name is required');
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const newPlant = await api.createPlant({
        name: name.trim(),
        plant_type: plantType,
        capacity_mw: Number(capacity),
        latitude: Number(latitude),
        longitude: Number(longitude),
        timezone,
      });
      onPlantCreated(newPlant);
      onClose();
    } catch (err: any) {
      setError(err.message || 'Failed to create plant');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 backdrop-blur-xs p-4">
      <div className="bg-white border border-slate-200 rounded-xl w-full max-w-md p-6 shadow-xl relative animate-in fade-in zoom-in-95 duration-150">
        <button
          onClick={onClose}
          className="absolute top-4 right-4 text-slate-400 hover:text-slate-700 transition"
        >
          <X className="h-5 w-5" />
        </button>

        <h2 className="text-lg font-bold text-slate-900 mb-1">Register Renewable Plant</h2>
        <p className="text-xs text-slate-500 mb-5">
          Provision a solar or wind installation with meteorological telemetry tracking
        </p>

        {error && (
          <div className="mb-4 p-2.5 bg-rose-50 border border-rose-200 rounded-lg text-xs text-rose-700">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">Plant Name</label>
            <input
              type="text"
              required
              placeholder="e.g. Rewa Ultra Mega Solar"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full bg-white border border-slate-300 rounded-lg px-3 py-2 text-sm text-slate-900 placeholder-slate-400 focus:outline-none focus:border-amber-500 focus:ring-1 focus:ring-amber-500 shadow-xs"
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">Plant Type</label>
              <div className="flex rounded-lg bg-slate-100 border border-slate-200 p-0.5">
                <button
                  type="button"
                  onClick={() => setPlantType('SOLAR')}
                  className={`flex-1 py-1.5 text-xs font-medium rounded-md flex items-center justify-center gap-1 transition ${
                    plantType === 'SOLAR'
                      ? 'bg-white text-amber-700 font-bold shadow-xs border border-slate-200/80'
                      : 'text-slate-600 hover:text-slate-900'
                  }`}
                >
                  <Sun className="h-3.5 w-3.5" /> Solar
                </button>
                <button
                  type="button"
                  onClick={() => setPlantType('WIND')}
                  className={`flex-1 py-1.5 text-xs font-medium rounded-md flex items-center justify-center gap-1 transition ${
                    plantType === 'WIND'
                      ? 'bg-white text-sky-700 font-bold shadow-xs border border-slate-200/80'
                      : 'text-slate-600 hover:text-slate-900'
                  }`}
                >
                  <Wind className="h-3.5 w-3.5" /> Wind
                </button>
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">Capacity (MW)</label>
              <input
                type="number"
                required
                min="1"
                step="0.1"
                value={capacity}
                onChange={(e) => setCapacity(Number(e.target.value))}
                className="w-full bg-white border border-slate-300 rounded-lg px-3 py-2 text-sm text-slate-900 focus:outline-none focus:border-amber-500 focus:ring-1 focus:ring-amber-500 shadow-xs"
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">Latitude</label>
              <input
                type="number"
                required
                step="0.0001"
                value={latitude}
                onChange={(e) => setLatitude(Number(e.target.value))}
                className="w-full bg-white border border-slate-300 rounded-lg px-3 py-2 text-sm text-slate-900 focus:outline-none focus:border-amber-500 focus:ring-1 focus:ring-amber-500 shadow-xs"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">Longitude</label>
              <input
                type="number"
                required
                step="0.0001"
                value={longitude}
                onChange={(e) => setLongitude(Number(e.target.value))}
                className="w-full bg-white border border-slate-300 rounded-lg px-3 py-2 text-sm text-slate-900 focus:outline-none focus:border-amber-500 focus:ring-1 focus:ring-amber-500 shadow-xs"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">Timezone</label>
            <input
              type="text"
              required
              value={timezone}
              onChange={(e) => setTimezone(e.target.value)}
              className="w-full bg-white border border-slate-300 rounded-lg px-3 py-2 text-sm text-slate-900 focus:outline-none focus:border-amber-500 focus:ring-1 focus:ring-amber-500 shadow-xs"
            />
          </div>

          <div className="pt-2 flex items-center justify-end space-x-3">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-xs font-medium text-slate-600 hover:text-slate-900"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading}
              className="bg-amber-500 hover:bg-amber-400 disabled:opacity-50 text-slate-950 text-xs font-bold px-4 py-2 rounded-lg transition flex items-center gap-1.5 shadow-xs"
            >
              <Plus className="h-4 w-4" />
              <span>{loading ? 'Creating...' : 'Register Plant'}</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
