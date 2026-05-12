import { signIn } from "@/src/auth"

export default function LoginPage() {
  return (
    <div className="flex flex-1 items-center justify-center bg-zinc-50 px-6 dark:bg-black">
      <div className="w-full max-w-sm rounded-2xl border border-black/[.08] bg-white p-8 shadow-sm dark:border-white/[.145] dark:bg-zinc-950">
        <div className="flex flex-col items-center gap-2 text-center">
          <h1 className="text-2xl font-semibold tracking-tight text-black dark:text-zinc-50">
            Welcome to Draftly
          </h1>
          <p className="text-sm text-zinc-600 dark:text-zinc-400">
            Sign in to continue to your account
          </p>
        </div>

        <form
          action={async () => {
            "use server"
            await signIn("google", { redirectTo: "/" })
          }}
          className="mt-8"
        >
          <button
            type="submit"
            className="flex h-11 w-full items-center justify-center gap-3 rounded-full border border-black/[.08] bg-white px-5 text-sm font-medium text-black transition-colors hover:bg-black/[.04] dark:border-white/[.145] dark:bg-zinc-950 dark:text-zinc-50 dark:hover:bg-[#1a1a1a]"
          >
            <svg
              aria-hidden
              viewBox="0 0 24 24"
              width={18}
              height={18}
              className="shrink-0"
            >
              <path
                fill="#EA4335"
                d="M12 10.2v3.9h5.5c-.2 1.4-1.6 4.1-5.5 4.1-3.3 0-6-2.7-6-6.1S8.7 6 12 6c1.9 0 3.1.8 3.8 1.5l2.6-2.5C16.8 3.5 14.6 2.5 12 2.5 6.8 2.5 2.6 6.7 2.6 12s4.2 9.5 9.4 9.5c5.4 0 9-3.8 9-9.2 0-.6-.1-1.1-.2-1.6H12z"
              />
              <path
                fill="#34A853"
                d="M3.9 7.3l3.2 2.3C8 7.7 9.8 6 12 6c1.9 0 3.1.8 3.8 1.5l2.6-2.5C16.8 3.5 14.6 2.5 12 2.5 8.3 2.5 5.1 4.5 3.9 7.3z"
              />
              <path
                fill="#FBBC05"
                d="M12 21.5c2.5 0 4.7-.8 6.3-2.3l-2.9-2.4c-.8.6-2 1-3.4 1-2.6 0-4.9-1.8-5.7-4.2l-3.2 2.5c1.4 2.9 4.6 5.4 8.9 5.4z"
              />
              <path
                fill="#4285F4"
                d="M21 12.3c0-.6-.1-1.1-.2-1.6H12v3.9h5.5c-.3 1.2-1.1 2.2-2.1 2.8l2.9 2.4c1.7-1.6 2.7-4 2.7-7.5z"
              />
            </svg>
            Login with Google
          </button>
        </form>
      </div>
    </div>
  )
}
