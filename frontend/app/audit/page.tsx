import {
    ErrorPanel,
    PageHeader,
    syncUserWithBackend,
} from "@/src/components/app-shell"
import { AuditList } from "@/src/components/audit-list"
import { searchAuditLogs } from "@/src/lib/audit"
import { PAGE_SIZE } from "@/src/lib/pagination"

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
            ? await searchAuditLogs(session.accessToken, {
                  subject,
                  limit: PAGE_SIZE,
              })
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
                    <AuditList
                        initialLogs={result.data.logs}
                        initialNextCursor={result.data.next_cursor}
                        initialHasMore={result.data.has_more}
                        subject={subject}
                    />
                )}
            </div>
        </div>
    )
}
