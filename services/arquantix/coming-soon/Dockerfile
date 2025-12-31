FROM nginx:alpine

# Copy static HTML file
COPY index.html /usr/share/nginx/html/index.html

# Expose port 80
EXPOSE 80

# Nginx runs on port 80 by default
CMD ["nginx", "-g", "daemon off;"]

