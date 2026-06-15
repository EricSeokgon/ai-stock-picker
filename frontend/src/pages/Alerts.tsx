// 알림 설정 페이지 — 목표가·급등락 알림 관리 (SPEC-STOCK-020 REQ-FE-001)
import { useEffect, useState } from 'react';
import { useAuth } from '../context/AuthContext';
import {
  fetchAlerts,
  createAlert,
  deleteAlert,
  toggleAlert,
  type Alert,
  type AlertCreatePayload,
  type AlertType,
  type AlertDirection,
} from '../api/alerts';

// ─── 타입 뱃지 ────────────────────────────────────────────────────────────────

function AlertTypeBadge({ alertType }: { alertType: AlertType }) {
  const map: Record<AlertType, { label: string; cls: string }> = {
    target_price: { label: '목표가', cls: 'bg-blue-100 text-blue-800' },
    surge_drop: { label: '급등락', cls: 'bg-orange-100 text-orange-800' },
    ex_dividend: { label: '배당락', cls: 'bg-purple-100 text-purple-800' },
  };
  const { label, cls } = map[alertType] ?? { label: alertType, cls: 'bg-gray-100 text-gray-700' };
  return (
    <span className={`inline-block text-xs font-medium px-2 py-0.5 rounded ${cls}`}>
      {label}
    </span>
  );
}

// ─── 알림 생성 폼 ─────────────────────────────────────────────────────────────

interface CreateFormProps {
  onCreated: (alert: Alert) => void;
  token: string;
}

function CreateAlertForm({ onCreated, token }: CreateFormProps) {
  const [krxCode, setKrxCode] = useState('');
  const [stockName, setStockName] = useState('');
  const [alertType, setAlertType] = useState<AlertType>('target_price');
  const [conditionValue, setConditionValue] = useState('');
  const [direction, setDirection] = useState<AlertDirection>('above');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const value = parseFloat(conditionValue);
    if (!krxCode || isNaN(value) || value <= 0) {
      setError('종목코드와 조건 값을 올바르게 입력하세요.');
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      const payload: AlertCreatePayload = {
        krx_code: krxCode.trim(),
        stock_name: stockName.trim() || null,
        alert_type: alertType,
        condition_value: value,
        condition_direction: alertType === 'surge_drop' ? direction : direction,
      };
      const created = await createAlert(token, payload);
      onCreated(created);
      setKrxCode('');
      setStockName('');
      setConditionValue('');
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="bg-white rounded-lg shadow p-4 mb-6 space-y-3">
      <h3 className="font-semibold text-gray-800">새 알림 설정</h3>
      {error && <p className="text-sm text-red-600">{error}</p>}
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="block text-xs text-gray-600 mb-1">종목코드 *</label>
          <input
            className="w-full border rounded px-2 py-1 text-sm"
            placeholder="005930"
            value={krxCode}
            onChange={(e) => setKrxCode(e.target.value)}
            maxLength={10}
          />
        </div>
        <div>
          <label className="block text-xs text-gray-600 mb-1">종목명 (선택)</label>
          <input
            className="w-full border rounded px-2 py-1 text-sm"
            placeholder="삼성전자"
            value={stockName}
            onChange={(e) => setStockName(e.target.value)}
          />
        </div>
      </div>
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="block text-xs text-gray-600 mb-1">알림 유형 *</label>
          <select
            className="w-full border rounded px-2 py-1 text-sm"
            value={alertType}
            onChange={(e) => setAlertType(e.target.value as AlertType)}
          >
            <option value="target_price">목표가 알림</option>
            <option value="surge_drop">급등락 알림</option>
          </select>
        </div>
        <div>
          <label className="block text-xs text-gray-600 mb-1">방향</label>
          <select
            className="w-full border rounded px-2 py-1 text-sm"
            value={direction}
            onChange={(e) => setDirection(e.target.value as AlertDirection)}
          >
            {alertType === 'surge_drop' ? (
              <>
                <option value="either">급등 또는 급락</option>
                <option value="above">급등만</option>
                <option value="below">급락만</option>
              </>
            ) : (
              <>
                <option value="above">이상 (상향 돌파)</option>
                <option value="below">이하 (하향 돌파)</option>
              </>
            )}
          </select>
        </div>
      </div>
      <div>
        <label className="block text-xs text-gray-600 mb-1">
          {alertType === 'target_price' ? '목표가 (원) *' : '임계값 (%) *'}
        </label>
        <input
          type="number"
          step={alertType === 'target_price' ? '100' : '0.1'}
          min="0.01"
          className="w-full border rounded px-2 py-1 text-sm"
          placeholder={alertType === 'target_price' ? '70000' : '5.0'}
          value={conditionValue}
          onChange={(e) => setConditionValue(e.target.value)}
        />
      </div>
      <button
        type="submit"
        disabled={submitting}
        className="w-full bg-blue-600 text-white rounded py-2 text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
      >
        {submitting ? '등록 중...' : '알림 등록'}
      </button>
    </form>
  );
}

// ─── 알림 카드 ────────────────────────────────────────────────────────────────

interface AlertCardProps {
  alert: Alert;
  onDelete: (id: number) => void;
  onToggle: (id: number, isActive: boolean) => void;
}

