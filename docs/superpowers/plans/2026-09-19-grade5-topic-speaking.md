# Grade 5 Topic Speaking Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Xây phòng luyện nói độc lập cho lớp 5: chọn chủ đề/từ, trò chuyện bằng micro, hỗ trợ thích ứng và tổng kết có bằng chứng.

**Architecture:** Một dịch vụ hội thoại dùng chung cho HTTP văn bản và adapter giọng nói; SQLite là nguồn trạng thái chính. Hai lần gọi mô hình cho một lượt bình thường: đánh giá có cấu trúc rồi sinh lời theo quyết định của code. Trạng thái, API và prompt riêng với Unit 1; tái sử dụng client OpenRouter và hạ tầng âm thanh.

**Tech Stack:** Python, Pydantic, SQLite, FastAPI, Pipecat đang khóa trong `voice/server/uv.lock`; Next.js 16.3.5, React 19.2.8; pytest, Vitest, Playwright. Không nâng cấp framework để làm tính năng.

**Spec:** `docs/superpowers/specs/2026-09-19-grade5-topic-speaking-design.md` — người dùng duyệt trong hội thoại; kế hoạch này chờ duyệt và chọn cách thực hiện.

## Global Constraints

- Phòng độc lập với bài học theo kịch bản và Free Talk cuối Unit 1.
- Bản đầu phục vụ lớp 5.
- Gợi ý tối đa 8 từ theo chủ đề; chọn hoặc nhập 1–5 từ cho một phiên.
- Không giới hạn thời gian cứng; trẻ kết thúc bằng nút hoặc yêu cầu rõ ràng.
- Không đồng nhất hoàn thành phiên với thành thạo từ vựng.
- Không chấm phát âm từ transcript.
- Không ghi đè các thay đổi OpenPronounce hiện có; không đưa chúng vào commit tính năng vô tình.
- Không đổi khóa, model hoặc voice ID. Kiểm tra sự hiện diện của biến môi trường trước live test, không in giá trị.
- Không scaffold lại ứng dụng. Đọc AGENTS.md và kiểm chứng mọi API Pipecat mới bằng Context Hub hoặc source của bản cài.

## Review Focus

- Nhấn gửi lại sau timeout: một lượt chỉ ghi một lần, khác nội dung nhưng cùng ID bị từ chối — Task 2/4.
- Trẻ nói đè khi AI đang suy nghĩ: kết quả cũ không phát hoặc ghi bằng chứng sai — Task 6.
- Mở hai tab cùng phiên: chỉ một kết nối âm thanh được quyền ghi; tab cũ không tiếp tục sinh lượt — Task 2/6.
- Chọn từ bằng tiếng Việt, từ trùng hoặc cụm từ: có phản hồi hữu ích, không âm thầm cắt danh sách — Task 1/5.
- Từ chối micro hoặc âm thanh không phát được: vẫn đọc/gõ được, không coi đó là lỗi của trẻ — Task 5/6.

## Nền hiện tại và ranh giới

`api/routes.py` tạo cứng phiên Unit 1; `api/runtime.py` là composition root và có fixture chỉ chạy khi ENV=test. `OpenRouterClient.structured_chat(messages, schema, request_id)` đã kiểm soát lỗi provider và khử thông tin liên hệ. `voice/server/bot.py` là bot hội thoại chung, chưa gọi dịch vụ học tập; không coi bot này đã đồng bộ với web. `web/src/app/page.tsx` chỉ dựng TutorShell; web chưa có client micro.

Code mới tập trung trong `backend/src/luna_tutor/speaking/`; file tests tương ứng trong `tests/backend/unit/speaking/`. Không dùng lại `LessonState` hay thêm điều kiện topic-speaking vào teaching engine.

## Task 1: Hợp đồng phiên và quy tắc hỗ trợ

