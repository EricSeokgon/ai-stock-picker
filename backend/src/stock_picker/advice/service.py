# AI 투자 조언 서비스 — SPEC-STOCK-014
# 리밸런싱·리스크 프로파일·시장 브리핑 생성 (Claude Haiku 동기 호출)
import json
import logging
import os
from typing import Any

import anthropic

from stock_picker.portfolio.utils import get_sector as _get_sector  # SPEC-STOCK-017: 공유 utils로 통합

logger = logging.getLogger(__name__)

# 면책 문구 — 기존 portfolio/ai_analysis.py 패턴 재사용
# @MX:NOTE: [AUTO] 모든 AI 조언 응답에 포함해야 하는 필수 면책 문구 (REQ-AIV-002)
_DISCLAIMER = "본 분석은 투자 권유가 아닌 정보 제공 목적입니다."


def _get_api_key() -> str:
    """ANTHROPIC_API_KEY 환경변수 조회"""
    key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not key:
        raise RuntimeError("ANTHROPIC_API_KEY가 설정되지 않았습니다")
    return key


def build_holdings_summary(holdings: list[Any]) -> list[dict[str, Any]]:
    """보유 종목 목록을 조언 생성용 요약 데이터로 변환.

    # @MX:ANCHOR: [AUTO] 조언 생성 공통 데이터 준비 함수
    # @MX:REASON: rebalance/risk/briefing 3개 엔드포인트에서 공통 호출

    사용자 식별 정보(user_id)는 포함하지 않음 (REQ-NFR-003).
    """
    if not holdings:
        return []

    total_value = sum(float(h.avg_buy_price) * h.quantity for h in holdings)

    result = []
    for h in holdings:
        invested = float(h.avg_buy_price) * h.quantity
        weight_pct = round((invested / total_value * 100), 2) if total_value > 0 else 0.0
        result.append({
            "krx_code": h.krx_code,
            "sector": _get_sector(h.krx_code),
            "quantity": h.quantity,
            "invested_amount": round(invested, 2),
            "weight_pct": weight_pct,
        })
    return result


def compute_risk_score(holdings_summary: list[dict[str, Any]]) -> int:
    """섹터 집중도·단일 종목 노출도 기반 리스크 점수 계산 (0~100).

    높을수록 고위험. 단일 종목 50% 초과 시 고위험 플래그.
    """
    if not holdings_summary:
        return 0

    # 단일 종목 최대 비중 기반 점수
    max_weight = max(h["weight_pct"] for h in holdings_summary)

    # 섹터 집중도 계산
    sector_weights: dict[str, float] = {}
    for h in holdings_summary:
        sector = h.get("sector", "기타")
        sector_weights[sector] = sector_weights.get(sector, 0) + h["weight_pct"]
    max_sector_weight = max(sector_weights.values()) if sector_weights else 0

    # 점수 = 단일 종목 집중도(60%) + 섹터 집중도(40%)
    single_stock_score = min(max_weight, 100)
    sector_score = min(max_sector_weight, 100)
    score = round(single_stock_score * 0.6 + sector_score * 0.4)
    return min(max(score, 0), 100)


def extract_json_from_response(response_text: str) -> dict[str, Any]:
    """Claude 응답 텍스트에서 JSON 블록 추출.

    파싱 실패 시 오류 딕셔너리 반환 (REQ-RB-004).
    """
    text = response_text.strip()
    # 직접 파싱 시도
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # JSON 블록 추출 시도
    start = text.find("{")
    end = text.rfind("}") + 1
    if start >= 0 and end > start:
        try:
            return json.loads(text[start:end])
        except json.JSONDecodeError:
            pass
    return {"error": "JSON 파싱 실패", "raw": text[:200]}


