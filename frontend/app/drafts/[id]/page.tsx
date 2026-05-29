import { notFound } from "next/navigation"

import { DraftReviewPanel } from "@/app/drafts/[id]/draft-review-panel"
import {
    ErrorPanel,
    PageHeader,
    statusBadge,
    syncUserWithBackend,
} from "@/src/components/app-shell"
import { fetchDraft } from "@/src/lib/drafts"

export default async function DraftDetailPage({
    params,
}: {
    params: Promise<{ id: string }>
}) {
    const { id } = await params
    const session = await syncUserWithBackend()
    const displayName =
        session.user.name ?? session.user.email ?? "your account"
    const avatarUrl = session.user.image ?? null
    const tokenError = session.error === "RefreshAccessTokenError"

    if (tokenError || !session.accessToken) {
        return (
            <div className="flex flex-1 bg-zinc-50 px-6 py-10 dark:bg-black">
                <div className="mx-auto w-full max-w-3xl">
                    <ErrorPanel
                        title="Session expired"
                        message="Please sign in again."
                        needsReauth
                    />
                </div>
            </div>
        )
    }

    const result = await fetchDraft(session.accessToken, id)
    if (!result.ok) {
        if (result.status === 404) notFound()
        return (
            <div className="flex flex-1 bg-zinc-50 px-6 py-10 dark:bg-black">
                <div className="mx-auto w-full max-w-3xl">
                    <ErrorPanel
                        title="Couldn't load draft"
                        message={result.error}
                        needsReauth={result.needsReauth}
                    />
                </div>
            </div>
        )
    }

    const draft = result.data

    return (
        <div className="flex flex-1 bg-zinc-50 px-6 py-10 dark:bg-black">
            <div className="mx-auto w-full max-w-3xl">
                <PageHeader
                    title="Review Draft"
                    subtitle={draft.generated_subject ?? "(no subject)"}
                    active="drafts"
                    avatarUrl={avatarUrl}
                    displayName={displayName}
                />

                <div className="mb-4 flex flex-wrap items-center gap-3 text-sm text-zinc-600 dark:text-zinc-400">
                    {statusBadge(draft.status)}
                    {draft.to ? <span>To: {draft.to}</span> : null}
                </div>

                <DraftReviewPanel draft={draft} />
            </div>
        </div>
    )
}
