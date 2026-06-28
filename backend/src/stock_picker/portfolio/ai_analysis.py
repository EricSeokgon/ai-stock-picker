# 포트폴리오 AI 분석 — Claude API를 사용한 포트폴리오 진단 및 최적화
# REQ-AI-PORTFOLIO: 보유 종목 구성 분석, 리스크 평가, 개선 제안 제공
# SPEC-STOCK-026: 비동기 클라이언트 전환, optimize_portfolio_with_claude 추가
import json
import logging
from typing import Any

import anthropic
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from stock_picker.db.models import Portfolio, PortfolioHolding
from stock_picker.portfolio import fx_rate as fx_rate_module
from stock_picker.portfolio.utils import (
    get_sector as _get_sector,
)  # SPEC-STOCK-017: 공유 utils로 통합

logger = logging.getLogger(__name__)

# 면책 문구 — 투자 권유 아님 명시
_DISCLAIMER = "본 분석은 투자 권유가 아닌 정보 제공 목적입니다."


# @MX:NOTE: [AUTO] SPEC-STOCK-026: 비동기 클라이언트로 전환 — 이벤트 루프 블로킹 해결
async def analyze_portfolio(portfolio_id: int, user_id: int, db: Session) -> dict[str, Any]:
    """포트폴리오 AI 분석 실행 (비동기).

    # @MX:ANCHOR: [AUTO] 포트폴리오 AI 분석 단일 진입점
    # @MX:REASON: portfolio/router.py에서 호출, Claude API 연동 담당

    1. 포트폴리오 + holdings 조회 (소유권 검증, 403)
    2. 보유 종목 없으면 Claude 미호출
    3. 보유 종목별 섹터, 비중, 수익률 계산
    4. Claude API(claude-haiku-4-5) 비동기 호출
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
        db.query(PortfolioHolding).filter(PortfolioHolding.portfolio_id == portfolio_id).all()
    )

    # 보유 종목 없으면 Claude 미호출
    if not holdings:
        return {"message": "분석할 보유 종목이 없습니다."}

    # 포트폴리오 구성 계산
    portfolio_data = _build_portfolio_data(holdings)

    # Claude API 비동기 호출
    try:
        analysis = await _call_claude_async(portfolio_data)
    except Exception:
        logger.exception("Claude AI 분석 실패 — portfolio_id=%s", portfolio_id)
        return {"error": "AI 분석을 일시적으로 사용할 수 없습니다."}

    analysis["disclaimer"] = _DISCLAIMER
    return analysis


def _build_portfolio_data(
    holdings: list[PortfolioHolding],
    fx_rate: float = 1.0,
) -> list[dict[str, Any]]:
    """보유 종목 목록을 분석용 데이터 구조로 변환.

    # @MX:NOTE: [AUTO] USD 종목은 fx_rate로 KRW 환산하여 total_value 및 weight_pct 계산
    사용자 식별 정보(user_id, portfolio_id)는 포함하지 않음.
    fx_rate: USD→KRW 환율 (기본 1.0 = KRX 전용 환경)
    """

    def _krw_value(h: PortfolioHolding) -> float:
        currency = getattr(h, "currency", "KRW") or "KRW"
        rate = fx_rate if currency == "USD" else 1.0
        return float(h.avg_buy_price) * h.quantity * rate

    total_value = sum(_krw_value(h) for h in holdings)

    result = []
    for h in holdings:
        invested_krw = _krw_value(h)
        weight_pct = round((invested_krw / total_value * 100), 2) if total_value > 0 else 0.0
        market = getattr(h, "market", "KRX") or "KRX"
        currency = getattr(h, "currency", "KRW") or "KRW"
        result.append(
            {
                "krx_code": h.krx_code,
                "sector": _get_sector(h.krx_code),
                "quantity": h.quantity,
                "avg_buy_price": float(h.avg_buy_price),
                "invested_amount": round(invested_krw, 2),
                "weight_pct": weight_pct,
                "market": market,
                "currency": currency,
            }
        )
    return result


async def _call_claude_async(portfolio_data: list[dict[str, Any]]) -> dict[str, Any]:
    """Claude API 비동기 호출 — 포트폴리오 분석 요청.

    SPEC-STOCK-026: anthropic.AsyncAnthropic 사용으로 이벤트 루프 블로킹 해결.

    Returns:
        {"diversification": str, "risk": str, "suggestions": str}
    """
    import os

    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY가 설정되지 않았습니다")

    client = anthropic.AsyncAnthropic(api_key=api_key)

    prompt = (
        "다음 포트폴리오 구성을 분석하고 한국어로 답변해 주세요.\n\n"
        f"포트폴리오 데이터:\n{json.dumps(portfolio_data, ensure_ascii=False, indent=2)}\n\n"
        "아래 JSON 형식으로만 응답하세요 (다른 텍스트 없이):\n"
        '{"diversification": "분산투자 평가 (2-3문장)", '
        '"risk": "위험 수준 평가 (2-3문장)", '
        '"suggestions": "개선 제안 (2-3문장)"}'
    )

    message = await client.messages.create(
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


# @MX:ANCHOR: [AUTO] 포트폴리오 코멘터리 생성 — router·테스트 다중 참조
# @MX:REASON: SPEC-STOCK-040 REQ-CMT-001; router.py get_ai_commentary 및 단위 테스트 3곳 이상 호출
async def generate_portfolio_commentary(
    portfolio_data: dict,
    anthropic_client=None,
) -> str:
    """포트폴리오 AI 코멘터리 생성 (비동기).

    portfolio_data: 수익률·보유 종목·리스크 지표 등을 담은 딕셔너리.
    anthropic_client: anthropic.AsyncAnthropic 인스턴스 (테스트 목업 주입 용이).
    예외 발생 시 대체 텍스트 반환 (절대 500 전파하지 않음).
    """
    try:
        # 프롬프트 구성 — 한국어 코멘터리 요청
        total_value = portfolio_data.get("total_value", 0)
        total_return_pct = portfolio_data.get("total_return_pct", 0)
        holdings = portfolio_data.get("holdings", [])
        risk_metrics = portfolio_data.get("risk_metrics", {})
        sector_summary = portfolio_data.get("sector_summary", [])

        prompt_parts = [
            "다음 포트폴리오를 분석하고 한국어로 코멘터리를 작성해 주세요.\n",
            f"총 평가액: {total_value:,.0f}원",
            f"수익률: {total_return_pct:.1f}%\n",
            f"보유 종목:\n{json.dumps(holdings, ensure_ascii=False, indent=2)}\n",
        ]
        if risk_metrics:
            prompt_parts.append(
                f"리스크 지표:\n{json.dumps(risk_metrics, ensure_ascii=False, indent=2)}\n"
            )
        if sector_summary:
            prompt_parts.append(
                f"섹터 요약:\n{json.dumps(sector_summary, ensure_ascii=False, indent=2)}\n"
            )
        prompt_parts.append(
            "다음 내용을 포함한 3-4문장의 한국어 코멘터리를 작성해 주세요:\n"
            "1. 전체 수익률 요약\n"
            "2. 리스크 코멘트\n"
            "3. 섹터 집중도 코멘트\n"
            "4. 투자 제안 (1문장)\n"
        )
        prompt = "\n".join(prompt_parts)

        response = await anthropic_client.messages.create(
            model="claude-haiku-4-5",
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )

        result = response.content[0].text

        # 면책 문구가 없으면 자동 추가
        if _DISCLAIMER not in result:
            result = result + "\n" + _DISCLAIMER

        return result

    except Exception:
        logger.exception("포트폴리오 코멘터리 생성 실패")
        return "포트폴리오 분석을 일시적으로 제공할 수 없습니다. 잠시 후 다시 시도해 주세요."


async def optimize_portfolio_with_claude(
    holdings_data: list[dict[str, Any]],
    portfolio_codes: list[str],
    db: Session,
) -> dict[str, Any]:
    """Claude API를 사용한 포트폴리오 최적화 분석 (비동기).

    # @MX:ANCHOR: [AUTO] 포트폴리오 최적화 Claude 호출 진입점
    # @MX:REASON: service.optimize_portfolio, 테스트에서 2곳 이상 참조

    Args:
        holdings_data: 보유 종목 데이터 목록 (krx_code, weight_pct, sector 포함)
        portfolio_codes: 포트폴리오 보유 종목 코드 목록 (new_stocks 필터용)
        db: DB 세션 (recommendations 테이블 조회용)

    Returns:
        {"score_breakdown": {...}, "target_weights": [...], "new_stocks": [...], "summary": str}
    """
    import os
    from stock_picker.db.models import Recommendation  # noqa: F401

    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    # api_key가 없어도 AsyncAnthropic 인스턴스는 생성 가능 (테스트 환경)
    client = anthropic.AsyncAnthropic(api_key=api_key if api_key else None)

    prompt = (
        "다음 포트폴리오를 분석하여 최적화 방안을 제시해 주세요.\n\n"
        f"현재 보유 종목:\n{json.dumps(holdings_data, ensure_ascii=False, indent=2)}\n\n"
        "아래 JSON 형식으로만 응답하세요 (다른 텍스트 없이):\n"
        "{\n"
        '  "score_breakdown": {\n'
        '    "diversification": 70,\n'
        '    "risk_balance": 65,\n'
        '    "momentum": 75\n'
        "  },\n"
        '  "target_weights": [\n'
        '    {"krx_code": "005930", "current_pct": 50.0, "target_pct": 45.0}\n'
        "  ],\n"
        '  "new_stocks": [\n'
        '    {"krx_code": "035420", "name": "NAVER", "sector": "IT서비스", "reason": "추천 이유"}\n'
        "  ],\n"
        '  "summary": "포트폴리오 종합 평가 3-4 문장. 본 분석은 투자 권유가 아닌 정보 제공 목적입니다."\n'
        "}"
    )

    message = await client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )

    response_text = message.content[0].text.strip()

    # JSON 파싱 시도
    try:
        return json.loads(response_text)
    except json.JSONDecodeError:
        start = response_text.find("{")
        end = response_text.rfind("}") + 1
        if start >= 0 and end > start:
            return json.loads(response_text[start:end])
        raise
