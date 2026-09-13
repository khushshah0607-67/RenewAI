export type PlantType = 'SOLAR' | 'WIND';

export interface Plant {
  id: number;
  name: string;
  plant_type: PlantType;
  latitude: number;
  longitude: number;
  capacity_mw: number;
  timezone: string;
  created_at: string;
}

export interface PlantCreateInput {
  name: string;
  plant_type: PlantType;
  latitude: number;
  longitude: number;
  capacity_mw: number;
  timezone: string;
}

export interface PlantUpdateInput {
  name?: string;
  plant_type?: PlantType;
  latitude?: number;
  longitude?: number;
  capacity_mw?: number;
  timezone?: string;
}

export interface HistoricalGeneration {
  id: number;
  plant_id: number;
  timestamp: string;
  generation_mw: number;
  created_at: string;
}

export interface GenerationUploadSummary {
  plant_id: number;
  rows_received: number;
  rows_inserted: number;
  rows_rejected: number;
  duplicate_count: number;
  min_timestamp: string | null;
  max_timestamp: string | null;
  errors?: string[] | null;
}

export interface WeatherData {
  id: number;
  plant_id: number;
  timestamp: string;
  temperature_c: number | null;
  humidity_percent: number | null;
  wind_speed_mps: number | null;
  wind_direction_deg: number | null;
  cloud_cover_percent: number | null;
  precipitation_mm: number | null;
  radiation_w_m2: number | null;
  created_at: string;
}

export interface Forecast {
  id: number;
  plant_id: number;
  forecast_timestamp: string;
  generated_at: string;
  p10_mw: number;
  p50_mw: number;
  p90_mw: number;
  model_version: string;
}

export interface RiskMetric {
  score: number;
  level: 'LOW' | 'MEDIUM' | 'HIGH';
  description: string;
}

export interface PlantRisk {
  plant_id: number;
  plant_name: string;
  plant_type: PlantType;
  capacity_mw: number;
  forecast_points: number;
  overall_score: number;
  risk_level: 'LOW' | 'MEDIUM' | 'HIGH';
  generated_at: string;
  under_generation_risk: RiskMetric;
  forecast_uncertainty_risk: RiskMetric;
  ramp_change_risk: RiskMetric;
}

export interface FinancialExposure {
  plant_id: number;
  plant_name: string;
  plant_type: PlantType;
  capacity_mw: number;
  forecast_points: number;
  energy_price_inr_per_mwh: number;
  estimated_deviation_mwh: number;
  estimated_exposure_inr: number;
  exposure_label: string;
  currency: string;
  generated_at: string;
}

export interface OperationalRecommendation {
  priority: 'HIGH' | 'MEDIUM' | 'LOW';
  severity: 'HIGH' | 'MEDIUM' | 'LOW';
  action: string;
  explanation: string;
  rationale?: string | null;
}

export interface DecisionRecommendations {
  plant_id: number;
  plant_name: string;
  plant_type: PlantType;
  risk_level: 'LOW' | 'MEDIUM' | 'HIGH';
  overall_risk_score: number;
  estimated_exposure_inr: number;
  exposure_label: string;
  recommendations: OperationalRecommendation[];
  generated_at: string;
}

export interface ExplainabilityFactor {
  factor_name: string;
  importance: number | null;
  contribution: number | null;
  direction: 'positive' | 'negative';
  explanation: string;
  is_prototype: boolean;
  source: string;
}

export interface PlantExplanation {
  plant_id: number;
  plant_name: string;
  plant_type: PlantType;
  risk_level: 'LOW' | 'MEDIUM' | 'HIGH';
  overall_risk_score: number;
  estimated_exposure_inr: number;
  exposure_label: string;
  forecast_summary: string;
  explanation_version: string;
  prototype_note: string;
  factors: ExplainabilityFactor[];
  generated_at: string;
}

export interface SimulationScenario {
  battery_reserve_target: number;
  backup_availability: boolean;
  flexible_load_availability: boolean;
  curtailment_allowance: boolean;
  energy_price_inr_per_mwh?: number | null;
}

export interface SimulationRecommendation {
  priority: string;
  severity: string;
  action: string;
  explanation: string;
  rationale?: string | null;
}

export interface SimulationResult {
  plant_id: number;
  plant_name: string;
  plant_type: PlantType;
  baseline_risk_score: number;
  baseline_risk_level: string;
  simulated_risk_score: number;
  simulated_risk_level: string;
  baseline_estimated_exposure_inr: number;
  simulated_estimated_exposure_inr: number;
  risk_change: number;
  exposure_change: number;
  recommendations: SimulationRecommendation[];
  generated_at: string;
  simulation_note: string;
}

export type TabId =
  | 'overview'
  | 'forecast'
  | 'historical'
  | 'weather'
  | 'risk'
  | 'recommendations'
  | 'simulation'
  | 'plants';

