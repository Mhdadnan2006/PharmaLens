"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import { Download, Loader2, Search, ShieldCheck } from "lucide-react";

import { Badge, type BadgeProps } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import {
  predictDrug,
  generateReport,
  getAvailableModels,
  type AvailableModel,
  type PredictResponse,
  type RiskLevel
} from "@/lib/api";

const AUTOCOMPLETE_DRUGS = [
  "aspirin",
  "ibuprofen",
  "acetaminophen",
  "metformin",
  "atorvastatin",
  "lisinopril",
  "amoxicillin",
  "omeprazole",
  "warfarin",
  "prednisone"
];

function riskVariant(risk: RiskLevel): BadgeProps["variant"] {
  const key = risk.toLowerCase();
  if (key === "low") return "low";
  if (key === "medium") return "medium";
  if (key === "high") return "high";
  if (key === "critical") return "critical";
  return "unknown";
}

function percent(value: number) {
  return `${(value * 100).toFixed(1)}%`;
}

export default function PredictPage() {
  const [drugName, setDrugName] = useState("");
  const [result, setResult] = useState<PredictResponse | null>(null);
  const [modelName, setModelName] = useState<string | null>(null);
  const [availableModels, setAvailableModels] = useState<AvailableModel[]>([]);
  const [modelsLoading, setModelsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [downloadLoading, setDownloadLoading] = useState(false);
  const [downloadError, setDownloadError] = useState<string | null>(null);
  const [reportSummary, setReportSummary] = useState<string | null>(null);

  const suggestions = useMemo(() => {
    const query = drugName.trim().toLowerCase();
    if (!query) return AUTOCOMPLETE_DRUGS.slice(0, 5);
    return AUTOCOMPLETE_DRUGS.filter((drug) => drug.includes(query)).slice(0, 5);
  }, [drugName]);

  const [activeIndex, setActiveIndex] = useState<number>(-1);

  function handleKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setActiveIndex((i) => Math.min(i + 1, suggestions.length - 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setActiveIndex((i) => Math.max(i - 1, 0));
    } else if (e.key === "Enter") {
      if (activeIndex >= 0) {
        e.preventDefault();
        setDrugName(suggestions[activeIndex]);
        setActiveIndex(-1);
      }
    } else if (e.key === "Escape") {
      setActiveIndex(-1);
    }
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoading(true);
    setError(null);
    setResult(null);
    setReportSummary(null);
    setDownloadError(null);

    try {
      const response = await predictDrug(drugName, modelName ?? undefined);
      setResult(response);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Prediction failed");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    let mounted = true;
    setModelsLoading(true);
    getAvailableModels()
      .then((res) => {
        if (!mounted) return;
        const models = res.models ?? [];
        setAvailableModels(models);
        const defaultModel = models.find((model) => model.available && model.selected_by_default);
        const firstAvailable = models.find((model) => model.available);
        setModelName((current) => current ?? defaultModel?.key ?? firstAvailable?.key ?? null);
      })
      .catch(() => {
        if (!mounted) return;
        setAvailableModels([]);
      })
      .finally(() => {
        if (!mounted) return;
        setModelsLoading(false);
      });
    return () => {
      mounted = false;
    };
  }, []);

  return (
    <main id="content" className="mx-auto max-w-6xl px-4 py-10 sm:px-6 lg:px-8">
      <div className="mb-8 flex flex-col justify-between gap-4 md:flex-row md:items-end">
        <div>
          <Badge variant="outline" className="mb-3">
            Prediction
          </Badge>
          <h1 className="text-3xl font-semibold tracking-normal">Drug risk Predictor</h1>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-muted-foreground">
            Enter a drug name to estimate FAERS report risk and rank commonly reported side effects.
          </p>
        </div>
        <Button
          type="button"
          variant="outline"
          onClick={async () => {
            if (!result) return;
            setDownloadError(null);
            setDownloadLoading(true);
            try {
              const report = await generateReport(result);
              setReportSummary(report.summary || "Report generated successfully.");
              const url = URL.createObjectURL(report.blob);
              const a = document.createElement("a");
              a.href = url;
              const name = result?.drug_name?.replace(/\s+/g, "_") ?? "report";
              a.download = `pharmalens_report_${name}.pdf`;
              document.body.appendChild(a);
              a.click();
              a.remove();
              URL.revokeObjectURL(url);
            } catch (err) {
              setDownloadError(err instanceof Error ? err.message : String(err));
            } finally {
              setDownloadLoading(false);
            }
          }}
          disabled={!result || downloadLoading}
        >
          {downloadLoading ? (
            <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
          ) : (
            <Download className="h-4 w-4" aria-hidden="true" />
          )}
          Generate & download report
        </Button>
        {downloadError ? <p className="text-sm text-red-700">{downloadError}</p> : null}
      </div>

      <div className="grid gap-6 lg:grid-cols-[420px_1fr]">
        <Card>
          <CardHeader>
            <CardTitle>Search drug</CardTitle>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="relative">
                <Search className="pointer-events-none absolute left-3 top-3.5 h-4 w-4 text-muted-foreground" />
                <Input
                  id="drug-input"
                  aria-label="Drug name"
                  aria-autocomplete="list"
                  aria-controls="drug-suggestions"
                  aria-activedescendant={activeIndex >= 0 ? `suggestion-${activeIndex}` : undefined}
                  value={drugName}
                  onChange={(event) => {
                    setDrugName(event.target.value);
                    setActiveIndex(-1);
                  }}
                  onKeyDown={handleKeyDown}
                  placeholder="aspirin"
                  className="pl-9"
                  autoComplete="off"
                />
              </div>
              <div>
                <ul id="drug-suggestions" role="listbox" className="flex flex-wrap gap-2">
                  {suggestions.map((drug, idx) => (
                    <li key={drug} role="option" aria-selected={activeIndex === idx} id={`suggestion-${idx}`}>
                      <button
                        type="button"
                        onClick={() => {
                          setDrugName(drug);
                          setActiveIndex(-1);
                        }}
                        onMouseEnter={() => setActiveIndex(idx)}
                        className={
                          "rounded-md border px-2.5 py-1 text-xs transition-colors " +
                          (activeIndex === idx
                            ? "bg-primary text-primary-foreground"
                            : "text-muted-foreground hover:border-primary hover:text-primary")
                        }
                      >
                        {drug}
                      </button>
                    </li>
                  ))}
                </ul>
              </div>
              <div>
                <label htmlFor="model-select" className="text-sm text-muted-foreground block mb-2">
                  Choose algorithm
                </label>
                <select
                  id="model-select"
                  className="w-full rounded-md border px-2 py-1"
                  value={modelName ?? ""}
                  onChange={(e) => setModelName(e.target.value || null)}
                >
                  <option value="">Notebook statistic only</option>
                  {modelsLoading ? (
                    <option value="">Loading models...</option>
                  ) : (
                    availableModels.map((m) => (
                      <option key={m.key} value={m.key} disabled={!m.available}>
                        {m.name}{m.available ? "" : " (artifact missing)"}
                      </option>
                    ))
                  )}
                </select>
                {!modelsLoading && !availableModels.some((model) => model.available) ? (
                  <p className="mt-2 text-xs text-muted-foreground">No serialized model artifacts are loaded on the server.</p>
                ) : null}
              </div>
              <Button type="submit" className="w-full" disabled={loading || !drugName.trim()}>
                {loading ? (
                  <div className="flex items-center gap-2">
                    <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
                    <span>Analyzing</span>
                  </div>
                ) : (
                  <ShieldCheck className="h-4 w-4" aria-hidden="true" />
                )}
                Predict risk
              </Button>
            </form>
            {error ? (
              <p className="mt-4 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
                {error}
              </p>
            ) : null}
            <div aria-live="polite" className="sr-only">
              {loading ? `Analyzing ${drugName}` : result ? `Prediction ready: ${result.risk_level} risk for ${result.drug_name}` : ""}
            </div>
          </CardContent>
        </Card>

        <section className="space-y-6">
          {loading ? (
            <>
              <Card>
                <CardContent>
                  <div className="space-y-4">
                    <div className="h-3 w-2/3 rounded bg-muted/60" />
                    <div className="h-2 w-full rounded bg-muted/40" />
                    <div className="flex items-center gap-2">
                      <div className="h-2 w-full rounded bg-primary/30 animate-pulse" />
                    </div>
                    <p className="text-sm text-muted-foreground">Processing the model and fetching signals…</p>
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardContent>
                  <div className="space-y-3">
                    <div className="h-12 rounded bg-muted/40" />
                    <div className="h-12 rounded bg-muted/40" />
                    <div className="h-12 rounded bg-muted/40" />
                  </div>
                </CardContent>
              </Card>
            </>
          ) : result ? (
            <>
              <Card className="overflow-hidden motion-safe:fade-in">
                <CardHeader className="flex-row items-start justify-between space-y-0">
                  <div>
                    <CardTitle className="capitalize">{result.drug_name}</CardTitle>
                    <p className="mt-2 text-sm text-muted-foreground">{result.report_count} reports analyzed</p>
                  </div>
                  <Badge variant={riskVariant(result.risk_level)}>{result.risk_level}</Badge>
                </CardHeader>
                <CardContent>
                  <div className="grid gap-4 sm:grid-cols-3">
                    <div className="rounded-lg border p-4 bg-gradient-to-b from-white/40 to-white/0 dark:from-card dark:to-card">
                      <p className="text-xs text-muted-foreground">Serious reports</p>
                      <p className="mt-2 text-2xl font-semibold"><span className="stat-counter">
                        {result.serious_report_percentage === null
                          ? "N/A"
                          : `${result.serious_report_percentage.toFixed(1)}%`}
                      </span>
                      </p>
                    </div>
                    <div className="rounded-lg border p-4 bg-gradient-to-b from-white/40 to-white/0 dark:from-card dark:to-card">
                      <p className="text-xs text-muted-foreground">Confidence</p>
                      <p className="mt-2 text-2xl font-semibold">{percent(result.confidence)}</p>
                    </div>
                    <div className="rounded-lg border p-4 bg-gradient-to-b from-white/40 to-white/0 dark:from-card dark:to-card">
                      <p className="text-xs text-muted-foreground">95% interval</p>
                      <p className="mt-2 text-lg font-semibold">
                        {result.confidence_interval.lower === null
                          ? "N/A"
                          : `${result.confidence_interval.lower.toFixed(1)}-${result.confidence_interval.upper?.toFixed(1)}%`}
                      </p>
                    </div>
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle>Selected model</CardTitle>
                </CardHeader>
                <CardContent>
                  {result.model.name && result.model.report_level_summary ? (
                    <div className="grid gap-4 sm:grid-cols-3">
                      <div className="rounded-lg border p-4">
                        <p className="text-xs text-muted-foreground">Algorithm</p>
                        <p className="mt-2 font-semibold">{result.model.name}</p>
                      </div>
                      <div className="rounded-lg border p-4">
                        <p className="text-xs text-muted-foreground">Mean serious probability</p>
                        <p className="mt-2 text-2xl font-semibold">
                          {percent(result.model.report_level_summary.mean_probability_serious)}
                        </p>
                      </div>
                      <div className="rounded-lg border p-4">
                        <p className="text-xs text-muted-foreground">Predicted serious reports</p>
                        <p className="mt-2 text-2xl font-semibold">
                          {percent(result.model.report_level_summary.predicted_serious_report_fraction)}
                        </p>
                      </div>
                    </div>
                  ) : (
                    <p className="text-sm text-muted-foreground">
                      No classifier artifact is loaded. This result uses the direct FAERS statistic.
                    </p>
                  )}
                </CardContent>
              </Card>

              {reportSummary ? (
                <Card>
                  <CardHeader>
                    <CardTitle>AI report summary</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <p className="whitespace-pre-line text-sm leading-6 text-muted-foreground">{reportSummary}</p>
                  </CardContent>
                </Card>
              ) : null}

              <Card>
                <CardHeader>
                  <CardTitle>Ranked side effects</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-3">
                    {result.side_effects.length > 0 ? (
                      result.side_effects.map((effect, index) => (
                        <div key={effect.name} className="grid gap-2 rounded-lg border p-3 sm:grid-cols-[32px_1fr_90px] sm:items-center hover:shadow-sm transition-shadow">
                          <span className="flex h-8 w-8 items-center justify-center rounded-md bg-muted text-sm font-semibold">
                            {index + 1}
                          </span>
                          <div>
                            <p className="font-medium">{effect.name}</p>
                            <p className="text-sm text-muted-foreground">{effect.count} reports</p>
                          </div>
                          <p className="text-left font-semibold text-cyan-800 sm:text-right">{percent(effect.probability)}</p>
                        </div>
                      ))
                    ) : (
                      <p className="rounded-lg border p-4 text-sm text-muted-foreground">No ranked side effects returned.</p>
                    )}
                  </div>
                </CardContent>
              </Card>
            </>
          ) : (
            <Card className="min-h-[320px]">
              <CardContent className="flex h-[320px] items-center justify-center text-center">
                <div>
                  <ShieldCheck className="mx-auto h-10 w-10 text-cyan-800" aria-hidden="true" />
                  <p className="mt-3 text-sm text-muted-foreground">Prediction results will appear here.</p>
                </div>
              </CardContent>
            </Card>
          )}
        </section>
      </div>
    </main>
  );
}
