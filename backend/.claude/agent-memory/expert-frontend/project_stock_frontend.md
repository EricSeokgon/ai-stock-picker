---
name: project-stock-frontend
description: ai-stock-picker 프로젝트 프론트엔드 구현 현황 - React 18, TypeScript, Vitest 스택
metadata:
  type: project
---

프론트엔드 구현 완료 (TASK-017, TASK-018).

**Why:** SPEC-STOCK-001 한국 주식 ETF 추천 시스템 MVP 대시보드 구현
**How to apply:** 추가 컴포넌트 작업 시 기존 파일 구조와 인라인 CSS 패턴을 유지할 것

## 구현된 파일 목록

- `/home/sklee/moai/ai-stock-picker/frontend/package.json` - React 18, Vitest 2, Testing Library 설정
- `/home/sklee/moai/ai-stock-picker/frontend/vite.config.ts` - jsdom 환경, setupFiles 포함
- `/home/sklee/moai/ai-stock-picker/frontend/tsconfig.json` - bundler moduleResolution
- `/home/sklee/moai/ai-stock-picker/frontend/index.html` - lang="ko"
- `/home/sklee/moai/ai-stock-picker/frontend/src/types.ts` - 도메인 타입 (RecommendationItem, RecommendationsData, PreparingData, NewsItem 등)
- `/home/sklee/moai/ai-stock-picker/frontend/src/api/client.ts` - fetch 래퍼, VITE_API_BASE_URL 지원
- `/home/sklee/moai/ai-stock-picker/frontend/src/components/Disclaimer.tsx`
- `/home/sklee/moai/ai-stock-picker/frontend/src/components/DataPreparingState.tsx` - AC-10 구현
- `/home/sklee/moai/ai-stock-picker/frontend/src/components/RecommendationList.tsx` - 점수 바 시각화
- `/home/sklee/moai/ai-stock-picker/frontend/src/components/NewsFeed.tsx` - 감성 배지
- `/home/sklee/moai/ai-stock-picker/frontend/src/App.tsx` - Promise.all fetch, 4가지 상태 처리
- `/home/sklee/moai/ai-stock-picker/frontend/src/main.tsx`
- `/home/sklee/moai/ai-stock-picker/frontend/src/test-setup.ts`
- 테스트 5개 파일 (24 테스트 모두 통과)

## API 계약

- GET /recommendations → RecommendationsData | PreparingData
- GET /news?limit=N → NewsResponse
- Base URL: VITE_API_BASE_URL env 또는 http://localhost:8000
