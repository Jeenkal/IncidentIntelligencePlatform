"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
    ArrowLeft,
    RefreshCw,
    Loader2,
    ShieldAlert,
    AlertCircle,
    FileText,
    Play,
} from "lucide-react";

import { getIncident } from "@/lib/api";
import type { Incident } from "@/types/incident";

type Props = {
    id: string;
};

function displayValue(value?: string | null) {
    if (!value) return "Not specified";

    return value
        .replaceAll("_", " ")
        .replace(/\b\w/g, (character) => character.toUpperCase());
}

/* ---------- Investigation report helpers ---------- */

const REPORT_SECTIONS: [string, string][] = [
    ["incident_summary", "Summary"],
    ["root_cause", "Root cause"],
    ["hypotheses", "Hypotheses"],
    ["evidence", "Evidence"],
    ["limitations", "Limitations"],
    ["recommended_next_steps", "Recommended next steps"],
];

function normalizeReport(
    raw: unknown
): Record<string, unknown> | string | null {
    if (!raw) return null;

    if (typeof raw === "string") {
        try {
            const parsed = JSON.parse(raw);
            if (parsed && typeof parsed === "object") {
                return parsed as Record<string, unknown>;
            }
        } catch {
            // Not JSON, treat as plain text
        }
        return raw;
    }

    if (typeof raw === "object") {
        return raw as Record<string, unknown>;
    }

    return String(raw);
}

function ReportValue({ value }: { value: unknown }) {
    if (value === null || value === undefined || value === "") {
        return <p className="text-slate-400">Not available</p>;
    }

    if (Array.isArray(value)) {
        if (value.length === 0) {
            return <p className="text-slate-400">None</p>;
        }

        return (
            <ul className="list-disc space-y-2 pl-5">
                {value.map((item, index) => (
                    <li key={index}>
                        <ReportValue value={item} />
                    </li>
                ))}
            </ul>
        );
    }

    if (typeof value === "object") {
        return (
            <dl className="space-y-3">
                {Object.entries(value as Record<string, unknown>).map(
                    ([key, val]) => (
                        <div key={key}>
                            <dt className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                                {displayValue(key)}
                            </dt>
                            <dd className="mt-1">
                                <ReportValue value={val} />
                            </dd>
                        </div>
                    )
                )}
            </dl>
        );
    }

    return (
        <p className="whitespace-pre-wrap break-words">{String(value)}</p>
    );
}

