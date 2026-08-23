#!/usr/bin/env python3
"""Dich vu Telegram cho content-team: duyet bai (nut bam) + chon tin (reply so).

Chi MOT tien trinh duoc long-poll mot bot token voi mot offset -- Telegram
getUpdates xac nhan (va xoa khoi hang doi) MOI update tinh toi offset, khong
chi loai dang loc qua allowed_updates. Chay hai poller doc lap se lam rot
update cua nhau. Vi vay dich vu nay xu ly ca hai luong trong cung mot vong lap:

  A) callback_query -- nut Duyet/Bo tren ban nhap draft (nhu truoc)
  B) message -- Ong Chu reply so thu tu trong topic scout -> tao cap task
     illustrator+writer cho dung tin da chon trong manifest cua Finn
"""
import json
import os
import re
import subprocess
import sys
import threading
import time
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parent))
import chat_router                                          # noqa: E402
import moat_publish                                         # noqa: E402

ROOT = Path.home() / "content-team"
DRAFTS = ROOT / "drafts"
STATE_DIR = ROOT / "state"
OFFSET = STATE_DIR / "offset.txt"
API = "https://api.telegram.org/bot{token}/{method}"
HERMES_PY = Path.home() / "hermes-agent" / "venv" / "bin" / "python"
HERMES_HOME = str(Path.home() / ".hermes")

import env_load                                              # noqa: E402


def load_secrets():
    env_load.nap()
    tok = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not tok:
        sys.exit("Thieu TELEGRAM_BOT_TOKEN")
    return (tok,
            os.environ.get("TELEGRAM_CHANNEL_ID"),
            os.environ.get("TELEGRAM_GROUP_ID"))


def call(token, method, **kw):
    with httpx.Client(timeout=90) as c:
        r = c.post(API.format(token=token, method=method), json=kw)
    return r.json()


def scout_thread_id():
    p = STATE_DIR / "topics.json"
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8")).get("scout")


# ---------- A) duyet ban nhap (khong doi so voi truoc) ----------

def keyboard(draft_id):
    return {"inline_keyboard": [[
        {"text": "✅ Duyệt & đăng", "callback_data": "ok:" + draft_id},
        {"text": "❌ Bỏ", "callback_data": "no:" + draft_id},
    ]]}


def _send_media_group(token, chat, media, thread_id=None):
    """Gui album URL anh (Telegram tu tai, khong can file cuc bo). Album
    KHONG the gan nut bam -- day la gioi han cua Telegram Bot API."""
    items = [{"type": "photo", "media": m} for m in media]
    data = {"chat_id": chat, "media": json.dumps(items)}
    if thread_id:
        data["message_thread_id"] = str(int(thread_id))
    with httpx.Client(timeout=120) as c:
        r = c.post(API.format(token=token, method="sendMediaGroup"), data=data)
    return r.json()


def draft_push(token, group, draft_id, thread_id=None):
    d = json.loads((DRAFTS / (draft_id + ".json")).read_text(encoding="utf-8"))
    caption = "<b>BẢN NHÁP</b>\n\n" + d["caption"]
    payload = {"chat_id": group, "caption": caption, "parse_mode": "HTML",
               "reply_markup": keyboard(draft_id)}
    if thread_id:
        payload["message_thread_id"] = int(thread_id)

    images = d.get("images")
    if images:
        # Album truoc (khong nut), roi tin nhan chu rieng kem nut duyet --
        # nut bam luon nam tren tin nhan NAY, khong phai anh.
        _send_media_group(token, group, images, thread_id)
        text_payload = {"chat_id": group, "text": caption, "parse_mode": "HTML",
                        "reply_markup": keyboard(draft_id)}
        if thread_id:
            text_payload["message_thread_id"] = int(thread_id)
        return call(token, "sendMessage", **text_payload)

    img = d.get("image")
    if img and Path(img).exists():
        with httpx.Client(timeout=120) as c, open(img, "rb") as fh:
            r = c.post(API.format(token=token, method="sendPhoto"),
                       data={k: (json.dumps(v) if k == "reply_markup" else v)
                             for k, v in payload.items()},
                       files={"photo": (Path(img).name, fh, "image/png")})
        return r.json()
    payload["text"] = payload.pop("caption")
    return call(token, "sendMessage", **payload)


