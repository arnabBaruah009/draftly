"use server"

import { revalidatePath } from "next/cache"

import { auth } from "@/src/auth"
import {
    approveDraft,
    editDraft,
    regenerateDraft,
    rejectDraft,
} from "@/src/lib/drafts"
import { updateUserPrompt } from "@/src/lib/user"

async function requireToken() {
    const session = await auth()
    if (!session?.accessToken || session.error) {
        throw new Error("Not authenticated")
    }
    return session.accessToken
}

export async function approveDraftAction(draftId: string) {
    const token = await requireToken()
    const result = await approveDraft(token, draftId)
    if (!result.ok) throw new Error(result.error)
    revalidatePath("/drafts")
    revalidatePath(`/drafts/${draftId}`)
    return result.data
}

export async function rejectDraftAction(draftId: string) {
    const token = await requireToken()
    const result = await rejectDraft(token, draftId)
    if (!result.ok) throw new Error(result.error)
    revalidatePath("/drafts")
    revalidatePath(`/drafts/${draftId}`)
    return result.data
}

export async function regenerateDraftAction(draftId: string) {
    const token = await requireToken()
    const result = await regenerateDraft(token, draftId)
    if (!result.ok) throw new Error(result.error)
    revalidatePath("/drafts")
    revalidatePath(`/drafts/${draftId}`)
    return result.data
}

export async function editDraftAction(
    draftId: string,
    body: string,
    subject?: string,
) {
    const token = await requireToken()
    const result = await editDraft(token, draftId, {
        generated_body: body,
        generated_subject: subject,
    })
    if (!result.ok) throw new Error(result.error)
    revalidatePath("/drafts")
    revalidatePath(`/drafts/${draftId}`)
    return result.data
}

export async function updatePromptAction(formData: FormData) {
    const token = await requireToken()
    const current_prompt = String(formData.get("current_prompt") ?? "")
    const writing_style = String(formData.get("writing_style") ?? "")
    const result = await updateUserPrompt(token, {
        current_prompt,
        writing_style: writing_style || undefined,
    })
    if (!result.ok) throw new Error(result.error)
    revalidatePath("/settings")
}

export async function syncInboxAction() {
    const session = await auth()
    if (!session?.accessToken || session.error) {
        throw new Error("Not authenticated")
    }
    const { syncInbox } = await import("@/src/lib/user")
    const result = await syncInbox(session.accessToken)
    if (!result.ok) throw new Error(result.error)
    revalidatePath("/")
    revalidatePath("/drafts")
}
