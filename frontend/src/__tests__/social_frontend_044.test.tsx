// SPEC-STOCK-044: 소셜 프론트엔드 완성 TDD 테스트 (AC-044-001 ~ AC-044-015)
// 커버리지: 좋아요 토글(T-044-001~008), 조회 통계(T-044-009~014), 알림 뱃지(T-044-015)

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

// --- vi.mock 선언 (hoisted) ---
vi.mock('react-router-dom', () => ({
  useParams: vi.fn(() => ({ shareToken: 'tok-abc' })),
}));

vi.mock('../auth/AuthContext', () => ({
  useAuth: vi.fn(() => ({ token: 'test-jwt' })),
}));

vi.mock('../api/feed', () => ({
  getSharedPortfolio: vi.fn(),
  likeSharedPortfolio: vi.fn(),
  unlikeSharedPortfolio: vi.fn(),
}));

vi.mock('../api/portfolio', () => ({
  apiGetShare: vi.fn(),
  apiCreateShare: vi.fn(),
  apiDeleteShare: vi.fn(),
  getShareStats: vi.fn(),
}));

vi.mock('../api/notifications', () => ({
  fetchNotifications: vi.fn(),
  markNotificationRead: vi.fn(),
  markAllNotificationsRead: vi.fn(),
}));

// --- 모듈 import (mock 이후) ---
import SharedPortfolio from '../pages/SharedPortfolio';
import SharePanel from '../components/SharePanel';
import NotificationsPage from '../pages/Notifications';
import { useAuth } from '../auth/AuthContext';
import {
  getSharedPortfolio,
  likeSharedPortfolio,
  unlikeSharedPortfolio,
} from '../api/feed';
import { apiGetShare, getShareStats } from '../api/portfolio';
import { fetchNotifications, markAllNotificationsRead } from '../api/notifications';

// 타입 캐스팅 헬퍼
const mockedUseAuth = useAuth as ReturnType<typeof vi.fn>;
const mockedGetSharedPortfolio = getSharedPortfolio as ReturnType<typeof vi.fn>;
const mockedLike = likeSharedPortfolio as ReturnType<typeof vi.fn>;
const mockedUnlike = unlikeSharedPortfolio as ReturnType<typeof vi.fn>;
const mockedApiGetShare = apiGetShare as ReturnType<typeof vi.fn>;
const mockedGetShareStats = getShareStats as ReturnType<typeof vi.fn>;
const mockedFetchNotifications = fetchNotifications as ReturnType<typeof vi.fn>;
const mockedMarkAllRead = markAllNotificationsRead as ReturnType<typeof vi.fn>;

// 공유 포트폴리오 mock 응답 (getSharedPortfolio)
const mockPublicPortfolio = {
  share_token: 'tok-abc',
  portfolio_id: 1,
  owner_display: 'TestUser',
  created_at: '2024-01-01T00:00:00Z',
  name: 'Test Portfolio',
  description: null,
  holdings: [],
  total_value: 100000,
  total_return_rate: 5.0,
  goal_progress: null,
  like_count: 5,
  view_count: 10,
};

// ShareResponse mock (apiGetShare)
const mockShareData = {
  portfolio_id: 1,
  share_token: 'tok-abc',
  share_url: '/shared/tok-abc',
  view_count: 10,
  like_count: 5,
  created_at: '2024-01-01T00:00:00Z',
  is_active: true,
};

// 7일 통계 mock (날짜 오름차순)
const mockStats = [
  { date: '2024-01-01', view_count: 3 },
  { date: '2024-01-02', view_count: 7 },
  { date: '2024-01-03', view_count: 0 },
  { date: '2024-01-04', view_count: 2 },
  { date: '2024-01-05', view_count: 5 },
  { date: '2024-01-06', view_count: 1 },
  { date: '2024-01-07', view_count: 8 },
];

// ==================== 공통 beforeEach ====================
beforeEach(() => {
  vi.clearAllMocks();
  mockedUseAuth.mockReturnValue({ token: 'test-jwt' });
  mockedGetSharedPortfolio.mockResolvedValue(mockPublicPortfolio);
  mockedLike.mockResolvedValue({ like_count: 6, liked: true });
  mockedUnlike.mockResolvedValue(undefined);
  mockedApiGetShare.mockResolvedValue(mockShareData);
  mockedGetShareStats.mockResolvedValue({ stats: mockStats });
  mockedFetchNotifications.mockResolvedValue([]);
  mockedMarkAllRead.mockResolvedValue({ updated: 0 });
});

// ==================== SharedPortfolio 좋아요 토글 ====================

