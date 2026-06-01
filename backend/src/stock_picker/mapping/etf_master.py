# ETF 마스터 데이터 로딩 (JSON 기반)
# ETF 코드 → 섹터 매핑 정보를 JSON 파일에서 읽어 제공한다.
import json
from pathlib import Path

# 기본 ETF 마스터 파일 경로 (tests/fixtures/etf_master.json 또는 프로젝션 설정)
_DEFAULT_ETF_MASTER_PATH = Path(__file__).parent.parent.parent.parent.parent / "tests" / "fixtures" / "etf_master.json"


def load_etf_master(path: Path | None = None) -> list[dict]:
    """ETF 마스터 데이터 로딩.

    # @MX:ANCHOR: [AUTO] ETF 마스터 데이터 로딩 - EtfRecommender에서 직접 호출
    # @MX:REASON: 섹터→ETF 매핑의 유일한 데이터 소스 (REQ-REC-003)

    Args:
        path: JSON 파일 경로. None이면 기본 경로 사용.

    Returns:
        ETF 목록: [{etf_code, etf_name, sectors}, ...]
    """
    target = path or _DEFAULT_ETF_MASTER_PATH
    with open(target, encoding="utf-8") as f:
        data = json.load(f)
    return data
