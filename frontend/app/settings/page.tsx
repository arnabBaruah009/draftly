import {
    ErrorPanel,
    PageHeader,
    syncUserWithBackend,
} from "@/src/components/app-shell"
import { updatePromptAction } from "@/src/actions/drafts"
import { fetchCurrentUser } from "@/src/lib/user"

export default async function SettingsPage() {
    const session = await syncUserWithBackend()
    const displayName =
        session.user.name ?? session.user.email ?? "your account"
    const avatarUrl = session.user.image ?? null
    const tokenError = session.error === "RefreshAccessTokenError"

    const profileResult =
        !tokenError && session.accessToken
            ? await fetchCurrentUser(session.accessToken)
            : null

    return (
        <div className="flex flex-1 bg-zinc-50 px-6 py-10 dark:bg-black">
            <div className="mx-auto w-full max-w-3xl">
                <PageHeader
                    title="Settings"
                    subtitle="Customize how the AI generates your email replies"
                    active="settings"
                    avatarUrl={avatarUrl}
                    displayName={displayName}
                />

                {tokenError || !profileResult ? (
                    <ErrorPanel
                        title="Session expired"
                        message="Please sign in again."
                        needsReauth
                    />
                ) : !profileResult.ok ? (
                    <ErrorPanel
                        title="Couldn't load settings"
                        message={profileResult.error}
                        needsReauth={profileResult.needsReauth}
                    />
                ) : (
                    <form
                        action={updatePromptAction}
                        className="space-y-5 rounded-2xl border border-black/[.06] bg-white p-6 dark:border-white/[.08] dark:bg-zinc-950"
                    >
                        <div>
                            <label
                                htmlFor="current_prompt"
                                className="text-sm font-medium"
                            >
                                Response prompt
                            </label>
                            <p className="mt-1 text-xs text-zinc-500">
                                Instructions the AI follows when drafting replies.
                            </p>
                            <textarea
                                id="current_prompt"
                                name="current_prompt"
                                defaultValue={
                                    profileResult.data.current_prompt
                                }
                                rows={5}
                                required
                                className="mt-2 w-full rounded-lg border border-black/[.08] bg-zinc-50 p-3 text-sm dark:border-white/[.145] dark:bg-black"
                            />
                        </div>

                        <div>
                            <label
                                htmlFor="writing_style"
                                className="text-sm font-medium"
                            >
                                Writing style
                            </label>
                            <p className="mt-1 text-xs text-zinc-500">
                                Describe your tone and communication preferences.
                            </p>
                            <textarea
                                id="writing_style"
                                name="writing_style"
                                defaultValue={
                                    profileResult.data.writing_style ?? ""
                                }
                                rows={3}
                                className="mt-2 w-full rounded-lg border border-black/[.08] bg-zinc-50 p-3 text-sm dark:border-white/[.145] dark:bg-black"
                            />
                        </div>

                        <button
                            type="submit"
                            className="rounded-full bg-black px-4 py-2 text-sm font-medium text-white hover:bg-black/85 dark:bg-white dark:text-black"
                        >
                            Save preferences
                        </button>
                    </form>
                )}
            </div>
        </div>
    )
}
