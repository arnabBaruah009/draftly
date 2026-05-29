import NextAuth, { type DefaultSession } from "next-auth"
import type { JWT } from "next-auth/jwt"
import Google from "next-auth/providers/google"

const GMAIL_SCOPE = "https://www.googleapis.com/auth/gmail.modify"

// --- Module augmentation ----------------------------------------------------
// Surface the Google access token (and any auth errors) on `session` and the
// JWT so server components can pass it to the backend.

declare module "next-auth" {
    interface Session {
        accessToken?: string
        refreshToken?: string
        error?: "RefreshAccessTokenError"
        user: {
            id?: string
        } & DefaultSession["user"]
    }
}

declare module "next-auth/jwt" {
    interface JWT {
        accessToken?: string
        refreshToken?: string
        // Absolute expiry of the access token, in seconds since epoch.
        accessTokenExpires?: number
        scope?: string
        error?: "RefreshAccessTokenError"
    }
}

// --- Token refresh ----------------------------------------------------------
// Google access tokens last ~1 hour. When the JWT callback notices the token
// is expired, we exchange the refresh token for a fresh access token. If the
// refresh fails (e.g. user revoked access), we flag the session so the UI can
// force a re-login.

async function refreshGoogleAccessToken(token: JWT): Promise<JWT> {
    try {
        if (!token.refreshToken) {
            throw new Error("Missing refresh token")
        }

        const response = await fetch("https://oauth2.googleapis.com/token", {
            method: "POST",
            headers: { "Content-Type": "application/x-www-form-urlencoded" },
            body: new URLSearchParams({
                client_id: process.env.AUTH_GOOGLE_ID ?? "",
                client_secret: process.env.AUTH_GOOGLE_SECRET ?? "",
                grant_type: "refresh_token",
                refresh_token: token.refreshToken,
            }),
            cache: "no-store",
        })

        const refreshed = (await response.json()) as {
            access_token?: string
            expires_in?: number
            scope?: string
            refresh_token?: string
            error?: string
        }

        if (!response.ok || !refreshed.access_token) {
            throw new Error(refreshed.error ?? "Failed to refresh token")
        }

        return {
            ...token,
            accessToken: refreshed.access_token,
            accessTokenExpires:
                Math.floor(Date.now() / 1000) + (refreshed.expires_in ?? 3600),
            scope: refreshed.scope ?? token.scope,
            refreshToken: refreshed.refresh_token ?? token.refreshToken,
            error: undefined,
        }
    } catch (error) {
        console.error("[auth] Failed to refresh Google access token:", error)
        return { ...token, error: "RefreshAccessTokenError" }
    }
}

// --- NextAuth configuration -------------------------------------------------

export const { handlers, auth, signIn, signOut } = NextAuth({
    providers: [
        Google({
            // `access_type=offline` + `prompt=consent` makes Google reliably
            // return a refresh token on every sign-in. Without these we'd
            // only ever get a refresh token on the very first consent.
            authorization: {
                params: {
                    scope: `openid email profile ${GMAIL_SCOPE}`,
                    access_type: "offline",
                    prompt: "consent",
                },
            },
        }),
    ],
    callbacks: {
        async jwt({ token, account }) {
            if (account) {
                return {
                    ...token,
                    accessToken: account.access_token,
                    refreshToken: account.refresh_token ?? token.refreshToken,
                    accessTokenExpires:
                        account.expires_at ??
                        (account.expires_in
                            ? Math.floor(Date.now() / 1000) +
                              Number(account.expires_in)
                            : undefined),
                    scope: account.scope ?? token.scope,
                    error: undefined,
                }
            }

            const nowSeconds = Math.floor(Date.now() / 1000)
            // Refresh slightly before the real expiry so we don't hand out a
            // token that dies mid-request.
            const safetyMarginSeconds = 60
            if (
                token.accessTokenExpires &&
                nowSeconds <
                    token.accessTokenExpires - safetyMarginSeconds
            ) {
                return token
            }

            return refreshGoogleAccessToken(token)
        },
        async session({ session, token }) {
            session.accessToken = token.accessToken
            session.refreshToken = token.refreshToken
            session.error = token.error
            if (token.sub) {
                session.user.id = token.sub
            }
            return session
        },
    },
})
