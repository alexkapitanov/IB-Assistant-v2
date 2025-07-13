import React from "react"

interface Props {
  role: "user" | "assistant"
  children: React.ReactNode
}

export default function MessageBubble({ role, children }: Props) {
  const isUser = role === "user"
  const base = "px-4 py-3 rounded-xl max-w-[75%] shadow-sm"
  const cls = isUser 
    ? `${base} bg-blue-600 text-white ml-auto rounded-br-sm`
    : `${base} bg-white text-gray-900 border border-gray-200 rounded-bl-sm`
  
  return (
    <div className={cls}>
      <div dangerouslySetInnerHTML={{ __html: String(children) }} />
    </div>
  )
}
