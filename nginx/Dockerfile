FROM nginx:alpine

# Remove default config
RUN rm /etc/nginx/nginx.conf

# Bake our production config into the image
# Config is version-controlled in git and rebuilt on every push via CI/CD
COPY nginx.prod.conf /etc/nginx/nginx.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
