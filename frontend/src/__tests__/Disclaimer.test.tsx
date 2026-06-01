// Disclaimer 컴포넌트 테스트
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { Disclaimer } from '../components/Disclaimer';

describe('Disclaimer', () => {
  it('면책 조항 텍스트를 렌더링한다', () => {
    render(<Disclaimer text="이 정보는 투자 참고용입니다." />);
    expect(screen.getByText('이 정보는 투자 참고용입니다.')).toBeInTheDocument();
  });

  it('면책 조항 레이블이 있다', () => {
    render(<Disclaimer text="테스트 면책 조항" />);
    expect(screen.getByRole('note', { name: '면책 조항' })).toBeInTheDocument();
  });

  it('"면책 조항:" 제목을 포함한다', () => {
    render(<Disclaimer text="임의의 텍스트" />);
    expect(screen.getByText('면책 조항:')).toBeInTheDocument();
  });
});
