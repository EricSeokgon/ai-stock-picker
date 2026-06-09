// LivePriceBadge 컴포넌트 테스트
import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { LivePriceBadge } from '../components/LivePriceBadge';
import type { LivePrice } from '../hooks/useLivePrice';

// useLivePrice 모킹
const mockUseLivePrice = vi.fn<[string], LivePrice | null>();

vi.mock('../hooks/useLivePrice', () => ({
  useLivePrice: (krxCode: string) => mockUseLivePrice(krxCode),
}));

describe('LivePriceBadge', () => {
  beforeEach(() => {
    mockUseLivePrice.mockReturnValue(null);
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it('가격 데이터가 없으면 "시세 조회 중..."을 표시한다', () => {
    mockUseLivePrice.mockReturnValue(null);
    render(<LivePriceBadge krxCode="005930" />);
    expect(screen.getByText('시세 조회 중...')).toBeDefined();
  });

  it('양수 등락률은 빨간색으로 표시한다', () => {
    mockUseLivePrice.mockReturnValue({
      price: 75000,
      change_pct: 1.23,
      timestamp: '2024-01-01T09:00:00',
    });

    render(<LivePriceBadge krxCode="005930" />);

    // 등락률 텍스트 확인
    const changePctEl = screen.getByText('(+1.23%)');
    expect(changePctEl).toBeDefined();
    // 빨간색 확인
    expect(changePctEl.style.color).toBe('rgb(198, 40, 40)');
  });

  it('음수 등락률은 파란색으로 표시한다', () => {
    mockUseLivePrice.mockReturnValue({
      price: 70000,
      change_pct: -2.50,
      timestamp: '2024-01-01T09:00:00',
    });

    render(<LivePriceBadge krxCode="005930" />);

    const changePctEl = screen.getByText('(-2.50%)');
    expect(changePctEl).toBeDefined();
    // 파란색 확인
    expect(changePctEl.style.color).toBe('rgb(21, 101, 192)');
  });

  it('등락률 0이면 검정색으로 표시한다', () => {
    mockUseLivePrice.mockReturnValue({
      price: 75000,
      change_pct: 0,
      timestamp: '2024-01-01T09:00:00',
    });

    render(<LivePriceBadge krxCode="005930" />);

    const changePctEl = screen.getByText('(0.00%)');
    expect(changePctEl.style.color).toBe('rgb(51, 51, 51)');
  });

  it('가격을 포맷하여 표시한다', () => {
    mockUseLivePrice.mockReturnValue({
      price: 75000,
      change_pct: 1.23,
      timestamp: '2024-01-01T09:00:00',
    });

    render(<LivePriceBadge krxCode="005930" />);

    expect(screen.getByText('₩75,000')).toBeDefined();
  });
});
