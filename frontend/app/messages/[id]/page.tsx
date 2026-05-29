import Link from "next/link"
import { notFound } from "next/navigation"

import {
    ErrorPanel,
    PageHeader,
    formatDate,
    parseSender,
    syncUserWithBackend,
} from "@/src/components/app-shell"
import { fetchEmailDetail } from "@/src/lib/gmail"

export default async function MessageDetailPage({
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

    const result = await fetchEmailDetail(session.accessToken, id)
    if (!result.ok) {
        if (result.status === 404) notFound()
        return (
            <div className="flex flex-1 bg-zinc-50 px-6 py-10 dark:bg-black">
                <div className="mx-auto w-full max-w-3xl">
                    <ErrorPanel
                        title="Couldn't load message"
                        message={result.error}
                        needsReauth={result.needsReauth}
                    />
                </div>
            </div>
        )
    }

    const message = result.data
    const sender = parseSender(message.from)

    return (
        <div className="flex flex-1 bg-zinc-50 px-6 py-10 dark:bg-black">
            <div className="mx-auto w-full max-w-3xl">
                <PageHeader
                    title={message.subject?.trim() || "(no subject)"}
                    subtitle={`From ${sender.name}`}
                    active="inbox"
                    avatarUrl={avatarUrl}
                    displayName={displayName}
                />

                <div className="mb-4">
                    <Link
                        href="/"
                        className="text-sm text-zinc-600 underline dark:text-zinc-400"
                    >
                        ← Back to inbox
                    </Link>
                </div>

                <article className="rounded-2xl border border-black/[.06] bg-white p-6 dark:border-white/[.08] dark:bg-zinc-950">
                    <div className="text-xs text-zinc-500">
                        {formatDate(message.date)}
                    </div>
                    <div className="mt-4 whitespace-pre-wrap text-sm leading-relaxed text-zinc-800 dark:text-zinc-200">
                        {message.body ?? message.snippet ?? "(empty message)"}
                    </div>
                </article>

                {message.thread_messages.length > 1 ? (
                    <section className="mt-8">
                        <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-zinc-500">
                            Thread history
                        </h2>
                        <ul className="space-y-3">
                            {message.thread_messages.map((item) => (
                                <li
                                    key={item.id}
                                    className="rounded-xl border border-black/[.06] bg-white p-4 dark:border-white/[.08] dark:bg-zinc-950"
                                >
                                    <div className="text-xs text-zinc-500">
                                        {parseSender(item.from).name} ·{" "}
                                        {formatDate(item.date)}
                                    </div>
                                    <p className="mt-2 whitespace-pre-wrap text-sm text-zinc-700 dark:text-zinc-300">
                                        {item.body ?? item.subject ?? ""}
                                    </p>
                                </li>
                            ))}
                        </ul>
                    </section>
                ) : null}

                {message.draft_id ? (
                    <div className="mt-6">
                        <Link
                            href={`/drafts/${message.draft_id}`}
                            className="inline-flex rounded-full bg-black px-4 py-2 text-sm font-medium text-white dark:bg-white dark:text-black"
                        >
                            Review AI draft
                        </Link>
                    </div>
                ) : null}
            </div>
        </div>
    )
}
