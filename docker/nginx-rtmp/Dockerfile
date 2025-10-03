FROM alpine:3.18

# Install nginx with RTMP module
RUN apk add --no-cache \
    nginx \
    nginx-mod-rtmp \
    ffmpeg

# Create required directories
RUN mkdir -p /tmp/hls && \
    mkdir -p /var/log/nginx

# Copy nginx configuration
COPY nginx.conf /etc/nginx/nginx.conf

# Expose RTMP port and HTTP stats port
EXPOSE 1935 8080

# Start nginx
CMD ["nginx", "-g", "daemon off;"]

