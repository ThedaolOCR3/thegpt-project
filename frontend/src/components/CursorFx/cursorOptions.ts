// 커서 디자인 종류. cssCursor는 커서 아이콘, trailGlyph는 마우스 이동 시 남는 잔상 문자.
export type CursorOption = {
  id: string;
  label: string;
  cssCursor: string;
  trailGlyph: string | null;
  trailColor: string;
};

function dotCursorSvg(color: string) {
  const svg = `<svg xmlns='http://www.w3.org/2000/svg' width='20' height='20'><circle cx='10' cy='10' r='6' fill='${color}' stroke='white' stroke-width='2'/></svg>`;
  return `url("data:image/svg+xml,${encodeURIComponent(svg)}") 10 10, auto`;
}

export const CURSOR_OPTIONS: CursorOption[] = [
  { id: 'off', label: '기본 커서 (끄기)', cssCursor: 'auto', trailGlyph: null, trailColor: '' },
  { id: 'dot', label: '파란 도트', cssCursor: dotCursorSvg('%233b82f6'), trailGlyph: '●', trailColor: '#3b82f6' },
  { id: 'sparkle', label: '반짝이', cssCursor: 'auto', trailGlyph: '✨', trailColor: '#f59e0b' },
  { id: 'paw', label: '고양이 발자국', cssCursor: 'auto', trailGlyph: '🐾', trailColor: '#a16207' },
];

export function getCursorOption(id: string): CursorOption {
  return CURSOR_OPTIONS.find((option) => option.id === id) ?? CURSOR_OPTIONS[0];
}
