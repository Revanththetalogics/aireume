FROM nginx:alpine

# Remove default config
RUN rm /etc/nginx/nginx.conf

# Build argument to select nginx config (staging or production)
ARG NGINX_CONF=nginx.prod.conf

# Copy the selected nginx config into the image
# CI/CD passes NGINX_CONF=nginx.staging.conf or nginx.production.conf
COPY ${NGINX_CONF} /etc/nginx/nginx.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
