import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
// 데이터 준비 중 상태 컴포넌트 (AC-10)
export function DataPreparingState() {
    return (_jsxs("div", { style: {
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            padding: '4rem 2rem',
            gap: '1.5rem',
        }, role: "status", "aria-live": "polite", children: [_jsx("div", { style: {
                    width: '48px',
                    height: '48px',
                    border: '4px solid #e0e0e0',
                    borderTop: '4px solid #1976d2',
                    borderRadius: '50%',
                    animation: 'spin 1s linear infinite',
                }, "aria-hidden": "true" }), _jsx("style", { children: `
        @keyframes spin {
          0% { transform: rotate(0deg); }
          100% { transform: rotate(360deg); }
        }
      ` }), _jsx("p", { style: {
                    fontSize: '1.25rem',
                    color: '#555',
                    margin: 0,
                    fontWeight: 500,
                }, children: "\uB370\uC774\uD130\uB97C \uC900\uBE44\uD558\uACE0 \uC788\uC2B5\uB2C8\uB2E4" }), _jsx("p", { style: { fontSize: '0.875rem', color: '#888', margin: 0 }, children: "\uC624\uB298\uC758 \uC8FC\uC2DD \uCD94\uCC9C \uB370\uC774\uD130\uB97C \uBD84\uC11D \uC911\uC785\uB2C8\uB2E4. \uC7A0\uC2DC \uD6C4 \uB2E4\uC2DC \uD655\uC778\uD574 \uC8FC\uC138\uC694." })] }));
}