describe('AC-044-001/002: SharedPortfolio 좋아요 성공', () => {
  it('T-044-001: 좋아요 클릭 후 버튼 라벨이 "좋아요 취소"로 변경된다', async () => {
    const user = userEvent.setup();
    render(<SharedPortfolio />);

    // 로딩 완료 대기
    await waitFor(() =>
      expect(screen.queryByText('로딩 중...')).not.toBeInTheDocument()
    );

    const btn = screen.getByTestId('like-btn');
    expect(btn).not.toHaveTextContent('취소');

    await user.click(btn);

    await waitFor(() => {
      expect(screen.getByTestId('like-btn')).toHaveTextContent('좋아요 취소');
    });
  });

  it('T-044-002: 좋아요 성공 시 서버 응답 like_count 값이 표시된다', async () => {
    mockedLike.mockResolvedValue({ like_count: 9, liked: true });
    const user = userEvent.setup();
    render(<SharedPortfolio />);

    await waitFor(() =>
      expect(screen.queryByText('로딩 중...')).not.toBeInTheDocument()
    );

    await user.click(screen.getByTestId('like-btn'));

    await waitFor(() => {
      expect(screen.getByTestId('like-count')).toHaveTextContent('9');
    });
  });
});

describe('AC-044-003/004: SharedPortfolio 좋아요 취소 성공', () => {
  it('T-044-003: 좋아요 취소 성공 후 버튼 라벨이 "좋아요"로 복귀한다', async () => {
    const user = userEvent.setup();
    render(<SharedPortfolio />);

    await waitFor(() =>
      expect(screen.queryByText('로딩 중...')).not.toBeInTheDocument()
    );

    // 먼저 좋아요
    await user.click(screen.getByTestId('like-btn'));
    await waitFor(() =>
      expect(screen.getByTestId('like-btn')).toHaveTextContent('좋아요 취소')
    );

    // 취소 클릭
    await user.click(screen.getByTestId('like-btn'));

    await waitFor(() => {
      expect(screen.getByTestId('like-btn')).not.toHaveTextContent('취소');
    });
  });

  it('T-044-004: 좋아요 취소 후 like_count가 1 감소한다', async () => {
    mockedLike.mockResolvedValue({ like_count: 6, liked: true });
    const user = userEvent.setup();
    render(<SharedPortfolio />);

    await waitFor(() =>
      expect(screen.queryByText('로딩 중...')).not.toBeInTheDocument()
    );

    // 좋아요 → count 6
    await user.click(screen.getByTestId('like-btn'));
    await waitFor(() =>
      expect(screen.getByTestId('like-count')).toHaveTextContent('6')
    );

    // 취소 → count 5 (6 - 1)
    await user.click(screen.getByTestId('like-btn'));

    await waitFor(() => {
      expect(screen.getByTestId('like-count')).toHaveTextContent('5');
    });
  });
});

describe('AC-044-005/006: SharedPortfolio 비인증 사용자 처리', () => {
  it('T-044-005: 토큰 없을 때 좋아요 클릭 시 API를 호출하지 않는다', async () => {
    mockedUseAuth.mockReturnValue({ token: null });
    const user = userEvent.setup();
    render(<SharedPortfolio />);

    await waitFor(() =>
      expect(screen.queryByText('로딩 중...')).not.toBeInTheDocument()
    );

    await user.click(screen.getByTestId('like-btn'));

    expect(mockedLike).not.toHaveBeenCalled();
    expect(mockedUnlike).not.toHaveBeenCalled();
  });

  it('T-044-006: 토큰 없을 때 좋아요 클릭 시 로그인 안내 메시지가 표시된다', async () => {
    mockedUseAuth.mockReturnValue({ token: null });
    const user = userEvent.setup();
    render(<SharedPortfolio />);

    await waitFor(() =>
      expect(screen.queryByText('로딩 중...')).not.toBeInTheDocument()
    );

    await user.click(screen.getByTestId('like-btn'));

    await waitFor(() => {
      expect(screen.getByText(/로그인/)).toBeInTheDocument();
    });
  });
});

