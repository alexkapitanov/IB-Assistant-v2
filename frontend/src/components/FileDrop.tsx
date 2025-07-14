import {useCallback} from "react"
export default function FileDrop({onFile}:{onFile:(f:File)=>void}){
  const handle=useCallback((e:React.DragEvent)=>{
    e.preventDefault(); const f=e.dataTransfer.files?.[0]; f&&onFile(f)},[])
  return <div onDragOver={e=>e.preventDefault()} onDrop={handle}
    className="border-dashed border-2 border-gray-300 rounded-lg p-4 text-center text-gray-400">
      Перетащите PDF сюда
    </div>
}
