"use client"

import { useEffect, useState } from "react"
import { Button } from "@/components/ui/button"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Skeleton } from "@/components/ui/skeleton" // For loading state
import { Plus, MessageSquare, Settings, AlertTriangle } from "lucide-react"
import { createClient } from "@/lib/supabase/client" // Import the client-side Supabase client

interface Conversation {
  id: string
  title: string | null
  updated_at: string
}

export function Sidebar() {
  const [conversations, setConversations] = useState<Conversation[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    async function fetchConversations() {
      const supabase = createClient()
      setIsLoading(true)
      setError(null)

      // In a real app with authentication, you would filter by user_id:
      // const { data: { user } } = await supabase.auth.getUser();
      // if (user) {
      //   const { data, error } = await supabase
      //     .from("conversations")
      //     .select("id, title, updated_at")
      //     .eq("user_id", user.id) // Filter by user ID
      //     .order("updated_at", { ascending: false });
      // } else { ... handle no user ... }

      // For now, fetching all conversations for demonstration
      const { data, error: fetchError } = await supabase
        .from("conversations")
        .select("id, title, updated_at")
        .order("updated_at", { ascending: false })
        .limit(20) // Limit the number of conversations fetched

      if (fetchError) {
        console.error("Error fetching conversations:", fetchError)
        setError("Failed to load conversations. Please try again.")
      } else if (data) {
        setConversations(data as Conversation[])
      }
      setIsLoading(false)
    }

    fetchConversations()
  }, [])

  return (
    <div className="flex flex-col h-full bg-gray-50 dark:bg-gray-950 border-r border-gray-200 dark:border-gray-800">
      <div className="p-4 border-b border-gray-200 dark:border-gray-800 flex justify-between items-center">
        <h2 className="text-xl font-bold text-gray-800 dark:text-gray-100">Lunafreya_Core</h2>
      </div>
      <div className="p-4">
        <Button className="w-full bg-blue-600 hover:bg-blue-700 text-white">
          <Plus className="mr-2 h-4 w-4" />
          New Chat
        </Button>
      </div>
      <ScrollArea className="flex-grow px-4 pb-4">
        <h3 className="text-xs font-semibold text-gray-500 dark:text-gray-400 mb-3 uppercase tracking-wider">
          Recent Chats
        </h3>
        {isLoading && (
          <div className="space-y-2">
            {[...Array(5)].map((_, i) => (
              <div key={i} className="flex items-center space-x-2 p-2">
                <Skeleton className="h-5 w-5 rounded-full" />
                <Skeleton className="h-4 w-4/5" />
              </div>
            ))}
          </div>
        )}
        {error && (
          <div className="p-3 text-sm text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-900/30 rounded-md flex items-center">
            <AlertTriangle className="mr-2 h-4 w-4" />
            {error}
          </div>
        )}
        {!isLoading && !error && conversations.length === 0 && (
          <p className="text-sm text-gray-500 dark:text-gray-400 px-2">No recent chats.</p>
        )}
        {!isLoading && !error && conversations.length > 0 && (
          <div className="space-y-1">
            {conversations.map((convo) => (
              <Button
                key={convo.id}
                variant="ghost"
                className="w-full justify-start text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-800"
                // onClick={() => console.log("Load conversation:", convo.id)} // Placeholder for loading chat
              >
                <MessageSquare className="mr-3 h-4 w-4 flex-shrink-0" />
                <span className="truncate text-sm">
                  {convo.title || `Chat from ${new Date(convo.updated_at).toLocaleDateString()}`}
                </span>
              </Button>
            ))}
          </div>
        )}
      </ScrollArea>
      <div className="p-4 mt-auto border-t border-gray-200 dark:border-gray-800">
        <Button
          variant="ghost"
          className="w-full justify-start text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-800"
        >
          <Settings className="mr-3 h-4 w-4" />
          <span className="text-sm">Settings</span>
        </Button>
      </div>
    </div>
  )
}
