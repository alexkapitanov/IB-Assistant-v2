FROM node:20-alpine AS build
WORKDIR /app
COPY package*.json ./
RUN npm i
COPY . .
RUN npm run build     # → dist/

FROM nginx:1.25-alpine
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
CMD ["nginx","-g","daemon off;"]
