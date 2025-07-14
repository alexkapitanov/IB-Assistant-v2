export default function Status({text}:{text:string}){
  if(!text) return null
  return (
    <p className="flex items-center gap-2 text-sm text-gray-500 italic">
      <span className="w-3 h-3 border-2 border-gray-500 border-t-transparent rounded-full animate-spinSlow"/>
      {text}
    </p>
  )
}
