import React from "react"
import { marked } from "marked"
import DOMPurify from "dompurify"

interface Props {
  role: "user" | "assistant"
  children: React.ReactNode
}

export default function MessageBubble({ role, children }: Props) {
  const isUser = role === "user"
  const base = "px-4 py-3 rounded-xl max-w-[75%] shadow-sm"
  const cls = isUser 
    ? `${base} bg-blue-600 dark:bg-blue-700 text-white ml-auto rounded-br-sm`
    : `${base} bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 border border-gray-200 dark:border-gray-600 rounded-bl-sm prose prose-sm dark:prose-invert`
  
  // Если это ответ ассистента, рендерим markdown
  if (role === "assistant") {
    const markdownHtml = marked.parse(children as string, { async: false }) as string
    const html = DOMPurify.sanitize(markdownHtml)
    return (
      <div className={cls}>
        <div dangerouslySetInnerHTML={{ __html: html }} />
      </div>
    )
  }
  
  // Для пользователя оставляем как было
  return (
    <div className={cls}>
      <div dangerouslySetInnerHTML={{ __html: String(children) }} />
    </div>
  )
}
