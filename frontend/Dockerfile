# 멀티스테이지 빌드: node 빌더 → nginx 런타임
FROM node:20-alpine AS builder

WORKDIR /app

# 의존성 먼저 (캐시 레이어)
COPY package.json package-lock.json* ./
RUN npm install

# 소스 복사 및 Vite 운영 빌드
# API 경로는 /api (nginx 프록시 경유)로 빌드 시 주입
COPY . .
# .js 처리: tsx/ts 사이드카는 삭제, 독립 .js는 .jsx로 변환 후 내부 import 경로도 수정
RUN find src -name "*.js" | while read f; do \
      tsx="${f%.js}.tsx"; ts="${f%.js}.ts"; \
      if [ -f "$tsx" ] || [ -f "$ts" ]; then rm "$f"; \
      else mv "$f" "${f%.js}.jsx"; fi; \
    done
# import 경로 수정: 상대경로 .js 확장자를 제거 (vite가 .ts/.tsx/.jsx 자동 해석)
RUN find src \( -name "*.jsx" -o -name "*.tsx" \) -exec \
      sed -i "s|from '\./\([^']*\)\.js'|from './\1'|g" {} \; && \
    find src \( -name "*.jsx" -o -name "*.tsx" \) -exec \
      sed -i "s|from '\.\./\([^']*\)\.js'|from '../\1'|g" {} \; && \
    find src \( -name "*.jsx" -o -name "*.tsx" \) -exec \
      sed -i 's|from "\./\([^"]*\)\.js"|from "./\1"|g' {} \; && \
    find src \( -name "*.jsx" -o -name "*.tsx" \) -exec \
      sed -i 's|from "\.\./\([^"]*\)\.js"|from "../\1"|g' {} \;
ARG VITE_API_BASE_URL=/api
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}
RUN npx vite build

# ─────────────────────────────────────────────
FROM nginx:alpine AS runtime

# non-root 사용자 설정 (nginx 기본 사용자 활용)
# nginx:alpine은 기본적으로 nginx 사용자로 실행됨

# 빌드 산출물 및 nginx 설정 복사
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
