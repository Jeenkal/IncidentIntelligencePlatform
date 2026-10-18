export type Severity =
    | "low"
    | "medium"
    | "high"
    | "critical";

export type IncidentStatus =
    | "Open"
    | "Investigating"
    | "In Progress"
    | "Completed"
    | "Resolved"
    | "Failed";

export interface Incident {
    id: number;
    title: string;
    description?: string;
    domain?: string;
    severity: Severity | string;
    status: IncidentStatus | string;
    created_at?: string;
    updated_at?: string;
    investigation_report ?: InvestigationReport | string | null;
}

export interface IncidentCreate {
    title: string;
    description: string;
    domain: string;
    severity: Severity;
}

export type IncidentDomain =
    | "devops"
    | "ai_engineering"
    | "postgresql"
    | "enterprise_it"
    | "security";

export type InvestigationReport = {
    incident_summary?: string;
    domain?: string;
    status?: string;
    root_cause?: unknown;
    hypotheses?: unknown;
    evidence?: unknown;
    limitations?: unknown;
    recommended_next_steps?: unknown;
};

// inside your Incident type:
