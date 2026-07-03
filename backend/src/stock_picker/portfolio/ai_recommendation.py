"""AI 개인화 추천 핵심 로직 — 순수 함수 모음 (SPEC-STOCK-037).

DB 접근 없이 테스트 가능한 순수 함수만 포함한다.
- apply_preference_filter: 좋아요/싫어요 기반 추천 재정렬
- rank_by_portfolio_context: 포트폴리오 보유 종목·섹터 기반 필터링
- build_portfolio_context_prompt: Claude 프롬프트 텍스트 생성
- save_preference_select_then_write: SELECT-then-write 선호 저장 (DB 연산 포함)

scipy 미사용(REQ-AIEX-NFR-001) — 표준 라이브러리 산술만 사용.
"""

from __future__ import annotations

import json
from collections import defaultdict
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from stock_picker.db.models import UserRecommendationPreference


# @MX:ANCHOR: [AUTO] 선호 필터 — apply_preference_filter, rank_by_portfolio_context 3곳 이상 호출
# @MX:REASON: router.py POST recommendations, personalized_rec_service.py, 테스트에서 직접 호출
# @MX:SPEC: SPEC-STOCK-037 REQ-AIEX-APPLY


def apply_preference_filter(
    recommendations: list[dict[str, Any]],
    preferences: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """선호(좋아요/싫어요) 기반으로 추천 목록을 재정렬한다 (REQ-AIEX-APPLY).

    - disliked 종목: 목록 끝으로 이동 (제거하지 않음)
    - liked 종목과 같은 섹터: 목록 앞으로 이동
    - 기타: 원래 순서 유지

    scipy 미사용 — 표준 파이썬 sort/partition만 사용 (REQ-AIEX-NFR-001).

    Args:
        recommendations: 추천 종목 dict 목록. 각 dict은 'krx_code'·'sector' 키를 포함할 수 있다.
        preferences: 선호 dict 목록. 각 dict은 'krx_code'·'preference'·'sector' 키를 포함.

    Returns:
        재정렬된 추천 목록 (새 리스트, 원본 변경 없음).
    """
    # 선호 맵 구성: krx_code → preference
    pref_map: dict[str, str] = {}
    liked_sectors: set[str] = set()

    for p in preferences:
        code = p.get("krx_code", "")
        pref = p.get("preference", "")
        # "liked"/"disliked" 이외 값은 무시 (REQ-AIEX-APPLY 안전 처리)
        if pref in ("liked", "disliked"):
            pref_map[code] = pref
        if pref == "liked":
            sector = p.get("sector")
            if sector:
                liked_sectors.add(sector)

    if not pref_map:
        # 선호 없으면 그대로 반환 (복사본)
        return list(recommendations)

    # 3 버킷으로 분류: front(선호 섹터), middle(기타), back(disliked)
    front: list[dict[str, Any]] = []
    middle: list[dict[str, Any]] = []
    back: list[dict[str, Any]] = []

    for rec in recommendations:
        code = rec.get("krx_code", "")
        pref = pref_map.get(code)

        if pref == "disliked":
            back.append(rec)
        elif liked_sectors and rec.get("sector") in liked_sectors:
            front.append(rec)
        else:
            middle.append(rec)

    return front + middle + back


def rank_by_portfolio_context(
    recommendations: list[dict[str, Any]],
    holdings: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """포트폴리오 보유 현황을 반영해 추천 목록을 필터링한다 (REQ-AIEX-PORT).

    - 이미 보유한 종목은 제외
    - 특정 섹터가 포트폴리오 50% 초과(> 50%)이면 해당 섹터 추천 제외

    Args:
        recommendations: 추천 종목 dict 목록. 각 dict은 'krx_code'·'sector' 키를 포함.
        holdings: 보유 종목 dict 목록. 'krx_code'·'sector' 필수.
            집중도 계산에 'current_value'(절댓값) 또는 'weight_pct'(퍼센트, 0~100) 사용.
            'weight_pct'가 있으면 우선 사용.

    Returns:
        필터링된 추천 목록 (새 리스트).
    """
    if not recommendations:
        return []

    # 보유 종목 코드 집합
    owned_codes: set[str] = {h.get("krx_code", "") for h in holdings}

    # 섹터별 집중도 계산 — current_value(절댓값)와 weight_pct(퍼센트) 모두 지원
    # weight_pct가 있으면 퍼센트 직접 합산, current_value이면 비율 계산 (REQ-AIEX-PORT)
    use_weight_pct = any("weight_pct" in h for h in holdings)

    sector_value: dict[str, float] = defaultdict(float)
    total_value = 0.0

    for h in holdings:
        sector = h.get("sector")
        if use_weight_pct:
            # weight_pct는 퍼센트 값(0~100) — 직접 합산
            value = h.get("weight_pct", 0.0) or 0.0
        else:
            # current_value는 절댓값 — 비율로 집중도 계산
            value = h.get("current_value", 0.0) or 0.0
        total_value += value
        if sector:
            sector_value[sector] += value

    # 50% 초과 섹터 집합 (> 50%, NOT >= 50%)
    concentrated_sectors: set[str] = set()
    if total_value > 0:
        if use_weight_pct:
            # weight_pct 합산: 섹터 합 > 50 (퍼센트 기준)
            for sector, val in sector_value.items():
                if val > 50.0:
                    concentrated_sectors.add(sector)
        else:
            # current_value 비율: val / total > 0.5
            for sector, val in sector_value.items():
                if val / total_value > 0.5:
                    concentrated_sectors.add(sector)

    result: list[dict[str, Any]] = []
    for rec in recommendations:
        code = rec.get("krx_code", "")
        sector = rec.get("sector")

        # 보유 종목 제외
        if code in owned_codes:
            continue

        # 집중 섹터 제외
        if sector and sector in concentrated_sectors:
            continue

        result.append(rec)

    return result


def build_portfolio_context_prompt(
    holdings: list[dict[str, Any]],
) -> str:
    """포트폴리오 보유 현황을 기반으로 Claude 추천 요청 프롬프트를 생성한다 (REQ-AIEX-PORT).

    Args:
        holdings: 보유 종목 dict 목록. 'krx_code'·'sector' 필수.
            섹터 분포 계산에 'current_value'(절댓값) 또는 'weight_pct'(퍼센트, 0~100) 사용.

    Returns:
        Claude에 전달할 포트폴리오 컨텍스트 프롬프트 문자열.
    """
    if not holdings:
        return "현재 보유 종목 없음. 초기 포트폴리오 구성을 위한 추천을 요청합니다."

    # 보유 종목 코드 목록
    codes = [h.get("krx_code", "") for h in holdings if h.get("krx_code")]

    # 섹터 분포 계산
    sector_value: dict[str, float] = defaultdict(float)
    total_value = 0.0
    for h in holdings:
        sector = h.get("sector")
        # current_value 우선, 없거나 0이면 weight_pct 폴백 (REQ-AIEX-PORT)
        value = h.get("current_value") or h.get("weight_pct", 0.0) or 0.0
        total_value += value
        if sector:
            sector_value[sector] += value

    # 섹터 분포 텍스트
    sector_lines: list[str] = []
    if total_value > 0:
        for sector, val in sorted(sector_value.items(), key=lambda x: -x[1]):
            pct = val / total_value * 100
            sector_lines.append(f"  - {sector}: {pct:.1f}%")
    sector_text = "\n".join(sector_lines) if sector_lines else "  - 섹터 정보 없음"

    prompt = (
        f"현재 포트폴리오 보유 종목: {', '.join(codes)}\n"
        f"섹터 분포:\n{sector_text}\n\n"
        "위 포트폴리오를 보완할 신규 종목을 5개 추천해 주세요. "
        "각 종목에 대해 krx_code, name, sector, fit_score(0.0~1.0), rationale를 포함한 "
        "JSON 배열로 응답해 주세요."
    )
    return prompt


def save_preference_select_then_write(
    db: "Session",
    user_id: int,
    portfolio_id: int,
    krx_code: str,
    preference: str,
    sector: str | None = None,
) -> "UserRecommendationPreference":
    """SELECT-then-write 패턴으로 선호를 저장한다 (REQ-AIEX-NFR-005).

    ON CONFLICT/upsert 미사용. 기존 행이 있으면 UPDATE, 없으면 INSERT.

    # @MX:WARN: [AUTO] DB 세션 직접 조작 — 호출 측에서 commit/rollback 책임
    # @MX:REASON: FastAPI Depends 주입 패턴에서 세션 수명을 router가 관리

    Args:
        db: SQLAlchemy 세션 (동기).
        user_id: 사용자 ID.
        portfolio_id: 포트폴리오 ID.
        krx_code: 종목 코드.
        preference: "liked" 또는 "disliked".
        sector: 섹터 (nullable).

    Returns:
        저장된 UserRecommendationPreference 인스턴스.
    """
    from stock_picker.db.models import UserRecommendationPreference

    # SELECT 먼저 — 기존 행 조회
    existing: UserRecommendationPreference | None = (
        db.query(UserRecommendationPreference)
        .filter(
            UserRecommendationPreference.user_id == user_id,
            UserRecommendationPreference.portfolio_id == portfolio_id,
            UserRecommendationPreference.krx_code == krx_code,
        )
        .first()
    )

    if existing is not None:
        # UPDATE — 기존 행 수정
        existing.preference = preference
        if sector is not None:
            existing.sector = sector
        db.commit()
        return existing
    else:
        # INSERT — 신규 행 추가
        new_pref = UserRecommendationPreference(
            user_id=user_id,
            portfolio_id=portfolio_id,
            krx_code=krx_code,
            preference=preference,
            sector=sector,
        )
        db.add(new_pref)
        db.commit()
        return new_pref


def parse_claude_recommendations(
    raw_json: str,
    portfolio_id: int,
) -> dict[str, Any]:
    """Claude 응답 JSON을 파싱해 RecommendationResponse 형식의 dict을 반환한다.

    파싱 실패 시 빈 추천 목록과 에러 메시지를 포함한 fallback dict 반환
    (REQ-AIEX-NFR-004: Claude API 실패 시 에러 전파 금지).

    Args:
        raw_json: Claude가 반환한 JSON 문자열 (배열 또는 객체).
        portfolio_id: 포트폴리오 ID.

    Returns:
        recommendations 키를 포함하는 dict.
    """
    try:
        data = json.loads(raw_json)
        if isinstance(data, list):
            items = data
        elif isinstance(data, dict):
            # {"recommendations": [...]} 형태도 허용
            items = data.get("recommendations", [])
        else:
            items = []

        return {
            "portfolio_id": portfolio_id,
            "recommendations": items,
            "disclaimer": "본 추천은 AI 분석 참고 정보이며 투자 권유가 아닙니다.",
        }
    except (json.JSONDecodeError, TypeError, ValueError):
        # Claude API 파싱 실패 — fallback (REQ-AIEX-NFR-004)
        return {
            "portfolio_id": portfolio_id,
            "recommendations": [],
            "disclaimer": "본 추천은 AI 분석 참고 정보이며 투자 권유가 아닙니다.",
            "error": "추천 파싱에 실패했습니다. 잠시 후 다시 시도해 주세요.",
        }
