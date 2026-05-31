import "server-only"

import { backendFetch } from "@/src/lib/api"

export type DraftStatus = "pending" | "approved" | "rejected" | "sent"

export type EmailSummary = {
    id: string
    thread_id: string
    subject: string | null
    from: string | null
    to: string | null
    snippet: string | null
    date: string | null
    label_ids: string[]
    is_unread: boolean
    draft_id: string | null
    draft_status: DraftStatus | null
}

export type ThreadMessage = {
    id: string
    from: string | null
    to: string | null
    subject: string | null
    body: string | null
    date: string | null
}

export type EmailDetail = EmailSummary & {
    body: string | null
    thread_messages: ThreadMessage[]
}

export type FetchEmailsResult =
    | {
          ok: true
          messages: EmailSummary[]
          count: number
          nextPageToken: string | null
          hasMore: boolean
      }
    | {
          ok: false
          status: number
          error: string
          needsReauth: boolean
      }

type MessagesResponse = {
    count: number
    messages: EmailSummary[]
    next_page_token: string | null
    has_more: boolean
}

/**
 * Fetch the latest emails from the Draftly FastAPI backend.
 *
 * Always run this on the server (Server Components, route handlers, server
 * actions) so the Google access token never reaches the browser.
 */
export async function fetchLatestEmails(
    accessToken: string,
    options: { limit?: number; pageToken?: string } = {},
): Promise<FetchEmailsResult> {
    const { limit = 25, pageToken } = options
    const params = new URLSearchParams({ limit: String(limit) })
    if (pageToken) {
        params.set("page_token", pageToken)
    }
    const result = await backendFetch<MessagesResponse>(
        `/api/gmail/messages?${params}`,
        accessToken,
    )
    if (!result.ok) {
        return result
    }
    return {
        ok: true,
        messages: result.data.messages,
        count: result.data.count,
        nextPageToken: result.data.next_page_token,
        hasMore: result.data.has_more,
    }
}

export async function fetchEmailDetail(
    accessToken: string,
    messageId: string,
) {
    return backendFetch<EmailDetail>(
        `/api/gmail/messages/${messageId}`,
        accessToken,
    )
}
