"use client";

import { useEffect, useMemo, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis
} from "recharts";
import { Activity, Gauge, Loader2, TrendingUp } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { getLatencySeries, getMetrics, setSelectedModel, type MetricsResponse, type LatencyPoint } from "@/lib/api";

function metricPercent(value?: number) {
  if (typeof value !== "number") return "N/A";
  return `${(value * 100).toFixed(1)}%`;
}

function flattenMatrix(matrix?: number[][]) {
  if (!matrix) return [];
  return [
    { label: "TN", count: matrix[0]?.[0] ?? 0 },
    { label: "FP", count: matrix[0]?.[1] ?? 0 },
    { label: "FN", count: matrix[1]?.[0] ?? 0 },
    { label: "TP", count: matrix[1]?.[1] ?? 0 }
  ];
}

export default function DashboardPage() {
  const [metrics, setMetrics] = useState<MetricsResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [latencyData, setLatencyData] = useState<LatencyPoint[] | null>(null);
  const [latencyError, setLatencyError] = useState<string | null>(null);
  const [latencyLoading, setLatencyLoading] = useState(true);
  const [selectedModel, setSelectedModel] = useState<string | null>(null);
  const [persisting, setPersisting] = useState(false);

  useEffect(() => {
    setLoading(true);
    setError(null);
    getMetrics()
      .then(setMetrics)
      .catch((err) => setError(err instanceof Error ? err.message : "Could not load metrics"))
      .finally(() => setLoading(false));

    setLatencyLoading(true);
    setLatencyError(null);
    getLatencySeries()
      .then((data) => setLatencyData(data))
      .catch((err) => setLatencyError(err instanceof Error ? err.message : "Could not load latency series"))
      .finally(() => setLatencyLoading(false));
  }, []);

  const selectedMetrics = metrics?.test_set[selectedModel ?? metrics?.selected_model ?? ""];
  const matrixData = useMemo(
    () => flattenMatrix(selectedMetrics?.confusion_matrix),
    [selectedMetrics?.confusion_matrix]
  );

  return (
    <main id="content" className="mx-auto max-w-7xl px-4 py-10 sm:px-6 lg:px-8">
      <div className="mb-8 flex flex-col justify-between gap-4 md:flex-row md:items-end">
        <div>
          <Badge variant="outline" className="mb-3">
            Dashboard
          </Badge>
          <h1 className="text-3xl font-semibold tracking-normal">Model performance</h1>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-muted-foreground">
            Monitor notebook metrics, report classification quality, and prediction latency trends.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <select
            aria-label="Select model"
            className="rounded-md border px-2 py-1"
            value={selectedModel ?? metrics?.selected_model ?? ""}
            onChange={(e) => setSelectedModel(e.target.value)}
          >
            {metrics ? Object.keys(metrics.test_set).map((m) => <option key={m} value={m}>{m}</option>) : <option>Loading…</option>}
          </select>
          <Badge variant="secondary">{selectedModel ?? metrics?.selected_model ?? "Loading model"}</Badge>
          <button
            className="ml-2 rounded-md border px-3 py-1 text-sm"
            onClick={async () => {
              if (!selectedModel) return;
              setPersisting(true);
              try {
                await setSelectedModel(selectedModel);
                // Refresh metrics
                const refreshed = await getMetrics();
                setMetrics(refreshed);
              } catch (err) {
                // ignore; error will show in UI via existing error state if needed
              } finally {
                setPersisting(false);
              }
            }}
            disabled={persisting}
          >
            {persisting ? "Saving…" : "Set as default"}
          </button>
        </div>
      </div>

      {loading ? (
        <Card>
          <CardContent className="flex h-64 items-center justify-center gap-2 text-sm text-muted-foreground">
            <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
            Loading metrics
          </CardContent>
        </Card>
      ) : error ? (
        <Card>
          <CardContent className="p-5 text-sm text-red-700">{error}</CardContent>
        </Card>
      ) : metrics && selectedMetrics ? (
        <Tabs defaultValue="overview" className="space-y-6">
          <TabsList>
            <TabsTrigger value="overview">Overview</TabsTrigger>
            <TabsTrigger value="diagnostics">Diagnostics</TabsTrigger>
          </TabsList>

          <TabsContent value="overview" className="space-y-6">
            <div className="grid gap-4 md:grid-cols-3">
              {[
                { title: "Accuracy", value: metricPercent(selectedMetrics.accuracy), icon: Gauge },
                { title: "F1", value: metricPercent(selectedMetrics.f1), icon: TrendingUp },
                { title: "ROC-AUC", value: metricPercent(selectedMetrics.roc_auc), icon: Activity }
              ].map((item) => (
                <Card key={item.title} className="overflow-hidden">
                  <CardHeader className="flex-row items-center justify-between space-y-0">
                    <CardTitle className="text-sm font-medium">{item.title}</CardTitle>
                    <item.icon className="h-4 w-4 text-cyan-800" aria-hidden="true" />
                  </CardHeader>
                  <CardContent>
                    <p className="text-3xl font-semibold tracking-tight"><span className="stat-counter">{item.value}</span></p>
                    <p className="mt-2 text-sm text-muted-foreground">{item.title} measured on test set</p>
                  </CardContent>
                </Card>
              ))}
            </div>

            <div className="grid gap-6 lg:grid-cols-2">
              <Card>
                <CardHeader>
                  <CardTitle>Confusion matrix</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="h-72">
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={matrixData}>
                        <CartesianGrid strokeDasharray="3 3" strokeOpacity={0.06} />
                        <XAxis dataKey="label" />
                        <YAxis />
                        <Tooltip />
                        <Bar dataKey="count" fill="url(#colorUv)" radius={[6, 6, 6, 6]} />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle>Recent prediction latency</CardTitle>
                </CardHeader>
                <CardContent>
                  {latencyLoading ? (
                    <div className="flex h-72 items-center justify-center text-sm text-muted-foreground">
                      <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
                      <span className="ml-2">Loading latency</span>
                    </div>
                  ) : latencyError ? (
                    <div className="p-4 text-sm text-red-700">{latencyError}</div>
                  ) : (
                    <div className="h-72">
                      <ResponsiveContainer width="100%" height="100%">
                        <LineChart data={latencyData ?? []}>
                          <CartesianGrid strokeDasharray="3 3" strokeOpacity={0.06} />
                          <XAxis dataKey="label" />
                          <YAxis />
                          <Tooltip />
                          <Legend />
                          <Line type="monotone" dataKey="p50" stroke="#06b6d4" strokeWidth={2} dot={false} />
                          <Line type="monotone" dataKey="p95" stroke="#fb923c" strokeWidth={2} dot={false} />
                        </LineChart>
                      </ResponsiveContainer>
                    </div>
                  )}
                </CardContent>
              </Card>
            </div>
          </TabsContent>

          <TabsContent value="diagnostics" className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle>Feature importance</CardTitle>
              </CardHeader>
              <CardContent>
                {metrics.feature_importance.available && metrics.feature_importance.values.length > 0 ? (
                  <div className="h-80">
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={metrics.feature_importance.values} layout="vertical">
                        <CartesianGrid strokeDasharray="3 3" />
                        <XAxis type="number" />
                        <YAxis dataKey="feature" type="category" width={140} />
                        <Tooltip />
                        <Bar dataKey="importance" fill="#15803d" radius={[0, 4, 4, 0]} />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                ) : (
                  <p className="rounded-lg border p-4 text-sm leading-6 text-muted-foreground">
                    {metrics.feature_importance.unavailable_reason ?? "Feature importance is unavailable."}
                  </p>
                )}
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      ) : null}
    </main>
  );
}
