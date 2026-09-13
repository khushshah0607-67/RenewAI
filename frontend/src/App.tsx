import React, { useEffect, useState, useCallback } from 'react';
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
} from './types';
import { api } from './services/api';
import { Navbar } from './components/Navbar';
import { PlantHeader } from './components/PlantHeader';
import { OverviewView } from './components/OverviewView';
import { ForecastView } from './components/ForecastView';
import { HistoricalView } from './components/HistoricalView';
import { WeatherView } from './components/WeatherView';
import { RiskFinancialView } from './components/RiskFinancialView';
import { RecommendationExplainView } from './components/RecommendationExplainView';
import { SimulationSandbox } from './components/SimulationSandbox';
import { PlantManagementView } from './components/PlantManagementView';
import { NewPlantModal } from './components/NewPlantModal';
import { EditPlantModal } from './components/EditPlantModal';
import { DeletePlantModal } from './components/DeletePlantModal';
import { UploadGenerationModal } from './components/UploadGenerationModal';
import { AlertCircle, Loader2, CheckCircle2 } from 'lucide-react';

export const App: React.FC = () => {
  const [plants, setPlants] = useState<Plant[]>([]);
  const [selectedPlant, setSelectedPlant] = useState<Plant | null>(null);
  const [activeTab, setActiveTab] = useState<TabId>('overview');

  // Plant Data States
  const [forecasts, setForecasts] = useState<Forecast[]>([]);
  const [historical, setHistorical] = useState<HistoricalGeneration[]>([]);
  const [weather, setWeather] = useState<WeatherData[]>([]);
  const [risk, setRisk] = useState<PlantRisk | null>(null);
  const [financial, setFinancial] = useState<FinancialExposure | null>(null);
  const [recommendations, setRecommendations] = useState<DecisionRecommendations | null>(null);
  const [explanation, setExplanation] = useState<PlantExplanation | null>(null);

  // Status flags
  const [loading, setLoading] = useState<boolean>(true);
  const [isRefreshing, setIsRefreshing] = useState<boolean>(false);
  const [isGenerating, setIsGenerating] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  // Modals
  const [isNewPlantOpen, setIsNewPlantOpen] = useState<boolean>(false);
  const [isEditPlantOpen, setIsEditPlantOpen] = useState<boolean>(false);
  const [plantToEdit, setPlantToEdit] = useState<Plant | null>(null);
  const [isDeletePlantOpen, setIsDeletePlantOpen] = useState<boolean>(false);
  const [plantToDelete, setPlantToDelete] = useState<Plant | null>(null);
  const [isUploadOpen, setIsUploadOpen] = useState<boolean>(false);

  const showToast = (msg: string) => {
    setToastMessage(msg);
    setTimeout(() => setToastMessage(null), 4000);
  };

  // Load plants
  const loadPlants = useCallback(async () => {
    try {
      const data = await api.getPlants();
      setPlants(data);
      if (data.length > 0 && !selectedPlant) {
        setSelectedPlant(data[0]);
      }
    } catch (err: any) {
      setError(err.message || 'Failed to load plants from database');
    } finally {
      setLoading(false);
    }
  }, [selectedPlant]);

  useEffect(() => {
    loadPlants();
  }, [loadPlants]);

  // Load all telemetry & analysis for selected plant
  const loadPlantDetails = useCallback(async (plant: Plant) => {
    setIsRefreshing(true);
    setError(null);
    try {
      const [
        forecastData,
        histData,
        weatherData,
        riskData,
        financialData,
        recData,
        explainData,
      ] = await Promise.all([
        api.getForecast(plant.id),
        api.getGeneration(plant.id, { limit: 48 }),
        api.getWeather(plant.id, { limit: 48 }),
        api.getRisk(plant.id),
        api.getFinancial(plant.id),
        api.getRecommendations(plant.id),
        api.getExplanation(plant.id),
      ]);

      setForecasts(forecastData);
      setHistorical(histData);
      setWeather(weatherData);
      setRisk(riskData);
      setFinancial(financialData);
      setRecommendations(recData);
      setExplanation(explainData);
    } catch (err: any) {
      console.error('Error loading plant telemetry:', err);
      setError(err.message || 'Failed to load plant telemetry');
    } finally {
      setIsRefreshing(false);
    }
  }, []);

  useEffect(() => {
    if (selectedPlant) {
      loadPlantDetails(selectedPlant);
    }
  }, [selectedPlant, loadPlantDetails]);

  const handleRegenerateForecast = async () => {
    if (!selectedPlant) return;
    setIsGenerating(true);
    try {
      const newForecasts = await api.generateForecast(selectedPlant.id);
      setForecasts(newForecasts);

      // reload dependent risk & recommendations
      const [riskData, financialData, recData, explainData] = await Promise.all([
        api.getRisk(selectedPlant.id),
        api.getFinancial(selectedPlant.id),
        api.getRecommendations(selectedPlant.id),
        api.getExplanation(selectedPlant.id),
      ]);
      setRisk(riskData);
      setFinancial(financialData);
      setRecommendations(recData);
      setExplanation(explainData);
      showToast('Forecast model updated successfully with latest telemetry.');
    } catch (err: any) {
      setError(err.message || 'Forecast generation failed');
    } finally {
      setIsGenerating(false);
    }
  };

  const handleCustomPriceChange = async (newPrice: number) => {
    if (!selectedPlant) return;
    try {
      const updated = await api.getFinancial(selectedPlant.id, newPrice);
      setFinancial(updated);
    } catch (err) {
      console.error('Failed to update financial tariff:', err);
    }
  };

  const handlePlantCreated = (newPlant: Plant) => {
    setPlants((prev) => [...prev, newPlant]);
    setSelectedPlant(newPlant);
    showToast(`Plant "${newPlant.name}" registered successfully.`);
    setActiveTab('overview');
  };

  const handlePlantUpdated = (updatedPlant: Plant) => {
    setPlants((prev) => prev.map((p) => (p.id === updatedPlant.id ? updatedPlant : p)));
    if (selectedPlant?.id === updatedPlant.id) {
      setSelectedPlant(updatedPlant);
    }
    showToast(`Plant "${updatedPlant.name}" configurations updated.`);
  };

  const handlePlantDeleted = (deletedPlantId: number) => {
    const remaining = plants.filter((p) => p.id !== deletedPlantId);
    setPlants(remaining);
    if (selectedPlant?.id === deletedPlantId) {
      setSelectedPlant(remaining.length > 0 ? remaining[0] : null);
    }
    showToast('Plant decommissioned successfully.');
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-50 flex flex-col items-center justify-center text-slate-600">
        <Loader2 className="h-8 w-8 animate-spin text-amber-500 mb-3" />
        <p className="text-sm font-semibold text-slate-800">Initializing RenewAI Telemetry Engine...</p>
        <p className="text-xs text-slate-500 mt-1">Connecting to Open-Meteo & Renewable Fleet Database</p>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 flex flex-col">
      {/* Toast Notification */}
      {toastMessage && (
        <div className="fixed bottom-5 right-5 z-50 bg-slate-900 text-white text-xs px-4 py-3 rounded-xl shadow-lg flex items-center gap-2 animate-in fade-in slide-in-from-bottom-3 duration-200">
          <CheckCircle2 className="h-4 w-4 text-emerald-400 shrink-0" />
          <span>{toastMessage}</span>
        </div>
      )}

      {/* Top Navigation */}
      <Navbar
        plants={plants}
        selectedPlant={selectedPlant}
        onSelectPlant={(p) => setSelectedPlant(p)}
        onOpenNewPlant={() => setIsNewPlantOpen(true)}
        activeTab={activeTab}
        onSelectTab={setActiveTab}
        onRefresh={() => selectedPlant && loadPlantDetails(selectedPlant)}
        isRefreshing={isRefreshing}
      />

      {/* Main Container */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6">
        {error && (
          <div className="mb-6 p-4 bg-rose-50 border border-rose-200 rounded-xl flex items-center justify-between text-xs text-rose-800">
            <div className="flex items-center space-x-2">
              <AlertCircle className="h-4 w-4 text-rose-600 shrink-0" />
              <span>{error}</span>
            </div>
            <button
              onClick={() => selectedPlant && loadPlantDetails(selectedPlant)}
              className="px-2.5 py-1 bg-rose-100 hover:bg-rose-200 text-rose-800 rounded font-semibold transition cursor-pointer"
            >
              Retry
            </button>
          </div>
        )}

        {selectedPlant ? (
          <>
            {/* Plant Header Info & Controls (except when in Plant Fleet view) */}
            {activeTab !== 'plants' && (
              <PlantHeader
                plant={selectedPlant}
                onOpenUpload={() => setIsUploadOpen(true)}
                onOpenEdit={() => {
                  setPlantToEdit(selectedPlant);
                  setIsEditPlantOpen(true);
                }}
                onRegenerateForecast={handleRegenerateForecast}
                isGenerating={isGenerating}
              />
            )}

            {/* Active Tab View Routing */}
            <div className="animate-in fade-in duration-150">
              {activeTab === 'overview' && (
                <OverviewView
                  plant={selectedPlant}
                  forecasts={forecasts}
                  historical={historical}
                  weather={weather}
                  risk={risk}
                  financial={financial}
                  recommendations={recommendations}
                  explanation={explanation}
                  onNavigateTab={setActiveTab}
                  onRegenerateForecast={handleRegenerateForecast}
                  isGenerating={isGenerating}
                />
              )}

              {activeTab === 'forecast' && (
                <ForecastView
                  plant={selectedPlant}
                  forecasts={forecasts}
                  historical={historical}
                  onRegenerate={handleRegenerateForecast}
                  isGenerating={isGenerating}
                />
              )}

              {activeTab === 'historical' && (
                <HistoricalView
                  plant={selectedPlant}
                  historical={historical}
                  onOpenUpload={() => setIsUploadOpen(true)}
                />
              )}

              {activeTab === 'weather' && (
                <WeatherView
                  plant={selectedPlant}
                  weather={weather}
                />
              )}

              {activeTab === 'risk' && (
                <RiskFinancialView
                  plant={selectedPlant}
                  risk={risk}
                  financial={financial}
                  onPriceChange={handleCustomPriceChange}
                />
              )}

              {activeTab === 'recommendations' && (
                <RecommendationExplainView
                  plant={selectedPlant}
                  recommendations={recommendations}
                  explanation={explanation}
                />
              )}

              {activeTab === 'simulation' && (
                <SimulationSandbox plant={selectedPlant} />
              )}

              {activeTab === 'plants' && (
                <PlantManagementView
                  plants={plants}
                  selectedPlant={selectedPlant}
                  onSelectPlant={(p) => setSelectedPlant(p)}
                  onOpenNewPlant={() => setIsNewPlantOpen(true)}
                  onOpenEditPlant={(p) => {
                    setPlantToEdit(p);
                    setIsEditPlantOpen(true);
                  }}
                  onOpenDeletePlant={(p) => {
                    setPlantToDelete(p);
                    setIsDeletePlantOpen(true);
                  }}
                />
              )}
            </div>
          </>
        ) : (
          <div className="text-center py-20 bg-white border border-slate-200 rounded-xl shadow-xs">
            <p className="text-slate-600 text-sm">No renewable plant selected or registered in the fleet.</p>
            <button
              onClick={() => setIsNewPlantOpen(true)}
              className="mt-3 inline-flex items-center px-4 py-2 bg-amber-500 hover:bg-amber-400 text-slate-950 font-bold rounded-lg text-xs transition shadow-xs cursor-pointer"
            >
              Add First Renewable Plant
            </button>
          </div>
        )}
      </main>

      {/* Footer */}
      <footer className="border-t border-slate-200 bg-white py-4 text-center text-[11px] text-slate-500">
        <div className="max-w-7xl mx-auto px-4 flex flex-col sm:flex-row items-center justify-between gap-2">
          <span>RenewAI · Operational Solar & Wind Generation Forecasting & Risk Intelligence</span>
          <span>Open-Meteo Telemetry · CERC Deviation Settlement Mechanism (DSM) Framework</span>
        </div>
      </footer>

      {/* Modals */}
      <NewPlantModal
        isOpen={isNewPlantOpen}
        onClose={() => setIsNewPlantOpen(false)}
        onPlantCreated={handlePlantCreated}
      />

      {plantToEdit && (
        <EditPlantModal
          isOpen={isEditPlantOpen}
          onClose={() => {
            setIsEditPlantOpen(false);
            setPlantToEdit(null);
          }}
          plant={plantToEdit}
          onPlantUpdated={handlePlantUpdated}
        />
      )}

      {plantToDelete && (
        <DeletePlantModal
          isOpen={isDeletePlantOpen}
          onClose={() => {
            setIsDeletePlantOpen(false);
            setPlantToDelete(null);
          }}
          plant={plantToDelete}
          onPlantDeleted={handlePlantDeleted}
        />
      )}

      {selectedPlant && (
        <UploadGenerationModal
          isOpen={isUploadOpen}
          onClose={() => setIsUploadOpen(false)}
          plant={selectedPlant}
          onUploadSuccess={() => {
            loadPlantDetails(selectedPlant);
            showToast('SCADA records ingested and metrics updated.');
          }}
        />
      )}
    </div>
  );
};

export default App;
