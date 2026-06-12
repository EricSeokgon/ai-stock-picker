# 포트폴리오 AI 분석 — Claude API를 사용한 포트폴리오 진단
# REQ-AI-PORTFOLIO: 보유 종목 구성 분석, 리스크 평가, 개선 제안 제공
import json
import logging
from typing import Any

import anthropic
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from stock_picker.db.models import Portfolio, PortfolioHolding
from stock_picker.portfolio.utils import get_sector as _get_sector  # SPEC-STOCK-017: 공유 utils로 통합

logger = logging.getLogger(__name__)

# 면책 문구 — 투자 권유 아님 명시
_DISCLAIMER = "본 분석은 투자 권유가 아닌 정보 제공 목적입니다."


def analyze_portfolio(portfolio_id: int, user_id: int, db: Session) -> dict[str, Any]:
    """포트폴리오 AI 분석 실행.

    # @MX:ANCHOR: [AUTO] 포트폴리오 AI 분석 단일 진입점
    # @MX:REASON: portfolio/router.py에서 호출, Claude API 연동 담당

    1. 포트폴리오 + holdings 조회 (소유권 검증, 403)
    2. 보유 종목 없으면 Claude 미호출
    3. 보유 종목별 섹터, 비중, 수익률 계산
    4. Claude API(claude-haiku-4-5) 호출
    5. 면책 문구 추가
    6. Claude 실패 시 오류 딕셔너리 반환 (500 대신)

    Returns:
        분석 결과 딕셔너리 또는 오류/메시지 딕셔너리
    """
    # 포트폴리오 소유권 확인
    portfolio = (
        db.query(Portfolio)
        .filter(Portfolio.id == portfolio_id, Portfolio.user_id == user_id)
        .first()
    )
    if portfolio is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="포트폴리오에 접근할 수 없습니다",
        )

    # holdings 조회
    holdings = (
        db.query(PortfolioHolding)
        .filter(PortfolioHolding.portfolio_id == portfolio_id)
        .all()
    )

    # 보유 종목 없으면 Claude 미호출
    if not holdings:
        return {"message": "분석할 보유 종목이 없습니다."}

    # 포트폴리오 구성 계산
    portfolio_data = _build_portfolio_data(holdings)

    # Claude API 호출
    try:
        analysis = _call_claude(portfolio_data)
    except Exception:
        logger.exception("Claude AI 분석 실패 — portfolio_id=%s", portfolio_id)
        return {"error": "AI 분석을 일시적으로 사용할 수 없습니다."}

    analysis["disclaimer"] = _DISCLAIMER
    return analysis


def _build_portfolio_data(holdings: list[PortfolioHolding]) -> list[dict[str, Any]]:
    """보유 종목 목록을 분석용 데이터 구조로 변환.

    사용자 식별 정보(user_id, portfolio_id)는 포함하지 않음.
    """
    total_value = sum(float(h.avg_buy_price) * h.quantity for h in holdings)

    result = []
    for h in holdings:
        invested = float(h.avg_buy_price) * h.quantity
        weight_pct = round((invested / total_value * 100), 2) if total_value > 0 else 0.0
        result.append({
            "krx_code": h.krx_code,
            "sector": _get_sector(h.krx_code),
            "quantity": h.quantity,
            "avg_buy_price": float(h.avg_buy_price),
            "invested_amount": round(invested, 2),
            "weight_pct": weight_pct,
        })
    return result


def _call_claude(portfolio_data: list[dict[str, Any]]) -> dict[str, Any]:
    """Claude API 동기 호출 — 포트폴리오 분석 요청.

    # @MX:WARN: [AUTO] 외부 API 동기 호출 — 응답 지연 가능
    # @MX:REASON: anthropic.Anthropic() 동기 클라이언트 사용;
    #             FastAPI 라우터에서 직접 호출 시 이벤트 루프 블로킹 발생 가능.
    #             고부하 환경에서는 run_in_executor 또는 비동기 클라이언트 전환 필요.

    Returns:
        {"diversification": str, "risk": str, "suggestions": str}
    """
    import os
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY가 설정되지 않았습니다")

    client = anthropic.Anthropic(api_key=api_key)

    prompt = (
        "다음 포트폴리오 구성을 분석하고 한국어로 답변해 주세요.\n\n"
        f"포트폴리오 데이터:\n{json.dumps(portfolio_data, ensure_ascii=False, indent=2)}\n\n"
        "아래 JSON 형식으로만 응답하세요 (다른 텍스트 없이):\n"
        '{"diversification": "분산투자 평가 (2-3문장)", '
        '"risk": "위험 수준 평가 (2-3문장)", '
        '"suggestions": "개선 제안 (2-3문장)"}'
    )

    message = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=512,
        messages=[{"role": "user", "content": prompt}],
    )

    response_text = message.content[0].text.strip()

    # JSON 파싱 시도
    try:
        return json.loads(response_text)
    except json.JSONDecodeError:
        # JSON 블록 추출 시도
        start = response_text.find("{")
        end = response_text.rfind("}") + 1
        if start >= 0 and end > start:
            return json.loads(response_text[start:end])
        raise
