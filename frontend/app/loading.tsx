export default function Loading() {
  return (
    <div className="flex flex-1 bg-zinc-50 px-6 py-10 dark:bg-black">
      <div className="mx-auto w-full max-w-3xl">
        <div className="mb-8 flex items-center justify-between">
          <div className="h-7 w-32 animate-pulse rounded-md bg-black/[.08] dark:bg-white/[.08]" />
          <div className="h-9 w-24 animate-pulse rounded-full bg-black/[.08] dark:bg-white/[.08]" />
        </div>

        <ul className="space-y-2">
          {Array.from({ length: 8 }).map((_, i) => (
            <li
              key={i}
              className="flex items-start gap-3 rounded-xl border border-black/[.06] bg-white p-4 dark:border-white/[.1] dark:bg-zinc-950"
            >
              <div className="mt-1 h-2 w-2 shrink-0 rounded-full bg-black/[.1] dark:bg-white/[.1]" />
              <div className="flex-1 space-y-2">
                <div className="flex items-center justify-between gap-3">
                  <div className="h-3 w-40 animate-pulse rounded bg-black/[.08] dark:bg-white/[.08]" />
                  <div className="h-3 w-16 animate-pulse rounded bg-black/[.06] dark:bg-white/[.06]" />
                </div>
                <div className="h-4 w-3/4 animate-pulse rounded bg-black/[.1] dark:bg-white/[.1]" />
                <div className="h-3 w-full animate-pulse rounded bg-black/[.06] dark:bg-white/[.06]" />
              </div>
            </li>
          ))}
        </ul>
      </div>
    </div>
  )
}
