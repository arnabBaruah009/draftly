import { redirect } from "next/navigation"

import { auth, signIn, signOut } from "@/src/auth"
import { fetchLatestEmails, type EmailSummary } from "@/src/lib/gmail"

export default async function Home() {
    const session = await auth()

    if (!session?.user) {
        redirect("/login")
    }

    const displayName =
        session.user.name ?? session.user.email ?? "your inbox"
    const avatarUrl = session.user.image ?? null
    const tokenError = session.error === "RefreshAccessTokenError"

    const result =
        !tokenError && session.accessToken
            ? await fetchLatestEmails(session.accessToken, { limit: 10 })
            : null

    return (
        <div className="flex flex-1 bg-zinc-50 px-6 py-10 dark:bg-black">
            <div className="mx-auto w-full max-w-3xl">
                <Header displayName={displayName} avatarUrl={avatarUrl} />

                <Body
                    tokenError={tokenError}
                    result={result}
                />
            </div>
        </div>
    )
}

function Header({
    displayName,
    avatarUrl,
}: {
    displayName: string
    avatarUrl: string | null
}) {
    return (
        <header className="mb-8 flex flex-wrap items-center justify-between gap-4">
            <div>
                <h1 className="text-2xl font-semibold tracking-tight text-black dark:text-zinc-50">
                    Inbox
                </h1>
                <p className="mt-1 text-sm text-zinc-600 dark:text-zinc-400">
                    Signed in as {displayName}
                </p>
            </div>

            <div className="flex items-center gap-3">
                {avatarUrl ? (
                    /* eslint-disable-next-line @next/next/no-img-element */
                    <img
                        src={avatarUrl}
                        alt=""
                        width={32}
                        height={32}
                        className="h-8 w-8 rounded-full border border-black/[.06] dark:border-white/[.1]"
                    />
                ) : null}
                <form
                    action={async () => {
                        "use server"
                        await signOut({ redirectTo: "/login" })
                    }}
                >
                    <button
                        type="submit"
                        className="flex h-9 items-center justify-center rounded-full border border-black/[.08] bg-white px-4 text-sm font-medium text-black transition-colors hover:bg-black/[.04] dark:border-white/[.145] dark:bg-zinc-950 dark:text-zinc-50 dark:hover:bg-[#1a1a1a]"
                    >
                        Sign out
                    </button>
                </form>
            </div>
        </header>
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
            <ErrorState
                title="Your Google session expired"
                message="We couldn't refresh your access token. Please sign in again to keep reading your inbox."
                action={
                    <form
                        action={async () => {
                            "use server"
                            await signIn("google", { redirectTo: "/" })
                        }}
                    >
                        <button
                            type="submit"
                            className="flex h-10 items-center justify-center rounded-full bg-black px-4 text-sm font-medium text-white transition-colors hover:bg-black/85 dark:bg-white dark:text-black dark:hover:bg-white/85"
                        >
                            Sign in again
                        </button>
                    </form>
                }
            />
        )
    }

    if (!result.ok) {
        return (
            <ErrorState
                title={
                    result.needsReauth
                        ? "Couldn't access your Gmail"
                        : "Couldn't load your inbox"
                }
                message={result.error}
                action={
                    result.needsReauth ? (
                        <form
                            action={async () => {
                                "use server"
                                await signIn("google", { redirectTo: "/" })
                            }}
                        >
                            <button
                                type="submit"
                                className="flex h-10 items-center justify-center rounded-full bg-black px-4 text-sm font-medium text-white transition-colors hover:bg-black/85 dark:bg-white dark:text-black dark:hover:bg-white/85"
                            >
                                Sign in again
                            </button>
                        </form>
                    ) : null
                }
            />
        )
    }

    if (result.messages.length === 0) {
        return (
            <EmptyState />
        )
    }

    return (
        <section aria-label="Inbox">
            <p className="mb-3 text-xs uppercase tracking-wide text-zinc-500 dark:text-zinc-500">
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
            className={`group flex items-start gap-3 rounded-xl border bg-white p-4 transition-colors dark:bg-zinc-950 ${
                message.is_unread
                    ? "border-black/[.12] dark:border-white/[.18]"
                    : "border-black/[.06] dark:border-white/[.08]"
            } hover:border-black/[.18] dark:hover:border-white/[.25]`}
        >
            <span
                aria-hidden
                className={`mt-2 h-2 w-2 shrink-0 rounded-full ${
                    message.is_unread
                        ? "bg-blue-500"
                        : "bg-transparent"
                }`}
            />

            <div className="min-w-0 flex-1">
                <div className="flex items-baseline justify-between gap-3">
                    <p
                        className={`truncate text-sm ${
                            message.is_unread
                                ? "font-semibold text-black dark:text-zinc-50"
                                : "font-medium text-zinc-700 dark:text-zinc-300"
                        }`}
                        title={message.from ?? undefined}
                    >
                        {sender.name}
                        {sender.email ? (
                            <span className="ml-2 text-xs font-normal text-zinc-500 dark:text-zinc-500">
                                {sender.email}
                            </span>
                        ) : null}
                    </p>
                    {dateLabel ? (
                        <time className="shrink-0 text-xs text-zinc-500 dark:text-zinc-500">
                            {dateLabel}
                        </time>
                    ) : null}
                </div>

                <p
                    className={`mt-1 truncate text-sm ${
                        message.is_unread
                            ? "font-medium text-black dark:text-zinc-100"
                            : "text-zinc-800 dark:text-zinc-200"
                    }`}
                >
                    {subject}
                </p>

                {snippet ? (
                    <p className="mt-1 line-clamp-2 text-sm text-zinc-500 dark:text-zinc-400">
                        {snippet}
                    </p>
                ) : null}
            </div>
        </li>
    )
}

