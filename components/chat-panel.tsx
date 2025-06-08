"use client"

import { useState } from "react"
import { useChat, type Message } from "@ai-sdk/react"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Avatar } from "@/components/ui/avatar"
import { SendHorizonal, Bot, User } from "lucide-react"

export function ChatPanel() {
  const [conversationId, setConversationId] = useState<string | null>(null)

  const { messages, input, handleInputChange, handleSubmit } = useChat({
    api: "/api/chat",
    body: {
      conversationId,
    },
    onResponse: (response) => {
      const newId = response.headers.get("x-conversation-id")
      if (newId) {
        setConversationId(newId)
      }
    },
  })

  return (
    <div className="flex flex-col h-full">
      <header className="p-4 border-b bg-white dark:bg-gray-950">
        <h2 className="text-lg font-semibold">AI Chat Interface</h2>
      </header>
      <div className="flex-grow p-6 overflow-y-auto">
        <ScrollArea className="h-full pr-4 -mr-4">
          <div className="space-y-6">
            {messages.map((m: Message) => (
              <div key={m.id} className={`flex items-start gap-4 ${m.role === "user" ? "justify-end" : ""}`}>
                {m.role !== "user" && (
                  <Avatar className="w-9 h-9 bg-primary text-primary-foreground flex items-center justify-center">
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
                  <Avatar className="w-9 h-9 bg-secondary text-secondary-foreground flex items-center justify-center">
                    <User className="w-5 h-5" />
                  </Avatar>
                )}
              </div>
            ))}
          </div>
        </ScrollArea>
      </div>
      <div className="p-4 border-t bg-white dark:bg-gray-950">
        <form onSubmit={handleSubmit} className="flex items-center gap-4">
          <Input value={input} onChange={handleInputChange} placeholder="Message Lunafreya..." className="flex-grow" />
          <Button type="submit" size="icon" disabled={!input}>
            <SendHorizonal className="w-4 h-4" />
            <span className="sr-only">Send</span>
          </Button>
        </form>
      </div>
    </div>
  )
}
