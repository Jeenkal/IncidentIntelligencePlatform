
export const instant = false;

import { IncidentDetailsClient } from "./IncidentDetailsClient";

type PageProps = {
    params: Promise<{ id: string }>;
};

export default async function IncidentDetailsPage({
    params,
}: PageProps) {
    const { id } = await params;

    return <IncidentDetailsClient id={id} />;
}
