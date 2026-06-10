#!/bin/sh
# 컨테이너 시작 시 Alembic 마이그레이션 후 uvicorn 기동
set -e

echo "데이터베이스 마이그레이션 실행 중..."
alembic upgrade head

echo "서버 시작..."
exec uvicorn stock_picker.api.main:app --host 0.0.0.0 --port 8000
