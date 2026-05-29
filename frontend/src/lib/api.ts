import "server-only"

type ApiError = {
    ok: false
    status: number
    error: string
    needsReauth: boolean
}

type ApiSuccess<T> = {
    ok: true
    data: T
}

export type ApiResult<T> = ApiSuccess<T> | ApiError

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

export async function backendFetch<T>(
    path: string,
    accessToken: string,
    options: RequestInit = {},
): Promise<ApiResult<T>> {
    let response: Response
    try {
        response = await fetch(`${getBackendUrl()}${path}`, {
            ...options,
            headers: {
                Authorization: `Bearer ${accessToken}`,
                Accept: "application/json",
                ...(options.body ? { "Content-Type": "application/json" } : {}),
                ...options.headers,
            },
            cache: "no-store",
        })
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
            // ignore
        }
        return {
            ok: false,
            status: response.status,
            error: detail ?? `Backend returned ${response.status}.`,
            needsReauth: response.status === 401 || response.status === 403,
        }
    }

    if (response.status === 204) {
        return { ok: true, data: undefined as T }
    }

    const data = (await response.json()) as T
    return { ok: true, data }
}
