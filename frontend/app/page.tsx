import Link from "next/link"

import { syncInboxAction } from "@/src/actions/drafts"
import {
    ErrorPanel,
    PageHeader,
    formatDate,
    parseSender,
    statusBadge,
    syncUserWithBackend,
} from "@/src/components/app-shell"
import { fetchLatestEmails, type EmailSummary } from "@/src/lib/gmail"
import { fetchDrafts } from "@/src/lib/drafts"

export default async function Home() {
    const session = await syncUserWithBackend()
    const displayName =
        session.user.name ?? session.user.email ?? "your inbox"
    const avatarUrl = session.user.image ?? null
    const tokenError = session.error === "RefreshAccessTokenError"

    const result =
        !tokenError && session.accessToken
            ? await fetchLatestEmails(session.accessToken, { limit: 10 })
            : null

    const draftsResult =
        !tokenError && session.accessToken
            ? await fetchDrafts(session.accessToken, "pending")
            : null

    const pendingCount =
        draftsResult?.ok ? draftsResult.data.count : 0

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
        <section aria-label="Inbox">
            <p className="mb-3 text-xs uppercase tracking-wide text-zinc-500">
                Latest {result.count} messages
            </p>
            <ul className="space-y-2">
                {result.messages.map((message) => (
                    <EmailRow key={message.id} message={message} />
                ))}
            </ul>
        </section>
    )
}

function EmailRow({ message }: { message: EmailSummary }) {
    const sender = parseSender(message.from)
    const subject = message.subject?.trim() || "(no subject)"
    const snippet = message.snippet?.trim() ?? ""
    const dateLabel = formatDate(message.date)

    return (
        <li
            className={`group rounded-xl border bg-white p-4 transition-colors dark:bg-zinc-950 ${
                message.is_unread
                    ? "border-black/[.12] dark:border-white/[.18]"
                    : "border-black/[.06] dark:border-white/[.08]"
            } hover:border-black/[.18] dark:hover:border-white/[.25]`}
        >
            <Link href={`/messages/${message.id}`} className="flex items-start gap-3">
                <span
                    aria-hidden
                    className={`mt-2 h-2 w-2 shrink-0 rounded-full ${
                        message.is_unread ? "bg-blue-500" : "bg-transparent"
                    }`}
                />
                <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                        <p
                            className={`truncate text-sm ${
                                message.is_unread
                                    ? "font-semibold text-black dark:text-zinc-50"
                                    : "font-medium text-zinc-700 dark:text-zinc-300"
                            }`}
                        >
                            {sender.name}
                        </p>
                        <div className="flex items-center gap-2">
                            {message.draft_status
                                ? statusBadge(message.draft_status)
                                : null}
                            {dateLabel ? (
                                <time className="shrink-0 text-xs text-zinc-500">
                                    {dateLabel}
                                </time>
                            ) : null}
                        </div>
                    </div>
                    <p className="mt-1 truncate text-sm text-zinc-800 dark:text-zinc-200">
                        {subject}
                    </p>
                    {snippet ? (
                        <p className="mt-1 line-clamp-2 text-sm text-zinc-500 dark:text-zinc-400">
                            {snippet}
                        </p>
                    ) : null}
                </div>
            </Link>
        </li>
    )
}
