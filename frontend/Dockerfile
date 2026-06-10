# 멀티스테이지 빌드: node 빌더 → nginx 런타임
FROM node:20-alpine AS builder

WORKDIR /app

# 의존성 먼저 (캐시 레이어)
COPY package.json package-lock.json* ./
RUN npm ci

# 소스 복사 및 Vite 운영 빌드
# API 경로는 /api (nginx 프록시 경유)로 빌드 시 주입
COPY . .
ARG VITE_API_BASE_URL=/api
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}
RUN npm run build

# ─────────────────────────────────────────────
FROM nginx:alpine AS runtime

# non-root 사용자 설정 (nginx 기본 사용자 활용)
# nginx:alpine은 기본적으로 nginx 사용자로 실행됨

# 빌드 산출물 및 nginx 설정 복사
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
