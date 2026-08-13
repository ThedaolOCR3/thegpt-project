import { useEffect, useRef, useState } from 'react';
import { useCursorFx } from './CursorFxContext';
import { CURSOR_OPTIONS, getCursorOption } from './cursorOptions';

type Particle = { id: number; x: number; y: number };

/** body에 커서 스타일 적용 + 마우스 이동 잔상 효과 + Alt+D 드롭다운 메뉴. */
export function CursorFxLayer() {
  const { enabled, cursorId, dropdownOpen, setCursorId, toggleEnabled, closeDropdown } = useCursorFx();
  const option = getCursorOption(cursorId);
  const [particles, setParticles] = useState<Particle[]>([]);
  const lastSpawnRef = useRef(0);
  const idRef = useRef(0);

  useEffect(() => {
    document.body.style.cursor = enabled ? option.cssCursor : '';
    return () => {
      document.body.style.cursor = '';
    };
  }, [enabled, option.cssCursor]);

  useEffect(() => {
    if (!enabled || !option.trailGlyph) return;

    function handleMouseMove(event: MouseEvent) {
      const now = performance.now();
      if (now - lastSpawnRef.current < 45) return;
      lastSpawnRef.current = now;

      const id = idRef.current++;
      setParticles((current) => [...current.slice(-30), { id, x: event.clientX, y: event.clientY }]);
      window.setTimeout(() => {
        setParticles((current) => current.filter((p) => p.id !== id));
      }, 600);
    }

    window.addEventListener('mousemove', handleMouseMove);
    return () => window.removeEventListener('mousemove', handleMouseMove);
  }, [enabled, option.trailGlyph]);

  return (
    <>
      {enabled &&
        option.trailGlyph &&
        particles.map((p) => (
          <span
            key={p.id}
            aria-hidden
            className="pointer-events-none fixed z-[9999] select-none animate-[cursorfx-fade_0.6s_ease-out_forwards] text-sm"
            style={{ left: p.x, top: p.y, color: option.trailColor }}
          >
            {option.trailGlyph}
          </span>
        ))}

      {dropdownOpen && (
        <div
          className="fixed right-4 top-4 z-[10000] w-56 rounded-xl border border-neutral-200 bg-white p-2 shadow-lg dark:border-neutral-700 dark:bg-neutral-800"
          role="menu"
        >
          <div className="flex items-center justify-between px-2 py-1">
            <p className="text-xs font-semibold text-neutral-500 dark:text-neutral-400">
              커서 디자인 (Alt+D)
            </p>
            <button
              type="button"
              title="닫기"
              onClick={closeDropdown}
              className="text-neutral-400 hover:text-neutral-700 dark:hover:text-neutral-200"
            >
              ✕
            </button>
          </div>
          {CURSOR_OPTIONS.map((opt) => (
            <button
              key={opt.id}
              type="button"
              role="menuitemradio"
              aria-checked={cursorId === opt.id}
              onClick={() => setCursorId(opt.id)}
              className={`flex w-full items-center gap-2 rounded-lg px-2 py-1.5 text-left text-sm ${
                cursorId === opt.id
                  ? 'bg-blue-50 text-blue-700 dark:bg-blue-950 dark:text-blue-300'
                  : 'text-neutral-700 hover:bg-neutral-100 dark:text-neutral-200 dark:hover:bg-neutral-700'
              }`}
            >
              <span>{opt.trailGlyph ?? '⭘'}</span>
              {opt.label}
            </button>
          ))}
          <div className="mt-1 border-t border-neutral-100 px-2 pt-2 dark:border-neutral-700">
            <button
              type="button"
              onClick={toggleEnabled}
              className="w-full rounded-lg bg-neutral-900 py-1.5 text-xs font-medium text-white dark:bg-white dark:text-neutral-900"
            >
              {enabled ? 'OFF (Alt+S)' : 'ON (Alt+S)'}
            </button>
          </div>
        </div>
      )}
    </>
  );
}
