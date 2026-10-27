# Public gateway (requirements section 10). In Azure the client and data
# containers run in the same Container App as this one and have no ingress of
# their own, so the gateway reaches them on 127.0.0.1 and nothing else is public.
FROM nginx:1.27-alpine

# The official image renders /etc/nginx/templates/*.template with envsubst at
# start-up (only variables that are set are replaced, so nginx's own $vars
# survive). NGINX_ENTRYPOINT_LOCAL_RESOLVERS makes it export the container's
# DNS server as ${NGINX_LOCAL_RESOLVERS}, so upstreams resolve per request and
# the gateway still starts when a backend app does not exist yet.
ENV NGINX_ENTRYPOINT_LOCAL_RESOLVERS=1 \
    CLIENT_UPSTREAM=http://client:3000 \
    SERVER_UPSTREAM=http://server:8000 \
    DATA_UPSTREAM=http://dataservice:8000

RUN rm -f /etc/nginx/conf.d/default.conf
COPY templates/ /etc/nginx/templates/

EXPOSE 8080