**Files:** Create `backend/src/luna_tutor/speaking/{__init__,models,policy,catalog}.py`, `backend/src/luna_tutor/speaking/topics.yaml`; test `tests/backend/unit/speaking/test_policy.py`, `test_catalog.py`.

**Interfaces:** `SessionConfig(grade: Literal[5], topic: str, words: tuple[str,...])`; `SpeakingState(session_id, config, version, status, level, independent_streak, difficulty_streak, word_evidence, last_delivered_text)`; `TurnInput(turn_id, text, expected_version, quality)`; `Evidence(kind, independent, difficulty, word_uses)`; `Decision(action, level, independent_streak, difficulty_streak)`; `decide(state: SpeakingState, evidence: Evidence) -> Decision`.

- [ ] Viết kiểm thử với các mẫu thực tế: ba lượt độc lập tăng một mức; hai lượt khó giảm một mức; hỏi trợ giúp được hỗ trợ ngay; không rõ giữ mức; kết thúc không cần đủ từ. Ví dụ hợp đồng:

```python
def test_unclear_does_not_lower_level():
    state = SpeakingState.initial('s1', SessionConfig(grade=5, topic='Animals', words=('rabbit',)))
    result = decide(state, Evidence(kind='unclear', independent=False, difficulty=False, word_uses=()))
    assert result.level == state.level
    assert result.action == 'clarify'

def test_duplicate_words_are_normalized():
    config = SessionConfig(grade=5, topic='Food', words=(' Juice ', 'juice', 'sandwich'))
    assert config.words == ('juice', 'sandwich')
```

- [ ] Chạy `uv run --project voice/server python -m pytest tests/backend/unit/speaking -q`, xác nhận lỗi thiếu module trước triển khai.
- [ ] Tạo models strict, loại trường lạ. Giới hạn chủ đề 120 ký tự, từ/cụm từ 40 ký tự, đầu vào lượt 2000 ký tự. Chuẩn hóa khoảng trắng và chữ hoa; từ tiếng Việt đi qua bước xác nhận gợi ý Task 3, không tự chuyển nghĩa. Cấm cấu hình không phải lớp 5 hoặc ngoài 1–5 từ sau chuẩn hóa.
- [ ] Viết bảng quyết định thuần: `finish`, `clarify`, `offer_choices`, `continue`, `expand`. Mức 0–2, khởi đầu 1; độc lập tăng streak và reset difficulty; khó khăn làm ngược lại; hỗ trợ/không rõ reset chuỗi độc lập nhưng không tăng difficulty do lỗi audio. Dùng `min(2, level + 1)` và `max(0, level - 1)` tại ngưỡng 3/2, reset streak sau đổi mức.
- [ ] Thêm sáu chủ đề từ spec, mỗi chủ đề có tên Việt/Anh, tình huống picnic/chăm thú/trường học/sở thích/bạn bè/du lịch và từ mẫu làm đầu vào gợi ý; không phải script bắt buộc.
- [ ] Chạy lại tests, commit đúng các file Task 1.

## Task 2: Kho phiên và chống lặp/concurrent update

**Files:** Create `speaking/repository.py`, `speaking/schema.sql`, `tests/backend/unit/speaking/test_repository.py`.

**Interfaces:** `SpeakingRepository(path)`; `create(state)`, `get(session_id)`, `list_sessions()`, `reserve_turn(session_id, turn: TurnInput)`, `commit_turn(session_id, turn_id, next_state, reply)`, `release_turn(session_id, turn_id)`, `finish(session_id, expected_version)`, `record_delivery(session_id, turn_id, delivered_text, status)`. Typed errors: `NotFound`, `Conflict`, `SessionClosed`.

- [ ] Viết test hai repository connections cùng SQLite file, cùng version gửi hai lượt khác nhau; chỉ một reservation thành công. Kiểm tra cùng ID/cùng payload trả kết quả cũ, khác payload báo Conflict; finish phiên đã hoàn tất không tạo tổng kết thứ hai.