describe('AC-044-007/008: SharedPortfolio 좋아요 취소 실패 처리', () => {
  it('T-044-007: 취소 실패 시 liked 상태가 변경되지 않아 라벨이 "좋아요 취소"를 유지한다', async () => {
    mockedUnlike.mockRejectedValue(new Error('취소 실패'));
    const user = userEvent.setup();
    render(<SharedPortfolio />);

    await waitFor(() =>
      expect(screen.queryByText('로딩 중...')).not.toBeInTheDocument()
    );

    // 좋아요 → liked 상태
    await user.click(screen.getByTestId('like-btn'));
    await waitFor(() =>
      expect(screen.getByTestId('like-btn')).toHaveTextContent('좋아요 취소')
    );

    // 취소 시도 (실패)
    await user.click(screen.getByTestId('like-btn'));

    await waitFor(() => {
      // 라벨 변경 없음
      expect(screen.getByTestId('like-btn')).toHaveTextContent('좋아요 취소');
    });
  });

  it('T-044-008: 좋아요 취소 실패 시 오류 메시지가 표시된다', async () => {
    mockedUnlike.mockRejectedValue(new Error('취소 실패'));
    const user = userEvent.setup();
    render(<SharedPortfolio />);

    await waitFor(() =>
      expect(screen.queryByText('로딩 중...')).not.toBeInTheDocument()
    );

    await user.click(screen.getByTestId('like-btn'));
    await waitFor(() =>
      expect(screen.getByTestId('like-btn')).toHaveTextContent('좋아요 취소')
    );

    await user.click(screen.getByTestId('like-btn'));

    await waitFor(() => {
      expect(screen.getByTestId('like-error')).toBeInTheDocument();
    });
  });
});

// ==================== SharePanel 7일 조회 통계 ====================

describe('AC-044-009: SharePanel 활성 공유 시 getShareStats 호출', () => {
  it('T-044-009: 공유 데이터 존재 시 getShareStats(token, portfolioId)를 호출한다', async () => {
    render(<SharePanel portfolioId={1} />);

    await waitFor(() => {
      expect(mockedGetShareStats).toHaveBeenCalledWith('test-jwt', 1);
    });
  });
});

describe('AC-044-010/011: SharePanel 통계 항목 렌더링', () => {
  it('T-044-010: 통계 7개 항목이 날짜 오름차순으로 렌더링된다', async () => {
    render(<SharePanel portfolioId={1} />);

    await waitFor(() => {
      const items = screen.getAllByTestId('stat-item');
      expect(items).toHaveLength(7);
      expect(items[0]).toHaveTextContent('2024-01-01');
      expect(items[6]).toHaveTextContent('2024-01-07');
    });
  });

  it('T-044-011: view_count가 0인 날짜도 0으로 표시된다', async () => {
    render(<SharePanel portfolioId={1} />);

    await waitFor(() => {
      const items = screen.getAllByTestId('stat-item');
      // 2024-01-03의 view_count = 0 (인덱스 2)
      expect(items[2]).toHaveTextContent('0');
    });
  });
});

describe('AC-044-012/013: SharePanel 통계 조회 실패 격리', () => {
  it('T-044-012: getShareStats 실패 시 오류 표시', async () => {
    mockedGetShareStats.mockRejectedValue(new Error('통계 조회 실패'));
    render(<SharePanel portfolioId={1} />);

    await waitFor(() => {
      expect(screen.getByTestId('stats-error')).toBeInTheDocument();
    });
  });

  it('T-044-013: getShareStats 실패해도 공유 링크와 복사 버튼이 유지된다', async () => {
    mockedGetShareStats.mockRejectedValue(new Error('통계 오류'));
    render(<SharePanel portfolioId={1} />);

    await waitFor(() => {
      expect(screen.getByRole('button', { name: '링크 복사' })).toBeInTheDocument();
    });
  });
});

describe('AC-044-014: SharePanel 공유 없을 때 통계 미호출', () => {
  it('T-044-014: 활성 공유 링크가 없으면 getShareStats를 호출하지 않는다', async () => {
    mockedApiGetShare.mockResolvedValue(null);
    render(<SharePanel portfolioId={1} />);

    // 로딩 완료 대기
    await waitFor(() => {
      expect(screen.queryByText('로딩 중...')).not.toBeInTheDocument();
    });

    expect(mockedGetShareStats).not.toHaveBeenCalled();
  });
});

// ==================== Notifications portfolio_like 뱃지 ====================

describe('AC-044-015: portfolio_like 알림 TypeBadge', () => {
  it('T-044-015: portfolio_like 타입 알림의 TypeBadge가 "좋아요" 텍스트를 표시한다', async () => {
    mockedFetchNotifications.mockResolvedValue([
      {
        id: 1,
        type: 'portfolio_like',
        krx_code: '',
        title: '누군가 좋아요를 눌렀습니다',
        body: null,
        is_read: false,
        ref_date: null,
        related_alert_id: null,
        created_at: '2024-01-01T00:00:00Z',
        read_at: null,
      },
    ]);

    render(<NotificationsPage />);

    await waitFor(() => {
      expect(screen.getByText('좋아요')).toBeInTheDocument();
    });
  });
});
