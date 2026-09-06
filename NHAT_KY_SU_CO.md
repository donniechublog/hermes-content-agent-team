# Nhật ký sự cố & bài học

Tách khỏi `README.md` ngày 06/09/2026. README chỉ mô tả **hiện trạng**; mọi
chẩn đoán, số đo một lần, và bài học rút ra thì nằm ở đây — nguyên văn, không
cắt gọt, vì phần lớn giá trị của chúng nằm ở con số cụ thể và cách đo.

Đọc README trước để biết hệ thống ĐANG chạy thế nào; đọc tệp này khi cần biết
**vì sao** nó thành ra như vậy, hoặc khi một sự cố cũ có vẻ đang lặp lại.

Nguồn sự thật của cấu hình luôn là chính máy chủ, không phải hai tệp này:

```bash
grep -h "^  model:" ~/.hermes-*/profiles/*/config.yaml | sort | uniq -c
```

---

## Nova: 12 bảng → 23 bảng (06/09/2026)

Trích nguyên văn từ mục `scan_models.py` của README cũ.

**06/09/2026 — 12 bảng → 23 bảng.** Khảo sát 16 nguồn ứng viên, mỗi kết luận
"lấy được" bị một lần fetch độc lập phản biện. Ba nhóm thay đổi:

1. *Sửa chỗ tràn trước đã.* Ở trạng thái production (arena sống + có mốc cũ)
   báo cáo ra **13.635 ký tự** trong khi brief cắt ở 12.000 — `LIVEBENCH` và
   `OPENROUTER USAGE` bị nuốt **câm lặng**, Nova không biết hai bảng đó tồn
   tại. Ba mục `MODEL MOI`, trích benchmark, `ENGINE SUY LUAN` trước đó không
   có cận trên. Nay có `TRAN_*`, trần brief lên 22.000, và `_cat()` nói rõ khi
   đã cắt. Thêm nguồn trước khi vá chỗ này là làm phủ sóng **tệ đi**.
2. *Số đã tải về mà chưa dùng.* `agenticIndex` nằm sẵn trong payload AA từ lâu
   nhưng chưa bao giờ được dựng bảng → `so_hang()` mù với "leo hạng agentic"
   (cùng loại sự cố qwen3.8-max WebDev 02/09). SWE-bench trả 5 split trong
   **một** request, ta chỉ dùng `Verified`. Cả hai không tốn thêm request nào.
3. *Chiều thật sự mới* — `tbench` (agent gõ lệnh trong container), `arcagi`
   (bài chưa từng thấy), `hle` (trần kiến thức), `eci` (Epoch, có khoảng tin
   cậy), `opencompass` (đề đóng, phần lớn lab TQ), `tts`/`stt`/`i2v` (mảng
   không phải văn bản — trước đây mù hẳn), `hf_trending` (bắt model thả trọng
   số trước router 1–3 ngày).

**Bảng bị loại và lý do** — không phải vì lấy không được, cả 5 đều lấy được:
BFCL đóng băng từ 13/04/2026, LiveCodeBench từ 01/08/2025, Aider Polyglot từ
03/10/2025, BigCodeBench từ 16/04/2025, Papers With Code đã đóng cửa. Thêm
bảng chết vào script quét = mỗi lần chạy tốn một request để nhận `diff = 0`
vĩnh viễn. Vellum bị loại vì tự nó ghi là trang **tổng hợp** lại số của người
khác; GAIA vì nó xếp hạng **hệ thống agent** chứ không phải model (cột model
là chuỗi viết tay, không join được). SWE-bench `Lite`/`Full`/`Multimodal` đều
quá hạn nên chỉ lấy `Verified` + `Multilingual`.

Nợ kỹ thuật đã biết: `TBENCH` là edge function moi từ bundle JS của tbench.ai,
không phải API công bố — đổi project ref là chết im, cần theo dõi. `ids` trong
`models_seen.json` chỉ tăng, chưa có cơ chế cắt tỉa (~40 byte/model/ngày).

`fetch_opencompass` chập chờn (máy chủ ở TQ, hỏng kiểu `ConnectTimeout` /
`SSL: UNEXPECTED_EOF` chứ không phải bị chặn) nên có retry 2 lần; đo 06/09 từ
server thì một lượt hỏng cả 2 lần, lượt sau sạch. **Đường lui nếu nó tệ đi**:
CDN tĩnh `https://cdn.opencompass.org.cn/assets/llm-rank/<fileName>.json`
nhanh và ổn hơn hẳn (1,7s so với 6,5s), schema là `OverallTable`/`Knowledge`/
`Reason`/`Math`/`CodeTable`. Chưa dùng vì `<fileName>` xoay theo quý và chỉ
API kia mới cho biết tên — muốn chuyển thì phải nhớ tên tệp vào state và chỉ
gọi API khi CDN trả 404. Chưa làm: đổi một nguồn đang chạy được lấy thêm một
chỗ để hỏng thì không lời.