CAPTION_LIMIT = 1024      # gioi han caption cua sendPhoto / sendMediaGroup
TEXT_LIMIT = 4096         # gioi han cua sendMessage


def publish(token, channel, draft_id):
    """Dang draft len channel.

    Caption dai (teaser thuong 3000+ ky tu) VUOT gioi han 1024 cua caption anh.
    Truong hop do: gui anh truoc khong caption, roi gui chu rieng — thay vi de
    Telegram tu choi ca bai.
    """
    d = json.loads((DRAFTS / (draft_id + ".json")).read_text(encoding="utf-8"))
    caption = d["caption"]
    long_caption = len(caption) > CAPTION_LIMIT

    images = d.get("images")
    if images:
        # Anh co the la URL (teaser lay tu bai goc) HOAC tep cuc bo (the do Iris
        # dung + anh that tai ve). Tep cuc bo phai dinh kem multipart qua
        # attach://, khong the truyen duong dan — Telegram khong doc duoc o may ta.
        items, files = [], {}
        for i, m in enumerate(images[:10]):          # Telegram cho toi da 10
            e = {"type": "photo"}
            if str(m).startswith("http"):
                e["media"] = str(m)
            else:
                pth = Path(m)
                if not pth.exists():
                    continue
                khoa = f"anh{i}"
                e["media"] = f"attach://{khoa}"
                files[khoa] = (pth.name, pth.read_bytes(), "image/png")
            if not items and not long_caption:
                e["caption"] = caption
                e["parse_mode"] = "HTML"
            items.append(e)
        with httpx.Client(timeout=180) as c:
            r = c.post(API.format(token=token, method="sendMediaGroup"),
                       data={"chat_id": channel, "media": json.dumps(items)},
                       files=files or None)
        res = r.json()
        if long_caption and res.get("ok"):
            return call(token, "sendMessage", chat_id=channel, text=caption,
                        parse_mode="HTML", disable_web_page_preview=True)
        return res

    img = d.get("image")
    if img and Path(img).exists():
        with httpx.Client(timeout=120) as c, open(img, "rb") as fh:
            data = {"chat_id": channel, "parse_mode": "HTML"}
            if not long_caption:
                data["caption"] = caption
            r = c.post(API.format(token=token, method="sendPhoto"),
                       data=data,
                       files={"photo": (Path(img).name, fh, "image/png")})
        res = r.json()
        if long_caption and res.get("ok"):
            return call(token, "sendMessage", chat_id=channel, text=caption,
                        parse_mode="HTML", disable_web_page_preview=True)
        return res
    return call(token, "sendMessage", chat_id=channel, text=caption,
                parse_mode="HTML", disable_web_page_preview=True)


def mark_draft(draft_id, status):
    p = DRAFTS / (draft_id + ".json")
    d = json.loads(p.read_text(encoding="utf-8"))
    d["status"] = status
    d["decided_at"] = int(time.time())
    p.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")


def handle_callback(token, channel, cq):
    data = cq.get("data", "")
    action, _, draft_id = data.partition(":")
    msg = cq["message"]
    chat_id, msg_id = msg["chat"]["id"], msg["message_id"]

    if not (DRAFTS / (draft_id + ".json")).exists():
        call(token, "answerCallbackQuery", callback_query_id=cq["id"],
             text="Không tìm thấy bản nháp", show_alert=True)
        return

    if action == "ok":
        res = publish(token, channel, draft_id)
        ok = res.get("ok")
        mark_draft(draft_id, "published" if ok else "publish_failed")
        note = ("✅ ĐÃ ĐĂNG lên channel" if ok
                else "⚠️ Đăng lỗi: " + str(res.get("description")))
        # Bai da len channel thi day tiep sang moat cho extension dang len social.
        # Chi day khi Telegram da nhan -- khong dang duoc o day thi bai chua duyet xong.
        # Loi ben moat chi them mot dong vao the, KHONG lam hong luong duyet.
        if ok:
            pushed, why = moat_publish.intake(draft_id)
            note += ("\n\U0001f4e4 moat: " + why) if pushed else ("\n\u26a0\ufe0f moat: " + why)
        call(token, "answerCallbackQuery", callback_query_id=cq["id"],
             text="Đã đăng" if ok else "Lỗi khi đăng")
    elif action == "no":
        mark_draft(draft_id, "rejected")
        note = "❌ ĐÃ BỎ — không đăng"
        call(token, "answerCallbackQuery", callback_query_id=cq["id"],
             text="Đã bỏ bài")
    else:
        return

    base = msg.get("caption") or msg.get("text") or ""
    body = base.replace("BẢN NHÁP", "BẢN NHÁP (đã xử lý)", 1)
    method = "editMessageCaption" if msg.get("caption") else "editMessageText"
    key = "caption" if msg.get("caption") else "text"
    call(token, method, chat_id=chat_id, message_id=msg_id,
         **{key: body + "\n\n<b>" + note + "</b>"}, parse_mode="HTML",
         reply_markup={"inline_keyboard": []})