```python
def test_session_is_not_a_unit_session(tmp_path):
    repo = SpeakingRepository(tmp_path / 'sessions.sqlite3')
    state = SpeakingState.initial('s1', SessionConfig(grade=5, topic='Food', words=('juice',)))
    repo.create(state)
    assert repo.get('s1').config.topic == 'Food'
    assert not hasattr(repo.get('s1'), 'unit_id')
```

- [ ] Chạy riêng `test_repository.py` và xác nhận fail trước khi viết kho.
- [ ] Tạo bảng sessions và turns có khóa `(session_id, turn_id)`, JSON trạng thái, payload hash, status reserved/committed, deadline reservation và generation. Transaction ngắn `BEGIN IMMEDIATE` cho reserve/commit; không giữ transaction trong lúc gọi model. Lease theo timeout tổng xử lý cấu hình; commit bắt buộc đúng generation/version và lease hiện hành. Worker cũ hết lease không được commit.
- [ ] Delivery riêng với revision, status pending/spoken/interrupted/failed; không tăng version học tập. Lượt lặp lại chỉ cập nhật prefix dài hơn thuộc reply cùng ID; không cộng bằng chứng từ lần phát lại. Finish kiểm tra phiên bản, vô hiệu reservation cũ.
- [ ] Bổ sung test crash/lease hết hạn, kết quả đến muộn sau finish, transcript rỗng, prefix không thuộc câu AI, và ghi đồng thời text/voice. Run test file, commit Task 2.

## Task 3: Gợi ý từ và lõi hội thoại hai bước

**Files:** Create `speaking/{llm,service,summary}.py`, `speaking/prompts/{suggestions,evaluator,conversation}.yaml`; tests `test_llm.py`, `test_service.py`, `test_summary.py` trong thư mục unit speaking.

**Interfaces:** `SpeakingModels(client)` exposes async `suggest(topic: str) -> Suggestions`, `evaluate(state, turn: TurnInput) -> Evidence`, `reply(state, turn: TurnInput | None, evidence: Evidence | None, decision: Decision) -> Reply`; `Reply(text, support_kind)`; `Suggestions(topic, words, clarification)`; `SpeakingService(repository, models)` exposes async `start(config) -> SpeakingState`, `submit(session_id, turn) -> TurnResult`, `finish(session_id, version) -> Summary`. `TurnResult(state, reply)`. `Summary(independent, supported, unseen, next_practice)` from stored evidence only.

- [ ] Fake model records calls; kiểm tra evaluator thấy lời AI đã phát, không thấy phần bị ngắt. Test lỗi sinh lời sau đánh giá không ghi tiến độ, retry cùng ID không cộng đôi; không có lời trẻ thì không tính bằng chứng.

```python
async def test_provider_failure_does_not_advance(speaking_service, repo, failing_models):
    before = repo.get('s1')
    speaking_service.models = failing_models
    with pytest.raises(ProviderError):
        await speaking_service.submit('s1', TurnInput(turn_id='t1', text='I like juice.', expected_version=before.version, quality='final'))
    assert repo.get('s1').version == before.version
```

