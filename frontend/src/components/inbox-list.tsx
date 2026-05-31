"use client"

import Link from "next/link"
import { useCallback } from "react"

import { loadMoreEmails } from "@/src/actions/lists"
import {
    formatDate,
    parseSender,
    statusBadge,
} from "@/src/lib/display"
import { InfiniteScrollList } from "@/src/components/infinite-scroll-list"
import type { EmailSummary } from "@/src/lib/gmail"

export function InboxList({
    initialMessages,
    initialNextPageToken,
    initialHasMore,
}: {
    initialMessages: EmailSummary[]
    initialNextPageToken: string | null
    initialHasMore: boolean
}) {
    const loadMore = useCallback(async (cursor: string) => {
        const result = await loadMoreEmails(cursor)
        if (!result.ok) {
            return { ok: false as const, error: result.error }
        }
        return {
            ok: true as const,
            items: result.messages,
            nextCursor: result.nextPageToken,
            hasMore: result.hasMore,
        }
    }, [])

    return (
        <section aria-label="Inbox">
            <InfiniteScrollList
                initialItems={initialMessages}
                initialNextCursor={initialNextPageToken}
                initialHasMore={initialHasMore}
                getItemKey={(message) => message.id}
                loadMore={loadMore}
                renderItem={(message) => <EmailRow message={message} />}
            />
        </section>
    )
}

function EmailRow({ message }: { message: EmailSummary }) {
    const sender = parseSender(message.from)
    const subject = message.subject?.trim() || "(no subject)"
    const snippet = message.snippet?.trim() ?? ""
    const dateLabel = formatDate(message.date)

    return (
        <div
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
        </div>
    )
}