def generate_rebalancing_advice(
    holdings_summary: list[dict[str, Any]],
    rec_universe: list[dict[str, Any]],
) -> dict[str, Any]:
    """리밸런싱 제안 생성 — Claude Haiku 동기 호출.

    # @MX:WARN: [AUTO] 외부 API 동기 호출 — 고부하 시 이벤트 루프 블로킹 가능
    # @MX:REASON: anthropic.Anthropic() 동기 클라이언트; run_in_executor 사용 검토 필요

    예외 격리: Claude 실패 시 오류 딕셔너리 반환, 예외 비전파 (REQ-AIV-005).
    """
    try:
        api_key = _get_api_key()
        client = anthropic.Anthropic(api_key=api_key)

        prompt = (
            "다음 포트폴리오와 최신 추천 유니버스를 바탕으로 리밸런싱 제안을 한국어로 제공해 주세요.\n\n"
            f"보유 종목:\n{json.dumps(holdings_summary, ensure_ascii=False, indent=2)}\n\n"
            f"추천 유니버스:\n{json.dumps(rec_universe, ensure_ascii=False, indent=2)}\n\n"
            "아래 JSON 형식으로만 응답하세요:\n"
            '{"actions": [{"krx_code": "종목코드", "action": "buy_more|reduce|hold", "reason": "한국어 이유"}]}'
        )

        message = client.messages.create(
            model="claude-haiku-4-5",
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )
        response_text = message.content[0].text
        return extract_json_from_response(response_text)

    except Exception:
        logger.exception("리밸런싱 Claude 호출 실패")
        return {"error": "AI 리밸런싱 조언을 일시적으로 사용할 수 없습니다."}


def generate_risk_profile(
    holdings_summary: list[dict[str, Any]],
) -> dict[str, Any]:
    """리스크 프로파일 생성 — 리스크 점수 계산 + Claude 설명 생성.

    # @MX:WARN: [AUTO] 외부 API 동기 호출
    # @MX:REASON: anthropic.Anthropic() 동기 클라이언트 사용

    예외 격리: 실패 시 오류 딕셔너리 반환 (REQ-AIV-005).
    """
    risk_score = compute_risk_score(holdings_summary)

    try:
        api_key = _get_api_key()
        client = anthropic.Anthropic(api_key=api_key)

        prompt = (
            "다음 포트폴리오의 리스크를 분석하고 한국어로 설명해 주세요.\n\n"
            f"보유 종목:\n{json.dumps(holdings_summary, ensure_ascii=False, indent=2)}\n\n"
            f"계산된 리스크 점수: {risk_score}/100\n\n"
            "집중도 위험 요인과 개선 방향을 3~5문장으로 설명해 주세요."
        )

        message = client.messages.create(
            model="claude-haiku-4-5",
            max_tokens=512,
            messages=[{"role": "user", "content": prompt}],
        )
        explanation = message.content[0].text.strip()
        return {"risk_score": risk_score, "explanation": explanation}

    except Exception:
        logger.exception("리스크 프로파일 Claude 호출 실패")
        return {"error": "AI 리스크 분석을 일시적으로 사용할 수 없습니다."}


def generate_market_briefing(
    holdings_summary: list[dict[str, Any]],
    market_context: dict[str, Any],
) -> dict[str, Any]:
    """맞춤형 시장 브리핑 생성 — Claude Haiku 동기 호출 (1일 1회).

    # @MX:WARN: [AUTO] 외부 API 동기 호출
    # @MX:REASON: anthropic.Anthropic() 동기 클라이언트 사용; 1일 1회 캐시로 호출 최소화

    예외 격리: 실패 시 오류 딕셔너리 반환 (REQ-MB-005).
    """
    try:
        api_key = _get_api_key()
        client = anthropic.Anthropic(api_key=api_key)

        prompt = (
            "오늘의 시장 상황과 사용자 포트폴리오에 대한 맞춤형 브리핑을 한국어로 작성해 주세요.\n\n"
            f"시장 컨텍스트:\n{json.dumps(market_context, ensure_ascii=False, indent=2)}\n\n"
            f"보유 종목:\n{json.dumps(holdings_summary, ensure_ascii=False, indent=2)}\n\n"
            "시장 동향과 보유 종목에 미치는 영향을 3~5문장으로 서술해 주세요."
        )

        message = client.messages.create(
            model="claude-haiku-4-5",
            max_tokens=512,
            messages=[{"role": "user", "content": prompt}],
        )
        briefing = message.content[0].text.strip()
        return {"briefing": briefing}

    except Exception:
        logger.exception("시장 브리핑 Claude 호출 실패")
        return {"error": "시장 브리핑을 일시적으로 사용할 수 없습니다."}
