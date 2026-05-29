import Link from "next/link"
import { redirect } from "next/navigation"

import { auth, signIn, signOut } from "@/src/auth"
import { syncUser } from "@/src/lib/user"

export async function ensureAuthenticatedSession() {
    const session = await auth()
    if (!session?.user) {
        redirect("/login")
    }
    return session
}

export async function syncUserWithBackend() {
    const session = await ensureAuthenticatedSession()
    if (!session.accessToken || session.error) {
        return session
    }

    await syncUser(session.accessToken, {
        refresh_token: session.refreshToken,
        name: session.user.name ?? undefined,
    })

    return session
}

export function AppNav({ active }: { active: string }) {
    const links = [
        { href: "/", label: "Inbox", key: "inbox" },
        { href: "/drafts", label: "Drafts", key: "drafts" },
        { href: "/settings", label: "Settings", key: "settings" },
        { href: "/audit", label: "Audit", key: "audit" },
    ]

    return (
        <nav className="flex flex-wrap gap-2">
            {links.map((link) => (
                <Link
                    key={link.key}
                    href={link.href}
                    className={`rounded-full px-4 py-1.5 text-sm font-medium transition-colors ${
                        active === link.key
                            ? "bg-black text-white dark:bg-white dark:text-black"
                            : "border border-black/[.08] bg-white text-zinc-700 hover:bg-black/[.04] dark:border-white/[.145] dark:bg-zinc-950 dark:text-zinc-300 dark:hover:bg-[#1a1a1a]"
                    }`}
                >
                    {link.label}
                </Link>
            ))}
        </nav>
    )
}

export function PageHeader({
    title,
    subtitle,
    active,
    avatarUrl,
    displayName,
}: {
    title: string
    subtitle?: string
    active: string
    avatarUrl: string | null
    displayName: string
}) {
    return (
        <header className="mb-8 space-y-5">
            <div className="flex flex-wrap items-center justify-between gap-4">
                <div>
                    <h1 className="text-2xl font-semibold tracking-tight text-black dark:text-zinc-50">
                        {title}
                    </h1>
                    {subtitle ? (
                        <p className="mt-1 text-sm text-zinc-600 dark:text-zinc-400">
                            {subtitle}
                        </p>
                    ) : null}
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
                    <span className="text-sm text-zinc-600 dark:text-zinc-400">
                        {displayName}
                    </span>
                    <form
                        action={async () => {
                            "use server"
                            const session = await auth()
                            if (session?.accessToken && !session.error) {
                                const { logoutUser } = await import(
                                    "@/src/lib/user"
                                )
                                await logoutUser(session.accessToken)
                            }
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
            </div>
            <AppNav active={active} />
        </header>
    )
}

export function ErrorPanel({
    title,
    message,
    needsReauth,
}: {
    title: string
    message: string
    needsReauth?: boolean
}) {
    return (
        <div className="rounded-2xl border border-black/[.06] bg-white p-8 text-center dark:border-white/[.08] dark:bg-zinc-950">
            <h2 className="text-base font-semibold text-black dark:text-zinc-50">
                {title}
            </h2>
            <p className="mx-auto mt-2 max-w-md text-sm text-zinc-600 dark:text-zinc-400">
                {message}
            </p>
            {needsReauth ? (
                <div className="mt-5 flex justify-center">
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
                </div>
            ) : null}
        </div>
    )
}

export function formatDate(iso: string | null): string | null {
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

export function parseSender(raw: string | null): {
    name: string
    email: string | null
} {
    if (!raw) return { name: "Unknown sender", email: null }

    const match = raw.match(/^\s*"?([^"<]*?)"?\s*<([^>]+)>\s*$/)
    if (match) {
        const name = match[1].trim()
        const email = match[2].trim()
        return { name: name || email, email: name ? email : null }
    }
    return { name: raw.trim(), email: null }
}

export function statusBadge(status: string) {
    const styles: Record<string, string> = {
        pending:
            "bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-200",
        approved:
            "bg-blue-100 text-blue-800 dark:bg-blue-950 dark:text-blue-200",
        rejected:
            "bg-red-100 text-red-800 dark:bg-red-950 dark:text-red-200",
        sent: "bg-green-100 text-green-800 dark:bg-green-950 dark:text-green-200",
    }
    return (
        <span
            className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium capitalize ${
                styles[status] ?? "bg-zinc-100 text-zinc-700"
            }`}
        >
            {status}
        </span>
    )
}
