# BroCompass

**English** | [日本語](README.ja.md) | [한국어](README.ko.md)

A block-style workout & diet note app with a macro calculator, AI meal-photo analysis, and a coach that backs its advice with PubMed papers. Technical black UI with neon-green accents. The UI is available in Korean, Japanese and English.

<!-- Demo video: add the YouTube URL here when it is ready, e.g. "Demo: https://youtu.be/..." -->

Implemented so far: **Phase 1** (TDEE/macro calculation API + dashboard), **Phase 2** (block-style daily note), **Phase 3** (meal-photo analysis), **Phase 4** (paper-backed coach), **Phase 5** (PC layout, game-style feedback), **Phase 6** (combat sessions, diet helper) and a Korean/Japanese/English UI. `db/schema.sql` contains the target schema that separates plans from actual performance.

## Daily note (`/note`)

A single line of text turns into a block.

| Input | Result |
| --- | --- |
| `bench press 5x5 80` | Workout block: 5 sets × 5 reps, 80 kg |
| `pull-up 4x10` | Workout block (bodyweight) |
| `chicken breast 200kcal p40` | Meal block: 200 kcal, 40 g protein |
| `brown rice 300kcal p6 c65 f2` | Meal block: 65 g carbs, 2 g fat |
| anything else | Memo block |

Exercise names are recognized in Korean, Japanese and English, and small typos in longer exercise names are tolerated.

- Tapping a set marks it as done (Actual), with a spring animation and vibration. The last set uses a stronger pattern.
- When a set is completed, the previous set's actual values (or the planned values if none) are recorded. Open `▼ Edit actual log` to adjust weight (±2.5 kg) and reps (±1) per set. Sets that differ from the plan get a yellow dot, and volume is calculated from the actual values.
- The date bar moves to the previous/next day, the date tab opens a calendar, and the `Today` button returns. Notes are stored per date.
- Drag the `⋮⋮` handle on the left to reorder blocks (dnd-kit).
- The PLAN vs ACTUAL bar at the top shows achievement for sets, volume, calories and protein.
- `⧉ Copy previous plan` copies the plan of the nearest earlier record (up to 14 days back) into today. Set completion, intake checks and actual logs are cleared, and the copied blocks are appended after existing ones. Both this device and the server are searched, so records written on another device are found too.

### Server storage (local-first)

- Changes are saved to the browser's `localStorage` immediately and sent to the server (`PUT /api/notes/{date}`) after 0.8 s. The app keeps working while the server is down and shows `Offline · saved on this device only`. The note is uploaded the next time that date is opened with the server running.
- Conflict rule: **the side with the newer `updatedAt` wins.** If a device clock is far off, the older side may win.
- Storage is SQLite (`backend/brocompass.db`, path configurable with `BROCOMPASS_DB`), one JSON document per date. The normalized `db/schema.sql` (plan_blocks / actual_logs) is the target structure for a future Supabase migration; any class that implements the same methods as `NoteStore` in `backend/store.py` can replace it.
- **There is no login.** Notes are separated per browser by a random ID (`X-Client-Id`); see "Protections for a public demo" below. This is not real authentication.

| Method | Path | Description |
| --- | --- | --- |
| GET | `/api/notes/{date}` | Get a note (404 if none) |
| PUT | `/api/notes/{date}` | Save. If the server has a newer note it is not overwritten and that note is returned |
| GET | `/api/notes?start=&end=` | Dates in a range that have at least one block |

## Structure

```
brocompass/
├── backend/    FastAPI (logic + tests)
├── frontend/   Next.js 14 + Tailwind + Framer Motion
└── db/         PostgreSQL schema
```

## Running locally