# ---------- B) Ong Chu reply so thu tu -> tao cap task ----------

def slugify(title, fallback):
    s = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    return (s[:40].strip("-") or fallback)


# Topic nao chon tin tu manifest nao. Finn, Nova va Vera deu la vai DI TIM TIN,
# nen ca ba phai chon duoc bang cach tra loi so — truoc day chi Finn lam duoc,
# bao cao cua Nova va Vera la van xuoi khong so nen Ong Chu khong biet rep gi.
MANIFEST_THEO_TOPIC = {
    "scout": "finn_candidates_*.json",
    "nova": "nova_candidates_*.json",
    "market": "vera_candidates_*.json",
}


def latest_manifest(vai="scout"):
    files = sorted(STATE_DIR.glob(MANIFEST_THEO_TOPIC.get(vai, "finn_candidates_*.json")))
    return files[-1] if files else None


# Vai dung anh -> thuong hieu. Ong Chu chon bang cach tra loi "1 - Ethan".
# Khong ghi ten ai thi mac dinh Iris, giu nguyen thoi quen cu.
VAI_ANH = {
    "iris": ("illustrator", "donniechublog"),
    "illustrator": ("illustrator", "donniechublog"),
    "ethan": ("ethan", "dcgr"),
}
MAC_DINH_ANH = "iris"


def doc_lenh_chon(text: str):
    """Phan tich lenh chon tin. Tra ve [(so, vai_anh, thuong_hieu)] hoac None.

    Quy tac: ten vai ap cho MOI SO dung truoc no, tinh tu ten vai gan nhat.
    So nao khong co ten vai nao phia sau thi ve mac dinh (Iris).

        1                    -> Iris
        1, 2, 3              -> ca ba Iris
        1, 2, 3 - Ethan      -> ca ba Ethan
        1 - Iris, 2 - Ethan  -> 1 Iris, 2 Ethan
        1, 2 - Ethan, 3      -> 1 va 2 Ethan, 3 Iris

    Tra None neu co phan khong hieu duoc, de tin nhan roi ve luong hoi thoai
    thay vi bao loi — Ong Chu con dung chinh topic do de tro chuyen.
    """
    if not text or not text.strip():
        return None

    # Tach thanh cac manh: moi manh la mot SO hoac mot TEN VAI
    manh = []
    for c in re.split(r"[,\n;]+", text.strip()):
        c = c.strip()
        if not c:
            continue
        for phan in c.split():
            phan = phan.strip("-\u2013\u2012:")
            if not phan:
                continue
            if phan.isdigit():
                manh.append(("so", int(phan)))
            elif re.fullmatch(r"[A-Za-zÀ-ỹ]+", phan):
                if phan.lower() not in VAI_ANH:
                    return None          # ten la -> khong phai lenh chon
                manh.append(("vai", phan.lower()))
            else:
                return None
    if not any(k == "so" for k, _ in manh):
        return None

    ra, cho, thay = [], [], set()
    def _xa(ten):
        for n in cho:
            if n in thay:
                continue
            thay.add(n)
            ra.append((n, *VAI_ANH[ten]))
        cho.clear()

    for kind, v in manh:
        if kind == "so":
            cho.append(v)
        else:
            _xa(v)                        # ten vai ap cho moi so dang cho
    _xa(MAC_DINH_ANH)                     # so con lai ve mac dinh
    return ra or None


def vai_cua_topic(thread_id):
    """Topic id -> ten vai, doc tu state/topics.json."""
    tp = STATE_DIR / "topics.json"
    if thread_id is None or not tp.exists():
        return None
    try:
        m = json.loads(tp.read_text(encoding="utf-8"))
    except Exception:                                        # noqa: BLE001
        return None
    for ten, tid in m.items():
        if str(tid) == str(thread_id):
            return ten
    return None


