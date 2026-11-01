# BroCompass 배포 가이드 (Render + Vercel)

구성: **프론트(Next.js) = Vercel**, **백엔드(FastAPI) = Render**. 브라우저는 프론트 주소만 호출하고,
`/api/*` 요청은 `next.config.js` 의 rewrite 가 백엔드로 전달합니다(그래서 CORS 설정이 필요 없습니다).

| 파일 | 역할 |
| --- | --- |
| `backend/Dockerfile` | 백엔드 실행 환경 정의. 이미지를 만들 때 PubMed 에서 논문 DB 를 수집 |
| `backend/.dockerignore` | 이미지에 넣지 않을 파일(키, DB, 테스트) |
| `render.yaml` | Render 서비스 설정(포트·헬스체크·보호 환경변수). **키는 넣지 않음** |
| `frontend/.env.example` | Vercel 에 넣을 `API_URL` 예시 |
| `backend/smoke_check.py` | 배포 직후 동작 점검 스크립트 |

C# 비유: Dockerfile 은 "배포 패키지를 만드는 publish 설정", render.yaml 은 "IIS 사이트 설정 파일"에 해당합니다.

## 0. 올리기 전에
1. 백엔드 폴더에서 `pytest`, 프론트 폴더에서 `npx tsc --noEmit` 이 통과하는지 확인
2. 프로젝트 루트에서 `git grep -n "nvapi-"` 결과가 `.env.example` 의 자리표시자뿐인지 확인
3. 4차 패치(`REQUIRE_CLIENT_ID` 등)가 적용되어 있는지 확인

## 1. GitHub 에 올리기
`git init -b main` → `git add .` → `git status` 로 `node_modules`, `.env`, `*.db` 가 없는지 확인 →
`git commit -m "..."` → GitHub 에서 빈 저장소를 만든 뒤 `git remote add origin ...` → `git push -u origin main`.

## 2. 백엔드를 Render 에 올리기
1. render.com 에 GitHub 계정으로 가입
2. **New → Blueprint** 에서 저장소를 연결하면 `render.yaml` 이 읽힙니다
3. `NVIDIA_API_KEY` 입력 칸이 나오면 키를 붙여 넣습니다(채팅·저장소가 아니라 이 칸에만)
4. 첫 빌드는 논문 수집 때문에 시간이 걸립니다. 로그에 `현재 논문 DB: ...편` 이 나오면 수집 성공입니다
5. 완료되면 `https://<서비스명>.onrender.com` 주소가 생깁니다. `/health` 를 브라우저로 열어 `{"status":"ok"}` 확인

참고: 무료 플랜 서버는 일정 시간 요청이 없으면 잠들고, 다음 첫 요청이 수십 초 걸릴 수 있습니다.
면접·제출 직전에 한 번 열어 깨워 두세요.

## 3. 프론트를 Vercel 에 올리기
1. vercel.com 에 GitHub 계정으로 가입 → **Add New → Project** 에서 저장소 선택
2. **Root Directory 를 `frontend` 로 지정**
3. **Environment Variables** 에 `API_URL` = 2단계에서 받은 Render 주소(끝에 `/` 없이)
4. Deploy. 환경변수는 빌드 때 읽히므로, 나중에 값을 바꾸면 **다시 배포**해야 합니다

## 4. 점검
```
cd backend
python smoke_check.py https://<프론트>.vercel.app
```
논문 수, 노트 저장·조회, 사용자 분리가 `OK` 인지 봅니다. 그 뒤 브라우저에서 계산기 → 노트 → 코치를 직접 눌러 보세요.
사진 분석과 AI 요약은 하루 한도를 쓰므로 스크립트는 호출하지 않습니다.

## 문제 해결
| 증상 | 확인할 것 |
| --- | --- |
| 화면은 뜨는데 계산·저장이 실패 | Vercel 의 `API_URL` 오타, 값 변경 후 재배포 여부 |
| 노트가 저장되지 않음(400) | 백엔드에서 `REQUIRE_CLIENT_ID=1` 인데 프론트가 4차 패치 이전 버전인지 |
| 모든 방문자가 같은 제한에 걸림 | `TRUST_PROXY` 설정, 프록시가 접속자 IP 를 전달하는지 |
| 코치에 논문이 0편 | Render 빌드 로그의 논문 수집 결과. 실패했다면 재배포 |
| 사진 분석이 중간에 끊김 | 프론트 프록시의 대기 시간 제한일 수 있음. 라이브에서 실제로 시험해 보고, 필요하면 브라우저가 백엔드를 직접 호출하도록 바꾸고 `CORS_ORIGINS` 에 프론트 주소를 추가 |
| 429 오류 | IP 별 분당 한도 또는 `AI_DAILY_CAP`(하루 총량). 데모 시연 전에 한도를 확인 |

## 주의
- 무료 서버는 재시작하면 노트 DB 가 초기화될 수 있습니다. 데모 데이터는 사라져도 되는 것만 쓰세요
- 이 구성은 로그인이 없는 **공개 데모용**입니다. 실사용 서비스로 쓰려면 인증과 영구 DB 가 필요합니다
- 노출된 키는 폐기·재발급해야 합니다. 의심되면 즉시 build.nvidia.com 에서 키를 교체하세요
