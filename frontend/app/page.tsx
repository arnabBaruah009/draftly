import Link from "next/link"

import { syncInboxAction } from "@/src/actions/drafts"
import {
    ErrorPanel,
    PageHeader,
    syncUserWithBackend,
} from "@/src/components/app-shell"
import { InboxList } from "@/src/components/inbox-list"
import { fetchPendingDraftCount } from "@/src/lib/drafts"
import { fetchLatestEmails } from "@/src/lib/gmail"
import { PAGE_SIZE } from "@/src/lib/pagination"

export default async function Home() {
    const session = await syncUserWithBackend()
    const displayName =
        session.user.name ?? session.user.email ?? "your inbox"
    const avatarUrl = session.user.image ?? null
    const tokenError = session.error === "RefreshAccessTokenError"

    const result =
        !tokenError && session.accessToken
            ? await fetchLatestEmails(session.accessToken, { limit: PAGE_SIZE })
            : null

    const pendingCountResult =
        !tokenError && session.accessToken
            ? await fetchPendingDraftCount(session.accessToken)
            : null

    const pendingCount =
        pendingCountResult?.ok ? pendingCountResult.data.count : 0

    return (
        <div className="flex flex-1 bg-zinc-50 px-6 py-10 dark:bg-black">
            <div className="mx-auto w-full max-w-3xl">
                <PageHeader
                    title="Inbox"
                    subtitle="Relevant emails and AI-generated draft replies"
                    active="inbox"
                    avatarUrl={avatarUrl}
                    displayName={displayName}
                />

                {!tokenError && session.accessToken ? (
                    <form action={syncInboxAction} className="mb-6">
                        <button
                            type="submit"
                            className="flex h-9 items-center justify-center rounded-full bg-black px-4 text-sm font-medium text-white transition-colors hover:bg-black/85 dark:bg-white dark:text-black dark:hover:bg-white/85"
                        >
                            Sync inbox & generate drafts
                        </button>
                    </form>
                ) : null}

                {pendingCount > 0 ? (
                    <div className="mb-6 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900 dark:border-amber-900 dark:bg-amber-950 dark:text-amber-100">
                        {pendingCount} draft{pendingCount === 1 ? "" : "s"}{" "}
                        awaiting your review.{" "}
                        <Link
                            href="/drafts"
                            className="font-medium underline"
                        >
                            Review drafts
                        </Link>
                    </div>
                ) : null}

                <Body tokenError={tokenError} result={result} />
            </div>
        </div>
    )
}

function Body({
    tokenError,
    result,
}: {
    tokenError: boolean
    result: Awaited<ReturnType<typeof fetchLatestEmails>> | null
}) {
    if (tokenError || result === null) {
        return (
            <ErrorPanel
                title="Your Google session expired"
                message="We couldn't refresh your access token. Please sign in again."
                needsReauth
            />
        )
    }

    if (!result.ok) {
        return (
            <ErrorPanel
                title={
                    result.needsReauth
                        ? "Couldn't access your Gmail"
                        : "Couldn't load your inbox"
                }
                message={result.error}
                needsReauth={result.needsReauth}
            />
        )
    }

    if (result.messages.length === 0) {
        return (
            <div className="rounded-2xl border border-black/[.06] bg-white p-10 text-center dark:border-white/[.08] dark:bg-zinc-950">
                <h2 className="text-base font-semibold text-black dark:text-zinc-50">
                    You&apos;re all caught up
                </h2>
                <p className="mt-1 text-sm text-zinc-600 dark:text-zinc-400">
                    No relevant messages in your inbox right now.
                </p>
            </div>
        )
    }

    return (
        <InboxList
            initialMessages={result.messages}
            initialNextPageToken={result.nextPageToken}
            initialHasMore={result.hasMore}
        />
    )
}
