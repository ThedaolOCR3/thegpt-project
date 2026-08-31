# Frontend

Vite, React, TypeScript 기반 프론트엔드입니다.

```bash
npm install
npm run dev
```

실제 환경변수는 프로젝트 최상위 `.env`에서 관리합니다. `frontend/.env.example`은 Frontend 협업자를 위한 `VITE_API_URL` 예시로 유지합니다. Frontend에 공개 가능한 값만 `VITE_` 접두사를 사용하며, `GEMINI_API_KEY` 같은 Backend 비밀값은 Vite 번들에 포함하지 않습니다.

메인 채팅은 Backend LLM Catalog에서 모델 목록을 읽고 선택한
`model_id`를 대화 메시지 API로 전달합니다. 전체 연동 순서와 모델 추가
방법은 `docs/3_flow/12_FLW_MainLLM_메인페이지연동가이드_20260831.md`를 참고합니다.