- [ ] Chạy tests này để có failure; xây fixture `speaking_service`, `repo`, `failing_models` trong `tests/backend/unit/speaking/conftest.py` bằng kho thật temp SQLite và fake async models.
- [ ] Dùng `structured_chat` với schema Pydantic ở mỗi lần gọi; prompt YAML theo loader convention hiện có. Transcript/topic/words là dữ liệu JSON, không system instructions. Mỗi từ được ghi nhận phải nằm trong danh sách đích và có quote có thật trong lời trẻ; evidence ghi rõ supported/independent và không nâng độc lập khi trả lời theo mẫu vừa cung cấp.
- [ ] Prompt hội thoại: tiếng Anh ngắn, cô–con khi hỗ trợ tiếng Việt; phản hồi ý trẻ trước câu hỏi tiếp; tối đa một câu hỏi chính; không ép lặp mẫu, không nhồi từ; trả lời câu hỏi ngược; nói được thành tiếng, không markdown. Prompt đánh giá không được chọn bước tiếp hoặc chấm phát âm. Thêm schema giới hạn output để tránh lời quá dài.
- [ ] `submit`: reserve → redact → evaluate → decide → reply → validate → commit, giải phóng reservation khi lỗi. Lượt unclear bỏ đánh giá năng lực, dùng câu xin nói lại. Yêu cầu dừng rõ do evaluator xác định dẫn tới finish thay vì hỏi tiếp. Ghi thời gian evaluate/reply/total không log transcript hay khóa.
- [ ] `start` dùng một lần sinh lời mở đầu sau xác thực cấu hình; chỉ lưu phiên khi có lời hợp lệ. `suggest` tối đa 8 từ có nghĩa/ví dụ, trả clarification cho đầu vào không phù hợp/không rõ; không thay từ người học âm thầm. Tổng kết tạo trực tiếp từ kho, không gọi LLM để bịa nhận xét.
- [ ] Test prompt injection trong chủ đề, từ tiếng Việt nhiều nghĩa, câu từ chối JSON, từ đích chưa dùng, hỗ trợ đã nói nhưng bị ngắt. Chạy unit speaking, commit Task 3.

## Task 4: API chung cho web và adapter giọng nói

**Files:** Create `speaking/{routes,schemas,fixtures}.py`, test `tests/backend/integration/api/test_speaking.py`; modify `backend/src/luna_tutor/api/{app,runtime}.py`.

**Interfaces:** `build_speaking_router(service, repository)`; routes `GET /api/speaking/topics`, `POST /suggestions`, `POST /sessions`, `GET /sessions`, `GET /sessions/{id}`, `POST /sessions/{id}/turns`, `POST /sessions/{id}/finish`, `POST /sessions/{id}/delivery`. Prefix đầy đủ `/api/speaking` cho mọi route. `create_app` nhận optional speaking service/repository để giữ tests cũ.

- [ ] Viết integration tests gọi thật HTTP client và SQLite; kiểm tra 404 unknown, 409 conflict/closed, 422 input không hợp lệ, 503 provider và retryable true. Hai requests đồng thời cùng lượt chỉ tạo một reply.

```python
def test_cannot_create_grade_four(client):
    response = client.post('/api/speaking/sessions', json={'grade': 4, 'topic': 'Food', 'words': ['juice']})
    assert response.status_code == 422
```

- [ ] Chạy `uv run --project voice/server python -m pytest tests/backend/integration/api/test_speaking.py -q`, xác nhận routes chưa có.
- [ ] Wire service/kho riêng vào runtime. Dùng chung lifespan OpenRouter client. Fixtures chỉ bật với `ENV=test` và `TUTOR_LLM_MODE=fixture`; có scenario English/Vietnamese/help/end/failure. Trả lỗi an toàn, không exception chứa khóa.
- [ ] Lịch sử trả replies với delivered_text/status; không giả định text displayed là audio heard. Văn bản mode đánh dấu presented riêng; audio mode delivery do server audio xác nhận. Route delivery nội bộ dùng credential server-only, không cho browser tự khai nghe đủ để ghi bằng chứng.
- [ ] Thêm test API cũ vẫn tạo Unit 1; chạy toàn bộ `tests/backend/integration/api`, commit Task 4.

## Task 5: Phòng lớp 5 trên web, dùng được qua text

**Files:** Create `web/src/app/speaking/page.tsx`, `web/src/components/speaking/{SpeakingRoom,TopicPicker,WordPicker,Conversation,SessionSummary}.tsx`, `web/src/lib/{speaking-api,speaking-types}.ts`, `web/src/components/speaking/speaking.module.css`; modify `web/src/components/TutorShell.tsx` để thêm link; tests `tests/web/speaking-room.test.tsx`, `tests/e2e/speaking-session.spec.ts`.