ILLU_BODY = """Nguon: {source_note}
Link: {link}
Nguon anh (via): {via}
Chu de: {title}
Tom tat: {summary}
image_url (og:image so bo, co the la the thuong hieu): {image_url}

NHIEM VU: dung the anh cho bai nay tu ANH THAT cua nguon.
Thuong hieu: {brand}

NGUYEN TAC TREN HET: KHONG BAO GIO tu ve minh hoa.
Ve ra la bia dat — the anh phai phan anh dung cai co that trong nguon. Khong tim
duoc anh thi BAO LAI, khong duoc lap cho trong bang hinh tu nghi ra.

BUOC 1 — tim anh that cua tin nay (BAT BUOC chay lenh nay):
cd /home/donniechu/content-team && venv/bin/python anh_bai.py \\
  --tieu-de "{title}" --link "{link}" --json \\
  --tu-nguon /home/donniechu/content-team/state/nguon_{draft_id}.json

Finn DA tim nguon san va ghi vao tep tren — day la ket qua research cua cau ay.
Ban dung lai bo nguon do, khong tu di tim. Quinn cung doc chinh tep nay de viet,
nho vay bai viet va tam anh cung noi ve mot thu.

Script lay anh tu chinh link goc VA tu cac bao khac dua cung tin, loc bo
logo/favicon/the thuong hieu, do kich thuoc that roi xep hang. Anh co bang so
hay bieu do duoc cong diem — do la thu doc gia muon nhin.

BUOC 2 — chon anh:
- Lay anh diem cao nhat lam anh chinh. Tai ve: /tmp/src_{draft_id}.png
- Neu con anh khac tu 40 diem tro len va NOI DUNG KHAC NHAU (bang benchmark,
  bieu do gia, so do kien truc...), tai them: /tmp/src_{draft_id}_2.png,
  _3.png... Toi da 4 anh. Nhieu anh la TOT, khong sao ca.
- Bo anh trung noi dung, bo anh chi la anh bia chung chung neu da co anh co so lieu.

BUOC 3 — neu KHONG tim duoc anh nao:
Dung lai. Bao dung mot cau: "Khong tim duoc anh that cho tin nay" kem link da thu.
KHONG tao the, KHONG ve SVG, KHONG chay card.py. Ong Chu se quyet dinh bo tin
hay tu dua anh vao.

BUOC 4 — dung the cho anh CHINH (chi khi buoc 2 co anh):
cd /home/donniechu/content-team && /home/donniechu/hermes-agent/venv/bin/python card.py \\
  --image /tmp/src_{draft_id}.png \\
  --title "<tieu de ngan, TOI DA 60 KY TU>" \\
  --subtitle "<mot cau tom tat y chinh, toi da 140 ky tu>" \\
  --via "{via}" \\
  --category "{category}" \\
  --category-right "<nhan phu ngan, vd: MA NGUON MO / BENCHMARK / M&A>" \\
  --ratio 1:1{co_brand} \\
  --out {out_png}

Cac anh phu KHONG dung the — giu nguyen ban goc, chi doi ten thanh
{out_png_goc}_2.png, _3.png... de buoc dang sau gui thanh album.

LUU Y:
- Anh co chu thich tieng Anh thi doc va dich sang tieng Viet de dung cho subtitle.
- Tieu de dung font don cach (JetBrains Mono) nen chiem nhieu be ngang. Qua 60
  ky tu se bi thu nho hoac cat bot. Viet NGAN va DAT.
- Tieu de va subtitle deu bang TIENG VIET CO DAU.
- Ket qua bat buoc: file {out_png} phai ton tai sau khi chay (tru truong hop
  buoc 3 — khong co anh that)."""


