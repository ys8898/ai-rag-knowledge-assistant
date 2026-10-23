# 第一阶段：构建Vue项目

FROM node:20 AS build


WORKDIR /app


COPY package*.json ./


RUN npm install


COPY . .


RUN npm run build



# 第二阶段：nginx运行

FROM nginx:latest


COPY --from=build /app/dist /usr/share/nginx/html


COPY nginx.conf /etc/nginx/conf.d/default.conf


EXPOSE 80


CMD ["nginx", "-g", "daemon off;"]