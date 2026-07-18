import { useCallback, useEffect } from "react";
import { MapContainer, TileLayer, Marker, useMap, useMapEvents } from "react-leaflet";
import L from "leaflet";

const ICON = L.divIcon({
  className: "solar-marker",
  html: `<svg width="32" height="32" viewBox="0 0 32 32" fill="none">
    <circle cx="16" cy="16" r="14" fill="#F59E0B" opacity="0.3"/>
    <circle cx="16" cy="16" r="8" fill="#F59E0B"/>
    <circle cx="16" cy="16" r="4" fill="#fff"/>
  </svg>`,
  iconSize: [32, 32],
  iconAnchor: [16, 16],
});

interface Props {
  lat: number;
  lng: number;
  onChange: (lat: number, lng: number) => void;
}

function ClickHandler({ onChange }: { onChange: (lat: number, lng: number) => void }) {
  useMapEvents({
    click(e) {
      onChange(e.latlng.lat, e.latlng.lng);
    },
  });
  return null;
}

function CenterUpdater({ lat, lng }: { lat: number; lng: number }) {
  const map = useMap();
  useEffect(() => {
    map.setView([lat, lng], map.getZoom());
  }, [lat, lng, map]);
  return null;
}

export default function MapPicker({ lat, lng, onChange }: Props) {
  const handleClick = useCallback(
    (newLat: number, newLng: number) => {
      onChange(Math.round(newLat * 10000) / 10000, Math.round(newLng * 10000) / 10000);
    },
    [onChange]
  );

  return (
    <MapContainer center={[lat, lng]} zoom={5} scrollWheelZoom={true} style={{ height: "100%", width: "100%", borderRadius: 12 }}>
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      <ClickHandler onChange={handleClick} />
      <CenterUpdater lat={lat} lng={lng} />
      <Marker position={[lat, lng]} icon={ICON} draggable={true}
        eventHandlers={{
          dragend: (e) => {
            const m = e.target;
            const pos = m.getLatLng();
            handleClick(pos.lat, pos.lng);
          },
        }}
      />
    </MapContainer>
  );
}
