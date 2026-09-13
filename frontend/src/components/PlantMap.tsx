import React, { useEffect, useRef } from 'react';
import L from 'leaflet';
import { Plant } from '../types';
import { MapPin, AlertTriangle } from 'lucide-react';

interface PlantMapProps {
  plant?: Plant | null;
  plants?: Plant[];
  height?: string;
  onSelectPlant?: (plant: Plant) => void;
}

export const PlantMap: React.FC<PlantMapProps> = ({
  plant,
  plants,
  height = '360px',
  onSelectPlant,
}) => {
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const mapInstanceRef = useRef<L.Map | null>(null);
  const markersRef = useRef<L.LayerGroup | null>(null);

  // Check if plant has valid coordinates
  const hasValidCoords =
    plant &&
    typeof plant.latitude === 'number' &&
    typeof plant.longitude === 'number' &&
    !isNaN(plant.latitude) &&
    !isNaN(plant.longitude) &&
    plant.latitude >= -90 &&
    plant.latitude <= 90 &&
    plant.longitude >= -180 &&
    plant.longitude <= 180;

  // Initialize Map
  useEffect(() => {
    if (!mapContainerRef.current) return;

    if (!mapInstanceRef.current) {
      const map = L.map(mapContainerRef.current, {
        attributionControl: true,
        zoomControl: true,
      });

      L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        maxZoom: 19,
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
      }).addTo(map);

      const markers = L.layerGroup().addTo(map);
      markersRef.current = markers;
      mapInstanceRef.current = map;
    }

    const map = mapInstanceRef.current;
    const markers = markersRef.current;
    if (!map || !markers) return;

    markers.clearLayers();

    // Determine target list of plants to show
    const displayPlants = plants && plants.length > 0 ? plants : (plant ? [plant] : []);

    if (displayPlants.length === 0) {
      map.setView([20.5937, 78.9629], 5); // Default to India center
      return;
    }

    const bounds: L.LatLngTuple[] = [];

    displayPlants.forEach((p) => {
      if (
        typeof p.latitude !== 'number' ||
        typeof p.longitude !== 'number' ||
        isNaN(p.latitude) ||
        isNaN(p.longitude)
      ) {
        return;
      }

      const isSelected = plant?.id === p.id;
      const isSolar = p.plant_type === 'SOLAR';
      const color = isSolar ? '#f59e0b' : '#0284c7';
      const bgClass = isSolar ? 'bg-amber-500' : 'bg-sky-500';
      const ringClass = isSelected ? 'ring-4 ring-amber-300 scale-125 z-50' : 'ring-2 ring-white';

      const iconHtml = `
        <div style="transform: translate(-50%, -50%); cursor: pointer;" class="flex items-center justify-center">
          <div style="background-color: ${color}; width: 28px; height: 28px;" class="rounded-full shadow-md flex items-center justify-center text-white border-2 border-white ${ringClass}">
            <span style="font-size: 13px; font-weight: bold;">${isSolar ? '☀️' : '💨'}</span>
          </div>
        </div>
      `;

      const customIcon = L.divIcon({
        html: iconHtml,
        className: 'custom-plant-marker',
        iconSize: [28, 28],
        iconAnchor: [14, 14],
      });

      const marker = L.marker([p.latitude, p.longitude], { icon: customIcon });

      const popupContent = `
        <div style="font-family: inherit; min-width: 170px;" class="p-1">
          <div style="font-size: 13px; font-weight: 700; color: #0f172a; margin-bottom: 2px;">${p.name}</div>
          <div style="display: flex; align-items: center; gap: 4px; margin-bottom: 6px;">
            <span style="display: inline-block; padding: 2px 6px; font-size: 10px; font-weight: 600; border-radius: 4px; background: ${
              isSolar ? '#fef3c7' : '#e0f2fe'
            }; color: ${isSolar ? '#92400e' : '#0369a1'}">
              ${p.plant_type}
            </span>
            <span style="font-size: 11px; font-weight: 600; color: #334155;">${p.capacity_mw} MW</span>
          </div>
          <div style="font-size: 10px; color: #64748b; line-height: 1.4;">
            <div>Lat: ${p.latitude.toFixed(4)}°, Lon: ${p.longitude.toFixed(4)}°</div>
            <div>TZ: ${p.timezone}</div>
          </div>
        </div>
      `;

      marker.bindPopup(popupContent);

      if (onSelectPlant) {
        marker.on('click', () => {
          onSelectPlant(p);
        });
      }

      marker.addTo(markers);
      bounds.push([p.latitude, p.longitude]);
    });

    if (plant && hasValidCoords) {
      map.setView([plant.latitude, plant.longitude], 12);
    } else if (bounds.length > 0) {
      if (bounds.length === 1) {
        map.setView(bounds[0], 11);
      } else {
        map.fitBounds(L.latLngBounds(bounds), { padding: [40, 40] });
      }
    } else {
      map.setView([20.5937, 78.9629], 5);
    }

    // Force size calculation once visible
    setTimeout(() => {
      map.invalidateSize();
    }, 150);
  }, [plant, plants, hasValidCoords, onSelectPlant]);

  // Handle ResizeObserver
  useEffect(() => {
    if (!mapContainerRef.current) return;
    const observer = new ResizeObserver(() => {
      if (mapInstanceRef.current) {
        mapInstanceRef.current.invalidateSize();
      }
    });
    observer.observe(mapContainerRef.current);
    return () => observer.disconnect();
  }, []);

  return (
    <div className="relative w-full rounded-xl overflow-hidden border border-slate-200 shadow-xs bg-slate-100">
      {!hasValidCoords && !plants?.length && (
        <div className="absolute inset-0 z-20 flex flex-col items-center justify-center bg-white/90 backdrop-blur-xs p-6 text-center">
          <AlertTriangle className="h-8 w-8 text-amber-500 mb-2" />
          <p className="text-sm font-semibold text-slate-800">Missing Geolocation Coordinates</p>
          <p className="text-xs text-slate-500 mt-1 max-w-sm">
            Please edit this plant to configure valid latitude (-90 to 90) and longitude (-180 to 180) to visualize its geospatial location and weather telemetry.
          </p>
        </div>
      )}
      <div ref={mapContainerRef} style={{ height }} className="w-full z-10" />
      <div className="absolute bottom-2 left-2 z-20 bg-white/90 backdrop-blur-xs px-2.5 py-1 rounded-md border border-slate-200 text-[11px] text-slate-600 flex items-center gap-1.5 shadow-xs">
        <MapPin className="h-3.5 w-3.5 text-amber-600" />
        <span>OpenStreetMap Leaflet Engine</span>
      </div>
    </div>
  );
};
