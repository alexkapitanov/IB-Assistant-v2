import { useState,useEffect } from 'react'

export default function App() {
  const [ws,setWs]=useState<WebSocket>()
  const [input,setInput]=useState("")
  const [chat,setChat]=useState<{role:string,msg:string}[]>([])
  const [status,setStatus]=useState<string|undefined>()

  useEffect(()=>{
    // Для GitHub Codespaces нужно использовать правильный URL
    const wsUrl = location.hostname.includes('github.dev') 
      ? `wss://${location.hostname.replace('-5173', '-8000')}/ws`
      : `ws://${location.hostname}:8000/ws`
    console.log('Connecting to WebSocket:', wsUrl)
    const w=new WebSocket(wsUrl)
    setWs(w)
    w.onmessage=e=>{
      const data = JSON.parse(e.data)
      if (data.type === 'status') {
        setStatus(data.status)  // Исправлено: используем data.status вместо data.content
      } else {
        setStatus(undefined)
        const role=data.follow_up?"assistant(f/u)":"assistant"
        setChat(c=>[...c,{role,msg:data.answer||e.data}])
      }
    }
  },[])

  const send=()=>{
    if(input && ws){
      ws.send(input)
      setChat(c=>[...c,{role:"user",msg:input}])
      setInput("")
    }
  }

  return (
    <div className="p-4 space-y-2">
      {chat.map((m,i)=>(
        <p key={i}><b>{m.role}:</b> <span dangerouslySetInnerHTML={{__html:m.msg}}/></p>
      ))}
      {status && <p><i>Ассистент {
        status === 'thinking' ? 'думает' :
        status === 'searching' ? 'ищет' :
        status === 'generating' ? 'печатает' :
        status
      }...</i></p>}
      <input className="border p-1 w-full" value={input}
        onChange={e=>setInput(e.target.value)}
        onKeyDown={e=>e.key==="Enter"&&send()}/>
    </div>
  )
}
