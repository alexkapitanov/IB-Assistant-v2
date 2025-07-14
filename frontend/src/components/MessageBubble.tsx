import ReactMarkdown from "react-markdown"

export default function Bubble({role,children}:{role:"user"|"assistant"|"system";children:string}){
  const base="px-4 py-3 rounded-2xl max-w-[75%] shadow"
  const cls=role==="user"
      ?(`${base} bg-brand text-white ml-auto`)
      :role==="assistant"
        ?(`${base} bg-white text-gray-900`)
        :(`${base} bg-yellow-50 text-yellow-800`)
  return(
    <div className="flex gap-2">
      {role!=="user"&&<div className="w-8"><img src="/logo.svg" className="h-6 w-6 opacity-70"/></div>}
      <div className={`${cls} prose prose-sm dark:prose-invert`}>
        <ReactMarkdown>{children}</ReactMarkdown>
      </div>
    </div>
  )
}
