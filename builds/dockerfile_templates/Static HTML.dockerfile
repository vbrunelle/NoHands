# Static HTML/CSS/JS Website Dockerfile
FROM nginx:alpine

# Copy static files to Nginx
COPY . /usr/share/nginx/html

# Remove any existing default config
RUN rm -f /etc/nginx/conf.d/default.conf

# Create simple nginx config for SPA support
RUN echo 'server { \
    listen 80; \
    location / { \
        root /usr/share/nginx/html; \
        index index.html; \
        try_files $uri $uri/ /index.html; \
    } \
}' > /etc/nginx/conf.d/default.conf

# Expose port 80
EXPOSE 80

# Start Nginx
CMD ["nginx", "-g", "daemon off;"]
