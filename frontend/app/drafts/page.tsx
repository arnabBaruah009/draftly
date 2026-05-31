import Link from "next/link"

import {
    ErrorPanel,
    PageHeader,
    syncUserWithBackend,
} from "@/src/components/app-shell"
import { DraftList } from "@/src/components/draft-list"
import { fetchDrafts } from "@/src/lib/drafts"
import { PAGE_SIZE } from "@/src/lib/pagination"

export default async function DraftsPage() {
    const session = await syncUserWithBackend()
    const displayName =
        session.user.name ?? session.user.email ?? "your account"
    const avatarUrl = session.user.image ?? null
    const tokenError = session.error === "RefreshAccessTokenError"

    const result =
        !tokenError && session.accessToken
            ? await fetchDrafts(session.accessToken, undefined, {
                  limit: PAGE_SIZE,
              })
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
                            Sync your inbox from the{" "}
                            <Link href="/" className="font-medium underline">
                                home page
                            </Link>{" "}
                            to generate AI replies.
                        </p>
                    </div>
                ) : (
                    <DraftList
                        initialDrafts={result.data.drafts}
                        initialNextCursor={result.data.next_cursor}
                        initialHasMore={result.data.has_more}
                    />
                )}
            </div>
        </div>
    )
}