---

## Model từng vai

**Chuỗi đang chạy** (nguồn sự thật: `~/.hermes-<brand>/profiles/*/config.yaml`
— mỗi container một home riêng từ khi tách brand, không còn `~/.hermes` gộp
chung). Đo lại 04/09/2026, theo brand:

| Vai | donniechublog | dcgr.tech | Suy luận |
|---|---|---|---|
| Ada (analyst) | `ds/deepseek-reasoner` | `ds/deepseek-reasoner` | **bật** — vai duy nhất, việc đối chiếu điểm chấm cần suy luận thật |
| Bob | `ds/deepseek-v4-flash` | `ds/deepseek-v4-flash` | **medium** |
| Ethan (designer) | `ds/deepseek-v4-flash` | `ds/deepseek-v4-flash` | tắt |
| Dre (carousel) | `ds/deepseek-v4-flash` | `ds/deepseek-v4-flash` | tắt |
| Kite (carousel-edu) | `ds/deepseek-v4-flash` | — (chưa deploy *lúc đo 04/09*; dcgr deploy 05/09) | tắt |
| Gin / Itachi | `ds/deepseek-v4-flash` | `ds/deepseek-v4-flash` | tắt |
| Nova / Vera (market) | `ds/deepseek-v4-flash` | `ds/deepseek-v4-flash` | tắt |
| Finn (scout) | `ds/deepseek-v4-flash` | — (dcgr chỉ có Vera) | tắt |
| Jean (teaser) | `ds/deepseek-v4-flash` | — (blog only) | tắt |
| Miles (writer) | `ds/deepseek-v4-flash` | `ds/deepseek-v4-flash` | tắt |

Dự phòng của mọi vai (trừ Ada): `v4flash@api.b.ai → ds/deepseek-chat` (xem
mục Provider). Gin chạy việc thật **trên server** (torch+cpu cài từ 28/08/2026,
xem skill `inplace-translate`) — không còn phụ thuộc máy local. Kite ĐÃ DEPLOY
(2026-09-01), generator `render_edu.py` chạy live trên server.

**Đã thử glm-5.3 rồi hạ lại 04/09/2026:** Finn/Jean/Miles bên donniechublog và
Ethan bên dcgr.tech từng chạy chính bằng `xk/z-ai/glm-5.3`, kết quả một đợt A/B
chỉnh trực tiếp trên server ngày 01/09/2026 — không đi qua git nên không có
commit nào ghi lại lý do chọn. Audit 04/09 đo bằng `usage_audit.py`: glm-5.3 tốn
**$0,416 / 20 request** (~$0,0208/req) so với v4-flash **$0,0997 / 204 request**
(~$0,0005/req trong cùng cửa sổ) — đắt hơn khoảng **40 lần mỗi request** mà
không có bảng audition nào chứng minh bù lại được bằng chất lượng, nên cả bốn
vai đã hạ về `ds/deepseek-v4-flash` cùng ngày. Bản config trước khi hạ được giữ
ở `profiles/<vai>/config.yaml.bak-truoc-doi-v4flash-0904` trong từng home,
phòng khi cần so lại hoặc thử lại có kiểm soát hơn.

Đo bằng `cost_squeeze.py`, chạy lặp trên việc thật, chấm bằng code:

| Vai | Model | Trượt | USD/1000 lần |
|---|---|---|---|
| teaser | **deepseek-chat** | **0/5** | **0,77** |
| teaser | mimo-v2.5-pro | 1/5 (lan man 2417 từ) | 0,83 |
| teaser | v4-flash | 1/5 (rỗng) | 1,11 |
| teaser | v4-pro | 2/5 (rỗng, mất dấu) | 3,83 |
| writer | deepseek-chat | 0/6 | 0,06 |
| writer | v4-pro | 0/6 | 0,14 |

