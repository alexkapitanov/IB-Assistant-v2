FROM node:20-alpine AS build
WORKDIR /app

# Accept build arguments
ARG VITE_BACKEND_HOST
ARG VITE_BACKEND_PORT

# Set environment variables for Vite
ENV VITE_BACKEND_HOST=$VITE_BACKEND_HOST
ENV VITE_BACKEND_PORT=$VITE_BACKEND_PORT

COPY package*.json ./
RUN npm i
COPY . .
RUN npm run build     # → dist/

FROM nginx:1.25-alpine
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
CMD ["nginx","-g","daemon off;"]
