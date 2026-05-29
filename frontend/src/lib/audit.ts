import "server-only"

import { backendFetch } from "@/src/lib/api"

export type AuditAction =
    | "approved"
    | "rejected"
    | "edited"
    | "sent"
    | "regenerated"

export type AuditLog = {
    id: string
    user_id: string
    draft_id: string | null
    email_id: string | null
    action: AuditAction
    subject: string | null
    body_snapshot: string | null
    created_at: string
}

export type AuditSearchResponse = {
    count: number
    logs: AuditLog[]
}

export async function searchAuditLogs(
    accessToken: string,
    params: { subject?: string; start_date?: string; end_date?: string } = {},
) {
    const search = new URLSearchParams()
    if (params.subject) search.set("subject", params.subject)
    if (params.start_date) search.set("start_date", params.start_date)
    if (params.end_date) search.set("end_date", params.end_date)
    const query = search.toString()
    return backendFetch<AuditSearchResponse>(
        `/api/audit${query ? `?${query}` : ""}`,
        accessToken,
    )
}
