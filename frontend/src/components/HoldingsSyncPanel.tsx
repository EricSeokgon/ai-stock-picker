// 거래 기반 홀딩스 동기화 패널 (SPEC-STOCK-050 REQ-SYNC-014~016)
import { useState } from 'react';
import { useAuth } from '../auth/AuthContext';
import {
  applyHoldingsSync,
  previewHoldingsSync,
  type SyncHoldingItem,
  type SyncPreviewItem,
} from '../api/portfolio';

// @MX:NOTE: [AUTO] SPEC-STOCK-050 — 거래 원장 기반 홀딩스 동기화 미리보기/적용 패널.
// @MX:SPEC: SPEC-STOCK-050 REQ-SYNC-014~016

interface Props {
  portfolioId: number;
  onSynced?: (holdings: SyncHoldingItem[]) => void;
}

const actionLabel: Record<SyncPreviewItem['action'], string> = {
  upsert: '추가/수정',
  delete: '제거',
  unchanged: '변경 없음',
};

const actionColor: Record<SyncPreviewItem['action'], string> = {
  upsert: '#1976d2',
  delete: '#c62828',
  unchanged: '#666',
};

export default function HoldingsSyncPanel({ portfolioId, onSynced }: Props) {
  const { token } = useAuth();
  const [items, setItems] = useState<SyncPreviewItem[] | null>(null);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [applyLoading, setApplyLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [appliedCount, setAppliedCount] = useState<number | null>(null);

  async function handlePreview() {
    if (!token) return;
    setPreviewLoading(true);
    setError(null);
    setAppliedCount(null);
    try {
      const result = await previewHoldingsSync(token, portfolioId);
      setItems(result.items);
    } catch (e) {
      setError(e instanceof Error ? e.message : '동기화 미리보기 실패');
    } finally {
      setPreviewLoading(false);
    }
  }

  async function handleApply() {
    if (!token) return;
    setApplyLoading(true);
    setError(null);
    try {
      const result = await applyHoldingsSync(token, portfolioId);
      setAppliedCount(result.synced);
      setItems(null);
      onSynced?.(result.holdings);
    } catch (e) {
      setError(e instanceof Error ? e.message : '동기화 적용 실패');
    } finally {
      setApplyLoading(false);
    }
  }

  const panelStyle: React.CSSProperties = {
    border: '1px solid #e5e7eb',
    borderRadius: 8,
    padding: '1rem',
    marginTop: '1rem',
  };

  const hasChanges = items != null && items.length > 0;

  return (
    <div style={panelStyle}>
      <h3 style={{ margin: '0 0 0.75rem', fontSize: '1rem', fontWeight: 600 }}>
        홀딩스 동기화
      </h3>

      <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '0.75rem' }}>
        <button
          onClick={() => void handlePreview()}
          disabled={previewLoading}
          style={{ padding: '0.4rem 0.8rem', cursor: previewLoading ? 'default' : 'pointer' }}
        >
          {previewLoading ? '조회 중...' : '미리보기'}
        </button>
        {hasChanges && (
          <button
            onClick={() => void handleApply()}
            disabled={applyLoading}
            style={{ padding: '0.4rem 0.8rem', cursor: applyLoading ? 'default' : 'pointer' }}
          >
            {applyLoading ? '적용 중...' : '적용'}
          </button>
        )}
      </div>

      {error && <p style={{ color: '#dc2626' }}>{error}</p>}

      {appliedCount !== null && (
        <p style={{ color: '#10b981', fontWeight: 600 }}>
          동기화 완료 — {appliedCount}건 변경됨
        </p>
      )}

      {items != null && items.length === 0 && (
        <p style={{ color: '#6b7280' }}>변경 없음</p>
      )}

      {hasChanges && (
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.875rem' }}>
          <thead>
            <tr style={{ background: '#f3f4f6' }}>
              <th style={{ textAlign: 'left', padding: '0.35rem 0.5rem' }}>종목코드</th>
              <th style={{ textAlign: 'left', padding: '0.35rem 0.5rem' }}>변경</th>
              <th style={{ textAlign: 'right', padding: '0.35rem 0.5rem' }}>현재 수량</th>
              <th style={{ textAlign: 'right', padding: '0.35rem 0.5rem' }}>변경 후 수량</th>
            </tr>
          </thead>
          <tbody>
            {items!.map((item) => (
              <tr key={item.krx_code} style={{ borderBottom: '1px solid #eee' }}>
                <td style={{ padding: '0.35rem 0.5rem' }}>{item.krx_code}</td>
                <td style={{ padding: '0.35rem 0.5rem', color: actionColor[item.action] }}>
                  {actionLabel[item.action]}
                </td>
                <td style={{ padding: '0.35rem 0.5rem', textAlign: 'right' }}>{item.current_qty}</td>
                <td style={{ padding: '0.35rem 0.5rem', textAlign: 'right' }}>{item.derived_qty}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