Gemini đã gỡ khỏi mọi chuỗi: trên số liệu usage thật nó tốn 1,72 USD/1M input
còn v4-flash chỉ 0,04 — **đắt gấp 44 lần**, vì cột cached của gemini trống rỗng,
không cache nổi một token. Kimi K3 đắt gấp 14 lần v4-pro và mọi tuyến Kimi đều
báo `thinkingCanDisable: false` — không tắt suy luận được.


---

## Hai nguyên tắc bắt buộc khi dùng nhiều model

**1. Bắt buộc phải có giám sát model.** Hermes fallback im lặng hoàn toàn — đặt
model chính thành model chết, agent vẫn trả lời bình thường, không một dòng báo.
Cần cả hai lớp: `model_watch.py` (model còn sống không) và `theo_doi_9router.py`
(model nào **thật sự** được gọi).

**2. Ghim mỗi hội thoại vào một model. Chuyển tầng thì chuyển ở ranh giới task.**
`try_activate_fallback` đổi model ngay giữa lượt, `restore_primary_runtime` lật
về model chính ở lượt sau — một hội thoại có thể chạy qua 2–3 model mà không ai
biết. Cache là per-model, mỗi lần lật là mất sạch prefix đã cache và cả ngữ cảnh
bị tính lại giá gốc. Cột `cache%` trong nhật ký ngày của `theo_doi_9router.py` chính là thước đo
nguyên tắc này: tụt cache nghĩa là đang lật model.

**Đã bắt được một nguyên nhân lật cụ thể (cron 05/09/2026, cả Finn/Nova/Vera):**
bước phụ `title_generation` (Hermes tự đặt tên phiên) gửi `response_format` mà
DeepSeek v4-flash trả `400 This response_format type is unavailable now`; 9router
coi đó là lỗi provider và đưa `deepseek/deepseek-v4-flash` vào cooldown ~30s
(`reset after 28s`); hai lần retry của vòng chính (cách 2–3s) rơi trọn trong
cooldown → `Fallback activated: v4-flash → deepseek-chat`, dính tới hết phiên
(1 call v4-flash rồi 11–24 call deepseek-chat). Dòng log nằm ở
`profiles/<vai>/logs/agent.log`, **không** có trong `logs/gateway.log`. Đếm
19/08–04/09: lỗi này 5–48 lần/ngày, fallback 4–33 lần/ngày. Chặn bằng
`auxiliary.title_generation.enabled: false` trong `config.yaml` từng profile:
script `tat_title_generation.py` (đã chạy xong và xoá khỏi repo 05/09, xem git log; quay lại
bằng tệp `.bak-truoc-tat-title-0905` trong từng profile); tiêu đề phiên vô dụng với task kanban/cron.

**Từ 05/09/2026 model chính là combo `DS-v4Flash` của 9router** (đổi bằng script
`doi_model_combo.py`, đã chạy xong và xoá khỏi repo cùng `bo_fallback_chat.py`; quay lại bằng
`.bak-truoc-doi-combo-0905` / `.bak-truoc-bo-fallback-chat-0905`; analyst giữ `ds/deepseek-reasoner`).
9router chỉ xoay giữa các connection *cùng* provider; ba route v4-flash (deepseek trực
tiếp `ds/`, xKiro `dsx/deepseek/deepseek-v4-flash`, aellm `dsa/deepseek-v4-flash`) chỉ
nối được với nhau qua Combo, gọi bằng đúng tên combo làm model (không có prefix
`combo/`). Trước đó cả ba node đều đặt prefix `ds` nên hai node ngoài bị che, 7 ngày
0 request. Đo route thật bằng `usageHistory.provider` của 9router; Hermes chỉ thấy
model `DS-v4Flash`. Combo còn chứa mục chết (`ds/ds/…`, `tokenrouter/…` không có
credential, `oc/…-free` unavailable) và chưa có `dsa/`: dọn trên dashboard.