function EmptyState() {
    return (
        <div className="rounded-2xl border border-black/[.06] bg-white p-10 text-center dark:border-white/[.08] dark:bg-zinc-950">
            <h2 className="text-base font-semibold text-black dark:text-zinc-50">
                You&apos;re all caught up
            </h2>
            <p className="mt-1 text-sm text-zinc-600 dark:text-zinc-400">
                There are no messages in your inbox right now.
            </p>
        </div>
    )
}

function ErrorState({
    title,
    message,
    action,
}: {
    title: string
    message: string
    action: React.ReactNode
}) {
    return (
        <div className="rounded-2xl border border-black/[.06] bg-white p-8 text-center dark:border-white/[.08] dark:bg-zinc-950">
            <h2 className="text-base font-semibold text-black dark:text-zinc-50">
                {title}
            </h2>
            <p className="mx-auto mt-2 max-w-md text-sm text-zinc-600 dark:text-zinc-400">
                {message}
            </p>
            {action ? <div className="mt-5 flex justify-center">{action}</div> : null}
        </div>
    )
}

// --- Helpers ---------------------------------------------------------------

function parseSender(raw: string | null): { name: string; email: string | null } {
    if (!raw) return { name: "Unknown sender", email: null }

    // Typical formats: '"Display Name" <user@example.com>' or 'user@example.com'.
    const match = raw.match(/^\s*"?([^"<]*?)"?\s*<([^>]+)>\s*$/)
    if (match) {
        const name = match[1].trim()
        const email = match[2].trim()
        return { name: name || email, email: name ? email : null }
    }
    return { name: raw.trim(), email: null }
}

function formatDate(iso: string | null): string | null {
    if (!iso) return null
    const date = new Date(iso)
    if (Number.isNaN(date.getTime())) return null

    const now = new Date()
    const sameDay =
        date.getFullYear() === now.getFullYear() &&
        date.getMonth() === now.getMonth() &&
        date.getDate() === now.getDate()

    if (sameDay) {
        return date.toLocaleTimeString(undefined, {
            hour: "numeric",
            minute: "2-digit",
        })
    }

    const sameYear = date.getFullYear() === now.getFullYear()
    return date.toLocaleDateString(undefined, {
        month: "short",
        day: "numeric",
        year: sameYear ? undefined : "numeric",
    })
}