WRITER_BODY = """Bai goc: {title}
Link: {link}
Nguon: {source_note}
Via: {via}
Diem Finn cham: {score}/100 -- ly do: {score_reason}
(Dung ly do diem nay de viet phan "vi sao dang chu y" trong bai, dung tu y suy dien them)

Du kien (Finn da tom tat — CHI la diem khoi dau, KHONG du de viet):
{summary}

BUOC 1 — DOC TU LIEU THAT (bat buoc, lam truoc khi viet mot chu nao):
cd /home/donniechu/content-team && venv/bin/python tu_lieu.py \\
  --tieu-de "{title}" --link "{link}" --out /tmp/tulieu_{draft_id}.md \\
  --tu-nguon /home/donniechu/content-team/state/nguon_{draft_id}.json

Script boc chu tu bai goc VA tu cac bao khac dua cung tin, roi tach rieng muc
"Cau co so lieu". Tom tat cua Finn khong co con so nao — viet chay theo no thi
bai ra cung khong co so nao. Da gap that: tin co bang 11 dong benchmark, caption
viet ra 0 con so.

BUOC 2 — VIET. Day la bai SOCIAL, khong phai trang tai lieu:
nhanh, khach quan, ngan gon, xuc tich.

Nguoi doc luot qua trong vai giay. Ho can biet: chuyen gi, con so nao dang nho,
va co dang quan tam khong. Ho KHONG can bang thong so day du — cai do da co
tren the anh va o link.

KHONG dung em-dash (dau — hoac –) o bat cu dau. Dung dau phay, dau hai cham,
hoac tach thanh cau rieng. Script se tu choi caption co dau nay.

Bon y BAT BUOC co, moi y mot cau la du:
- Chuyen gi vua xay ra, kem SO quan trong nhat
- So sanh: hon hay kem cai gi, cach biet bao nhieu. Neu nguon co noi cho THUA
  thi phai noi — bo di la thien lech, khong con khach quan
- Han che hoac dieu kien kem theo, neu nguon co noi
- Vi sao dang chu y (dung ly do Finn cham diem)

Do dai: tan dung TOI DA 1024 ky tu, do la gioi han chu thich anh cua Telegram.
Vua trong muc do thi anh va chu di chung MOT tin nhan, doc gia thay ca hai cung
luc. Vuot qua la Telegram tach lam hai, anh mot noi chu mot noi.

Nham 800-1000 ky tu. Ngan gon nam o CACH VIET chu khong o viec cat bot y: moi
cau phai mang mot thong tin moi, khong cau nao lap lai cau truoc.

YEU CAU KY THUAT:
- Toi da 900 ky tu, HTML Telegram (chi <b> <i> <code>), dung cau truc SOUL.
- Ghi caption ra file tam /tmp/caption_{draft_id}.txt (CHI caption, khong kem gi khac).
- Tu kiem truoc khi ghep draft:
    cd /home/donniechu/content-team && venv/bin/python caption_check.py \\
      --caption-file /tmp/caption_{draft_id}.txt --tu-lieu /tmp/tulieu_{draft_id}.md
- Ghep draft bang lenh sau — script tu dien source_url / category / via / duong dan anh,
  BAN KHONG CAN go lai nhung gia tri do:
    cd /home/donniechu/content-team && venv/bin/python draft_write.py {draft_id} --caption-file /tmp/caption_{draft_id}.txt --tu-lieu /tmp/tulieu_{draft_id}.md
- Day vao hang duyet:
    cd /home/donniechu/content-team && venv/bin/python approve_service.py push {draft_id}
- KHONG tu dang len channel."""


def kanban_create(title, assignee, body, parent=None):
    env = dict(os.environ, HERMES_HOME=HERMES_HOME)
    args = [str(HERMES_PY), "-m", "hermes_cli.main", "kanban", "create", title,
            "--assignee", assignee, "--max-runtime", "25m", "--json",
            "--body", body]
    if parent:
        args += ["--parent", parent]
    r = subprocess.run(args, cwd=str(Path.home() / "hermes-agent"),
                        env=env, capture_output=True, text=True, timeout=60)
    if r.returncode != 0:
        return None, (r.stderr[-300:] or r.stdout[-300:])
    try:
        return json.loads(r.stdout)["id"], None
    except Exception:                                        # noqa: BLE001
        return None, r.stdout[-300:]


def write_meta(draft_id, item, out_png):
    """Ghi san metadata cho draft — writer khoi phai go lai bang tay.

    Nhung gia tri nay Finn da quyet tu luc quet; bat LLM go lai chi tao co hoi
    go sai. draft_write.py se doc file nay khi ghep draft cuoi cung.
    """
    meta = {
        "source_url": item["link"],
        "category": item.get("category", "CONG CU"),
        "via": item.get("via", ""),
        "image": out_png,
        "title": item["title"],
        "score": item.get("score"),
        "score_reason": item.get("score_reason", ""),
    }
    DRAFTS.mkdir(parents=True, exist_ok=True)
    (DRAFTS / (draft_id + ".meta.json")).write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")


