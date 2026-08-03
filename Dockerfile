FROM alpine:3.22 AS build
ARG BAMBO_RELEASE=unknown
ENV BAMBO_RELEASE=$BAMBO_RELEASE BAMBO_API_BASE_URL=/backend
WORKDIR /workspace
COPY smart-building-frontend/ ./smart-building-frontend/
RUN chmod +x smart-building-frontend/scripts/build-production.sh \
  && smart-building-frontend/scripts/build-production.sh /workspace/smart-building-frontend /workspace/dist

FROM nginxinc/nginx-unprivileged:1.29-alpine
COPY smart-building-frontend/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /workspace/dist/ /usr/share/nginx/html/
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 CMD wget -q -O /dev/null http://127.0.0.1:8080/healthz || exit 1

