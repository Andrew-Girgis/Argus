import axios from "axios";
import type { FeedbackPayload } from "@/lib/types";

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

const api = axios.create({ baseURL: API_URL });

export async function fetchProperty(lat: number, lon: number) {
  const { data } = await api.post("/api/v1/property", { lat, lon });
  return data;
}

export async function fetchImages(lat: number, lon: number) {
  const { data } = await api.get("/api/v1/property/images", { params: { lat, lon } });
  return data;
}

export async function analyzeProperty(streetViewUrl: string, satelliteUrl: string) {
  const { data } = await api.post("/api/v1/property/analyze", {
    street_view_url: streetViewUrl,
    satellite_url: satelliteUrl,
  });
  return data;
}

export async function fetchIsochrone(lat: number, lon: number) {
  const { data } = await api.get("/api/v1/property/isochrone", { params: { lat, lon } });
  return data;
}

export async function fetchPois(lat: number, lon: number) {
  const { data } = await api.get("/api/v1/property/pois", { params: { lat, lon } });
  return data;
}

export async function submitFeedback(payload: FeedbackPayload): Promise<{ ok: boolean; error: string | null }> {
  const { data } = await api.post("/api/v1/feedback", payload);
  return data;
}
