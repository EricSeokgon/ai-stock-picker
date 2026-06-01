// 면책 조항 컴포넌트
interface DisclaimerProps {
  text: string;
}

export function Disclaimer({ text }: DisclaimerProps) {
  return (
    <div
      style={{
        marginTop: '2rem',
        padding: '1rem',
        backgroundColor: '#fff3cd',
        border: '1px solid #ffc107',
        borderRadius: '4px',
        fontSize: '0.875rem',
        color: '#856404',
      }}
      role="note"
      aria-label="면책 조항"
    >
      <strong>면책 조항:</strong> {text}
    </div>
  );
}