**Interfaces:** TypeScript mirrors API `SessionConfig`, `TurnResult`, `Summary`; `speakingApi.create`, `.suggest`, `.get`, `.list`, `.submit`, `.finish`; mọi submit giữ nguyên turn_id khi retry.

- [ ] Test tạo phiên với chủ đề riêng, chọn từ gợi ý/tự nhập, lỗi quá 5 từ, bỏ từ trùng, provider failure giữ lựa chọn, kết thúc và đọc lại lịch sử.

```tsx
it('keeps typed words when suggestions fail', async () => {
  render(<SpeakingRoom />);
  await userEvent.type(screen.getByLabelText('Chủ đề của em'), 'Picnic');
  await userEvent.type(screen.getByLabelText('Từ muốn luyện'), 'juice');
  await userEvent.click(screen.getByRole('button', {name: 'Gợi ý từ'}));
  expect(await screen.findByRole('alert')).toBeVisible();
  expect(screen.getByLabelText('Từ muốn luyện')).toHaveValue('juice');
});
```

- [ ] Chạy `npm --prefix web test -- --run ../tests/web/speaking-room.test.tsx`, xác nhận fail. Dùng mock API conventions hiện có, không model live trong UI tests.
- [ ] Dựng chọn chủ đề/từ, Start, hội thoại, input chữ, Finish, History. Thông báo ngắn tiếng Việt, câu hội thoại tiếng Anh. Hiện nghĩa/ví dụ từ; nút nghe nối adapter ở Task 6. Không hiện level nội bộ hay raw evaluator JSON cho trẻ.
- [ ] Lưu session ID trong URL query để reload khôi phục; không tự gửi lại tin nhắn khi mount. Khóa submit trong lúc pending; retry dùng ID cũ. Đổi chủ đề hoàn tất phiên cũ rồi mở bộ chọn mới.
- [ ] E2E dùng fixture backend: chọn → 3 lượt → finish → reload/history; kiểm tra Unit 1 vẫn vào được. Chạy test UI và E2E file mới, commit Task 5.

## Task 6: Nối micro, TTS và đồng bộ lời đã phát

**Files:** Create `voice/server/{speaking_bot,speaking_processor,speaking_delivery,speaking_api_client}.py`, `web/src/lib/speaking-voice.ts`, `web/src/components/speaking/VoiceControls.tsx`; modify speaking web room, `web/package.json`/lock, `scripts/run-local.sh`, `voice/README.md`; tests `tests/voice/test_speaking_pipeline.py`, `tests/web/speaking-voice.test.ts`, `tests/e2e/speaking-voice.spec.ts`.

**Interfaces (application-owned):** `SpeakingVoiceClient.connect(sessionId: string): Promise<void>`, `.disconnect()`, `.setMuted(value: boolean)`, callbacks `onState`, `onSessionChanged`, `onError`. Server `SpeakingApiClient.submit(session_id, turn)`, `.record_delivery(...)`, `.get(session_id)` gọi Task 4; `SpeakingProcessor` chuyển lượt người học hoàn tất sang API và phát reply qua TTS. Không gửi text lần nữa từ browser khi đã có audio transcript.

- [ ] Tra exact installed Pipecat signatures trước viết imports, frames và hooks. Context Hub đã xác nhận 1.11.0 index ngày 2026-09-18; đối chiếu lock tại lúc thực hiện. Query `search-api`/`check-deprecation` cho processor, aggregation, delivery và lifecycle symbols được dùng; đọc source khi index không khớp.
- [ ] Test bằng fake STT/TTS và API: phát một reply, ngắt giữa câu, nhận delivered prefix; evaluator lượt sau chỉ thấy prefix. Test transcript partial rồi final không sinh hai lượt. Test generation cũ hoàn tất sau interrupt không được phát.

