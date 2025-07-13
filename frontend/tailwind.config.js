module.exports = {
  content:["./index.html","./src/**/*.{js,ts,jsx,tsx}"],
  theme:{
    extend:{
      keyframes:{
        spinSlow:{
          '0%':{transform:'rotate(0deg)'},
          '100%':{transform:'rotate(360deg)'}
        }
      },
      animation:{
        spinSlow:'spinSlow 2s linear infinite'
      }
    }
  },
  plugins:[]
}
