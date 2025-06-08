"use client"

import { useState, useCallback } from "react" // Added useCallback
import { useChat, type Message } from "@ai-sdk/react"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Avatar } from "@/components/ui/avatar"
import { SendHorizonal, Bot, User } from "lucide-react"
import { Sidebar } from "@/components/sidebar" // Ensure this path is correct

export default function LunafreyaCore() {
  const [conversationId, setConversationId] = useState<string | null>(null)

  const { messages, input, handleInputChange, handleSubmit, setMessages, isLoading } = useChat({
    api: "/api/chat",
    body: {
      conversationId, // Pass current conversationId to the API
    },
    onResponse: (response) => {
      const newId = response.headers.get("x-conversation-id")
      if (newId && newId !== conversationId) {
        // Only set if it's a new or different ID
        setConversationId(newId)
      }
    },
    // Clear messages if conversationId changes to null (new chat)
    // This is implicitly handled by how we'll use setMessages
  })

  const handleNewChat = useCallback(() => {
    setMessages([]) // Clear the messages in the UI
    setConversationId(null) // Reset the conversation ID
    // The input field (managed by useChat) will be cleared on next successful submit,
    // or user can clear it manually.
  }, [setMessages])

  // In a real app, you would fetch initial messages for a conversation like this:
  // useEffect(() => {
  //   if (conversationId && messages.length === 0) { // Only fetch if new convo ID and no messages
  //     // Fetch messages for conversationId from Supabase and use setMessages(fetchedMessages)
  //     // Example: loadMessagesForConversation(conversationId).then(setMessages);
  //   }
  // }, [conversationId, setMessages, messages.length]);

  return (
    <div className="grid grid-cols-[280px_1fr] h-screen w-screen bg-white dark:bg-gray-950 overflow-hidden">
      <aside className="h-full">
        <Sidebar
          onNewChat={handleNewChat}
          currentConversationId={conversationId}
          // onSelectConversation={(id) => setConversationId(id)} // We'll add this later
        />
      </aside>
      <main className="flex flex-col h-full bg-gray-100 dark:bg-gray-900">
        {/* This is the ChatPanel content, directly embedded for simplicity now */}
        <header className="p-4 border-b bg-white dark:bg-gray-950 flex-shrink-0">
          <h2 className="text-lg font-semibold text-gray-800 dark:text-gray-100">
            {conversationId ? `Chat: ${conversationId.substring(0, 8)}...` : "New Chat"}
          </h2>
        </header>
        <div className="flex-grow p-6 overflow-y-auto">
          <ScrollArea className="h-full pr-4 -mr-4">
            {" "}
            {/* Ensure ScrollArea takes available space */}
            <div className="space-y-6">
              {messages.map((m: Message) => (
                <div key={m.id} className={`flex items-start gap-4 ${m.role === "user" ? "justify-end" : ""}`}>
                  {m.role !== "user" && (
                    <Avatar className="w-9 h-9 bg-primary text-primary-foreground flex items-center justify-center flex-shrink-0">
                      <Bot className="w-5 h-5" />
                    </Avatar>
                  )}
                  <div
                    className={`max-w-[75%] rounded-lg p-3 text-sm whitespace-pre-wrap shadow-sm ${
                      m.role === "user" ? "bg-blue-600 text-white" : "bg-gray-100 dark:bg-gray-800"
                    }`}
                  >
                    <p>{m.content}</p>
                  </div>
                  {m.role === "user" && (
                    <Avatar className="w-9 h-9 bg-secondary text-secondary-foreground flex items-center justify-center flex-shrink-0">
                      <User className="w-5 h-5" />
                    </Avatar>
                  )}
                </div>
              ))}
            </div>
          </ScrollArea>
        </div>
        <div className="p-4 border-t bg-white dark:bg-gray-950 flex-shrink-0">
          <form onSubmit={handleSubmit} className="flex items-center gap-4">
            <Input
              value={input}
              onChange={handleInputChange}
              placeholder="Message Lunafreya..."
              className="flex-grow"
              disabled={isLoading}
            />
            <Button type="submit" size="icon" disabled={!input || isLoading}>
              <SendHorizonal className="w-4 h-4" />
              <span className="sr-only">Send</span>
            </Button>
          </form>
        </div>
      </main>
    </div>
  )
}
