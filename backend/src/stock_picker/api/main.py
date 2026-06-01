# FastAPI 앱 진입점
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from stock_picker.api.routes import news, recommendations


def create_app() -> FastAPI:
    """FastAPI 애플리케이션 팩토리.

    CORS는 React 개발 서버(5173)를 허용한다.
    """
    app = FastAPI(
        title="한국 주식 추천 시스템",
        version="0.1.0",
        description="AI 기반 한국 주식 & ETF 추천 서비스",
    )

    # CORS - React 프론트엔드 허용
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173"],
        allow_credentials=True,
        allow_methods=["GET"],
        allow_headers=["*"],
    )

    app.include_router(recommendations.router)
    app.include_router(news.router)

    @app.get("/health", tags=["system"])
    async def health() -> dict[str, str]:
        """서비스 헬스 체크"""
        return {"status": "ok"}

    return app


# 직접 실행 또는 uvicorn 진입점용 전역 앱 인스턴스
app = create_app()
