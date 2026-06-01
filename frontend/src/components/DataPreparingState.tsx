// 데이터 준비 중 상태 컴포넌트 (AC-10)
export function DataPreparingState() {
  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '4rem 2rem',
        gap: '1.5rem',
      }}
      role="status"
      aria-live="polite"
    >
      {/* 스피너 */}
      <div
        style={{
          width: '48px',
          height: '48px',
          border: '4px solid #e0e0e0',
          borderTop: '4px solid #1976d2',
          borderRadius: '50%',
          animation: 'spin 1s linear infinite',
        }}
        aria-hidden="true"
      />
      <style>{`
        @keyframes spin {
          0% { transform: rotate(0deg); }
          100% { transform: rotate(360deg); }
        }
      `}</style>
      <p
        style={{
          fontSize: '1.25rem',
          color: '#555',
          margin: 0,
          fontWeight: 500,
        }}
      >
        데이터를 준비하고 있습니다
      </p>
      <p style={{ fontSize: '0.875rem', color: '#888', margin: 0 }}>
        오늘의 주식 추천 데이터를 분석 중입니다. 잠시 후 다시 확인해 주세요.
      </p>
    </div>
  );
}
