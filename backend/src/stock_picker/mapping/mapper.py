# 기사 본문에서 종목명 추출 및 KRX 코드 매핑
# Phase 1 MVP: 단순 문자열 완전 일치 매핑 (정규식/형태소 분석 미사용)


class StockMapper:
    """기사 본문 내 종목명을 KRX 코드로 매핑하는 클래스.

    Phase 1 MVP 전략:
    - 종목명 완전 일치(exact match)만 허용
    - 부분 문자열 매칭 없음 (예: '삼성' 단독은 '삼성전자'에 매핑 안 됨)
    - 긴 종목명 우선 매칭으로 부분 매칭 방지
    """

    def map_mentions(
        self, content: str, krx_master: dict[str, str]
    ) -> list[dict]:
        """텍스트에서 종목명 추출 → KRX 코드 매핑.

        긴 종목명을 먼저 검색하여 '삼성' 단독이 '삼성전자'로 오매핑되는 것을 방지한다.

        Args:
            content: 기사 본문 텍스트
            krx_master: {종목명: KRX코드} 딕셔너리

        Returns:
            [{"stock_name": ..., "krx_code": ..., "mention_status": "mapped"|"unmapped"}]
        """
        if not content:
            return []

        mentions: list[dict] = []
        # 중복 매핑 방지 (동일 종목이 여러 번 언급되어도 한 번만)
        seen_names: set[str] = set()

        # 긴 종목명부터 매칭 (부분 매칭 방지)
        sorted_names = sorted(krx_master.keys(), key=len, reverse=True)

        for stock_name in sorted_names:
            # 이미 처리된 종목명 스킵
            if stock_name in seen_names:
                continue

            # 완전 단어 일치 검사: 종목명이 본문에 포함되어 있는지 확인
            if stock_name in content:
                krx_code = krx_master[stock_name]
                mentions.append(
                    {
                        "stock_name": stock_name,
                        "krx_code": krx_code,
                        "mention_status": "mapped",
                    }
                )
                seen_names.add(stock_name)

        return mentions
