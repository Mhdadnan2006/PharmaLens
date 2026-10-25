export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") ?? "http://localhost:8000";

export type RiskLevel = "Low" | "Medium" | "High" | "Critical" | "Unknown";

export interface SideEffect {
  name: string;
  count: number;
  probability: number;
}

export interface ConfidenceInterval {
  confidence_level: number;
  lower: number | null;
  upper: number | null;
  method: string;
  unit: string;
}

export interface PredictResponse {
  drug_name: string;
  risk_level: RiskLevel;
  confidence: number;
  confidence_interval: ConfidenceInterval;
  serious_report_percentage: number | null;
  report_count: number;
  side_effects: SideEffect[];
  model: {
    loaded: boolean;
    name?: string | null;
    report_level_summary?: Record<string, number> | null;
  };
  message: string;
}

export interface MetricRow {
  accuracy: number;
  precision?: number;
  recall?: number;
  f1: number;
  roc_auc?: number;
  confusion_matrix?: number[][];
  combined_score?: number;
}

export interface MetricsResponse {
  source_notebook: string;
  selected_model: string;
  selection_rule: string;
  test_set: Record<string, MetricRow>;
  training_set: Record<string, MetricRow>;
  cross_validation: Record<string, MetricRow | number | string>;
  feature_importance: {
    available: boolean;
    values: Array<{ feature: string; importance: number }>;
    unavailable_reason?: string;
  };
}

export interface LatencyPoint {
  label: string;
  p50: number;
  p95: number;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...init?.headers
    }
  });

  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || `Request failed with status ${response.status}`);
  }

  return response.json() as Promise<T>;
}

export function predictDrug(drugName: string, modelName?: string | null) {
  const body: Record<string, unknown> = { drug_name: drugName };
  if (modelName) body.model_name = modelName;
  return request<PredictResponse>("/predict", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function getMetrics() {
  return request<MetricsResponse>("/metrics");
}

export function getLatencySeries() {
  return request<LatencyPoint[]>("/latency");
}

export interface AvailableModel {
  key: string;
  name: string;
  alias: string;
  artifact: string;
  available: boolean;
  selected_by_default: boolean;
}

export interface ModelsResponse {
  models: AvailableModel[];
  preprocessor_loaded: boolean;
}

export function getAvailableModels() {
  return request<ModelsResponse>("/models");
}

export function setSelectedModel(modelName: string) {
  return request<{ selected_model: string }>("/metrics/select", {
    method: "POST",
    body: JSON.stringify({ selected_model: modelName }),
  });
}

export async function generateReport(prediction: PredictResponse): Promise<{ blob: Blob; summary: string }> {
  const resp = await fetch(`${API_BASE_URL}/report`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "application/pdf",
    },
    body: JSON.stringify(prediction),
  });

  if (!resp.ok) {
    const text = await resp.text();
    throw new Error(text || `Report generation failed: ${resp.status}`);
  }

  const encodedSummary = resp.headers.get("X-PharmaLens-Summary-Base64");
  let summary = "";
  if (encodedSummary) {
    const bytes = Uint8Array.from(atob(encodedSummary), (character) => character.charCodeAt(0));
    summary = new TextDecoder().decode(bytes);
  }
  return { blob: await resp.blob(), summary };
}