```python
async def test_interruption_keeps_only_spoken_prefix(voice_harness):
    await voice_harness.bot_reply('t1', 'A rabbit! What does it eat?')
    await voice_harness.played('t1', 'A rabbit!')
    await voice_harness.interrupt()
    assert voice_harness.delivery('t1').text == 'A rabbit!'
    assert voice_harness.delivery('t1').status == 'interrupted'
```

- [ ] Chạy test voice để xác nhận thiếu adapter; tạo harness frame-based dùng source hooks đã xác minh, không mock toàn bộ lifecycle.
- [ ] Tạo entry `speaking_bot.py` theo scaffold hiện có, giữ `bot(runner_args)` và reuse provider factory `create_stt` hiện tại, Soniox TTS cấu hình hiện hữu. SmallWebRTC request mang speaking session ID; server kiểm tra phiên tồn tại/active trước nhận. Truyền metadata mode setup để cho phép nói chủ đề trước tạo phiên; chế độ setup chỉ trả transcript, không ghi bằng chứng học tập.
- [ ] Pipeline dùng turn aggregation trước speaking processor; output và assistant aggregation sau TTS; delivery observer nằm ở phần output đã phát. Gửi reply text qua các frames được xác minh, không thêm LLM service thứ ba làm thay lời đã cam kết. Unknown playback chỉ ghi unknown, không mặc định toàn bộ câu đã được nghe. Khi ngắt, vô hiệu generation, chốt delivery trước đánh giá lượt kế tiếp.
- [ ] Giữ một lease audio cho mỗi session, kết nối mới chỉ vào khi lease trước đã đóng/hết hạn. Heartbeat và release khi disconnect; backend từ chối token cũ. Reconnect nạp kho; không tự phát lại opening. Nút nghe lại dùng turn ID cũ, không tạo bằng chứng/lượt mới. Nghe ví dụ từ không ghi tiến độ.
- [ ] Dùng `@pipecat-ai/client-js` + `@pipecat-ai/small-webrtc-transport`, đã được Context7 docs xác nhận; kiểm tra version tương thích và pin trong lockfile. Bọc trong speaking-voice.ts. Nối remote audio track vào audio element, xử lý autoplay rejection bằng nút Bật âm thanh. Không dùng browser SpeechRecognition thay STT provider. Mẫu kết nối từ docs hiện hành (kiểm tra types của bản cài vì docs cũng còn ví dụ `webrtcUrl`):

```typescript
import { PipecatClient } from '@pipecat-ai/client-js';
import { SmallWebRTCTransport } from '@pipecat-ai/small-webrtc-transport';
const client = new PipecatClient({
  transport: new SmallWebRTCTransport(), enableMic: true, enableCam: false,
});
await client.startBotAndConnect({
  endpoint: '/api/start', requestData: { speaking_session_id: sessionId },
});
```

Endpoint `/api/start` thuộc voice runner; proxy web chuyển tới voice origin cấu hình, không trỏ nhầm vào backend `/api/speaking`. Proxy chỉ cho phép đường start/offer được liệt kê và body có giới hạn, không nhận arbitrary upstream URL. Thêm `web/src/app/api/start/route.ts` và `web/src/app/api/offer/route.ts` cùng test request forwarding; giữ credential internal ở phía server.
- [ ] Kiểm tra mất mạng, deny micro, disconnect/unmount cleanup, hai tab, finish trong khi đang phát, text gửi khi mic đang xử lý; trạng thái UI connecting/listening/thinking/speaking/disconnected. Đường text luôn có khi audio không khả dụng.
- [ ] Chạy voice tests và UI tests; thêm fake-media browser smoke cho lifecycle, sau đó live audio ở Task 7. Commit riêng các file mới và hunk thuộc tính năng, bảo toàn diff OpenPronounce trước đó.

## Task 7: Đánh giá hành vi và bàn giao chạy thử