export function IncidentDetailsClient({ id }: Props) {
    const router = useRouter();

    const [incident, setIncident] = useState<Incident | null>(null);
    const [loading, setLoading] = useState(true);
    const [refreshing, setRefreshing] = useState(false);
    const [investigating, setInvestigating] = useState(false);
    const [error, setError] = useState("");
    const [investigationError, setInvestigationError] = useState("");
    const [successMessage, setSuccessMessage] = useState("");

    const loadIncident = useCallback(
        async (showRefresh = false) => {
            if (showRefresh) {
                setRefreshing(true);
            } else {
                setLoading(true);
            }

            setError("");

            try {
                const result = await getIncident(id);
                setIncident(result);
            } catch (err) {
                setError(
                    err instanceof Error
                        ? err.message
                        : "Unable to load this incident."
                );
            } finally {
                setLoading(false);
                setRefreshing(false);
            }
        },
        [id]
    );

    useEffect(() => {
        void loadIncident();
    }, [loadIncident]);

    async function handleInvestigate() {
        setInvestigating(true);
        setInvestigationError("");
        setSuccessMessage("");

        try {
            const baseUrl =
                process.env.NEXT_PUBLIC_API_URL ??
                "http://127.0.0.1:8000";

            // Confirm this route against your FastAPI /docs.
            const response = await fetch(
                `${baseUrl}/incidents/${encodeURIComponent(id)}/investigate`,
                {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                    },
                }
            );

            if (!response.ok) {
                const body = await response.text();

                throw new Error(
                    `Investigation failed (${response.status}): ${
                        body || response.statusText
                    }`
                );
            }

            setSuccessMessage(
                "Investigation request completed. Incident details refreshed."
            );

            await loadIncident(true);
        } catch (err) {
            setInvestigationError(
                err instanceof Error
                    ? err.message
                    : "Failed to investigate this incident."
            );
        } finally {
            setInvestigating(false);
        }
    }

    if (loading) {
        return (
            <main className="flex min-h-screen items-center justify-center bg-slate-50">
                <div className="flex items-center gap-3 text-slate-600">
                    <Loader2 className="animate-spin" size={22} />
                    <span>Loading incident...</span>
                </div>
            </main>
        );
    }

    if (error || !incident) {
        return (
            <main className="min-h-screen bg-slate-50 p-6 sm:p-10">
                <div className="mx-auto max-w-3xl rounded-2xl border border-red-200 bg-white p-6">
                    <div className="flex items-center gap-3 text-red-600">
                        <AlertCircle size={24} />
                        <h1 className="text-lg font-bold">
                            Unable to load incident
                        </h1>
                    </div>

                    <p className="mt-3 break-words text-sm text-slate-600">
                        {error || "The incident was not found."}
                    </p>

                    <div className="mt-6 flex flex-wrap gap-3">
                        <button
                            onClick={() => void loadIncident()}
                            className="rounded-xl bg-indigo-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-indigo-700"
                        >
                            Try again
                        </button>

                        <Link
                            href="/incidents"
                            className="rounded-xl border border-slate-200 px-4 py-2.5 text-sm font-semibold text-slate-700 hover:bg-slate-50"
                        >
                            Back to incidents
                        </Link>
                    </div>
                </div>
            </main>
        );
    }

    const report = normalizeReport(incident.investigation_report);

    return (
        <main className="min-h-screen bg-slate-50 px-4 py-8 sm:px-8">
            <div className="mx-auto max-w-6xl">
                <div className="mb-6 flex flex-wrap items-center justify-between gap-4">
                    <Link
                        href="/incidents"
                        className="inline-flex items-center gap-2 text-sm font-medium text-slate-600 hover:text-indigo-600"
                    >
                        <ArrowLeft size={17} />
                        Back to incidents
                    </Link>

                    <button
                        type="button"
                        onClick={() => router.refresh()}
                        className="inline-flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-sm font-medium text-slate-700 hover:bg-slate-50"
                    >
                        <RefreshCw size={16} />
                        Refresh page
                    </button>
                </div>

                {/* Incident heading */}
                <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm sm:p-8">
                    <div className="flex flex-col gap-5 sm:flex-row sm:items-start sm:justify-between">
                        <div className="flex gap-4">
                            <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-indigo-50 text-indigo-600">
                                <ShieldAlert size={25} />
                            </div>

                            <div>
                                <p className="text-sm font-medium text-slate-500">
                                    Incident #{incident.id}
                                </p>

                                <h1 className="mt-1 break-words text-2xl font-bold text-slate-900 sm:text-3xl">
                                    {incident.title}
                                </h1>

                                <p className="mt-3 whitespace-pre-wrap leading-7 text-slate-600">
                                    {incident.description}
                                </p>
                            </div>
                        </div>

                        <button
                            type="button"
                            onClick={handleInvestigate}
                            disabled={investigating}
                            className="inline-flex shrink-0 items-center justify-center gap-2 rounded-xl bg-indigo-600 px-5 py-3 text-sm font-semibold text-white transition hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-60"
                        >
                            {investigating ? (
                                <Loader2
                                    size={17}
                                    className="animate-spin"
                                />
                            ) : (
                                <Play size={17} />
                            )}

                            {investigating
                                ? "Investigating..."
                                : "Investigate incident"}
                        </button>
                    </div>

                    {/* Metadata */}
                    <div className="mt-8 grid gap-4 border-t border-slate-100 pt-6 sm:grid-cols-3">
                        <div className="rounded-xl bg-slate-50 p-4">
                            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                                Domain
                            </p>
                            <p className="mt-2 font-semibold text-slate-900">
                                {displayValue(incident.domain)}
                            </p>
                        </div>

                        <div className="rounded-xl bg-slate-50 p-4">
                            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                                Severity
                            </p>
                            <p className="mt-2 font-semibold text-slate-900">
                                {displayValue(incident.severity)}
                            </p>
                        </div>

                        <div className="rounded-xl bg-slate-50 p-4">
                            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                                Status
                            </p>
                            <p className="mt-2 font-semibold text-slate-900">
                                {displayValue(incident.status)}
                            </p>
                        </div>
                    </div>
                </section>

                {/* Investigation feedback */}
                {investigationError && (
                    <div
                        role="alert"
                        className="mt-6 flex gap-3 rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700"
                    >
                        <AlertCircle className="shrink-0" size={20} />
                        <p className="break-words">
                            {investigationError}
                        </p>
                    </div>
                )}

                {successMessage && (
                    <div
                        role="status"
                        className="mt-6 rounded-xl border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-800"
                    >
                        {successMessage}
                    </div>
                )}

                {/* Investigation report */}
                <section className="mt-6 overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
                    <div className="flex items-center gap-3 border-b border-slate-100 px-6 py-5">
                        <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-violet-50 text-violet-600">
                            <FileText size={21} />
                        </div>

                        <div>
                            <h2 className="font-bold text-slate-900">
                                Investigation report
                            </h2>
                            <p className="mt-1 text-sm text-slate-500">
                                Findings returned by the investigation workflow
                            </p>
                        </div>
                    </div>

                    <div className="p-6 sm:p-8">
                        {report ? (
                            typeof report === "string" ? (
                                <div className="whitespace-pre-wrap break-words leading-7 text-slate-700">
                                    {report}
                                </div>
                            ) : (
                                <div className="space-y-8 leading-7 text-slate-700">
                                    {REPORT_SECTIONS.filter(
                                        ([key]) => key in report
                                    ).map(([key, label]) => (
                                        <div key={key}>
                                            <h3 className="mb-2 text-sm font-bold uppercase tracking-wide text-slate-900">
                                                {label}
                                            </h3>
                                            <ReportValue
                                                value={report[key]}
                                            />
                                        </div>
                                    ))}
                                </div>
                            )
                        ) : (
                            <div className="py-8 text-center">
                                <FileText
                                    size={34}
                                    className="mx-auto text-slate-300"
                                />

                                <h3 className="mt-4 font-semibold text-slate-900">
                                    No investigation report yet
                                </h3>

                                <p className="mx-auto mt-2 max-w-md text-sm leading-6 text-slate-500">
                                    Run the investigation to retrieve relevant
                                    knowledge, analyze available evidence,
                                    and generate a report.
                                </p>

                                <button
                                    type="button"
                                    onClick={handleInvestigate}
                                    disabled={investigating}
                                    className="mt-5 inline-flex items-center gap-2 rounded-xl bg-indigo-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-indigo-700 disabled:opacity-60"
                                >
                                    {investigating && (
                                        <Loader2
                                            size={16}
                                            className="animate-spin"
                                        />
                                    )}
                                    Start investigation
                                </button>
                            </div>
                        )}
                    </div>
                </section>

                <div className="mt-6 text-center">
                    <button
                        type="button"
                        onClick={() => void loadIncident(true)}
                        disabled={refreshing}
                        className="inline-flex items-center gap-2 text-sm font-medium text-slate-600 hover:text-indigo-600 disabled:opacity-50"
                    >
                        <RefreshCw
                            size={15}
                            className={
                                refreshing ? "animate-spin" : ""
                            }
                        />
                        Refresh incident data
                    </button>
                </div>
            </div>
        </main>
    );
}