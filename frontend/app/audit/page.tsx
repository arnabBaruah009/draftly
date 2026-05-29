import {
    ErrorPanel,
    PageHeader,
    formatDate,
    syncUserWithBackend,
} from "@/src/components/app-shell"
import { searchAuditLogs } from "@/src/lib/audit"

export default async function AuditPage({
    searchParams,
}: {
    searchParams: Promise<{ subject?: string }>
}) {
    const { subject } = await searchParams
    const session = await syncUserWithBackend()
    const displayName =
        session.user.name ?? session.user.email ?? "your account"
    const avatarUrl = session.user.image ?? null
    const tokenError = session.error === "RefreshAccessTokenError"

    const result =
        !tokenError && session.accessToken
            ? await searchAuditLogs(session.accessToken, { subject })
            : null

    return (
        <div className="flex flex-1 bg-zinc-50 px-6 py-10 dark:bg-black">
            <div className="mx-auto w-full max-w-3xl">
                <PageHeader
                    title="Audit Log"
                    subtitle="History of approved, rejected, and edited responses"
                    active="audit"
                    avatarUrl={avatarUrl}
                    displayName={displayName}
                />

                <form method="get" className="mb-6 flex gap-2">
                    <input
                        type="search"
                        name="subject"
                        defaultValue={subject ?? ""}
                        placeholder="Search by subject…"
                        className="h-10 flex-1 rounded-full border border-black/[.08] bg-white px-4 text-sm dark:border-white/[.145] dark:bg-zinc-950"
                    />
                    <button
                        type="submit"
                        className="rounded-full bg-black px-4 text-sm font-medium text-white dark:bg-white dark:text-black"
                    >
                        Search
                    </button>
                </form>

                {tokenError || !result ? (
                    <ErrorPanel
                        title="Session expired"
                        message="Please sign in again."
                        needsReauth
                    />
                ) : !result.ok ? (
                    <ErrorPanel
                        title="Couldn't load audit logs"
                        message={result.error}
                        needsReauth={result.needsReauth}
                    />
                ) : result.data.logs.length === 0 ? (
                    <div className="rounded-2xl border border-black/[.06] bg-white p-10 text-center dark:border-white/[.08] dark:bg-zinc-950">
                        <p className="text-sm text-zinc-600 dark:text-zinc-400">
                            No audit entries found.
                        </p>
                    </div>
                ) : (
                    <ul className="space-y-3">
                        {result.data.logs.map((log) => (
                            <li
                                key={log.id}
                                className="rounded-xl border border-black/[.06] bg-white p-4 dark:border-white/[.08] dark:bg-zinc-950"
                            >
                                <div className="flex flex-wrap items-center justify-between gap-2">
                                    <span className="text-sm font-medium capitalize">
                                        {log.action}
                                    </span>
                                    <time className="text-xs text-zinc-500">
                                        {formatDate(log.created_at)}
                                    </time>
                                </div>
                                {log.subject ? (
                                    <p className="mt-1 text-sm text-zinc-700 dark:text-zinc-300">
                                        {log.subject}
                                    </p>
                                ) : null}
                                {log.body_snapshot ? (
                                    <p className="mt-2 line-clamp-3 text-sm text-zinc-500">
                                        {log.body_snapshot}
                                    </p>
                                ) : null}
                            </li>
                        ))}
                    </ul>
                )}
            </div>
        </div>
    )
}
