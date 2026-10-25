import Link from "next/link";
import { ArrowRight, Database, Gauge, LayoutDashboard, Pill, Search } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

function SignalBackdrop() {
  const rows = [
    ["Aspirin", "Low", "52.5%"],
    ["Warfarin", "High", "88.1%"],
    ["Metformin", "Medium", "76.8%"]
  ];

  return (
    <div className="absolute inset-0 overflow-hidden signal-grid" aria-hidden="true">
      <div className="absolute right-6 top-20 hidden w-[440px] rounded-lg border bg-white/80 p-4 shadow-sm backdrop-blur md:block">
        <div className="mb-4 flex items-center justify-between">
          <div className="h-3 w-28 rounded-sm bg-slate-900" />
          <div className="h-3 w-16 rounded-sm bg-teal-700" />
        </div>
        <div className="space-y-3">
          {rows.map((row, index) => (
            <div
              key={row[0]}
              className="signal-pulse grid grid-cols-[1fr_80px_70px] items-center gap-3 rounded-md border bg-white px-3 py-2"
              style={{ animationDelay: `${index * 0.7}s` }}
            >
              <span className="text-sm font-medium text-slate-800">{row[0]}</span>
              <span className="text-xs text-slate-500">{row[1]}</span>
              <span className="text-right text-sm font-semibold text-cyan-800">{row[2]}</span>
            </div>
          ))}
        </div>
      </div>
      <div className="absolute bottom-14 right-16 hidden h-36 w-64 items-end gap-3 rounded-lg border bg-white/75 p-4 shadow-sm backdrop-blur lg:flex">
        {[42, 76, 58, 96, 68, 112, 84].map((height, index) => (
          <span
            key={height}
            className="w-6 rounded-sm bg-cyan-700/80 signal-pulse"
            style={{ height, animationDelay: `${index * 0.35}s` }}
          />
        ))}
      </div>
    </div>
  );
}

export default function Home() {
  return (
    <main id="content">
      <section className="relative min-h-[calc(100vh-4rem)] overflow-hidden">
        <SignalBackdrop />
        <div className="relative mx-auto flex min-h-[calc(100vh-4rem)] max-w-7xl items-center px-4 py-16 sm:px-6 lg:px-8">
          <div className="grid w-full grid-cols-1 items-center gap-10 md:grid-cols-2">
            <div className="max-w-xl">
            <Badge variant="secondary" className="mb-5">
              FAERS side-effect intelligence
            </Badge>
            <h1 className="text-4xl font-semibold tracking-tight sm:text-5xl lg:text-6xl motion-safe:fade-in">
              Machine learning for smarter pharmaceutical prediction
            </h1>
            <p className="mt-5 max-w-xl text-lg leading-8 text-muted-foreground">
              PharmaLens analyzes adverse-event reports to estimate drug risk, rank reaction signals, and
              generate concise technical reports for analysts and reviewers.
            </p>
            <div className="mt-8 flex flex-col gap-3 sm:flex-row">
              <Link href="/predict">
                <Button className="h-11 px-6 shadow-sm" style={{ transform: "translateZ(0)" }}>
                  Start prediction
                  <ArrowRight className="h-4 w-4" aria-hidden="true" />
                </Button>
              </Link>
              <Link href="/dashboard">
                <Button className="h-11 px-6 border bg-background hover:bg-muted">
                  View dashboard
                  <LayoutDashboard className="h-4 w-4" aria-hidden="true" />
                </Button>
              </Link>
            </div>
          </div>
            <div className="hidden md:block motion-safe:fade-in" aria-hidden>
              <div className="rounded-xl border bg-card p-6 shadow-lg">
                <h3 className="mb-3 text-sm font-medium text-muted-foreground">Live signals</h3>
                <div className="flex h-44 items-end gap-3">
                  {[68, 110, 82, 96, 74, 128, 92].map((h, i) => (
                    <div key={i} className="flex-1">
                      <div className="mx-auto h-full w-3 rounded-sm bg-gradient-to-t from-cyan-700/80 to-cyan-400" style={{ height: `${h}px` }} />
                    </div>
                  ))}
                </div>
                <p className="mt-4 text-sm text-muted-foreground">Realtime FAERS-derived signal strength across recent submissions.</p>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="mx-auto max-w-7xl px-4 py-12 sm:px-6 lg:px-8">
        <div className="rounded-lg border bg-card p-6 shadow-sm">
          <h2 className="text-lg font-semibold">How PharmaLens works</h2>
          <div className="mt-4 grid gap-4 md:grid-cols-5">
            {[
              "Input Data",
              "ML Processing",
              "Prediction",
              "Confidence",
              "Report"
            ].map((step, idx) => (
              <div key={step} className="flex flex-col items-center gap-2 text-center">
                <div className="flex h-12 w-12 items-center justify-center rounded-full bg-gradient-to-tr from-cyan-700 to-teal-400 text-white shadow">{idx + 1}</div>
                <div className="text-sm font-medium">{step}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="border-y bg-white">
        <div className="mx-auto grid max-w-7xl gap-4 px-4 py-8 sm:px-6 md:grid-cols-3 lg:px-8">
          {[
            { icon: Search, title: "Input drug", text: "Enter a medication name." },
            { icon: Gauge, title: "Predict risk", text: "Fetch FAERS signals and classify risk." },
            { icon: Database, title: "View dashboard", text: "Review model metrics and trends." }
          ].map((item) => (
            <div key={item.title} className="flex items-center gap-4 rounded-lg border bg-background p-4">
              <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-md bg-accent text-accent-foreground">
                <item.icon className="h-5 w-5" aria-hidden="true" />
              </div>
              <div>
                <h2 className="text-sm font-semibold">{item.title}</h2>
                <p className="text-sm text-muted-foreground">{item.text}</p>
              </div>
            </div>
          ))}
        </div>
      </section>

      <section className="mx-auto grid max-w-7xl gap-4 px-4 py-12 sm:px-6 md:grid-cols-3 lg:px-8">
        {[
          { title: "Report-level ML", text: "Notebook-trained classifiers assess serious adverse-event reports." },
          { title: "Drug-level summary", text: "The API returns observed report statistics and ranked reactions." },
          { title: "Deployment-ready", text: "FastAPI backend, typed frontend client, and container-friendly setup." }
        ].map((item) => (
          <Card key={item.title}>
            <CardHeader>
              <CardTitle>{item.title}</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-sm leading-6 text-muted-foreground">{item.text}</p>
            </CardContent>
          </Card>
        ))}
      </section>
    </main>
  );
}