**Files:** Create `evals/speaking-grade5/{scenarios.yaml,report.md}`, `scripts/eval-speaking-grade5.py`; modify `README.md`, `tests/README.md`; test `tests/backend/integration/test_speaking_scenarios.py`.

**Interfaces:** CLI `uv run --project voice/server python scripts/eval-speaking-grade5.py --mode text --output eval-runs/speaking-grade5`; `--mode audio` dùng bot eval transport. Report gồm scenario, assertion, outcome, evaluate_ms, reply_ms, total_ms; audio ghi latency từ kết thúc lời trẻ đến bắt đầu âm thanh AI, không đánh đồng với tổng HTTP.

- [ ] Viết fixtures cho beginner/help/Vietnamese/advanced/child-question/off-topic/unclear/end-early và interrupt/reconnect audio. Mỗi scenario có topic/words, user turns, kỳ vọng hỗ trợ và bằng chứng; không đưa đáp án benchmark vào prompt.

```yaml
name: finish_without_all_words
topic: Animals
words: [rabbit, carrot, feed]
turns:
  - user: I like rabbits.
  - user: I want to stop now.
expect:
  status: completed
  independent_words_exclude: [carrot, feed]
```

- [ ] Test parser và deterministic assertions fail đúng khi chatbot gán feed đã dùng dù chưa có quote. Chạy scenario fixtures không khóa; các tiêu chí tự nhiên đánh giá bằng rubric và lưu mẫu review, không kiểm tra chính xác chuỗi lời AI.
- [ ] Kiểm tra khóa/cấu hình hiện diện trước live; chạy text với provider thật và audio bằng eval transport. Nếu thiếu credential hoặc upstream OpenPronounce chưa sẵn sàng, báo chính xác phần chưa kiểm chứng; không gọi suite fixture là kiểm chứng giọng nói thật.
- [ ] Chạy `uv run --project voice/server python -m pytest -q`, `npm --prefix web test -- --run`, `npm --prefix web run lint`, `npm --prefix web run build`, `npm --prefix web run test:e2e`. Phân biệt baseline failure với regression; không sửa lỗi ngoài phạm vi âm thầm.
- [ ] Nghe lại ít nhất tình huống help, child-question và interruption; ghi p50/p95 latency cùng số mẫu. Không đặt SLA giả khi chưa đo; ghi mọi độ trễ provider làm trải nghiệm bị gián đoạn và xử lý trước khi tuyên bố dùng được.
- [ ] Cập nhật hướng dẫn khởi chạy API/web/voice, URL phòng, cấu hình server-only, đường text thay thế và giới hạn đánh giá; commit report không chứa dữ liệu nhạy cảm. Review diff toàn nhánh trước bàn giao, không tự deploy.

## Đối chiếu spec và điểm kiểm tra khi thực thi

Mục 1–3 spec → Tasks 1/3/5; mục 4 → Tasks 1/3; mục 5 → Tasks 2/4/6; mục 6 → Tasks 2/3/4/6; mục 7 → Task 7 và test theo từng task. Chủ đề nói bằng micro và nghe ví dụ được bao phủ Task 6, không bỏ vì phiên text đã chạy.

Tài liệu đã tra trong lúc lập kế hoạch: Context7 `/pipecat-ai/pipecat-client-web` xác nhận start/connect và requestData; kết quả lẫn ví dụ package cũ/mới, vì vậy không sao chép package name từ trí nhớ. Context Hub có hướng dẫn interruption: https://docs.pipecat.ai/pipecat/fundamentals/interruptions.md — chỉ text đồng bộ với phần audio đã phát mới vào lịch sử nghe. Exact adapter API phải đối chiếu phiên bản cài ở Task 6.

Kế hoạch này chưa tạo sản phẩm hoặc cài phụ thuộc. Cách thực thi đề xuất: native trong phiên này, tuần tự theo các giao diện phụ thuộc; một lượt review độc lập toàn nhánh cuối cùng. Chờ người dùng duyệt kế hoạch và chọn cách thực thi.
