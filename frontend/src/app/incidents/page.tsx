"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ArrowLeft, Plus, Search } from "lucide-react";

import { getIncidents } from "@/lib/api";
import type { Incident } from "@/types/incident";

export default function IncidentsPage() {
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [query, setQuery] = useState("");
  const [status, setStatus] = useState("All");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    getIncidents()
      .then(setIncidents)
      .catch((err: unknown) => {
        setError(
          err instanceof Error ? err.message : "Could not load incidents."
        );
      })
      .finally(() => setLoading(false));
  }, []);

  const filtered = incidents.filter((incident) => {
    const matchesQuery = [
      incident.title,
      incident.description || "",
      incident.domain || "",
      String(incident.id),
    ]
      .join(" ")
      .toLowerCase()
      .includes(query.toLowerCase());

    const matchesStatus =
      status === "All" ||
      incident.status.toLowerCase() === status.toLowerCase();

    return matchesQuery && matchesStatus;
  });

  return (
    <main className="min-h-screen bg-slate-50 p-5 text-slate-900 sm:p-8">
      <div className="mx-auto max-w-7xl">
        <Link
          href="/"
          className="mb-5 inline-flex items-center gap-2 text-sm text-slate-600 hover:text-indigo-600"
        >
          <ArrowLeft size={16} /> Dashboard
        </Link>

        <div className="mb-7 flex flex-wrap items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold">Incidents</h1>
            <p className="mt-1 text-sm text-slate-500">
              Search and review recorded incidents.
            </p>
          </div>

          <Link
            href="/incidents/new"
            className="inline-flex items-center gap-2 rounded-xl bg-indigo-600 px-4 py-3 text-sm font-semibold text-white hover:bg-indigo-700"
          >
            <Plus size={17} /> New incident
          </Link>
        </div>

        <div className="mb-5 flex flex-col gap-3 sm:flex-row">
          <label className="flex flex-1 items-center gap-2 rounded-xl border border-slate-200 bg-white px-4 py-3">
            <Search size={17} className="text-slate-400" />
            <input
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Search title, domain, or ID"
              className="w-full bg-transparent text-sm outline-none"
            />
          </label>

          <select
            value={status}
            onChange={(event) => setStatus(event.target.value)}
            className="rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm"
          >
            <option>All</option>
            <option>Open</option>
            <option>Investigating</option>
            <option>In Progress</option>
            <option>Completed</option>
            <option>Resolved</option>
            <option>Failed</option>
          </select>
        </div>

        {error && (
          <p role="alert" className="mb-4 rounded-xl bg-red-50 p-4 text-sm text-red-700">
            {error}
          </p>
        )}

        <div className="overflow-x-auto rounded-2xl border border-slate-200 bg-white">
          <table className="w-full min-w-[650px] text-left text-sm">
            <thead className="bg-slate-100 text-slate-600">
              <tr>
                <th className="p-4">ID / Title</th>
                <th className="p-4">Domain</th>
                <th className="p-4">Severity</th>
                <th className="p-4">Status</th>
                <th className="p-4">Details</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {loading ? (
                <tr>
                  <td colSpan={5} className="p-8 text-center text-slate-500">
                    Loading incidents…
                  </td>
                </tr>
              ) : filtered.length === 0 ? (
                <tr>
                  <td colSpan={5} className="p-8 text-center text-slate-500">
                    No incidents match your filters.
                  </td>
                </tr>
              ) : (
                filtered.map((incident) => (
                  <tr key={incident.id} className="hover:bg-slate-50">
                    <td className="p-4">
                      <p className="text-xs text-slate-400">
                        INC-{incident.id}
                      </p>
                      <p className="mt-1 font-semibold">{incident.title}</p>
                    </td>
                    <td className="p-4">{incident.domain || "—"}</td>
                    <td className="p-4">{incident.severity}</td>
                    <td className="p-4">{incident.status}</td>
                    <td className="p-4">
                      <Link
                        href={`/incidents/${incident.id}`}
                        className="font-semibold text-indigo-600 hover:underline"
                      >
                        View
                      </Link>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        <p className="mt-3 text-xs text-slate-400">
          Displaying records returned by the backend; filtering is currently
          performed in the browser.
        </p>
      </div>
    </main>
  );
}