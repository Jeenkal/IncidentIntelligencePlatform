"use client";

import { FormEvent, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { ArrowLeft, Loader2, ShieldAlert } from "lucide-react";

import { createIncident } from "@/lib/api";
import type {
    Severity,
    IncidentDomain,
} from "@/types/incident";

export default function NewIncidentPage() {
    const router = useRouter();

    const [title, setTitle] = useState("");
    const [description, setDescription] = useState("");

    const [domain, setDomain] =
        useState<IncidentDomain>("devops");

    const [severity, setSeverity] =
        useState<Severity>("high");

    const [submitting, setSubmitting] = useState(false);
    const [error, setError] = useState("");

    async function handleSubmit(
        event: FormEvent<HTMLFormElement>
    ) {
        event.preventDefault();

        setError("");

        const cleanTitle = title.trim();
        const cleanDescription = description.trim();

        if (!cleanTitle || !cleanDescription) {
            setError(
                "Please enter both an incident title and description."
            );
            return;
        }

        setSubmitting(true);

        try {
            const incident = await createIncident({
                title: cleanTitle,
                description: cleanDescription,
                domain,
                severity,
            });

            if (incident?.id != null) {
                router.push(`/incidents/${incident.id}`);
            } else {
                router.push("/");
            }

            router.refresh();
        } catch (err) {
            setError(
                err instanceof Error
                    ? err.message
                    : "Failed to create the incident. Please try again."
            );
        } finally {
            setSubmitting(false);
        }
    }

    return (
        <main className="min-h-screen bg-slate-50 px-4 py-8 sm:px-8">
            <div className="mx-auto max-w-3xl">
                <Link
                    href="/"
                    className="mb-6 inline-flex items-center gap-2 text-sm font-medium text-slate-600 hover:text-indigo-600"
                >
                    <ArrowLeft size={17} />
                    Back to dashboard
                </Link>

                <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
                    <div className="border-b border-slate-100 px-6 py-6 sm:px-8">
                        <div className="flex items-center gap-3">
                            <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-indigo-50 text-indigo-600">
                                <ShieldAlert size={23} />
                            </div>

                            <div>
                                <h1 className="text-xl font-bold text-slate-900">
                                    Create incident
                                </h1>

                                <p className="mt-1 text-sm text-slate-500">
                                    Record an issue for investigation.
                                </p>
                            </div>
                        </div>
                    </div>

                    <form
                        onSubmit={handleSubmit}
                        className="space-y-6 p-6 sm:p-8"
                    >
                        {error && (
                            <div
                                role="alert"
                                className="break-words rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700"
                            >
                                {error}
                            </div>
                        )}

                        <div>
                            <label
                                htmlFor="title"
                                className="mb-2 block text-sm font-semibold text-slate-700"
                            >
                                Incident title
                            </label>

                            <input
                                id="title"
                                type="text"
                                value={title}
                                onChange={(event) =>
                                    setTitle(event.target.value)
                                }
                                required
                                minLength={1}
                                maxLength={200}
                                placeholder="e.g. Production API returning HTTP 502"
                                className="w-full rounded-xl border border-slate-200 px-4 py-3 text-sm outline-none transition focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100"
                            />
                        </div>

                        <div>
                            <label
                                htmlFor="description"
                                className="mb-2 block text-sm font-semibold text-slate-700"
                            >
                                Description
                            </label>

                            <textarea
                                id="description"
                                value={description}
                                onChange={(event) =>
                                    setDescription(event.target.value)
                                }
                                required
                                minLength={1}
                                rows={6}
                                maxLength={10000}
                                placeholder="Describe what happened, when it started, affected services, relevant errors, and recent changes."
                                className="w-full resize-y rounded-xl border border-slate-200 px-4 py-3 text-sm outline-none transition focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100"
                            />

                            <p className="mt-2 text-xs text-slate-400">
                                Include observed facts and logs when
                                available. Avoid credentials, API keys,
                                and other secrets.
                            </p>
                        </div>

                        <div className="grid gap-6 sm:grid-cols-2">
                            <div>
                                <label
                                    htmlFor="domain"
                                    className="mb-2 block text-sm font-semibold text-slate-700"
                                >
                                    Domain
                                </label>

                                <select
                                    id="domain"
                                    value={domain}
                                    onChange={(event) =>
                                        setDomain(
                                            event.target.value as IncidentDomain
                                        )
                                    }
                                    required
                                    className="w-full rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm outline-none transition focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100"
                                >
                                    <option value="devops">
                                        DevOps
                                    </option>
                                    <option value="ai_engineering">
                                        AI Engineering / RAG
                                    </option>
                                    <option value="postgresql">
                                        PostgreSQL
                                    </option>
                                    <option value="enterprise_it">
                                        Enterprise IT
                                    </option>
                                    <option value="security">
                                        Security
                                    </option>
                                </select>
                            </div>

                            <div>
                                <label
                                    htmlFor="severity"
                                    className="mb-2 block text-sm font-semibold text-slate-700"
                                >
                                    Severity
                                </label>

                                <select
                                    id="severity"
                                    value={severity}
                                    onChange={(event) =>
                                        setSeverity(
                                            event.target.value as Severity
                                        )
                                    }
                                    required
                                    className="w-full rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm outline-none transition focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100"
                                >
                                    <option value="low">Low</option>
                                    <option value="medium">Medium</option>
                                    <option value="high">High</option>
                                    <option value="critical">Critical</option>
                                </select>
                            </div>
                        </div>

                        <div className="flex flex-col-reverse gap-3 border-t border-slate-100 pt-6 sm:flex-row sm:justify-end">
                            <Link
                                href="/"
                                className="rounded-xl border border-slate-200 px-5 py-3 text-center text-sm font-semibold text-slate-700 transition hover:bg-slate-50"
                            >
                                Cancel
                            </Link>

                            <button
                                type="submit"
                                disabled={submitting}
                                className="inline-flex items-center justify-center gap-2 rounded-xl bg-indigo-600 px-5 py-3 text-sm font-semibold text-white transition hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-60"
                            >
                                {submitting && (
                                    <Loader2
                                        size={17}
                                        className="animate-spin"
                                    />
                                )}

                                {submitting
                                    ? "Creating..."
                                    : "Create incident"}
                            </button>
                        </div>
                    </form>
                </div>
            </div>
        </main>
    );
}
