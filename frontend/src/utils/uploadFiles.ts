export const MAX_MULTI_UPLOAD_FILES = 5;

export const MESSAGE_UPLOAD_ACCEPT = '.pdf,.png,.jpg,.jpeg,.docx,.pptx,.txt,.csv';
export const MESSAGE_UPLOAD_EXTENSIONS = new Set([
  'pdf',
  'png',
  'jpg',
  'jpeg',
  'docx',
  'pptx',
  'txt',
  'csv',
]);

export type FileMergeResult = {
  files: File[];
  duplicateCount: number;
  unsupportedNames: string[];
  limitExceeded: boolean;
};

export function getFileExtension(file: File) {
  return file.name.split('.').pop()?.toLowerCase() ?? '';
}

export function getFileIdentity(file: File) {
  return `${file.name}:${file.size}:${file.lastModified}`;
}

/** 기존 선택을 보존하면서 지원 형식, 중복과 최대 개수를 한곳에서 검사합니다. */
export function mergeSelectedFiles(
  current: readonly File[],
  selected: readonly File[],
  supportedExtensions: ReadonlySet<string>,
  maxFiles = MAX_MULTI_UPLOAD_FILES,
): FileMergeResult {
  const files = [...current];
  const identities = new Set(files.map(getFileIdentity));
  const unsupportedNames: string[] = [];
  let duplicateCount = 0;
  let limitExceeded = false;

  for (const file of selected) {
    if (!supportedExtensions.has(getFileExtension(file))) {
      unsupportedNames.push(file.name);
      continue;
    }
    const identity = getFileIdentity(file);
    if (identities.has(identity)) {
      duplicateCount += 1;
      continue;
    }
    if (files.length >= maxFiles) {
      limitExceeded = true;
      continue;
    }
    files.push(file);
    identities.add(identity);
  }

  return { files, duplicateCount, unsupportedNames, limitExceeded };
}

export function describeFileMerge(result: FileMergeResult, supportedLabel: string) {
  const messages: string[] = [];
  if (result.unsupportedNames.length > 0) {
    messages.push(`${supportedLabel} 파일만 첨부할 수 있습니다.`);
  }
  if (result.limitExceeded) {
    messages.push(`한 번에 최대 ${MAX_MULTI_UPLOAD_FILES}개까지 첨부할 수 있습니다.`);
  }
  if (result.duplicateCount > 0) {
    messages.push(`중복 파일 ${result.duplicateCount}개는 제외했습니다.`);
  }
  return messages.join(' ');
}
