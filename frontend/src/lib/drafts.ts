import "server-only"

import { backendFetch } from "@/src/lib/api"

export type DraftStatus = "pending" | "approved" | "rejected" | "sent"

export type Draft = {
    id: string
    user_id: string
    email_id: string
    thread_id: string
    generated_body: string
    generated_subject: string | null
    to: string | null
    status: DraftStatus
    approved_at: string | null
    created_at: string
    updated_at: string
}

export type DraftListResponse = {
    count: number
    drafts: Draft[]
    next_cursor: string | null
    has_more: boolean
}

export async function fetchPendingDraftCount(accessToken: string) {
    return backendFetch<{ count: number }>(
        "/api/drafts/count?status=pending",
        accessToken,
    )
}

export async function fetchDrafts(
    accessToken: string,
    status?: DraftStatus,
    options: { limit?: number; cursor?: string } = {},
) {
    const params = new URLSearchParams()
    if (status) params.set("status", status)
    if (options.limit) params.set("limit", String(options.limit))
    if (options.cursor) params.set("cursor", options.cursor)
    const query = params.toString()
    return backendFetch<DraftListResponse>(
        `/api/drafts${query ? `?${query}` : ""}`,
        accessToken,
    )
}

export async function fetchDraft(accessToken: string, draftId: string) {
    return backendFetch<Draft>(`/api/drafts/${draftId}`, accessToken)
}

export async function editDraft(
    accessToken: string,
    draftId: string,
    payload: { generated_body: string; generated_subject?: string },
) {
    return backendFetch<Draft>(`/api/drafts/${draftId}`, accessToken, {
        method: "PUT",
        body: JSON.stringify(payload),
    })
}

export async function approveDraft(accessToken: string, draftId: string) {
    return backendFetch<Draft>(
        `/api/drafts/${draftId}/approve`,
        accessToken,
        { method: "POST" },
    )
}

export async function rejectDraft(accessToken: string, draftId: string) {
    return backendFetch<Draft>(
        `/api/drafts/${draftId}/reject`,
        accessToken,
        { method: "POST" },
    )
}

export async function regenerateDraft(accessToken: string, draftId: string) {
    return backendFetch<Draft>(
        `/api/drafts/${draftId}/regenerate`,
        accessToken,
        { method: "POST" },
    )
}
