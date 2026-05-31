"use server"

import { auth, signIn, signOut } from "@/src/auth"
import { logoutUser } from "@/src/lib/user"

export async function signOutAction() {
    const session = await auth()
    if (session?.accessToken && !session.error) {
        await logoutUser(session.accessToken)
    }
    await signOut({ redirectTo: "/login" })
}

export async function signInGoogleAction() {
    await signIn("google", { redirectTo: "/" })
}
