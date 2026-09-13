import React from 'react';
import { WeatherData, Plant } from '../types';
import { Sun, Cloud, Droplets, Wind, Thermometer, Compass, CloudRain } from 'lucide-react';
import {
  ResponsiveContainer,
  ComposedChart,
  Line,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  Legend,
} from 'recharts';

interface WeatherViewProps {
  plant: Plant;
  weather: WeatherData[];
}

export const WeatherView: React.FC<WeatherViewProps> = ({ plant, weather }) => {
  const latest = weather[weather.length - 1] || weather[0] || null;
  const isSolar = plant.plant_type === 'SOLAR';

  const chartData = weather.slice(-36).map((w) => {
    const d = new Date(w.timestamp);
    return {
      time: d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      date: d.toLocaleDateString([], { month: 'short', day: 'numeric' }),
      radiation: w.radiation_w_m2 ?? 0,
      cloudCover: w.cloud_cover_percent ?? 0,
      temperature: w.temperature_c ?? 0,
      windSpeed: w.wind_speed_mps ?? 0,
      windDir: w.wind_direction_deg ?? 0,
      humidity: w.humidity_percent ?? 0,
      precipitation: w.precipitation_mm ?? 0,
    };
  });

  return (
    <div className="space-y-6">
      {/* Current Conditions Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-4">
        <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-xs">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs text-slate-500 font-medium">Solar Radiation</span>
            <Sun className="h-4 w-4 text-amber-500" />
          </div>
          <div className="text-2xl font-bold text-slate-900">
            {latest?.radiation_w_m2 != null ? `${latest.radiation_w_m2.toFixed(0)}` : '--'}
            <span className="text-xs text-slate-500 ml-1">W/m²</span>
          </div>
          <span className="text-[11px] text-slate-500">Global Horizontal (GHI)</span>
        </div>

        <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-xs">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs text-slate-500 font-medium">Cloud Cover</span>
            <Cloud className="h-4 w-4 text-slate-400" />
          </div>
          <div className="text-2xl font-bold text-slate-900">
            {latest?.cloud_cover_percent != null ? `${latest.cloud_cover_percent}%` : '--'}
          </div>
          <span className="text-[11px] text-slate-500">Atmospheric attenuation</span>
        </div>

        <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-xs">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs text-slate-500 font-medium">Wind Velocity</span>
            <Wind className="h-4 w-4 text-sky-500" />
          </div>
          <div className="text-2xl font-bold text-slate-900">
            {latest?.wind_speed_mps != null ? `${latest.wind_speed_mps.toFixed(1)}` : '--'}
            <span className="text-xs text-slate-500 ml-1">m/s</span>
          </div>
          <span className="text-[11px] text-slate-500">
            {latest?.wind_direction_deg != null ? `Dir: ${latest.wind_direction_deg}°` : 'Speed at 10m'}
          </span>
        </div>

        <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-xs">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs text-slate-500 font-medium">Temperature</span>
            <Thermometer className="h-4 w-4 text-rose-500" />
          </div>
          <div className="text-2xl font-bold text-slate-900">
            {latest?.temperature_c != null ? `${latest.temperature_c.toFixed(1)}°C` : '--'}
          </div>
          <span className="text-[11px] text-slate-500">Ambient at 2m</span>
        </div>

        <div className="bg-white border border-slate-200 rounded-xl p-4 col-span-2 sm:col-span-1 shadow-xs">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs text-slate-500 font-medium">Humidity & Rain</span>
            <Droplets className="h-4 w-4 text-blue-500" />
          </div>
          <div className="text-2xl font-bold text-slate-900">
            {latest?.humidity_percent != null ? `${latest.humidity_percent}%` : '--'}
          </div>
          <span className="text-[11px] text-slate-500">
            {latest?.precipitation_mm ? `${latest.precipitation_mm} mm rain` : 'No precipitation'}
          </span>
        </div>
      </div>

      {/* Weather Chart */}
      <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-xs">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 mb-4">
          <div>
            <h2 className="text-base font-semibold text-slate-900">
              {isSolar
                ? 'Solar Irradiance & Cloud Attenuation (Open-Meteo Feed)'
                : 'Wind Speed & Atmospheric Pressure (Open-Meteo Feed)'}
            </h2>
            <p className="text-xs text-slate-500">
              Meteorological parameters ingested directly into the probabilistic forecasting engine
            </p>
          </div>
          <div className="text-xs text-slate-500">
            Coordinates: {plant.latitude.toFixed(3)}°N, {plant.longitude.toFixed(3)}°E
          </div>
        </div>

        {chartData.length > 0 ? (
          <div className="h-80 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <ComposedChart data={chartData} margin={{ top: 10, right: 20, left: 0, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                <XAxis dataKey="time" stroke="#64748b" fontSize={11} tickLine={false} />
                <YAxis
                  yAxisId="left"
                  stroke="#b45309"
                  fontSize={11}
                  tickLine={false}
                  unit={isSolar ? ' W/m²' : ' m/s'}
                />
                <YAxis
                  yAxisId="right"
                  orientation="right"
                  stroke="#64748b"
                  fontSize={11}
                  tickLine={false}
                  unit="%"
                  domain={[0, 100]}
                />
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#ffffff',
                    borderColor: '#e2e8f0',
                    borderRadius: '0.5rem',
                    boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)',
                    fontSize: '12px',
                    color: '#0f172a',
                  }}
                  labelStyle={{ color: '#334155', fontWeight: 600 }}
                  labelFormatter={(label, items) => {
                    const item = items[0]?.payload;
                    return item ? `${item.date} ${label}` : label;
                  }}
                />
                <Legend wrapperStyle={{ fontSize: '12px', paddingTop: '10px' }} />
                <Bar
                  yAxisId="right"
                  dataKey="cloudCover"
                  fill="#94a3b8"
                  opacity={0.35}
                  name="Cloud Cover (%)"
                />
                {isSolar ? (
                  <Line
                    yAxisId="left"
                    type="monotone"
                    dataKey="radiation"
                    stroke="#d97706"
                    strokeWidth={2.5}
                    dot={false}
                    name="Solar Radiation (W/m²)"
                  />
                ) : (
                  <Line
                    yAxisId="left"
                    type="monotone"
                    dataKey="windSpeed"
                    stroke="#0284c7"
                    strokeWidth={2.5}
                    dot={false}
                    name="Wind Speed (m/s)"
                  />
                )}
                <Line
                  yAxisId="right"
                  type="monotone"
                  dataKey="temperature"
                  stroke="#dc2626"
                  strokeWidth={1.5}
                  dot={false}
                  name="Temperature (°C)"
                />
              </ComposedChart>
            </ResponsiveContainer>
          </div>
        ) : (
          <div className="py-12 text-center text-xs text-slate-500">
            No weather telemetry points available for this plant coordinate.
          </div>
        )}
      </div>
    </div>
  );
};