**dcgr chạy chat theo bot mode chuẩn của Hermes từ 05/09/2026 (thí điểm, blog giữ
chat_router để so ~1 tuần).** Gateway dcgr: `multiplex_profiles: true`, 8 `profile_routes`
theo thread_id, bot riêng @hermesdcgr_bot; approve dcgr vẫn dùng @hermesmodebot cho chọn
số/Duyệt/Làm lại, chỉ nhường phần chat qua cờ `CT_CHAT_QUA_GATEWAY=1` đặt trong drop-in
`~/.config/systemd/user/hermes-approve@dcgr.service.d/override.conf` (unit template dùng
chung, blog không có cờ). Mỗi profile cần `profiles/<vai>/.env` với `OPENAI_API_KEY` +
`TELEGRAM_ALLOWED_USERS` (multiplex fail-closed, không fallback `.env` gốc) nhưng
**KHÔNG** được chứa `TELEGRAM_BOT_TOKEN`/`TELEGRAM_HOME_CHANNEL`: `backfill_profile_envs`
của Hermes chép cả token → gateway từ chối 8 profile vì "same credential" (đã gặp 05/09,
phải xoá dòng token khỏi 8 tệp). Đo bằng journal `hermes-gateway@dcgr` + `logs/gateway.log`
(INFO không vào journal) so với approve.log blog: độ trễ, mất mạch, 429/timeout. Nhận xét
đầu: reply qua gateway ngắn và không biết tình trạng task kanban như approve.
Bản chụp config + drop-in + mẫu .env để tái tạo: `hermes/gateway/dcgr/` (xem DOC.md ở đó).


---

## Provider

Mọi vai trừ Ada chạy chính bằng `ds/deepseek-v4-flash` trên connection DeepSeek
gốc, dự phòng là `v4flash` của
provider mới (connection `openai-compatible-chat-ba685909…`, baseUrl `api.b.ai`)
rồi `ds/deepseek-chat`. Ada giữ `ds/deepseek-reasoner` vì provider mới không có.

**Provider mới từng là tuyến chính, đã hạ xuống dự phòng ngày 25/08** khi nó trả
429 hết quota suốt nhiều giờ. Dây chuyền không gãy vì dự phòng gánh được, nhưng
chạy dài ngày ở tuyến dự phòng là mất sạch cache per-model mà không ai đo được
(xem điểm mù bên dưới), nên đảo hẳn thứ tự thay vì để nguyên.

Provider mới **chỉ phục vụ `deepseek-v4-flash`** và bản vision — `deepseek-v4-pro`
trả 403, `deepseek-chat` và `deepseek-reasoner` trả 404.

**Điểm mù cần nhớ: 9router KHÔNG ghi log connection này.** Đo thật: gọi thẳng 5
lượt, số bản ghi trong `usageHistory` đứng yên. Nghĩa là `usage_audit.py` và bảng
usage của 9router không thấy chi phí chạy qua đây. Muốn đo phải dùng
`hermes --usage-file`.

Nhưng `--usage-file` cũng có bẫy: nó ghi model được **cấu hình**, không phải model
**thực chạy**. Đã bắt được một lần Miles lặng lẽ tụt xuống `ds/deepseek-v4-pro`
mà tệp usage vẫn khai là đang chạy provider mới — chỉ lộ ra khi đối chiếu với log
9router.

**Điểm mù thứ hai: cả hai brand dùng CHUNG một instance 9router cục bộ**
(`http://127.0.0.1:20128/v1` trong cả hai `config.yaml`), và trong log
`usageHistory` cả hai brand hiện ra đúng **một** `apiKey` duy nhất. `usage_audit.py`
có sẵn cờ `--api-key` để tách theo client, nhưng vô dụng ở trạng thái hiện tại vì
chỉ có một khoá — nên báo cáo usage-audit của blog và dcgr luôn ra **cùng một
con số tổng**, không tách được brand nào tốn bao nhiêu.

**Đã tách 05/09/2026:** 9router có hai khoá `hermes blog` và `hermes dcgr` (bảng
`apiKeys`); khoá vào Hermes qua `OPENAI_API_KEY` trong `~/.hermes-<brand>/.env`
(config.yaml chỉ ghi `${OPENAI_API_KEY}`). **Nhưng** dcgr chạy multiplex nên 8
`profiles/<vai>/.env` cũng có `OPENAI_API_KEY`, và Hermes nạp `.env` của profile với
`override=True` (`hermes_cli/env_loader.py`) → khoá trong profile **đè** khoá gốc. Lúc
05/09 12:55 chỉ `.env` gốc mang khoá `hermes dcgr`, 8 profile vẫn mang khoá `hermes blog`
→ 9router ghi 181/182 request dcgr vào khoá blog, tách mà như chưa tách. Đổi khoá cho
dcgr = sửa `.env` gốc **và** cả 8 `profiles/*/.env` (blog không có profile .env nên chỉ
một dòng), rồi restart gateway brand đó. Từ đó `theo_doi_9router.py` tự tách req/$ theo
brand ở mục "theo khoá API" (đọc tên khoá từ bảng `apiKeys`, không cần sửa code).

