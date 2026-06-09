import { jsx as _jsx } from "react/jsx-runtime";
// DataPreparingState 컴포넌트 테스트
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { DataPreparingState } from '../components/DataPreparingState';
describe('DataPreparingState', () => {
    it('크래시 없이 렌더링된다', () => {
        expect(() => render(_jsx(DataPreparingState, {}))).not.toThrow();
    });
    it('한국어 준비 중 텍스트를 표시한다', () => {
        render(_jsx(DataPreparingState, {}));
        expect(screen.getByText('데이터를 준비하고 있습니다')).toBeInTheDocument();
    });
    it('role="status" 속성이 있다', () => {
        render(_jsx(DataPreparingState, {}));
        expect(screen.getByRole('status')).toBeInTheDocument();
    });
});
