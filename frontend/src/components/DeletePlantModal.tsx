import React, { useState } from 'react';
import { Trash2, X, AlertTriangle } from 'lucide-react';
import { Plant } from '../types';
import { api } from '../services/api';

interface DeletePlantModalProps {
  isOpen: boolean;
  onClose: () => void;
  plant: Plant;
  onPlantDeleted: (plantId: number) => void;
}

export const DeletePlantModal: React.FC<DeletePlantModalProps> = ({
  isOpen,
  onClose,
  plant,
  onPlantDeleted,
}) => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleDelete = async () => {
    setLoading(true);
    setError(null);
    try {
      await api.deletePlant(plant.id);
      onPlantDeleted(plant.id);
      onClose();
    } catch (err: any) {
      setError(err.message || 'Failed to delete plant');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 backdrop-blur-xs p-4">
      <div className="bg-white border border-slate-200 rounded-xl w-full max-w-md p-6 shadow-xl relative animate-in fade-in zoom-in-95 duration-150">
        <button
          onClick={onClose}
          className="absolute top-4 right-4 text-slate-400 hover:text-slate-700 transition cursor-pointer"
        >
          <X className="h-5 w-5" />
        </button>

        <div className="flex items-center gap-3 text-rose-600 mb-3">
          <div className="p-2.5 bg-rose-50 rounded-xl border border-rose-100">
            <AlertTriangle className="h-6 w-6" />
          </div>
          <div>
            <h2 className="text-base font-bold text-slate-900">Decommission Plant</h2>
            <p className="text-xs text-slate-500">Irreversible plant removal</p>
          </div>
        </div>

        <p className="text-xs text-slate-600 mb-4 leading-relaxed">
          Are you sure you want to remove <strong className="text-slate-900 font-semibold">{plant.name}</strong> ({plant.capacity_mw} MW {plant.plant_type})? All associated forecast runs, risk analyses, and telemetry records for this plant will be deleted.
        </p>

        {error && (
          <div className="mb-4 p-2.5 bg-rose-50 border border-rose-200 rounded-lg text-xs text-rose-700">
            {error}
          </div>
        )}

        <div className="pt-2 flex items-center justify-end space-x-3">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 text-xs font-medium text-slate-600 hover:text-slate-900 cursor-pointer"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={handleDelete}
            disabled={loading}
            className="bg-rose-600 hover:bg-rose-700 disabled:opacity-50 text-white text-xs font-bold px-4 py-2 rounded-lg transition flex items-center gap-1.5 shadow-xs cursor-pointer"
          >
            <Trash2 className="h-4 w-4" />
            <span>{loading ? 'Deleting...' : 'Confirm Deletion'}</span>
          </button>
        </div>
      </div>
    </div>
  );
};
