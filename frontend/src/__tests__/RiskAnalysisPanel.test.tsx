// SPEC-STOCK-027 RiskAnalysisPanel 컴포넌트 테스트
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

// AuthContext mock — hoisting 안전
vi.mock('../auth/AuthContext', () => ({
  useAuth: () => ({ token: 'test-token' }),
}));

// portfolio API mock
vi.mock('../api/portfolio', () => ({
  apiGetRiskAnalysis: vi.fn(),
}));

import RiskAnalysisPanel from '../components/RiskAnalysisPanel';
import { apiGetRiskAnalysis } from '../api/portfolio';

// ─── 헬퍼: 목 데이터 생성 ─────────────────────────────────────────────────

function makeRiskData(tickers = ['005930', '000660']) {
  const matrix: Record<string, Record<string, number>> = {};
  for (const r of tickers) {
    matrix[r] = {};
    for (const c of tickers) {
      matrix[r][c] = r === c ? 1.0 : 0.3;
    }
  }
  return {
    correlation_matrix: matrix,
    holdings_volatility: [
      { krx_code: tickers[0], name: '삼성전자', annualized_volatility_pct: 25.5, price_data_days: 90 },
      { krx_code: tickers[1], name: 'SK하이닉스', annualized_volatility_pct: 35.2, price_data_days: 90 },
    ],
    portfolio_volatility_pct: 28.0,
    diversification_benefit_pct: 4.5,
    period_days: 90,
    calculated_at: '2026-06-18T00:00:00Z',
  };
}

const mockedApi = apiGetRiskAnalysis as ReturnType<typeof vi.fn>;

describe('RiskAnalysisPanel', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('초기 로딩 상태를 표시한다', () => {
    // pending promise → 로딩 상태 유지
    mockedApi.mockReturnValue(new Promise(() => { /* 영원히 대기 */ }));

    render(<RiskAnalysisPanel portfolioId={1} />);
    expect(screen.getByText('분석 중...')).toBeDefined();
  });

  it('데이터 로드 후 상관계수 매트릭스를 렌더링한다', async () => {
    mockedApi.mockResolvedValue(makeRiskData());

    render(<RiskAnalysisPanel portfolioId={1} />);

    await waitFor(() => {
      expect(screen.getByText('상관계수 매트릭스')).toBeDefined();
    });
    // 대각선 1.00 값 확인
    const onePairs = screen.getAllByText('1.00');
    expect(onePairs.length).toBeGreaterThanOrEqual(2);
  });

  it('변동성 테이블을 변동성 내림차순으로 정렬하여 렌더링한다', async () => {
    mockedApi.mockResolvedValue(makeRiskData());

    render(<RiskAnalysisPanel portfolioId={1} />);

    await waitFor(() => {
      expect(screen.getByText('보유 종목별 변동성')).toBeDefined();
    });

    // SK하이닉스(35.2%) > 삼성전자(25.5%) 순서로 표시되어야 함
    // getAllByText로 값 확인 (두 테이블이 있으므로 row 인덱스 대신 텍스트로 검증)
    expect(screen.getByText('35.20%')).toBeDefined();
    expect(screen.getByText('25.50%')).toBeDefined();

    // 내림차순 검증: SK하이닉스 행이 삼성전자 행보다 먼저 렌더링되어야 함
    const volatilityPanel = screen.getByText('보유 종목별 변동성').closest('div');
    const allText = volatilityPanel?.parentElement?.textContent ?? '';
    const idx35 = allText.indexOf('35.20');
    const idx25 = allText.indexOf('25.50');
    expect(idx35).toBeLessThan(idx25);
  });

  it('기간 선택 버튼 클릭 시 해당 period로 API를 재호출한다', async () => {
    mockedApi.mockResolvedValue(makeRiskData());

    render(<RiskAnalysisPanel portfolioId={1} />);

    await waitFor(() => {
      expect(screen.getByText('상관계수 매트릭스')).toBeDefined();
    });

    const user = userEvent.setup();
    const btn180 = screen.getByRole('button', { name: '180일 기간 선택' });
    await user.click(btn180);

    await waitFor(() => {
      // 두 번 이상 호출되었고, 마지막 호출에서 period=180 확인
      const calls = mockedApi.mock.calls;
      const lastCall = calls[calls.length - 1] as [string, number, number, boolean];
      expect(lastCall[2]).toBe(180);
    });
  });

  it('API 오류 시 에러 메시지를 표시한다', async () => {
    mockedApi.mockRejectedValue(new Error('리스크 분석 조회 실패: 500'));

    render(<RiskAnalysisPanel portfolioId={1} />);

    await waitFor(() => {
      expect(screen.getByText('리스크 분석 조회 실패: 500')).toBeDefined();
    });
  });
});
