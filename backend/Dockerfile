# 멀티스테이지 빌드: builder(의존성) → runtime(최소 이미지)
FROM python:3.11-slim AS builder

# uv 설치
RUN pip install --no-cache-dir uv

WORKDIR /app

# 의존성 파일만 먼저 복사 (레이어 캐시 활용)
COPY pyproject.toml uv.lock* ./

# 가상환경 생성 및 의존성 설치
RUN uv venv /app/.venv && \
    uv pip install --python /app/.venv/bin/python -r pyproject.toml

# 소스 복사
COPY . .

# ─────────────────────────────────────────────
FROM python:3.11-slim AS runtime

# non-root 사용자 생성
RUN useradd --create-home --shell /bin/bash appuser

WORKDIR /app

# 가상환경과 소스 복사
COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/src /app/src
COPY --from=builder /app/alembic /app/alembic
COPY --from=builder /app/alembic.ini /app/alembic.ini
COPY --from=builder /app/entrypoint.sh /app/entrypoint.sh

# PATH에 venv 추가
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH="/app/src"

# 엔트리포인트 실행 권한
RUN chmod +x /app/entrypoint.sh

# 파일 소유권 이전
RUN chown -R appuser:appuser /app

USER appuser

EXPOSE 8000

# 컨테이너 헬스 체크
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

ENTRYPOINT ["/app/entrypoint.sh"]
