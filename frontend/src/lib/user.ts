import "server-only"

import { backendFetch } from "@/src/lib/api"

export type UserProfile = {
    id: string
    email: string
    name: string | null
    current_prompt: string
    writing_style: string | null
    created_at: string
    updated_at: string
}

export async function syncUser(
    accessToken: string,
    payload: { refresh_token?: string; name?: string } = {},
) {
    return backendFetch<UserProfile>("/api/users/sync", accessToken, {
        method: "POST",
        body: JSON.stringify(payload),
    })
}

export async function fetchCurrentUser(accessToken: string) {
    return backendFetch<UserProfile>("/api/users/me", accessToken)
}

export async function updateUserPrompt(
    accessToken: string,
    payload: { current_prompt: string; writing_style?: string },
) {
    return backendFetch<UserProfile>("/api/users/me/prompt", accessToken, {
        method: "PATCH",
        body: JSON.stringify(payload),
    })
}

export async function logoutUser(accessToken: string) {
    return backendFetch<void>("/api/users/logout", accessToken, {
        method: "POST",
    })
}

export async function syncInbox(accessToken: string) {
    return backendFetch<{ status: string; processed: number }>(
        "/api/gmail/sync",
        accessToken,
        { method: "POST" },
    )
}

export async function syncSentEmails(accessToken: string) {
    return backendFetch<{
        status: string
        total: number
        embedded: number
        skipped: number
    }>("/api/gmail/sync-sent", accessToken, { method: "POST" })
}