function AlertCard({ alert, onDelete, onToggle }: AlertCardProps) {
  const directionLabel: Record<string, string> = {
    above: '이상',
    below: '이하',
    either: '급등/락',
  };
  const valueLabel =
    alert.alert_type === 'target_price'
      ? `${alert.condition_value.toLocaleString()}원`
      : `${alert.condition_value}%`;

  return (
    <div className={`bg-white rounded-lg shadow p-4 border-l-4 ${alert.is_triggered ? 'border-green-400' : alert.is_active ? 'border-blue-400' : 'border-gray-300'}`}>
      <div className="flex items-start justify-between">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <span className="font-semibold text-gray-900">
              {alert.stock_name ? `${alert.stock_name} (${alert.krx_code})` : alert.krx_code}
            </span>
            <AlertTypeBadge alertType={alert.alert_type} />
            {alert.is_triggered && (
              <span className="text-xs bg-green-100 text-green-800 px-2 py-0.5 rounded">발동됨</span>
            )}
            {!alert.is_active && !alert.is_triggered && (
              <span className="text-xs bg-gray-100 text-gray-600 px-2 py-0.5 rounded">비활성</span>
            )}
          </div>
          <p className="text-sm text-gray-600">
            {valueLabel} {directionLabel[alert.condition_direction ?? 'above'] ?? ''} 도달 시 알림
          </p>
          {alert.triggered_message && (
            <p className="text-xs text-green-700 mt-1">{alert.triggered_message}</p>
          )}
        </div>
        <div className="flex gap-2 ml-2">
          {!alert.is_triggered && (
            <button
              onClick={() => onToggle(alert.id, !alert.is_active)}
              className={`text-xs px-2 py-1 rounded ${alert.is_active ? 'bg-gray-100 text-gray-700 hover:bg-gray-200' : 'bg-blue-100 text-blue-700 hover:bg-blue-200'}`}
            >
              {alert.is_active ? '비활성화' : '활성화'}
            </button>
          )}
          <button
            onClick={() => onDelete(alert.id)}
            className="text-xs px-2 py-1 rounded bg-red-100 text-red-700 hover:bg-red-200"
          >
            삭제
          </button>
        </div>
      </div>
    </div>
  );
}

// ─── 메인 페이지 ─────────────────────────────────────────────────────────────

export default function AlertsPage() {
  const { token } = useAuth();
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadAlerts = async () => {
    if (!token) return;
    try {
      setLoading(true);
      const data = await fetchAlerts(token);
      setAlerts(data);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void loadAlerts();
  }, [token]);

  const handleCreated = (alert: Alert) => {
    setAlerts((prev) => [alert, ...prev]);
  };

  const handleDelete = async (id: number) => {
    if (!token) return;
    try {
      await deleteAlert(token, id);
      setAlerts((prev) => prev.filter((a) => a.id !== id));
    } catch (e) {
      setError((e as Error).message);
    }
  };

  const handleToggle = async (id: number, isActive: boolean) => {
    if (!token) return;
    try {
      const updated = await toggleAlert(token, id, isActive);
      setAlerts((prev) => prev.map((a) => (a.id === id ? updated : a)));
    } catch (e) {
      setError((e as Error).message);
    }
  };

  const activeAlerts = alerts.filter((a) => a.is_active && !a.is_triggered);
  const triggeredAlerts = alerts.filter((a) => a.is_triggered);
  const inactiveAlerts = alerts.filter((a) => !a.is_active && !a.is_triggered);

  return (
    <div className="max-w-2xl mx-auto px-4 py-6">
      <h2 className="text-xl font-bold text-gray-900 mb-4">알림 설정</h2>
      <p className="text-sm text-gray-600 mb-6">
        목표가 또는 급등락 조건 설정 시 발동 알림을 받습니다.
        발동된 알림은 인박스(알림 벨)에서 확인하세요.
      </p>

      {token && <CreateAlertForm onCreated={handleCreated} token={token} />}

      {error && (
        <div className="bg-red-50 border border-red-200 rounded p-3 mb-4 text-sm text-red-700">
          {error}
        </div>
      )}

      {loading ? (
        <p className="text-center text-gray-500 py-8">불러오는 중...</p>
      ) : alerts.length === 0 ? (
        <p className="text-center text-gray-400 py-8">등록된 알림이 없습니다.</p>
      ) : (
        <div className="space-y-6">
          {activeAlerts.length > 0 && (
            <section>
              <h3 className="text-sm font-semibold text-gray-700 mb-2">활성 알림 ({activeAlerts.length})</h3>
              <div className="space-y-3">
                {activeAlerts.map((a) => (
                  <AlertCard key={a.id} alert={a} onDelete={handleDelete} onToggle={handleToggle} />
                ))}
              </div>
            </section>
          )}
          {triggeredAlerts.length > 0 && (
            <section>
              <h3 className="text-sm font-semibold text-gray-700 mb-2">발동된 알림 ({triggeredAlerts.length})</h3>
              <div className="space-y-3">
                {triggeredAlerts.map((a) => (
                  <AlertCard key={a.id} alert={a} onDelete={handleDelete} onToggle={handleToggle} />
                ))}
              </div>
            </section>
          )}
          {inactiveAlerts.length > 0 && (
            <section>
              <h3 className="text-sm font-semibold text-gray-700 mb-2">비활성 알림 ({inactiveAlerts.length})</h3>
              <div className="space-y-3">
                {inactiveAlerts.map((a) => (
                  <AlertCard key={a.id} alert={a} onDelete={handleDelete} onToggle={handleToggle} />
                ))}
              </div>
            </section>
          )}
        </div>
      )}
    </div>
  );
}
