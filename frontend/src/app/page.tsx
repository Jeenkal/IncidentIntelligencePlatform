"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import {
  Activity,
  AlertTriangle,
  ArrowRight,
  BookOpen,
  CheckCircle2,
  CirclePlus,
  Clock3,
  LayoutDashboard,
  RefreshCw,
  Search,
  ShieldAlert,
} from "lucide-react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { getIncidents } from "@/lib/api";
import type { Incident } from "@/types/incident";

const severityColors: Record<string, string> = {
  Critical: "#dc2626",
  High: "#ea580c",
  Medium: "#d97706",
  Low: "#16a34a",
};

function normalize(value?: string) {
  return (value || "").trim().toLowerCase();
}

function isCompleted(status?: string) {
  return ["completed", "resolved"].includes(normalize(status));
}

function isInvestigating(status?: string) {
  return ["investigating", "in progress", "in_progress"].includes(
    normalize(status)
  );
}

function isOpen(status?: string) {
  return ["open", "new"].includes(normalize(status));
}

function isInsufficientEvidence(report?: string | null) {
  return Boolean(
    report &&
      /insufficient evidence|insufficient context|not enough evidence/i.test(
        report
      )
  );
}

function formatDate(value?: string) {
  if (!value) return "—";

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;

  return new Intl.DateTimeFormat("en-IN", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  }).format(date);
}

function statusStyle(status: string) {
  const value = normalize(status);

  if (["completed", "resolved"].includes(value)) {
    return "bg-emerald-50 text-emerald-700 ring-emerald-600/20";
  }

  if (["investigating", "in progress", "in_progress"].includes(value)) {
    return "bg-blue-50 text-blue-700 ring-blue-600/20";
  }

  if (["failed"].includes(value)) {
    return "bg-red-50 text-red-700 ring-red-600/20";
  }

  return "bg-slate-100 text-slate-700 ring-slate-500/20";
}

function severityStyle(severity: string) {
  const value = normalize(severity);

  if (value === "critical") return "text-red-700 bg-red-50";
  if (value === "high") return "text-orange-700 bg-orange-50";
  if (value === "medium") return "text-amber-700 bg-amber-50";
  if (value === "low") return "text-emerald-700 bg-emerald-50";

  return "text-slate-700 bg-slate-100";
}

