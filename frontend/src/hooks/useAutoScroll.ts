import {useEffect} from "react"
export default function useAutoScroll(dep:any[]){
  useEffect(()=>{document.getElementById("anchor")?.scrollIntoView({behavior:"smooth"})},dep)
}
