import "server-only"

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
}

export type FetchEmailsResult =
    | { ok: true; messages: EmailSummary[]; count: number }
    | {
          ok: false
          status: number
          error: string
          // True when the user needs to re-authenticate (token rejected or
          // scope missing). Lets the UI show a "Sign in again" CTA.
          needsReauth: boolean
      }

type MessagesResponse = {
    count: number
    messages: EmailSummary[]
}

function getBackendUrl(): string {
    const url = process.env.BACKEND_URL
    if (!url) {
        throw new Error(
            "BACKEND_URL is not set. Add it to your .env file " +
                "(e.g. BACKEND_URL=http://localhost:8000).",
        )
    }
    return url.replace(/\/+$/, "")
}

/**
 * Fetch the latest emails from the Draftly FastAPI backend.
 *
 * Always run this on the server (Server Components, route handlers, server
 * actions) so the Google access token never reaches the browser.
 */
export async function fetchLatestEmails(
    accessToken: string,
    options: { limit?: number; signal?: AbortSignal } = {},
): Promise<FetchEmailsResult> {
    const { limit = 10, signal } = options

    let response: Response
    try {
        response = await fetch(
            `${getBackendUrl()}/api/gmail/messages?limit=${limit}`,
            {
                method: "GET",
                headers: {
                    Authorization: `Bearer ${accessToken}`,
                    Accept: "application/json",
                },
                // The inbox should always reflect the latest state - never
                // cache this between requests or users.
                cache: "no-store",
                signal,
            },
        )
    } catch (error) {
        return {
            ok: false,
            status: 0,
            error:
                error instanceof Error
                    ? `Could not reach the Draftly backend: ${error.message}`
                    : "Could not reach the Draftly backend.",
            needsReauth: false,
        }
    }

    if (!response.ok) {
        let detail: string | undefined
        try {
            const body = (await response.json()) as { detail?: string }
            detail = body.detail
        } catch {
            // Body wasn't JSON - fall through with a generic message.
        }

        return {
            ok: false,
            status: response.status,
            error: detail ?? `Backend returned ${response.status}.`,
            needsReauth: response.status === 401 || response.status === 403,
        }
    }

    const data = (await response.json()) as MessagesResponse
    return { ok: true, messages: data.messages, count: data.count }
}
