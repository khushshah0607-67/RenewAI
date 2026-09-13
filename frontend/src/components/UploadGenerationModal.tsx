import React, { useState, useRef } from 'react';
import { X, Upload, FileText, CheckCircle, AlertTriangle, Sparkles } from 'lucide-react';
import { Plant } from '../types';
import { api } from '../services/api';

interface UploadGenerationModalProps {
  isOpen: boolean;
  onClose: () => void;
  plant: Plant;
  onUploadSuccess: () => void;
}

export const UploadGenerationModal: React.FC<UploadGenerationModalProps> = ({
  isOpen,
  onClose,
  plant,
  onUploadSuccess,
}) => {
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [summary, setSummary] = useState<any | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  if (!isOpen) return null;

  const handleFileDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      setFile(e.dataTransfer.files[0]);
    }
  };

  const handleUpload = async () => {
    if (!file) return;
    setUploading(true);
    setError(null);
    try {
      const res = await api.uploadGenerationCsv(plant.id, file);
      setSummary(res);
      onUploadSuccess();
    } catch (err: any) {
      setError(err.message || 'Upload failed');
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 backdrop-blur-xs p-4">
      <div className="bg-white border border-slate-200 rounded-xl w-full max-w-lg p-6 shadow-xl relative animate-in fade-in zoom-in-95 duration-150">
        <button
          onClick={onClose}
          className="absolute top-4 right-4 text-slate-400 hover:text-slate-700 transition"
        >
          <X className="h-5 w-5" />
        </button>

        <h2 className="text-lg font-bold text-slate-900 mb-1">Upload Generation Records</h2>
        <p className="text-xs text-slate-500 mb-4">
          Upload SCADA or telemetry meter CSV for <span className="text-amber-700 font-semibold">{plant.name}</span>
        </p>

        {error && (
          <div className="mb-4 p-2.5 bg-rose-50 border border-rose-200 rounded-lg text-xs text-rose-700 flex items-start gap-2">
            <AlertTriangle className="h-4 w-4 shrink-0 mt-0.5" />
            <span>{error}</span>
          </div>
        )}

        {summary ? (
          <div className="space-y-4">
            <div className="p-4 bg-emerald-50 border border-emerald-200 rounded-lg">
              <div className="flex items-center space-x-2 text-emerald-700 font-semibold text-sm mb-2">
                <CheckCircle className="h-4 w-4" />
                <span>Upload Processed Successfully</span>
              </div>
              <div className="grid grid-cols-2 gap-2 text-xs text-slate-700">
                <div>Rows Processed: <span className="font-bold text-slate-900">{summary.rows_received}</span></div>
                <div>Rows Ingested: <span className="font-bold text-emerald-700">{summary.rows_inserted}</span></div>
                <div>Duplicates Skipped: <span className="font-bold text-slate-500">{summary.duplicate_count}</span></div>
                <div>Rows Rejected: <span className="font-bold text-rose-600">{summary.rows_rejected}</span></div>
              </div>
            </div>

            <div className="flex justify-end">
              <button
                onClick={onClose}
                className="bg-white hover:bg-slate-50 text-slate-800 text-xs font-semibold px-4 py-2 rounded-lg border border-slate-300 shadow-xs transition"
              >
                Done
              </button>
            </div>
          </div>
        ) : (
          <div className="space-y-4">
            {/* Drag and Drop Zone */}
            <div
              onDragOver={(e) => e.preventDefault()}
              onDrop={handleFileDrop}
              onClick={() => fileInputRef.current?.click()}
              className="border-2 border-dashed border-slate-300 hover:border-amber-500 bg-slate-50 hover:bg-slate-100/60 rounded-xl p-6 text-center cursor-pointer transition"
            >
              <input
                ref={fileInputRef}
                type="file"
                accept=".csv"
                className="hidden"
                onChange={(e) => {
                  if (e.target.files?.[0]) setFile(e.target.files[0]);
                }}
              />
              <Upload className="h-8 w-8 text-amber-500 mx-auto mb-2 opacity-80" />
              {file ? (
                <div className="flex items-center justify-center space-x-2 text-xs text-slate-800">
                  <FileText className="h-4 w-4 text-amber-600" />
                  <span className="font-semibold">{file.name}</span>
                  <span className="text-slate-500">({(file.size / 1024).toFixed(1)} KB)</span>
                </div>
              ) : (
                <>
                  <p className="text-xs font-semibold text-slate-800">
                    Click to browse or drag and drop your CSV file here
                  </p>
                  <p className="text-[11px] text-slate-500 mt-1">
                    Format: <code className="bg-white px-1.5 py-0.5 rounded border border-slate-200 text-amber-700">timestamp,generation_mw</code>
                  </p>
                </>
              )}
            </div>

            <div className="pt-2 flex items-center justify-end space-x-3 border-t border-slate-200">
              <button
                type="button"
                onClick={onClose}
                className="px-4 py-2 text-xs font-medium text-slate-600 hover:text-slate-900"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleUpload}
                disabled={!file || uploading}
                className="bg-amber-500 hover:bg-amber-400 disabled:opacity-50 text-slate-950 text-xs font-bold px-4 py-2 rounded-lg transition flex items-center gap-1.5 shadow-xs"
              >
                <Upload className="h-4 w-4" />
                <span>{uploading ? 'Ingesting CSV...' : 'Upload & Process'}</span>
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