def create_pair(item, vai_anh="illustrator", brand="donniechublog"):
    draft_id = slugify(item["title"], "item-" + str(item["index"]))
    out_png = str(DRAFTS / (draft_id + ".png"))
    out_json = str(DRAFTS / (draft_id + ".json"))
    write_meta(draft_id, item, out_png)

    # BUOC RESEARCH — thuoc khau cua Finn, chay ngay khi Ong Chu chon tin.
    # Tim nguon la viec research, khong phai viec cua nguoi dung anh hay nguoi
    # viet chu. Lam mot lan o day thay vi de Iris va Quinn moi ben tu tim: khoi
    # tra cuu hai lan, va quan trong hon la ca hai cung doc MOT bo nguon nen bai
    # viet giai thich dung nhung gi doc gia nhin thay tren tam anh.
    nguon_path = STATE_DIR / f"nguon_{draft_id}.json"
    try:
        subprocess.run(
            [str(ROOT / "venv/bin/python"), str(ROOT / "nguon_bai.py"),
             "--tieu-de", item["title"], "--link", item["link"],
             "--out", str(nguon_path)],
            capture_output=True, text=True, timeout=180, cwd=str(ROOT))
    except Exception as e:                                   # noqa: BLE001
        print(f"[research] khong tim duoc nguon: {type(e).__name__}: {e}")

    illu_body = ILLU_BODY.format(
        source_note=item.get("source_note", ""), link=item["link"],
        via=item.get("via", ""), title=item["title"],
        summary=item.get("summary_vi", ""),
        image_url=item.get("image_url") or "khong co",
        out_png=out_png, out_png_goc=out_png[:-4],
        category=item.get("category", "CONG CU"), draft_id=draft_id,
        brand=brand, co_brand=("" if brand == "donniechublog" else f" --brand {brand}"))
    illu_id, err = kanban_create("Anh: " + item["title"], vai_anh, illu_body)
    if err:
        return None, "Loi tao task anh: " + err

    writer_body = WRITER_BODY.format(
        title=item["title"], link=item["link"],
        source_note=item.get("source_note", ""), via=item.get("via", ""),
        score=item.get("score", "?"),
        score_reason=item.get("score_reason", ""),
        summary=item.get("summary_vi", ""), out_png=out_png,
        out_json=out_json, category=item.get("category", "CONG CU"),
        draft_id=draft_id)
    writer_id, err = kanban_create("Bai: " + item["title"], "writer",
                                    writer_body, parent=illu_id)
    if err:
        return None, "Loi tao task viet: " + err
    return (illu_id, writer_id), None


def handle_chat(token, group, msg, thread_id, text):
    """Chuyen tin nhan toi dung agent theo topic, giu mach hoi thoai.

    Gateway cua hermes da tat Telegram (khong the cung long-poll mot token voi
    tien trinh nay), nen day la duong duy nhat de nhan voi LLM qua Telegram.
    Bu lai: dinh tuyen duoc theo topic, moi topic mot phien rieng.
    """
    topics = {}
    tp = STATE_DIR / "topics.json"
    if tp.exists():
        topics = json.loads(tp.read_text(encoding="utf-8"))
    profile, session = chat_router.route(thread_id, topics)

    who = profile or "trợ lý"
    call(token, "sendMessage", chat_id=group,
         **({"message_thread_id": thread_id} if thread_id else {}),
         text=f"⏳ Đang chuyển cho <b>{who}</b>…", parse_mode="HTML")

    out, err = chat_router.ask(profile, session, text)
    reply = ("⚠️ " + err) if err else chat_router.clean(out)
    call(token, "sendMessage", chat_id=group,
         **({"message_thread_id": thread_id} if thread_id else {}),
         text=reply, disable_web_page_preview=True)


