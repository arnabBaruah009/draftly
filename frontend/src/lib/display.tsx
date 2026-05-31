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
