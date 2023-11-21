# Use the official Nginx image as a base
FROM nginx:latest

# Remove the default Nginx content
RUN rm -rf /usr/share/nginx/html/*

# Copy the web content into the Nginx directory
COPY . /usr/share/nginx/html/
