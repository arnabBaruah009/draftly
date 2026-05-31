"use server"

import { auth } from "@/src/auth"
import { searchAuditLogs } from "@/src/lib/audit"
import { fetchDrafts } from "@/src/lib/drafts"
import { fetchLatestEmails } from "@/src/lib/gmail"
import { PAGE_SIZE } from "@/src/lib/pagination"

async function requireToken() {
    const session = await auth()
    if (!session?.accessToken || session.error) {
        throw new Error("Not authenticated")
    }
    return session.accessToken
}

export async function loadMoreEmails(pageToken: string) {
    const token = await requireToken()
    const result = await fetchLatestEmails(token, {
        limit: PAGE_SIZE,
        pageToken,
    })
    if (!result.ok) {
        return { ok: false as const, error: result.error }
    }
    return {
        ok: true as const,
        messages: result.messages,
        nextPageToken: result.nextPageToken,
        hasMore: result.hasMore,
    }
}

export async function loadMoreDrafts(cursor: string) {
    const token = await requireToken()
    const result = await fetchDrafts(token, undefined, {
        limit: PAGE_SIZE,
        cursor,
    })
    if (!result.ok) {
        return { ok: false as const, error: result.error }
    }
    return {
        ok: true as const,
        drafts: result.data.drafts,
        nextCursor: result.data.next_cursor,
        hasMore: result.data.has_more,
    }
}

export async function loadMoreAuditLogs(
    cursor: string,
    subject?: string,
) {
    const token = await requireToken()
    const result = await searchAuditLogs(token, {
        subject,
        limit: PAGE_SIZE,
        cursor,
    })
    if (!result.ok) {
        return { ok: false as const, error: result.error }
    }
    return {
        ok: true as const,
        logs: result.data.logs,
        nextCursor: result.data.next_cursor,
        hasMore: result.data.has_more,
    }
}
