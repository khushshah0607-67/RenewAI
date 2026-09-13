import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../services/api';
import {
  PlantCreateInput,
  PlantUpdateInput,
  SimulationScenario,
} from '../types';

export const queryKeys = {
  plants: ['plants'] as const,
  plant: (id: number) => ['plants', id] as const,
  forecast: (plantId: number) => ['forecast', plantId] as const,
  generation: (plantId: number, limit?: number) => ['generation', plantId, limit] as const,
  weather: (plantId: number, limit?: number) => ['weather', plantId, limit] as const,
  risk: (plantId: number) => ['risk', plantId] as const,
  financial: (plantId: number, price?: number) => ['financial', plantId, price] as const,
  recommendations: (plantId: number) => ['recommendations', plantId] as const,
  explanation: (plantId: number) => ['explanation', plantId] as const,
};

// --- Queries ---

export function usePlants() {
  return useQuery({
    queryKey: queryKeys.plants,
    queryFn: () => api.getPlants(),
    staleTime: 60 * 1000,
  });
}

export function usePlant(id: number | null | undefined) {
  return useQuery({
    queryKey: queryKeys.plant(id!),
    queryFn: () => api.getPlant(id!),
    enabled: !!id,
  });
}

export function useForecast(plantId: number | null | undefined) {
  return useQuery({
    queryKey: queryKeys.forecast(plantId!),
    queryFn: () => api.getForecast(plantId!),
    enabled: !!plantId,
    staleTime: 30 * 1000,
  });
}

export function useGeneration(plantId: number | null | undefined, limit = 48) {
  return useQuery({
    queryKey: queryKeys.generation(plantId!, limit),
    queryFn: () => api.getGeneration(plantId!, { limit }),
    enabled: !!plantId,
    staleTime: 30 * 1000,
  });
}

export function useWeather(plantId: number | null | undefined, limit = 48) {
  return useQuery({
    queryKey: queryKeys.weather(plantId!, limit),
    queryFn: () => api.getWeather(plantId!, { limit }),
    enabled: !!plantId,
    staleTime: 60 * 1000,
  });
}

export function useRisk(plantId: number | null | undefined) {
  return useQuery({
    queryKey: queryKeys.risk(plantId!),
    queryFn: () => api.getRisk(plantId!),
    enabled: !!plantId,
    staleTime: 30 * 1000,
  });
}

export function useFinancial(plantId: number | null | undefined, price?: number) {
  return useQuery({
    queryKey: queryKeys.financial(plantId!, price),
    queryFn: () => api.getFinancial(plantId!, price),
    enabled: !!plantId,
    staleTime: 30 * 1000,
  });
}

export function useRecommendations(plantId: number | null | undefined) {
  return useQuery({
    queryKey: queryKeys.recommendations(plantId!),
    queryFn: () => api.getRecommendations(plantId!),
    enabled: !!plantId,
    staleTime: 30 * 1000,
  });
}

export function useExplanation(plantId: number | null | undefined) {
  return useQuery({
    queryKey: queryKeys.explanation(plantId!),
    queryFn: () => api.getExplanation(plantId!),
    enabled: !!plantId,
    staleTime: 30 * 1000,
  });
}

// --- Mutations ---

export function useCreatePlant() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: PlantCreateInput) => api.createPlant(input),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.plants });
    },
  });
}

export function useUpdatePlant() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, updates }: { id: number; updates: PlantUpdateInput }) =>
      api.updatePlant(id, updates),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.plants });
      queryClient.invalidateQueries({ queryKey: queryKeys.plant(variables.id) });
    },
  });
}

export function useDeletePlant() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => api.deletePlant(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.plants });
    },
  });
}

export function useGenerateForecast() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (plantId: number) => api.generateForecast(plantId),
    onSuccess: (_, plantId) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.forecast(plantId) });
      queryClient.invalidateQueries({ queryKey: queryKeys.risk(plantId) });
      queryClient.invalidateQueries({ queryKey: queryKeys.financial(plantId) });
      queryClient.invalidateQueries({ queryKey: queryKeys.recommendations(plantId) });
      queryClient.invalidateQueries({ queryKey: queryKeys.explanation(plantId) });
    },
  });
}

export function useUploadGeneration() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ plantId, file }: { plantId: number; file: File }) =>
      api.uploadGenerationCsv(plantId, file),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['generation', variables.plantId] });
      queryClient.invalidateQueries({ queryKey: queryKeys.risk(variables.plantId) });
      queryClient.invalidateQueries({ queryKey: queryKeys.financial(variables.plantId) });
      queryClient.invalidateQueries({ queryKey: queryKeys.recommendations(variables.plantId) });
      queryClient.invalidateQueries({ queryKey: queryKeys.explanation(variables.plantId) });
    },
  });
}

export function useRunSimulation() {
  return useMutation({
    mutationFn: ({ plantId, scenario }: { plantId: number; scenario: SimulationScenario }) =>
      api.runSimulation(plantId, scenario),
  });
}
