"use client"

import { useCallback, useEffect, useRef, useState } from "react"

type LoadResult<T> =
    | { ok: true; items: T[]; nextCursor: string | null; hasMore: boolean }
    | { ok: false; error: string }

type InfiniteScrollListProps<T> = {
    initialItems: T[]
    initialNextCursor: string | null
    initialHasMore: boolean
    getItemKey: (item: T) => string
    loadMore: (cursor: string) => Promise<LoadResult<T>>
    renderItem: (item: T) => React.ReactNode
    emptyState?: React.ReactNode
    listClassName?: string
}

export function InfiniteScrollList<T>({
    initialItems,
    initialNextCursor,
    initialHasMore,
    getItemKey,
    loadMore,
    renderItem,
    emptyState,
    listClassName = "space-y-2",
}: InfiniteScrollListProps<T>) {
    const [items, setItems] = useState(initialItems)
    const [nextCursor, setNextCursor] = useState(initialNextCursor)
    const [hasMore, setHasMore] = useState(initialHasMore)
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState<string | null>(null)
    const sentinelRef = useRef<HTMLDivElement>(null)

    useEffect(() => {
        setItems(initialItems)
        setNextCursor(initialNextCursor)
        setHasMore(initialHasMore)
        setError(null)
    }, [initialItems, initialNextCursor, initialHasMore])

    const fetchNext = useCallback(async () => {
        if (!hasMore || loading || !nextCursor) return

        setLoading(true)
        setError(null)
        try {
            const result = await loadMore(nextCursor)
            if (!result.ok) {
                setError(result.error)
                return
            }
            setItems((prev) => {
                const seen = new Set(prev.map(getItemKey))
                const fresh = result.items.filter(
                    (item) => !seen.has(getItemKey(item)),
                )
                return [...prev, ...fresh]
            })
            setNextCursor(result.nextCursor)
            setHasMore(result.hasMore)
        } finally {
            setLoading(false)
        }
    }, [hasMore, loading, nextCursor, loadMore, getItemKey])

    useEffect(() => {
        const sentinel = sentinelRef.current
        if (!sentinel || !hasMore) return

        const observer = new IntersectionObserver(
            (entries) => {
                if (entries[0]?.isIntersecting) {
                    void fetchNext()
                }
            },
            { rootMargin: "200px" },
        )

        observer.observe(sentinel)
        return () => observer.disconnect()
    }, [fetchNext, hasMore])

    if (items.length === 0 && emptyState) {
        return <>{emptyState}</>
    }

    return (
        <>
            <ul className={listClassName}>
                {items.map((item) => (
                    <li key={getItemKey(item)}>{renderItem(item)}</li>
                ))}
            </ul>

            {hasMore ? (
                <div
                    ref={sentinelRef}
                    className="flex justify-center py-6"
                    aria-hidden
                >
                    {loading ? (
                        <span className="text-sm text-zinc-500">
                            Loading more…
                        </span>
                    ) : (
                        <span className="h-1 w-1" />
                    )}
                </div>
            ) : items.length > 0 ? (
                <p className="py-4 text-center text-xs text-zinc-400">
                    End of list
                </p>
            ) : null}

            {error ? (
                <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800 dark:border-red-900 dark:bg-red-950 dark:text-red-100">
                    {error}
                    <button
                        type="button"
                        onClick={() => void fetchNext()}
                        className="ml-2 font-medium underline"
                    >
                        Retry
                    </button>
                </div>
            ) : null}
        </>
    )
}
