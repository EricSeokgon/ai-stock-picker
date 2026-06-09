import { jsx as _jsx } from "react/jsx-runtime";
// Disclaimer 컴포넌트 테스트
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { Disclaimer } from '../components/Disclaimer';
describe('Disclaimer', () => {
    it('면책 조항 텍스트를 렌더링한다', () => {
        render(_jsx(Disclaimer, { text: "\uC774 \uC815\uBCF4\uB294 \uD22C\uC790 \uCC38\uACE0\uC6A9\uC785\uB2C8\uB2E4." }));
        expect(screen.getByText('이 정보는 투자 참고용입니다.')).toBeInTheDocument();
    });
    it('면책 조항 레이블이 있다', () => {
        render(_jsx(Disclaimer, { text: "\uD14C\uC2A4\uD2B8 \uBA74\uCC45 \uC870\uD56D" }));
        expect(screen.getByRole('note', { name: '면책 조항' })).toBeInTheDocument();
    });
    it('"면책 조항:" 제목을 포함한다', () => {
        render(_jsx(Disclaimer, { text: "\uC784\uC758\uC758 \uD14D\uC2A4\uD2B8" }));
        expect(screen.getByText('면책 조항:')).toBeInTheDocument();
    });
});
