# Only the exact Viladum hostname. Reuse the observed origin listener and TLS.
server {
    listen @LISTEN@;
    server_name viladum.investimenti.cz;
    @TLS@
    root @NGINX_ROOT@/current;
    index index.html;
    include /etc/nginx/mime.types;
    default_type application/octet-stream;
    autoindex off;
    add_header X-Content-Type-Options nosniff always;
    add_header Referrer-Policy strict-origin-when-cross-origin always;
    add_header Cache-Control "no-cache" always;

    location = /brozura.pdf {
        try_files $uri =404;
        default_type application/pdf;
        add_header Content-Disposition 'attachment; filename="Viladum-Louny.pdf"';
        add_header Cache-Control "no-cache" always;
        add_header X-Content-Type-Options nosniff always;
    }
    location = /Viladum-v-zahradach.pdf { return 301 /brozura.pdf; }
    location / { try_files $uri $uri/ =404; }
    location ~ /\. { deny all; }
}
