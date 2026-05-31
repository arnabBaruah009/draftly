"use client"

import { useCallback } from "react"

import { loadMoreAuditLogs } from "@/src/actions/lists"
import { formatDate } from "@/src/lib/display"
import { InfiniteScrollList } from "@/src/components/infinite-scroll-list"
import type { AuditLog } from "@/src/lib/audit"

export function AuditList({
    initialLogs,
    initialNextCursor,
    initialHasMore,
    subject,
}: {
    initialLogs: AuditLog[]
    initialNextCursor: string | null
    initialHasMore: boolean
    subject?: string
}) {
    const loadMore = useCallback(
        async (cursor: string) => {
            const result = await loadMoreAuditLogs(cursor, subject)
            if (!result.ok) {
                return { ok: false as const, error: result.error }
            }
            return {
                ok: true as const,
                items: result.logs,
                nextCursor: result.nextCursor,
                hasMore: result.hasMore,
            }
        },
        [subject],
    )

    return (
        <InfiniteScrollList
            initialItems={initialLogs}
            initialNextCursor={initialNextCursor}
            initialHasMore={initialHasMore}
            getItemKey={(log) => log.id}
            loadMore={loadMore}
            listClassName="space-y-3"
            renderItem={(log) => (
                <div className="rounded-xl border border-black/[.06] bg-white p-4 dark:border-white/[.08] dark:bg-zinc-950">
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
                </div>
            )}
        />
    )
}
