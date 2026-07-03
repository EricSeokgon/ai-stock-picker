---
name: project-stock-047
description: SPEC-STOCK-047 공유 포트폴리오 알림 딥링크 — 좋아요/댓글 알림 클릭→공유뷰 이동, 신규 마이그 0개(조회조인만)
metadata:
  type: project
---

SPEC-STOCK-047 = 공유 포트폴리오 알림 딥링크 (Shared Portfolio Notification Deep-Link).

소셜 아크 연속: 042(공유+좋아요) → 043(좋아요알림+조회통계) → 044(소셜FE) → 045(트렌딩/검색) → 046(댓글) → **047(알림 딥링크)**. SPEC-046 §2.2에서 명시 이연했던 후속 과제. 좋아요/댓글 알림이 클릭해도 아무데도 안 감 → 해당 공유 포트폴리오(`/shared/{share_token}`)로 이동하게 함.

**진짜 신규 (스키마 변경 0):**
- **신규 테이블·마이그레이션 없음** — 최신 마이그은 0028 유지. 순수 조회 조인(`Notification` + `PortfolioShare`)만.
- 알림 응답 `NotificationSchema`에 nullable `link: str | None` 추가(inbox_router.py).
- 링크 산출: type in {portfolio_like, portfolio_comment} + krx_code `^P(\d+)$` 파싱 + 활성 공개 공유(is_public=True) 조인 → `link="/shared/{share_token}"`. 그 외 null.
- FE: Notifications.tsx 링크 있으면 클릭가능→읽음처리 후 navigate. notifications.ts Notification 인터페이스에 link 추가.

**비자명 사실(구현 함정):**
- **인박스 라우터는 async**(`AsyncSession`/`get_session`)인데 `sharing.py`는 sync `Session`. 링크 산출 쿼리는 반드시 async로 작성, sync sharing 함수 재사용 금지(sync/async 혼용 금지). ← 가장 중요한 제약.
- 좋아요·댓글 알림 둘 다 `krx_code=f"P{portfolio.id}"` 동일 규약(043/046). 6자리 종목코드(005930)와 형식 달라 안전 구분.
- `link`는 응답 시점 동적 산출 — notifications 테이블에 컬럼 추가 안 함. 공유 비공개/삭제 시 다음 조회부터 자동 null(무효화 처리 불필요).
- 목록은 단일 배치 쿼리로 N+1 회피(limit 최대 200).
- 라우트 `/shared/:shareToken`(App.tsx:509) = 백엔드 산출 `/shared/{share_token}` 정확 일치.
- 단건 mark_as_read 응답도 link 포함(REQ-NLINK-006, 일관성).

**REQ 접두사 신규 `REQ-NLINK-001~011`**(REQ-NOTI/LIKE/COMMENT/FEED 충돌회피). AC-047-001~010(10개). 테스트 10개(test_notification_links_047.py + notification_links_047.test.tsx).

**제외:** 자동매매(영구)·신규테이블/마이그·일반알림(price_alert/rec) 딥링크·link 영속컬럼·unread-count/read-all 링크·공유없는 포폴 공유생성·클릭통계·이메일/텔레그램 딥링크·댓글 앵커스크롤·페이지네이션 변경.

단일 spec.md(작업지시 명시). 감사 PASS(D1 0건).

관련: [[stock-picker-spec-conventions]] [[project_stock_043]] [[project_stock_046]]
