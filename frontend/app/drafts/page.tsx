import Link from "next/link"

import {
    ErrorPanel,
    PageHeader,
    formatDate,
    statusBadge,
    syncUserWithBackend,
} from "@/src/components/app-shell"
import { fetchDrafts } from "@/src/lib/drafts"

export default async function DraftsPage() {
    const session = await syncUserWithBackend()
    const displayName =
        session.user.name ?? session.user.email ?? "your account"
    const avatarUrl = session.user.image ?? null
    const tokenError = session.error === "RefreshAccessTokenError"

    const result =
        !tokenError && session.accessToken
            ? await fetchDrafts(session.accessToken)
            : null

    return (
        <div className="flex flex-1 bg-zinc-50 px-6 py-10 dark:bg-black">
            <div className="mx-auto w-full max-w-3xl">
                <PageHeader
                    title="Draft Replies"
                    subtitle="Review, edit, approve, or reject AI-generated responses"
                    active="drafts"
                    avatarUrl={avatarUrl}
                    displayName={displayName}
                />

                {tokenError || !result ? (
                    <ErrorPanel
                        title="Session expired"
                        message="Please sign in again to view drafts."
                        needsReauth
                    />
                ) : !result.ok ? (
                    <ErrorPanel
                        title="Couldn't load drafts"
                        message={result.error}
                        needsReauth={result.needsReauth}
                    />
                ) : result.data.drafts.length === 0 ? (
                    <div className="rounded-2xl border border-black/[.06] bg-white p-10 text-center dark:border-white/[.08] dark:bg-zinc-950">
                        <h2 className="text-base font-semibold">No drafts yet</h2>
                        <p className="mt-1 text-sm text-zinc-600 dark:text-zinc-400">
                            Sync your inbox from the home page to generate AI replies.
                        </p>
                    </div>
                ) : (
                    <ul className="space-y-3">
                        {result.data.drafts.map((draft) => (
                            <li
                                key={draft.id}
                                className="rounded-xl border border-black/[.06] bg-white p-4 dark:border-white/[.08] dark:bg-zinc-950"
                            >
                                <div className="flex flex-wrap items-start justify-between gap-3">
                                    <div className="min-w-0">
                                        <div className="flex items-center gap-2">
                                            {statusBadge(draft.status)}
                                            <time className="text-xs text-zinc-500">
                                                {formatDate(draft.created_at)}
                                            </time>
                                        </div>
                                        <h2 className="mt-2 truncate text-sm font-semibold">
                                            {draft.generated_subject ?? "(no subject)"}
                                        </h2>
                                        <p className="mt-1 line-clamp-2 text-sm text-zinc-600 dark:text-zinc-400">
                                            {draft.generated_body}
                                        </p>
                                    </div>
                                    <Link
                                        href={`/drafts/${draft.id}`}
                                        className="shrink-0 rounded-full border border-black/[.08] px-4 py-1.5 text-sm font-medium hover:bg-black/[.04] dark:border-white/[.145] dark:hover:bg-[#1a1a1a]"
                                    >
                                        Review
                                    </Link>
                                </div>
                            </li>
                        ))}
                    </ul>
                )}
            </div>
        </div>
    )
}
