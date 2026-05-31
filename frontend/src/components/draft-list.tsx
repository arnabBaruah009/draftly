"use client"

import Link from "next/link"
import { useCallback } from "react"

import { loadMoreDrafts } from "@/src/actions/lists"
import { formatDate, statusBadge } from "@/src/lib/display"
import { InfiniteScrollList } from "@/src/components/infinite-scroll-list"
import type { Draft } from "@/src/lib/drafts"

export function DraftList({
    initialDrafts,
    initialNextCursor,
    initialHasMore,
}: {
    initialDrafts: Draft[]
    initialNextCursor: string | null
    initialHasMore: boolean
}) {
    const loadMore = useCallback(async (cursor: string) => {
        const result = await loadMoreDrafts(cursor)
        if (!result.ok) {
            return { ok: false as const, error: result.error }
        }
        return {
            ok: true as const,
            items: result.drafts,
            nextCursor: result.nextCursor,
            hasMore: result.hasMore,
        }
    }, [])

    return (
        <InfiniteScrollList
            initialItems={initialDrafts}
            initialNextCursor={initialNextCursor}
            initialHasMore={initialHasMore}
            getItemKey={(draft) => draft.id}
            loadMore={loadMore}
            listClassName="space-y-3"
            renderItem={(draft) => (
                <div className="rounded-xl border border-black/[.06] bg-white p-4 dark:border-white/[.08] dark:bg-zinc-950">
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
                </div>
            )}
        />
    )
}
