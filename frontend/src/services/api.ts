import { apiClient } from './apiClient';
import {
  Plant,
  PlantCreateInput,
  PlantUpdateInput,
  HistoricalGeneration,
  GenerationUploadSummary,
  WeatherData,
  Forecast,
  PlantRisk,
  FinancialExposure,
  DecisionRecommendations,
  PlantExplanation,
  SimulationScenario,
  SimulationResult,
} from '../types';

export const api = {
  // --- Plants ---
  async getPlants(): Promise<Plant[]> {
    const res = await apiClient.get<Plant[]>('/plants');
    return res.data;
  },

  async getPlant(id: number): Promise<Plant> {
    const res = await apiClient.get<Plant>(`/plants/${id}`);
    return res.data;
  },

  async createPlant(plant: PlantCreateInput): Promise<Plant> {
    const res = await apiClient.post<Plant>('/plants', plant);
    return res.data;
  },

  async updatePlant(id: number, updates: PlantUpdateInput): Promise<Plant> {
    const res = await apiClient.patch<Plant>(`/plants/${id}`, updates);
    return res.data;
  },

  async deletePlant(id: number): Promise<void> {
    await apiClient.delete(`/plants/${id}`);
  },

  // --- Historical Generation ---
  async getGeneration(
    plantId: number,
    params?: { start?: string; end?: string; limit?: number }
  ): Promise<HistoricalGeneration[]> {
    const res = await apiClient.get<HistoricalGeneration[]>(`/plants/${plantId}/generation`, {
      params,
    });
    return res.data;
  },

  async uploadGenerationCsv(plantId: number, file: File): Promise<GenerationUploadSummary> {
    const formData = new FormData();
    formData.append('file', file);
    const res = await apiClient.post<GenerationUploadSummary>(
      `/plants/${plantId}/generation/upload`,
      formData,
      {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      }
    );
    return res.data;
  },

  // --- Weather ---
  async getWeather(
    plantId: number,
    params?: { start?: string; end?: string; limit?: number }
  ): Promise<WeatherData[]> {
    const res = await apiClient.get<WeatherData[]>(`/plants/${plantId}/weather`, {
      params,
    });
    return res.data;
  },

  // --- Forecast ---
  async getForecast(plantId: number): Promise<Forecast[]> {
    const res = await apiClient.get<Forecast[]>(`/plants/${plantId}/forecast`);
    return res.data;
  },

  async generateForecast(plantId: number): Promise<Forecast[]> {
    const res = await apiClient.post<Forecast[]>(`/plants/${plantId}/forecast`);
    return res.data;
  },

  // --- Risk ---
  async getRisk(plantId: number): Promise<PlantRisk> {
    const res = await apiClient.get<PlantRisk>(`/plants/${plantId}/risk`);
    return res.data;
  },

  // --- Financial Exposure ---
  async getFinancial(plantId: number, price?: number): Promise<FinancialExposure> {
    const res = await apiClient.get<FinancialExposure>(`/plants/${plantId}/financial`, {
      params: price != null ? { price } : undefined,
    });
    return res.data;
  },

  // --- Recommendations ---
  async getRecommendations(plantId: number): Promise<DecisionRecommendations> {
    const res = await apiClient.get<DecisionRecommendations>(`/plants/${plantId}/recommendation`);
    return res.data;
  },

  // --- Explainability ---
  async getExplanation(plantId: number): Promise<PlantExplanation> {
    const res = await apiClient.get<PlantExplanation>(`/plants/${plantId}/explanation`);
    return res.data;
  },

  // --- Simulation Sandbox ---
  async runSimulation(plantId: number, scenario: SimulationScenario): Promise<SimulationResult> {
    const res = await apiClient.post<SimulationResult>(`/plants/${plantId}/simulation`, scenario);
    return res.data;
  },
};
