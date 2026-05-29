"use client"

import { useState, useTransition } from "react"

import {
    approveDraftAction,
    editDraftAction,
    regenerateDraftAction,
    rejectDraftAction,
} from "@/src/actions/drafts"
import type { Draft } from "@/src/lib/drafts"

export function DraftReviewPanel({ draft }: { draft: Draft }) {
    const [body, setBody] = useState(draft.generated_body)
    const [message, setMessage] = useState<string | null>(null)
    const [isPending, startTransition] = useTransition()

    const run = (action: () => Promise<unknown>, success: string) => {
        setMessage(null)
        startTransition(async () => {
            try {
                await action()
                setMessage(success)
            } catch (error) {
                setMessage(
                    error instanceof Error ? error.message : "Action failed",
                )
            }
        })
    }

    const disabled =
        isPending || draft.status === "sent" || draft.status === "approved"

    return (
        <div className="space-y-5">
            <div className="rounded-xl border border-black/[.06] bg-white p-4 dark:border-white/[.08] dark:bg-zinc-950">
                <label
                    htmlFor="draft-body"
                    className="text-xs font-medium uppercase tracking-wide text-zinc-500"
                >
                    Reply body
                </label>
                <textarea
                    id="draft-body"
                    value={body}
                    onChange={(e) => setBody(e.target.value)}
                    disabled={disabled}
                    rows={12}
                    className="mt-2 w-full resize-y rounded-lg border border-black/[.08] bg-zinc-50 p-3 text-sm leading-relaxed text-zinc-900 outline-none focus:border-black/20 disabled:opacity-60 dark:border-white/[.145] dark:bg-black dark:text-zinc-100"
                />
            </div>

            {message ? (
                <p className="text-sm text-zinc-600 dark:text-zinc-400">
                    {message}
                </p>
            ) : null}

            <div className="flex flex-wrap gap-2">
                <button
                    type="button"
                    disabled={disabled || !body.trim()}
                    onClick={() =>
                        run(
                            () => editDraftAction(draft.id, body),
                            "Draft saved.",
                        )
                    }
                    className="rounded-full border border-black/[.08] px-4 py-2 text-sm font-medium hover:bg-black/[.04] disabled:opacity-50 dark:border-white/[.145] dark:hover:bg-[#1a1a1a]"
                >
                    Save edits
                </button>
                <button
                    type="button"
                    disabled={disabled || !body.trim()}
                    onClick={() =>
                        run(
                            () => approveDraftAction(draft.id),
                            "Reply sent via Gmail.",
                        )
                    }
                    className="rounded-full bg-black px-4 py-2 text-sm font-medium text-white hover:bg-black/85 disabled:opacity-50 dark:bg-white dark:text-black"
                >
                    Approve & send
                </button>
                <button
                    type="button"
                    disabled={isPending || draft.status === "sent"}
                    onClick={() =>
                        run(
                            () => rejectDraftAction(draft.id),
                            "Draft rejected.",
                        )
                    }
                    className="rounded-full border border-red-200 px-4 py-2 text-sm font-medium text-red-700 hover:bg-red-50 disabled:opacity-50 dark:border-red-900 dark:text-red-300 dark:hover:bg-red-950"
                >
                    Reject
                </button>
                <button
                    type="button"
                    disabled={isPending || draft.status === "sent"}
                    onClick={() =>
                        run(async () => {
                            const updated = await regenerateDraftAction(
                                draft.id,
                            )
                            setBody(updated.generated_body)
                        }, "New draft generated.")
                    }
                    className="rounded-full border border-black/[.08] px-4 py-2 text-sm font-medium hover:bg-black/[.04] disabled:opacity-50 dark:border-white/[.145] dark:hover:bg-[#1a1a1a]"
                >
                    Regenerate
                </button>
            </div>
        </div>
    )
}
