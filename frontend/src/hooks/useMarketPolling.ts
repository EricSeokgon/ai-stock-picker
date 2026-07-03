// SPEC-STOCK-039 — 시장 상태 폴링 훅 (REST polling, WebSocket 사용 금지)
import { useCallback, useEffect, useRef, useState } from 'react';

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000';

// 허용 폴링 간격 (초)
export type PollInterval = 30 | 60 | 120;

export interface UseMarketPollingOptions {
  /** 포트폴리오 ID */
  portfolioId: number;
  /** 폴링 간격 (기본값: 60초) */
  interval?: PollInterval;
  /** 포트폴리오 성과 API 호출 콜백 */
  onPoll?: () => Promise<void>;
}

export interface UseMarketPollingResult {
  /** 폴링이 활성 상태인지 여부 */
  isPolling: boolean;
  /** 장 마감으로 폴링이 일시 중지 상태인지 여부 */
  isPaused: boolean;
  /** 현재 KRX 장 개장 여부 */
  isMarketOpen: boolean | null;
  /** 마지막 갱신 시각 */
  lastUpdated: Date | null;
  /** 폴링 토글 (수동 시작/중지) */
  toggle: () => void;
}

/**
 * KRX 시장 상태 기반 자동 폴링 훅.
 *
 * - REST 폴링만 사용 (WebSocket 사용 금지, SPEC-039 제약)
 * - 매 주기마다 /api/portfolios/market-status 를 먼저 확인
 * - 장 마감 시 폴링 건너뜀 (isPaused=true)
 * - 이전 요청이 진행 중이면 중복 폴링 건너뜀
 * - unmount 시 정리 (useEffect cleanup)
 */
export function useMarketPolling({
  portfolioId,
  interval = 60,
  onPoll,
}: UseMarketPollingOptions): UseMarketPollingResult {
  const [isPolling, setIsPolling] = useState<boolean>(true);
  const [isPaused, setIsPaused] = useState<boolean>(false);
  const [isMarketOpen, setIsMarketOpen] = useState<boolean | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  // 진행 중인 요청 여부 추적 (중복 폴링 방지)
  const inFlightRef = useRef<boolean>(false);
  // 타이머 참조 (cleanup 용)
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  // 현재 interval 값을 ref로 유지 (closure 문제 방지)
  const intervalRef = useRef<number>(interval * 1000);

  // interval props 변경 반영
  useEffect(() => {
    intervalRef.current = interval * 1000;
  }, [interval]);

  /** 시장 상태 확인 → 장 중이면 포트폴리오 성과 API 호출 */
  const executePoll = useCallback(async () => {
    // 이전 요청이 진행 중이면 건너뜀
    if (inFlightRef.current) return;

    inFlightRef.current = true;
    try {
      // 시장 상태 조회 (인증 불필요 공개 엔드포인트)
      const statusRes = await fetch(`${API_BASE}/portfolios/market-status`);
      if (!statusRes.ok) return;

      const statusData: { is_open: boolean; message: string } = await statusRes.json();
      setIsMarketOpen(statusData.is_open);

      if (!statusData.is_open) {
        // 장 마감 — 폴링 일시 중지
        setIsPaused(true);
        return;
      }

      // 장 중 — 성과 데이터 갱신
      setIsPaused(false);
      if (onPoll) {
        await onPoll();
      }
      setLastUpdated(new Date());
    } catch {
      // 네트워크 오류는 무시하고 다음 주기에 재시도
    } finally {
      inFlightRef.current = false;
    }
  }, [onPoll]);

  /** 폴링 루프 스케줄링 */
  const scheduleNext = useCallback(() => {
    if (timerRef.current) clearTimeout(timerRef.current);
    timerRef.current = setTimeout(async () => {
      await executePoll();
      scheduleNext();
    }, intervalRef.current);
  }, [executePoll]);

  // 폴링 시작/중지 효과
  useEffect(() => {
    if (!isPolling) {
      if (timerRef.current) {
        clearTimeout(timerRef.current);
        timerRef.current = null;
      }
      return;
    }

    // 즉시 첫 번째 폴링 실행
    void executePoll().then(() => scheduleNext());

    return () => {
      if (timerRef.current) {
        clearTimeout(timerRef.current);
        timerRef.current = null;
      }
    };
  }, [isPolling, portfolioId, executePoll, scheduleNext]);

  /** 폴링 토글 */
  const toggle = useCallback(() => {
    setIsPolling((prev) => !prev);
    if (isPolling) {
      setIsPaused(false);
    }
  }, [isPolling]);

  return { isPolling, isPaused, isMarketOpen, lastUpdated, toggle };
}