**Điểm mù thứ ba: 9router KHÔNG ghi IP máy gọi.** `usageHistory` không có cột IP,
`meta` luôn `{}`; `custom-server.js` có tính `x-9r-real-ip` nhưng chỉ dùng cho
rate-limit. Service đang bind `0.0.0.0` (LAN 192.168.1.61 + netbird) nên ai trong
mạng cũng gọi được bằng khoá chung. Watcher socket `--canh` (đọc bảng TCP mỗi 2s,
ghi IP theo kết nối) đo 05/09 sáng rồi **bỏ 05/09 chiều**: nó chỉ thấy kết nối,
không thấy request (httpx keep-alive chở nhiều request một kết nối), và cách đúng
là bind 9router về `127.0.0.1` hoặc địa chỉ netbird rồi cấp khoá riêng cho từng
máy (mục "theo khoá API" tự tách). Nhật ký ngày `9router_<ngày>.md` cột "đổi model
liên tiếp" chỉ tin cặp v4-flash→deepseek-chat là fallback thật,

Token burn đo được cho một luồng trọn vẹn (Finn quét → vai ảnh dựng → vai viết,
17 lượt gọi): **~398.000 token chạm model**, cache 36%, 227 giây, ước $0,038.


---

## Bài học một tuần config 9router không chuẩn (29/08–05/09/2026)

1. **Hai chuỗi dự phòng chồng nhau, không ai nhìn cả hai.** Combo của 9router và
   `fallback_providers` của Hermes là hai cơ chế độc lập. Tắt deepseek-chat trên 9router
   xong vẫn thấy nó trong log vì 19 config Hermes còn giữ nó làm dự phòng. Quy tắc: đổi
   model là phải sửa CẢ HAI chỗ, kiểm bằng `grep deepseek-chat ~/.hermes-*/**/config.yaml`.
2. **Một route chết trong combo kéo cả chuỗi lật.** xKiro trả 404 "model does not exist"
   từ 06:34 05/09 mà vẫn nằm trong combo → combo lỗi định kỳ → Hermes fallback. Trước khi
   thêm route vào combo phải gọi thử; snapshot connection lỗi trong nhật ký ngày để bắt.
3. **Bước phụ làm lật model chính.** `title_generation` gửi `response_format`, v4-flash trả
   400, 9router cooldown 30s, 2 retry của Hermes rơi đúng cooldown → cả phiên chạy
   deepseek-chat. Mọi bước phụ (title, summary, vision) phải cùng model hoặc tắt hẳn.
4. **9router chỉ xoay connection cùng provider.** Ba route v4-flash khác provider chỉ nối
   được qua Combo; gọi bằng đúng tên combo, không có tiền tố `combo/`. Prefix trùng
   (`ds`) từng che mất hai node ngoài.
5. **Tên model lệch ba kiểu.** Hermes ghi `ds/deepseek-v4-flash`, `DS-v4Flash`,
   `DeepSeek-V4-Flash`; 9router ghi `deepseek-v4-flash`, `deepseek/deepseek-v4-flash`.
   Mọi script đối chiếu phải chuẩn hoá (bỏ tiền tố nhà cung cấp, không phân biệt hoa
   thường, resolve combo qua bảng `combos`), không so chuỗi thô.
6. **Nhìn số gộp thì không thấy gì.** usage_audit in một bảng N giờ rồi quên; glm-5.3 đắt
   40x/request ăn 70% tiền suốt nhiều ngày mà README vẫn nói v4-flash. Phải có nhật ký
   theo ngày, $ theo vai, $/bài, và đọc config thật trên server chứ không tin README.
7. **Hạ tầng dùng chung thì không tách được ai tốn gì.** Một 9router, một apiKey cho hai
   brand, bind 0.0.0.0 không ghi IP. Muốn tách brand cần khoá riêng; muốn biết máy nào
   gọi phải tự bắt ở socket. Đừng để mặc định của công cụ quyết định độ quan sát.

8. **Cache là của từng nhà cung cấp, không phải của model.** Cùng v4-flash, qua DeepSeek
   trực tiếp cache 93–96%, qua aellm (bán lại) 49% → đắt ~7x mỗi token prompt. Combo phải
   xếp DeepSeek trực tiếp TRƯỚC, reseller chỉ để dự phòng; và đừng để hết credit (402 hôm
   05/09 đẩy cả ngày sang aellm).