Backend:

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
pytest            # backend tests
```

Frontend (check at a 390 px mobile width first):

```bash
cd frontend
npm install
npm run dev       # http://localhost:3000
npx tsc --noEmit  # type check
```

`/api/*` requests are forwarded to FastAPI (`API_URL`, default `http://localhost:8000`) by the rewrite in `next.config.js`.

## Calculation

- BMR: Mifflin-St Jeor (Katch-McArdle when body-fat % is entered)
- TDEE = BMR × activity factor (1.2 – 1.9)
- Target calories: cut −20% / maintain / bulk +10%
- Macros: carb/protein/fat ratios by body type, protein guaranteed at a minimum of 1.6 g/kg

Results are general estimates, not medical advice.

## Meal-photo analysis (Phase 3)

Choose a food photo with `📷 Add meal from photo` in the daily note. The server sends it to a vision AI, which estimates calories and macros per food item; you correct the values on a review screen and add them as a meal block. (`POST /api/meal/analyze`)

**Setup.** The default is the free NVIDIA build.nvidia.com API (see `backend/.env.example`). Free hosted models can disappear or stop responding without notice (`HTTP 404`/`410`, or a model that is listed but not served). If you see an error, run the diagnostic tool, which lists the models your key can use and tests which ones actually respond:

```bash
cd backend
export NVIDIA_API_KEY=nvapi-...                     # build.nvidia.com -> Settings -> API Keys
python diagnose_models.py                           # models visible to your key
python diagnose_models.py --vision                  # try image-capable candidates
python diagnose_models.py --scan --timeout 30       # find text models that respond right now
export VISION_MODEL=...                             # a model ID that returned OK
export VISION_NO_THINK=1                            # for reasoning models: skip the slow "thinking" step (after testing with --nothink)
uvicorn main:app --reload --port 8000
```

To use OpenAI instead, set `VISION_API_KEY`, `VISION_BASE_URL=https://api.openai.com/v1` and `VISION_MODEL=gpt-4o`. The API key lives only on the server and never reaches the browser.

**Things to know**

- The free API is limited to roughly 40 requests per minute, and total credits and terms follow NVIDIA's policy. Use it for personal development and testing. The server also limits requests itself (30/min by default, `VISION_RPM`).
- Nutrition estimated from one photo has large errors, so there is always a review step, and a warning appears when calories and macros do not match.
- Photos are shrunk in the browser to at most 768 px on the long side and about 150 KB before upload. The server does not store photos.
- The list and input format of free hosted models can change. If a model breaks the JSON format the server asks once more and shows an error if it still fails. Reasoning models may return an empty answer while "thinking"; the server falls back to the reasoning text and reports when the output was truncated (`VISION_MAX_TOKENS` raises the limit).

## Paper-backed coach (Phase 4, RAG)

The `/coach` screen analyzes the last 7/14/28 days of records, finds weak points, and attaches PubMed papers as evidence.

**How it works**

1. **Record analysis** (`insights.py`, rule-based): weekly sets per muscle group, push/pull balance, protein (when body weight is entered), plateaus on the same exercise, shoulder/knee/back discomfort notes, combat/cardio training load.
2. **Paper search** (`retrieval.py`): each finding is searched against the paper DB using English queries (`topics.py`). BM25 keyword search, a relevance gate weighted by term rarity (IDF), topic-specific required terms and excluded populations, and Reciprocal Rank Fusion across queries. Papers that do not match are dropped; nothing is cited by force.
3. **AI summary** (`coach.py`, optional): only the findings and paper excerpts are sent to the LLM, which returns a summary and plan-adjustment suggestions in the selected UI language. If the PMIDs the LLM cites were not actually retrieved, that advice is discarded. Raw memo text is never sent.
4. For under-trained muscle groups, an `Add to today's note` button inserts a workout block (weight is set to 0, so record the real value in the note).

**First time: fill the paper DB** (on your PC, internet required)

```bash
cd backend
python ingest_pubmed.py --email you@example.com          # 30 papers per topic, mainly meta-analyses / systematic reviews / RCTs / reviews
python ingest_pubmed.py --topics volume,protein --per-topic 50
python ingest_pubmed.py --embed                          # (optional) also create embeddings, needs EMBED_MODEL
```

- Papers are not bundled with the app; they are downloaded from the official PubMed API (E-utilities). Re-running is safe.
- Requests are spaced out to respect NCBI usage rules (3 requests/s without a key). For bulk collection, weekends or nighttime (US Eastern) are recommended.
- A topic that returns 0 papers means its PubMed query (`pubmed_term` in `topics.py`) is too narrow; fix it and run again.
- Embeddings (`--embed`) are experimental. Keyword search chooses the candidates and embeddings only refine the order.

**Things to know**

- Recommendations are **for reference only.** Thresholds (10 sets/week, 1.6 g/kg, etc.) are widely used rules of thumb (heuristics), not personal prescriptions. See a professional if you have pain.
- The AI summary is based on paper abstracts but can be wrong. Check the paper links and excerpts yourself.
- The analysis only uses records stored in this browser. Records from other devices are not included.
- If the AI step fails or times out, the rule-based findings and papers are still shown. The wait limit can be raised with `AI_TIMEOUT_S`.

## Accuracy improvements (Phase 4.5)

**Paper matching**
- Each topic has **required terms** (e.g. rear delts → `deltoid`; combat sports → names of the sports) and **excluded populations** (stroke, COVID, cancer, etc. in the title), so papers that only share keywords are removed (`topics.py`).
- When the AI summary is on, papers the model marks as irrelevant to a finding are hidden, and the number hidden is shown. Hidden papers are not accepted as citations either.
- The search queries for rear delts, push/pull and combat sports were widened, so **re-run `python ingest_pubmed.py`** (already downloaded papers are skipped).
- Check tool: `python eval_retrieval.py` prints which papers are attached to each recommendation (no network or key needed).

**Photo analysis**
- The model is asked for serving size (g) and confidence, and when calories differ from the macros (4/4/9 kcal per g) by more than 25%, both numbers are shown.
- On the review screen, **portion buttons (0.5×–2×)** scale calories and macros per item at once, and mismatched calories can be recalculated from the macros.
- If a food was misidentified, enter a **hint** (e.g. "chicken breast salad") and analyze the same photo again. The hint is passed only as a reference for the food name.

## Layout and game-style feedback (Phase 5)

- **PC layout**: a left sidebar on wide screens (lg and up), a bottom tab bar on narrow ones. The note screen becomes two columns on PC (records | summary and game panel).
- **Personal records**: compared between exercises with the same name. Weighted exercises use estimated 1RM (Epley; reps counted up to 12), bodyweight exercises use reps. The first record of an exercise is not counted as a PR. A new PR triggers a notification and vibration.
- **Streak**: consecutive days with at least one completed set. Before today's workout, the streak up to yesterday is kept.
- **Weekly quests** (last 7 days): 3 workout days, 30 sets, 3 days with ≥90% of the meal plan followed, 1 PR.
- **Level**: XP = 1 per completed set + 10 per workout day + 25 per PR. The total XP needed for level L is 50 × (L−1)².
- **Muscle map**: completed sets per muscle group over the last 7 days, shown by color (0 sets gray, 1–9 yellow, 10+ green). The classification rules are the same as in `backend/insights.py`; if you change one, update `frontend/lib/muscles.ts` too.
- Game statistics use the notes stored on this device (localStorage).

## Combat sessions and diet helper (Phase 6)

- **Session block**: writing `sparring 60min rpe7` creates a time-based training block. Load = minutes × RPE (arbitrary units, AU), and only completed sessions count. The coach warns when the last 7 days' load exceeds 1.5× the previous 7 days (when the previous load is at least 300 AU), or when there are three or more days with RPE ≥ 8. Both thresholds are heuristics.
- **Diet helper (`/diet`)**: from current and target body-fat %, weight, maintenance calories (linked to the TDEE saved in the calculator) and weekly loss rate (% of body weight), it computes target weight, expected duration, daily intake and a weekly weight curve. It assumes lean mass stays the same and counts 7,700 kcal per kg of fat. Warnings appear for plans that are too aggressive (over 1% of body weight per week, deficit over 25%, under 1,200 kcal/day, target body fat under 10%). The body figure is a gauge that shows 5–40% body fat as height.

## Multilingual UI (한국어 · 日本語 · English)

- Switch with the language button (in the sidebar, or top right on narrow screens); the choice is stored on this device. If nothing is stored, the browser language (ja/en) is used.
- The translation dictionary lives in one place: `frontend/lib/messages.ts`. Keys are the Korean source strings, used like `t("오늘")` in code. A sentence missing from the dictionary is shown in Korean, so a missing translation never breaks the screen. Placeholders like `{n}` are filled with `t("{n}세트", { n: 3 })`.
- Translated screens: navigation, calculator, note (blocks, summary, game panel, muscle map), diet helper, the coach screen frame, and the meal-photo screens. Sentences generated by the server (coach insights, recommended exercise names, disclaimers, photo-analysis warnings) are produced from the phrase table in `backend/texts.py` according to the request's `lang` (ko/ja/en); the AI summary and photo-analysis memo get their output language through the prompt. Server error messages (HTTP details) and paper text are not translated. After switching language, run the analysis again on the coach screen to get the new language.
- The Japanese and English strings were translated with AI assistance and have not been reviewed by native speakers yet.
- Exercise names are recognized in Korean, Japanese or English.

## Deployment

See [`DEPLOY.md`](DEPLOY.md) (Korean) for the Render (backend) + Vercel (frontend) setup. `backend/Dockerfile`, `render.yaml` and `backend/smoke_check.py` are included.

## Protections for a public demo

There is no login, so the following safeguards protect a public demo. This is not real authentication; treat it as a demo-level safety net.

- **Per-user note separation:** notes are separated by a random browser-generated ID (`X-Client-Id`). Turn on `REQUIRE_CLIENT_ID=1` on the server to reject requests without an ID. Server notes written before IDs existed are not visible in public mode; local records in the browser remain and are synced again under the new ID.
- **Per-IP rate limits:** separate per-minute limits for photo analysis, coach and note saving (`IP_VISION_RPM` etc.).
- **Daily AI call cap:** `AI_DAILY_CAP` (UTC) keeps the external AI key from running out.
- **Storage cap:** one user can store at most 1,000 notes.
- **Limits:** rate-limit state lives in server memory, so it resets on restart and is counted separately per server instance.

## Next steps

- Real user authentication + Supabase (Postgres) storage
- Coach: user-specific goals/profile, analysis of server-stored records, a vector DB (pgvector/Chroma)
- Distribute multi-joint exercises (e.g. squat) across several muscle groups by fractional sets (design only so far)
- Native-speaker review of the Japanese and English text
- Evaluate the heuristic thresholds (load spike, diet warnings) against real data
