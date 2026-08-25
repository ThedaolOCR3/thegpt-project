import type { Message } from '../api/types';

export type ExportMode = 'full' | 'summary';

function formatTimestamp(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleString('ko-KR', { year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' });
}

function roleLabel(role: Message['role']): string {
  return role === 'user' ? '환자' : 'AI 상담';
}

// 요약 모드에서 AI 답변 본문 중 첫 문장(또는 첫 줄)만 남긴다. LLM으로 다시 요약하지
// 않는 이유: 없는 내용을 지어낼 위험이 있어서(CLAUDE.md — 근거 없는 확정적 표현 금지)
// 원문에서 그대로 발췌하는 방식만 쓴다. 환자 메시지는 요약 모드에서도 원문 그대로 둔다
// (의료 맥락상 환자가 직접 말한 내용을 임의로 줄이면 안 되므로).
function firstSentence(content: string): string {
  const trimmed = content.trim();
  const match = trimmed.match(/^[^.!?\n]*[.!?]/) ?? trimmed.match(/^[^\n]+/);
  const sentence = (match?.[0] ?? trimmed).trim();
  return sentence.length < trimmed.length ? `${sentence} …` : sentence;
}

function bodyFor(message: Message, mode: ExportMode): string {
  return mode === 'summary' && message.role === 'assistant' ? firstSentence(message.content) : message.content;
}

function attachmentNames(message: Message): string | null {
  if (!message.attachments?.length) return null;
  return message.attachments.map((a) => a.name).join(', ');
}

function slugifyForFilename(text: string): string {
  const cleaned = text.trim().replace(/[\\/:*?"<>|\n]/g, ' ').replace(/\s+/g, ' ').slice(0, 40);
  return cleaned || '채팅내역';
}

export function buildFilenameBase(messages: Message[], mode: ExportMode): string {
  const firstUserMessage = messages.find((m) => m.role === 'user')?.content ?? '채팅내역';
  const date = new Date().toISOString().slice(0, 10);
  const modeLabel = mode === 'summary' ? '요약' : '전체';
  return `${slugifyForFilename(firstUserMessage)}_${modeLabel}_${date}`;
}

function modeNote(mode: ExportMode): string {
  return mode === 'summary'
    ? '요약본 — AI 답변은 첫 문장만 발췌했고, 환자 메시지는 원문 그대로입니다.'
    : '전체 대화 원문입니다.';
}

export function buildTranscriptText(title: string, messages: Message[], mode: ExportMode): string {
  const header = [title, modeNote(mode), `생성일시: ${new Date().toLocaleString('ko-KR')}`, '='.repeat(40)].join('\n');
  const body = messages
    .map((m) => {
      const attachments = attachmentNames(m);
      const lines = [`[${formatTimestamp(m.createdAt)}] ${roleLabel(m.role)}`, bodyFor(m, mode)];
      if (attachments) lines.push(`첨부: ${attachments}`);
      return lines.join('\n');
    })
    .join('\n\n');
  return `${header}\n\n${body}\n`;
}

export function buildTranscriptMarkdown(title: string, messages: Message[], mode: ExportMode): string {
  const body = messages
    .map((m) => {
      const attachments = attachmentNames(m);
      const attachmentLine = attachments ? `\n\n> 첨부: ${attachments}` : '';
      return `**${roleLabel(m.role)}** _(${formatTimestamp(m.createdAt)})_\n\n${bodyFor(m, mode)}${attachmentLine}`;
    })
    .join('\n\n---\n\n');
  return `# ${title}\n\n> ${modeNote(mode)}\n\n생성일시: ${new Date().toLocaleString('ko-KR')}\n\n---\n\n${body}\n`;
}

export function downloadTextFile(filename: string, content: string, mime: string): void {
  const blob = new Blob([content], { type: `${mime};charset=utf-8` });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

function escapeHtml(text: string): string {
  return text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

// PDF는 별도 라이브러리(jsPDF 등) 없이 브라우저 인쇄 대화상자를 이용한다.
// 한글 폰트를 임베드해야 하는 라이브러리 방식과 달리, 브라우저가 시스템 폰트로
// 그려주므로 한글이 항상 정상 출력되고("다른 이름으로 저장 > PDF"로 저장) 번들도 가벼워진다.
export function openPrintableTranscript(title: string, messages: Message[], mode: ExportMode): void {
  const win = window.open('', '_blank', 'noopener,noreferrer');
  if (!win) {
    window.alert('팝업이 차단되어 있어요. 이 사이트의 팝업을 허용한 뒤 다시 시도해주세요.');
    return;
  }

  const body = messages
    .map((m) => {
      const attachments = attachmentNames(m);
      const attachmentHtml = attachments ? `<p class="attachments">첨부: ${escapeHtml(attachments)}</p>` : '';
      return `
        <section class="turn">
          <p class="meta">${escapeHtml(roleLabel(m.role))} · ${escapeHtml(formatTimestamp(m.createdAt))}</p>
          <p class="content">${escapeHtml(bodyFor(m, mode)).replace(/\n/g, '<br/>')}</p>
          ${attachmentHtml}
        </section>`;
    })
    .join('\n');

  win.document.write(`<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8" />
<title>${escapeHtml(title)}</title>
<style>
  body { font-family: -apple-system, "Malgun Gothic", "Apple SD Gothic Neo", sans-serif; color: #1a1a1a; padding: 32px; max-width: 720px; margin: 0 auto; }
  h1 { font-size: 20px; margin-bottom: 4px; }
  .generated { color: #888; font-size: 12px; margin-bottom: 16px; }
  .note { background: #f5f5f5; border-radius: 8px; padding: 8px 12px; font-size: 12px; color: #555; margin-bottom: 16px; }
  .turn { padding: 10px 0; border-bottom: 1px solid #eee; }
  .meta { font-size: 11px; color: #999; margin: 0 0 4px; }
  .content { font-size: 14px; line-height: 1.6; margin: 0; white-space: pre-wrap; }
  .attachments { font-size: 12px; color: #666; margin: 4px 0 0; }
  @media print { body { padding: 0; } }
</style>
</head>
<body>
  <h1>${escapeHtml(title)}</h1>
  <p class="generated">생성일시: ${escapeHtml(new Date().toLocaleString('ko-KR'))}</p>
  <p class="note">${escapeHtml(modeNote(mode))}</p>
  ${body}
</body>
</html>`);
  win.document.close();
  win.focus();
  setTimeout(() => win.print(), 300);
}
