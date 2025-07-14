module.exports = {
  content:["./index.html","./src/**/*.{js,ts,jsx,tsx}"],
  darkMode: "class",
  theme:{
    extend:{
      fontFamily:{ sans:["Inter","sans-serif"] },
      colors:{ brand:"#2563eb" },
      keyframes:{
        spinSlow:{
          from:{transform:"rotate(0)"},
          to:{transform:"rotate(360deg)"}
        }
      },
      animation:{
        spinSlow:"spinSlow 2s linear infinite"
      }
    }
  },
  plugins:[
    require('@tailwindcss/typography')
  ]
}