def handle_message(token, group, scout_thread, msg):
    if msg.get("from", {}).get("is_bot"):
        return
    if msg.get("chat", {}).get("id") != int(group):
        return
    text = (msg.get("text") or "").strip()
    if not text:
        return
    thread_id = msg.get("message_thread_id")

    # So trong topic cua MOT VAI DI TIM TIN = lenh chon tin. Moi thu khac la
    # hoi thoai. Finn, Nova, Vera deu duoc — cung mot cach tra loi.
    vai = vai_cua_topic(thread_id)
    lenh = doc_lenh_chon(text) if vai in MANIFEST_THEO_TOPIC else None
    is_pick = lenh is not None
    if not is_pick:
        # Chay nen: mot lan goi agent co the toi 10 phut, khong duoc de nghen
        # vong lap poll (nut Duyet/Bo phai bam duoc bat cu luc nao).
        threading.Thread(target=handle_chat, daemon=True,
                         args=(token, group, msg, thread_id, text)).start()
        return

    manifest_path = latest_manifest(vai)
    if not manifest_path:
        call(token, "sendMessage", chat_id=group, message_thread_id=thread_id,
             text="Chưa có danh sách tin nào để chọn trong topic này.")
        return

    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    items = {it["index"]: it for it in data.get("items", [])}
    lines = []
    changed = False
    for n, vai_anh, brand in lenh:
        it = items.get(n)
        if not it:
            lines.append("#" + str(n) + ": không tìm thấy")
            continue
        if it.get("picked"):
            lines.append("#" + str(n) + ": đã chọn trước đó")
            continue
        ids, err = create_pair(it, vai_anh=vai_anh, brand=brand)
        if err:
            lines.append("#" + str(n) + ": lỗi — " + err)
            continue
        it["picked"] = True
        it["vai_anh"], it["brand"] = vai_anh, brand
        changed = True
        ten_hien = "Ethan" if vai_anh == "ethan" else "Iris"
        lines.append(f"#{n}: {ten_hien} dựng ảnh ({brand}) — task {ids[0]} + viết {ids[1]}")

    if changed:
        manifest_path.write_text(json.dumps(data, ensure_ascii=False, indent=2),
                                  encoding="utf-8")
    call(token, "sendMessage", chat_id=group, message_thread_id=thread_id,
         text="<b>Kết quả chọn:</b>\n" + "\n".join(lines), parse_mode="HTML")


# ---------- vong lap chinh ----------

def loop():
    token, channel, group = load_secrets()
    scout_thread = scout_thread_id()
    offset = int(OFFSET.read_text()) if OFFSET.exists() else 0
    print("[approve_service] chay, offset=" + str(offset) +
          ", scout_thread=" + str(scout_thread), flush=True)
    while True:
        try:
            r = call(token, "getUpdates", offset=offset, timeout=50,
                     allowed_updates=["callback_query", "message"])
            for u in r.get("result", []):
                offset = u["update_id"] + 1
                if "callback_query" in u:
                    handle_callback(token, channel, u["callback_query"])
                elif "message" in u:
                    handle_message(token, group, scout_thread, u["message"])
            OFFSET.parent.mkdir(parents=True, exist_ok=True)
            OFFSET.write_text(str(offset))
        except Exception as e:                              # noqa: BLE001
            print("[approve_service] loi: " + type(e).__name__ + ": " + str(e),
                  flush=True)
            time.sleep(5)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "push":
        tok, _ch, grp = load_secrets()
        draft_id = sys.argv[2]
        # Dinh tuyen topic theo loai noi dung: teaser ve topic Jean, tin tuc
        # ve topic Quinn. Tham so thu 3 (neu co) van ghi de duoc.
        thread = None
        tp = STATE_DIR / "topics.json"
        if tp.exists():
            topics = json.loads(tp.read_text(encoding="utf-8"))
            dpath = DRAFTS / (draft_id + ".json")
            category = ""
            if dpath.exists():
                try:
                    category = json.loads(
                        dpath.read_text(encoding="utf-8")).get("category", "")
                except Exception:                            # noqa: BLE001
                    pass
            key = "teaser" if category.upper() == "TEASER" else "writer"
            thread = topics.get(key)
        if len(sys.argv) > 3:
            thread = int(sys.argv[3])
        res = draft_push(tok, grp, draft_id, thread_id=thread)
        print("day ban nhap -> topic " + str(thread) + " | " +
              ("OK" if res.get("ok") else str(res.get("description"))))
    else:
        loop()
