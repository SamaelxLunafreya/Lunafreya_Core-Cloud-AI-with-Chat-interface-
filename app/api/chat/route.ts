import { xai } from "@ai-sdk/xai"
import { streamText, type CoreMessage } from "ai"
import { createClient } from "@/lib/supabase/server"
import type { NextRequest } from "next/server"

export const maxDuration = 30

export async function POST(req: NextRequest) {
  const supabase = createClient()
  const { messages, data } = await req.json()
  const { conversationId } = data

  const currentMessages: CoreMessage[] = messages.map((msg: any) => ({
    role: msg.role,
    content: msg.content,
  }))

  let newConversationId = conversationId

  // If it's a new conversation, create a record for it
  if (!newConversationId) {
    const { data: conversationData, error } = await supabase
      .from("conversations")
      .insert({ title: messages[0].content.substring(0, 50) }) // Use first message as title
      .select("id")
      .single()

    if (error) {
      console.error("Error creating conversation:", error)
      return new Response(JSON.stringify({ error: "Failed to create conversation" }), { status: 500 })
    }
    newConversationId = conversationData.id
  }

  // Save the user's message
  const userMessage = currentMessages[currentMessages.length - 1]
  if (userMessage.role === "user") {
    const { error } = await supabase.from("messages").insert({
      conversation_id: newConversationId,
      role: "user",
      content: userMessage.content as string,
    })
    if (error) {
      console.error("Error saving user message:", error)
    }
  }

  const result = await streamText({
    model: xai("grok-3-mini-beta"),
    messages: currentMessages,
    onCompletion: async (completion) => {
      // Save the assistant's final response
      const { error } = await supabase.from("messages").insert({
        conversation_id: newConversationId,
        role: "assistant",
        content: completion,
        model: "grok-3-mini-beta",
      })
      if (error) {
        console.error("Error saving assistant message:", error)
      }
    },
  })

  // Respond with the stream, including the conversation ID in a custom header
  const response = result.toAIStreamResponse()
  response.headers.set("x-conversation-id", newConversationId)
  return response
}
