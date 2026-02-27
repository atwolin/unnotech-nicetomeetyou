FROM nginx:alpine

# RUN apk add --no-cache certbot certbot-nginx

COPY . /usr/share/nginx/html

COPY nginx.conf /etc/nginx/conf.d/default.conf

# RUN mkdir -p /var/www/certbot

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]