9. **System prompt đổi mỗi task vì một dòng.** Hermes in `Current working directory:` vào
   giữa prompt; workspace `scratch` tạo thư mục mới mỗi task nên 37% cuối prompt (skills,
   memory) không bao giờ trúng cache giữa hai task. Đo 05/09: hai task carousel cách 5 phút
   chỉ khác đúng dòng đó. Sửa: `approve_service.kanban_create` tạo task với
   `--workspace dir:~/.hermes-<brand>/kanban/workspaces/co-dinh`. Còn lại trong prompt chỉ
   đổi theo ngày (`Conversation started`) và theo model (`Model:`) — thêm lý do ghim model.
   Sửa SOUL cũng làm cache về 0 cho vai đó, gom sửa thành đợt. Chạy thử từ `~/hermes-agent`
   thì bị nhét cả AGENTS.md của Hermes (prompt 115k ký tự) — chỉ thử từ `~/content-team`.

Trạng thái sau khi sửa (05/09): combo = [ds trực tiếp, dsx xKiro, dsa aellm], 19 profile dự
phòng `ds/deepseek-v4-flash`, title_generation tắt, nhật ký ngày + web + tin 6h đã chạy.
Chỉ tiêu: fallback = 0 từ 06/09; sai thì trang chi tiết chỉ ra route nào.


---

## Suy luận (reasoning) — số đo


Lý do: model deepseek đốt hết ngân sách token vào suy luận rồi trả về **rỗng**.
Đo thật trên v4-pro: 3/24 lần (2/8 ở `max_tokens=800`, 1/8 ở 1200, 0/8 ở 2000).
Tái hiện y hệt trên v4-flash. Lỗi phụ thuộc ngân sách nên im lặng và ngắt quãng —
loại tệ nhất. Tắt suy luận: 0/24 lần rỗng, nhanh gấp 3, rẻ hơn, chữ vẫn đủ dấu.

Đã thử model rẻ hơn cho Jean (`ds/deepseek-chat`, `ds/deepseek-v4-flash`): chữ
vẫn tốt nhưng **lệch giọng** — viết kiểu tường thuật "bài viết nói rằng..." thay
vì giọng mời đọc. Chênh lệch giá chỉ 0,0026 USD/teaser nên không đáng đổi.

Kimi K3 đậu audition nhưng **đắt gấp 14 lần** v4-pro và mọi tuyến Kimi đều báo
`thinkingCanDisable: false` — không tắt suy luận được. Không dùng.

---

## Thiết kế thẻ kiểu `dai` (bỏ khỏi mã 05/09/2026)

Giữ lại làm **tham chiếu thiết kế**, không phải mô tả hiện trạng: không vai nào
dùng kiểu này nữa và `card.py` không còn nhánh nào cho nó. Trước đây nằm trong
`STYLE_TEXT_SPEC.md` và làm tệp đó tự mâu thuẫn với chính mã.

## Hệ chữ — kiểu `dai` (đã bỏ khỏi mã 05/09/2026, giữ lại làm tham chiếu thiết kế)
| Vai trò | Font | Cỡ | Kiểu |
|---|---|---|---|
| Tiêu đề | JetBrains Mono ExtraBold | 38–104px (tự nở theo chỗ trống) | IN HOA toàn bộ, đơn cách |
| Subtitle | Noto Serif | 20–50px | chữ thường, có dấu, serif |
| Chip nhãn | JetBrains Mono Bold | 26px | IN HOA |
| Via | Inter weight 500 | 29px | chữ thường |
| Tên kênh | Inter weight 500 | 27px | chữ thường |

## Bố cục kiểu `dai` — đã bỏ khỏi mã 05/09/2026, tham chiếu thiết kế (1200px ngang)
1. Vùng ảnh nguồn trên cùng — ảnh thật, không chèn chữ đè lên (trừ mascot nếu còn góc trống).
2. Khung kỹ thuật: 4 góc vát — 2 góc trên cyan, 2 góc dưới trắng; 2 đường dọc đôi; đường chia ngắt quãng ngay ranh giới ảnh/text.
3. Chip category trái: nền đặc cyan, chữ đen, đè lên ranh giới ảnh/textbox, có 2 tam giác gấp xuống phải (kiểu ruy-băng).
4. Chip category phải: nền trong suốt, viền cyan, chữ trắng, gấp lên.
5. Tiêu đề: căn trái, tối đa 2 dòng, trắng FG.
6. Subtitle: căn trái, tối đa 3 dòng, màu xám nhạt (donniechublog) hoặc trắng 95% (dcgr).
7. Chân thẻ: `via: <nguồn>` trái, màu cyan mờ; hàng icon social + @handle phải, icon mờ hơn chữ.