export default function DashboardPage() {
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [search, setSearch] = useState("");

  const loadIncidents = useCallback(async () => {
    setLoading(true);
    setError("");

    try {
      const data = await getIncidents();
      setIncidents(data);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Unable to load incidents."
      );
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadIncidents();
  }, [loadIncidents]);

  const critical = incidents.filter(
    (item) => normalize(item.severity) === "critical"
  ).length;

  const open = incidents.filter((item) => isOpen(item.status)).length;
  const investigating = incidents.filter((item) =>
    isInvestigating(item.status)
  ).length;
  const completed = incidents.filter((item) =>
    isCompleted(item.status)
  ).length;

  const insufficient = incidents.filter((item) =>
    isInsufficientEvidence(item.status)
  ).length;

  const severityData = ["Critical", "High", "Medium", "Low"].map((name) => ({
    name,
    count: incidents.filter(
      (item) => normalize(item.severity) === normalize(name)
    ).length,
  }));

  const domainData = Array.from(
    incidents.reduce((map, item) => {
      const domain = item.domain?.trim() || "Unspecified";
      map.set(domain, (map.get(domain) || 0) + 1);
      return map;
    }, new Map<string, number>()),
    ([domain, count]) => ({ domain, count })
  ).sort((a, b) => b.count - a.count);

  const filteredIncidents = incidents
    .filter((item) => {
      const query = search.toLowerCase();

      return (
        String(item.id).includes(query) ||
        item.title.toLowerCase().includes(query) ||
        (item.domain || "").toLowerCase().includes(query) ||
        item.status.toLowerCase().includes(query)
      );
    })
    .sort((a, b) => b.id - a.id)
    .slice(0, 8);

  const stats = [
    {
      label: "Total incidents",
      value: incidents.length,
      icon: Activity,
      color: "text-indigo-600 bg-indigo-50",
    },
    {
      label: "Open incidents",
      value: open,
      icon: AlertTriangle,
      color: "text-orange-600 bg-orange-50",
    },
    {
      label: "Investigating",
      value: investigating,
      icon: Clock3,
      color: "text-blue-600 bg-blue-50",
    },
    {
      label: "Completed",
      value: completed,
      icon: CheckCircle2,
      color: "text-emerald-600 bg-emerald-50",
    },
  ];

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900">
      <div className="flex min-h-screen">
        <aside className="hidden w-64 shrink-0 border-r border-slate-200 bg-white md:flex md:flex-col">
          <div className="flex h-20 items-center gap-3 border-b border-slate-100 px-6">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-indigo-600 text-white">
              <ShieldAlert size={23} />
            </div>
            <div>
              <p className="font-bold tracking-tight">Incident IQ</p>
              <p className="text-xs text-slate-500">Intelligence Platform</p>
            </div>
          </div>

          <nav className="flex-1 space-y-2 p-4">
            <p className="px-3 pb-2 pt-3 text-xs font-semibold uppercase tracking-wider text-slate-400">
              Workspace
            </p>

            <Link
              href="/"
              className="flex items-center gap-3 rounded-xl bg-indigo-50 px-3 py-3 font-medium text-indigo-700"
            >
              <LayoutDashboard size={19} />
              Dashboard
            </Link>

            <Link
              href="/incidents"
              className="flex items-center gap-3 rounded-xl px-3 py-3 text-slate-600 transition hover:bg-slate-100"
            >
              <Activity size={19} />
              Incidents
            </Link>

            <Link
              href="/knowledge-base"
              className="flex items-center gap-3 rounded-xl px-3 py-3 text-slate-600 transition hover:bg-slate-100"
            >
              <BookOpen size={19} />
              Knowledge Base
            </Link>
          </nav>

          <div className="border-t border-slate-100 p-5">
            <div className="rounded-xl bg-slate-50 p-4">
              <div className="mb-2 flex items-center gap-2 text-sm font-semibold">
                <span className="h-2 w-2 rounded-full bg-emerald-500" />
                Local AI architecture
              </div>
              <p className="text-xs leading-5 text-slate-500">
                FastAPI · PostgreSQL · pgvector · Ollama
              </p>
            </div>
          </div>
        </aside>

        <main className="min-w-0 flex-1">
          <header className="sticky top-0 z-10 flex min-h-20 flex-wrap items-center justify-between gap-4 border-b border-slate-200 bg-white px-5 py-4 sm:px-8">
            <div>
              <h1 className="text-xl font-bold tracking-tight">
                Incident overview
              </h1>
              <p className="mt-1 text-sm text-slate-500">
                Monitor incidents and investigate root causes.
              </p>
            </div>

            <div className="flex flex-wrap items-center gap-3">
              <button
                onClick={() => void loadIncidents()}
                disabled={loading}
                className="flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-sm font-medium hover:bg-slate-50 disabled:opacity-50"
              >
                <RefreshCw
                  size={16}
                  className={loading ? "animate-spin" : ""}
                />
                Refresh
              </button>

              <Link
                href="/incidents/new"
                className="flex items-center gap-2 rounded-xl bg-indigo-600 px-4 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:bg-indigo-700"
              >
                <CirclePlus size={17} />
                New incident
              </Link>
            </div>
          </header>

          <div className="mx-auto max-w-[1600px] space-y-7 p-5 sm:p-8">
            {error && (
              <div
                role="alert"
                className="flex flex-col gap-3 rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-800 sm:flex-row sm:items-center sm:justify-between"
              >
                <div>
                  <p className="font-semibold">Could not load incidents</p>
                  <p className="mt-1 break-words">{error}</p>
                  <p className="mt-1 text-red-700">
                    Confirm that FastAPI is running and the GET /incidents
                    endpoint is available.
                  </p>
                </div>
                <button
                  onClick={() => void loadIncidents()}
                  className="shrink-0 rounded-lg border border-red-300 px-3 py-2 font-semibold hover:bg-red-100"
                >
                  Try again
                </button>
              </div>
            )}

            <section className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
              {stats.map((stat) => {
                const Icon = stat.icon;

                return (
                  <div
                    key={stat.label}
                    className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm"
                  >
                    <div className="flex items-center justify-between">
                      <p className="text-sm font-medium text-slate-500">
                        {stat.label}
                      </p>
                      <div
                        className={`flex h-10 w-10 items-center justify-center rounded-xl ${stat.color}`}
                      >
                        <Icon size={20} />
                      </div>
                    </div>

                    <p className="mt-4 text-3xl font-bold tracking-tight">
                      {loading ? "—" : stat.value}
                    </p>
                    <p className="mt-2 text-xs text-slate-400">
                      Based on returned incident records
                    </p>
                  </div>
                );
              })}
            </section>

            <section className="grid grid-cols-1 gap-6 xl:grid-cols-2">
              <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6">
                <div className="mb-6">
                  <h2 className="font-bold">Severity distribution</h2>
                  <p className="mt-1 text-sm text-slate-500">
                    Incidents grouped by recorded severity
                  </p>
                </div>

                {loading ? (
                  <div className="flex h-64 items-center justify-center text-sm text-slate-400">
                    Loading chart…
                  </div>
                ) : (
                  <div className="h-64 w-full">
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart
                        data={severityData}
                        margin={{ top: 5, right: 10, left: -20, bottom: 5 }}
                      >
                        <CartesianGrid
                          strokeDasharray="3 3"
                          vertical={false}
                          stroke="#e2e8f0"
                        />
                        <XAxis
                          dataKey="name"
                          axisLine={false}
                          tickLine={false}
                          tick={{ fill: "#64748b", fontSize: 12 }}
                        />
                        <YAxis
                          allowDecimals={false}
                          axisLine={false}
                          tickLine={false}
                          tick={{ fill: "#64748b", fontSize: 12 }}
                        />
                        <Tooltip />
                        <Bar dataKey="count" name="Incidents" radius={[6, 6, 0, 0]}>
                          {severityData.map((entry) => (
                            <Cell
                              key={entry.name}
                              fill={severityColors[entry.name]}
                            />
                          ))}
                        </Bar>
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                )}
              </div>

              <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6">
                <div className="mb-6">
                  <h2 className="font-bold">Domain distribution</h2>
                  <p className="mt-1 text-sm text-slate-500">
                    Where incidents originate
                  </p>
                </div>

                {loading ? (
                  <div className="flex h-64 items-center justify-center text-sm text-slate-400">
                    Loading chart…
                  </div>
                ) : domainData.length === 0 ? (
                  <div className="flex h-64 items-center justify-center text-sm text-slate-400">
                    No incident data available.
                  </div>
                ) : (
                  <div className="h-64 w-full">
                    <ResponsiveContainer width="100%" height="100%">
                      <PieChart>
                        <Pie
                          data={domainData}
                          dataKey="count"
                          nameKey="domain"
                          cx="50%"
                          cy="50%"
                          innerRadius={55}
                          outerRadius={90}
                          paddingAngle={3}
                        >
                          {domainData.map((entry, index) => (
                            <Cell
                              key={entry.domain}
                              fill={[
                                "#4f46e5",
                                "#0d9488",
                                "#ea580c",
                                "#7c3aed",
                                "#0284c7",
                                "#ca8a04",
                              ][index % 6]}
                            />
                          ))}
                        </Pie>
                        <Tooltip />
                      </PieChart>
                    </ResponsiveContainer>
                  </div>
                )}

                <div className="mt-3 flex flex-wrap gap-x-4 gap-y-2">
                  {domainData.slice(0, 6).map((item, index) => (
                    <div
                      key={item.domain}
                      className="flex items-center gap-2 text-xs text-slate-600"
                    >
                      <span
                        className="h-2.5 w-2.5 rounded-full"
                        style={{
                          backgroundColor: [
                            "#4f46e5",
                            "#0d9488",
                            "#ea580c",
                            "#7c3aed",
                            "#0284c7",
                            "#ca8a04",
                          ][index % 6],
                        }}
                      />
                      {item.domain} ({item.count})
                    </div>
                  ))}
                </div>
              </div>
            </section>

            {insufficient > 0 && (
              <section className="flex items-start gap-3 rounded-2xl border border-amber-200 bg-amber-50 p-5">
                <AlertTriangle className="mt-0.5 shrink-0 text-amber-700" />
                <div>
                  <h2 className="font-semibold text-amber-900">
                    Evidence needs review
                  </h2>
                  <p className="mt-1 text-sm text-amber-800">
                    {insufficient} incident report(s) contain wording that
                    indicates insufficient evidence. Review their reports
                    before making root-cause conclusions.
                  </p>
                </div>
              </section>
            )}

            <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
              <div className="flex flex-col gap-4 border-b border-slate-100 p-5 sm:flex-row sm:items-center sm:justify-between sm:p-6">
                <div>
                  <h2 className="font-bold">Recent incidents</h2>
                  <p className="mt-1 text-sm text-slate-500">
                    Latest records returned by the backend
                  </p>
                </div>

                <div className="flex flex-wrap items-center gap-3">
                  <label className="flex min-w-0 items-center gap-2 rounded-xl border border-slate-200 px-3 py-2">
                    <Search size={16} className="text-slate-400" />
                    <input
                      value={search}
                      onChange={(event) => setSearch(event.target.value)}
                      placeholder="Search incidents…"
                      className="w-full min-w-0 bg-transparent text-sm outline-none sm:w-48"
                    />
                  </label>

                  <Link
                    href="/incidents"
                    className="flex items-center gap-1 text-sm font-semibold text-indigo-600 hover:text-indigo-800"
                  >
                    View all <ArrowRight size={15} />
                  </Link>
                </div>
              </div>

              <div className="overflow-x-auto">
                <table className="w-full min-w-[760px] text-left text-sm">
                  <thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
                    <tr>
                      <th className="px-6 py-4 font-semibold">Incident</th>
                      <th className="px-6 py-4 font-semibold">Domain</th>
                      <th className="px-6 py-4 font-semibold">Severity</th>
                      <th className="px-6 py-4 font-semibold">Status</th>
                      <th className="px-6 py-4 font-semibold">Created</th>
                      <th className="px-6 py-4 text-right font-semibold">
                        Action
                      </th>
                    </tr>
                  </thead>

                  <tbody className="divide-y divide-slate-100">
                    {loading ? (
                      <tr>
                        <td
                          colSpan={6}
                          className="px-6 py-12 text-center text-slate-400"
                        >
                          Loading incidents…
                        </td>
                      </tr>
                    ) : error ? (
                      <tr>
                        <td
                          colSpan={6}
                          className="px-6 py-12 text-center text-slate-500"
                        >
                          Resolve the API error above to load incident records.
                        </td>
                      </tr>
                    ) : filteredIncidents.length === 0 ? (
                      <tr>
                        <td
                          colSpan={6}
                          className="px-6 py-12 text-center text-slate-500"
                        >
                          No matching incidents. Create an incident to get started.
                        </td>
                      </tr>
                    ) : (
                      filteredIncidents.map((incident) => (
                        <tr
                          key={incident.id}
                          className="transition hover:bg-slate-50/80"
                        >
                          <td className="px-6 py-4">
                            <Link
                              href={`/incidents/${incident.id}`}
                              className="font-semibold text-slate-800 hover:text-indigo-600"
                            >
                              {incident.title}
                            </Link>
                            <p className="mt-1 text-xs text-slate-400">
                              INC-{incident.id}
                            </p>
                          </td>

                          <td className="px-6 py-4 text-slate-600">
                            {incident.domain || "Unspecified"}
                          </td>

                          <td className="px-6 py-4">
                            <span
                              className={`inline-flex rounded-lg px-2.5 py-1 text-xs font-semibold ${severityStyle(incident.severity)}`}
                            >
                              {incident.severity}
                            </span>
                          </td>

                          <td className="px-6 py-4">
                            <span
                              className={`inline-flex rounded-lg px-2.5 py-1 text-xs font-semibold ring-1 ring-inset ${statusStyle(incident.status)}`}
                            >
                              {incident.status}
                            </span>
                          </td>

                          <td className="whitespace-nowrap px-6 py-4 text-slate-500">
                            {formatDate(incident.created_at)}
                          </td>

                          <td className="px-6 py-4 text-right">
                            <Link
                              href={`/incidents/${incident.id}`}
                              aria-label={`View incident ${incident.id}`}
                              className="inline-flex rounded-lg p-2 text-slate-500 hover:bg-indigo-50 hover:text-indigo-700"
                            >
                              <ArrowRight size={17} />
                            </Link>
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>

              <div className="border-t border-slate-100 px-6 py-4 text-xs text-slate-400">
                Showing up to 8 matching incidents.
              </div>
            </section>
          </div>
        </main>
      </div>
    </div>
  );
}