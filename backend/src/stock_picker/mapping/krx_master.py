# KRX 종목 마스터 데이터 로딩 - 종목명 → KRX코드 딕셔너리
import csv
from pathlib import Path

# 기본 픽스처 경로 (테스트 및 개발 환경)
_DEFAULT_CSV_PATH = Path(__file__).parent.parent.parent.parent.parent / "tests" / "fixtures" / "krx_master.csv"


def load_krx_master(csv_path: Path | None = None) -> dict[str, str]:
    """KRX 종목 마스터 CSV 로딩.

    # @MX:ANCHOR: [AUTO] KRX 마스터 데이터 로딩 - 매퍼와 추천 서비스에서 사용
    # @MX:REASON: StockMapper, RecommendationService에서 호출

    Args:
        csv_path: CSV 파일 경로. None이면 기본 경로 사용.

    Returns:
        {종목명: KRX코드} 딕셔너리
    """
    target_path = csv_path or _DEFAULT_CSV_PATH

    result: dict[str, str] = {}

    with open(target_path, encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            stock_name = row.get("종목명", "").strip()
            krx_code = row.get("종목코드", "").strip()
            if stock_name and krx_code:
                result[stock_name] = krx_code

    return result
