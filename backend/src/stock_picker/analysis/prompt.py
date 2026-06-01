# Claude API 프롬프트 빌더 - 시스템 프롬프트 및 사용자 메시지 생성

# Claude에게 한국 금융 뉴스 분석을 요청하는 시스템 프롬프트
SYSTEM_PROMPT = """당신은 한국 금융 뉴스 분석 전문가입니다.
주어진 뉴스 기사를 분석하여 정확히 아래 JSON 형식으로 응답하세요:
{
  "sentiment": "positive | negative | neutral",
  "sentiment_score": <-1.0 ~ 1.0 사이 부동소수>,
  "sector_tags": ["섹터1", "섹터2"],
  "keywords": ["키워드1", "키워드2"],
  "summary": "1문장 핵심 요약"
}
다른 텍스트 없이 JSON만 응답하세요."""


def build_user_message(
    title: str,
    content: str,
    max_content_chars: int = 2000,
) -> str:
    """기사 분석 요청 메시지 생성.

    비용 절감을 위해 본문 길이를 max_content_chars로 제한한다.

    Args:
        title: 기사 제목
        content: 기사 본문
        max_content_chars: 본문 최대 문자 수 (기본 2000)

    Returns:
        Claude에게 전송할 사용자 메시지 문자열
    """
    # 본문이 max_content_chars를 초과하면 잘라냄
    truncated_content = content[:max_content_chars] if len(content) > max_content_chars else content

    return f"제목: {title}\n\n본문: {truncated_content}"


# 배치 분석용 시스템 프롬프트 (REQ-AI-004)
BATCH_SYSTEM_PROMPT = """당신은 한국 금융 뉴스 분석 전문가입니다.
여러 뉴스 기사를 분석하여 정확히 아래 JSON 배열 형식으로 응답하세요.
기사 순서를 유지하고, 각 기사를 독립적으로 분석하세요:
[
  {
    "sentiment": "positive | negative | neutral",
    "sentiment_score": <-1.0 ~ 1.0 사이 부동소수>,
    "sector_tags": ["섹터1", "섹터2"],
    "keywords": ["키워드1", "키워드2"],
    "summary": "1문장 핵심 요약"
  },
  ...
]
다른 텍스트 없이 JSON 배열만 응답하세요."""


def build_batch_user_message(
    articles: list[tuple[str, str]],
    max_content_chars: int = 1000,
) -> str:
    """배치 기사 분석 요청 메시지 생성 (REQ-AI-004).

    복수 기사를 단일 Claude 호출로 분석하기 위한 메시지.

    Args:
        articles: (title, content) 튜플 목록
        max_content_chars: 기사별 본문 최대 문자 수

    Returns:
        Claude에게 전송할 배치 사용자 메시지 문자열
    """
    parts: list[str] = []
    for i, (title, content) in enumerate(articles, start=1):
        truncated = content[:max_content_chars] if len(content) > max_content_chars else content
        parts.append(f"[기사 {i}]\n제목: {title}\n본문: {truncated}")
    return "\n\n".join(parts)
