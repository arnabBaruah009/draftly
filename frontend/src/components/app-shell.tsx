import Link from "next/link"
import { redirect } from "next/navigation"

import { signInGoogleAction, signOutAction } from "@/src/actions/auth"
import { auth } from "@/src/auth"
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
                    <form action={signOutAction}>
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
                    <form action={signInGoogleAction}>
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

export {
    formatDate,
    parseSender,
    statusBadge,
} from "@/src/lib/display"
