export default function Status({ status }: { status: string }) {
  if (!status) return null
  
  const map: { [k: string]: string } = {
    thinking: "думает",
    searching: "ищет", 
    generating: "печатает"
  }

  const colorMap: { [k: string]: string } = {
    thinking: "border-blue-500",
    searching: "border-yellow-500",
    generating: "border-green-500"
  }
  
  const spinnerColor = colorMap[status] ?? "border-gray-500"
  
  return (
    <div className="flex justify-start">
      <div className="px-4 py-2 bg-gray-100 dark:bg-gray-700 rounded-lg flex items-center gap-2 text-gray-600 dark:text-gray-300">
        <span className={`w-3 h-3 border-2 rounded-full border-t-transparent animate-spinSlow ${spinnerColor}`} />
        <span className="text-sm">
          Ассистент {map[status] ?? status}…
        </span>
      </div>
    </div>
  )
}
