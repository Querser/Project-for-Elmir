# admin-frontend/Dockerfile
FROM node:20 AS build

WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
ARG VITE_BASE_PATH=/admin/
ENV VITE_BASE_PATH=${VITE_BASE_PATH}
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html

# SPA + API proxy config (so /api/* from the browser reaches the backend container)
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
