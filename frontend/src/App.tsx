import { useState,useEffect } from 'react'

export default function App() {
  const [ws,setWs]=useState<WebSocket>()
  const [input,setInput]=useState("")
  const [chat,setChat]=useState<{role:string,msg:string}[]>([])

  useEffect(()=>{
    const w=new WebSocket(`ws://${location.hostname}:8000/ws`)
    setWs(w)
    w.onmessage=e=>{
      const json=JSON.parse(e.data)
      const role=json.follow_up?"assistant(f/u)":"assistant"
      setChat(c=>[...c,{role,msg:json.answer||e.data}])
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
      <input className="border p-1 w-full" value={input}
        onChange={e=>setInput(e.target.value)}
        onKeyDown={e=>e.key==="Enter"&&send()}/>
    </div>
  )
}
