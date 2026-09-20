#!/usr/bin/env python3
"""replay.py — GHI / PHAT LAI hai canh khong tat dinh cua engine anh (LOW-312).

Cac ham hang F cua engine (`vision.classify`, `download_and_filter`,
`_round_capture_source`, `_round_brand`) va cac module 0% (`capture_chart`,
`capture_page`, `prepare/browser`) co chung mot ly do khong test duoc: chung goi
LLM vision va lai Chromium tren trang that. Viec dau tien ghi tu 07/09/2026 ma
chua bao gio co trong repo: ghi lai vai lan chay THAT roi phat lai trong test.

Hai canh, hai co che:

1. VISION — `VisionReplay` thay `prepare.vision._call_router`.
   Ban ghi la cap (cau hoi, cau tra loi) THAT, lay tu `vision_raw` ma engine da
   ghi san trong `state/<brand>/prepare/<draft>/manifest.json` tren may chu:
       venv/bin/python tests/replay.py harvest-vision <manifest.json> <out.json> [A1,A2...]
   Repo KHONG giu anh cua ben thu ba (ban quyen + nang repo): test dung anh THE
   CHO (`stand_in_image`) cung kich thuoc, danh dau so thu tu vao pixel (0,0);
   luc phat lai, `VisionReplay` doc pixel do de biet anh nao dang duoc hoi. Anh
   that (chay `record=True` tren may chu, noi co router) thi khop theo sha256.
   Khong co ban ghi -> `ReplayMiss` + ghi vao `.misses`: `description_image` nuot
   moi Exception thanh "CHUA AI NHIN", nen test PHAI khang dinh `misses == []`.

2. PLAYWRIGHT — `ReplayBrowserSession` thay `browser_session.BrowserSession`.
   Chromium THAT, mang gia: `context.route_from_har(...)` phat lai moi request
   tu tep HAR, request khong co trong HAR bi huy (khong bao gio ra mang).
       venv/bin/python tests/replay.py record-har <url> <out.har> [--no-js]
   Trang trong HAR la noi dung cua ben thu ba: chi ghi trang co giay phep mo
   (Wikipedia CC BY-SA, arXiv) va giu nho (`RECORD_BLOCK` bo video/font/ads).

Khong phai tep test (ten khong bat dau bang test_).
"""
import base64
import hashlib
import io
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "prepare"))

GOLDEN = Path(__file__).resolve().parent / "golden"
MARK_BLUE = 77                      # pixel (0,0) = (id // 256, id % 256, MARK_BLUE)


class ReplayMiss(LookupError):
    """Khong co ban ghi cho lan goi nay."""


# =========================================================================
# 1. vision
# =========================================================================
def stand_in_image(path, number: int, w: int, h: int, color=(120, 140, 160)):
    """Anh the cho: dung kich thuoc anh that, mau phang, so thu tu nam o pixel
    (0,0). PNG khong mat du lieu nen pixel do song qua moi lan ghi/doc."""
    from PIL import Image
    im = Image.new("RGB", (w, h), color)
    im.putpixel((0, 0), (number // 256, number % 256, MARK_BLUE))
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    im.save(path, format="PNG")
    return Path(path)


def _question_key(question: str) -> str:
    return hashlib.sha256(question.encode("utf-8")).hexdigest()[:16]


def _image_identity(data: bytes) -> tuple:
    """(sha256 cua byte, so thu tu the cho hoac None)."""
    sha = hashlib.sha256(data).hexdigest()
    try:
        from PIL import Image
        r, g, b = Image.open(io.BytesIO(data)).convert("RGB").getpixel((0, 0))
    except Exception:                                        # noqa: BLE001
        return sha, None
    return sha, (r * 256 + g if b == MARK_BLUE else None)


class _Response:
    def __init__(self, text: str):
        self._data = text.encode("utf-8")

    def read(self):
        return self._data


class VisionReplay:
    """Thay cho `vision._call_router(req)`.

    `recordings`: danh sach {"number", "question", "answer", "image_sha256"?}.
    `record=True` (chi noi co router): goi that, them ban ghi, `save()` de luu."""

    def __init__(self, recordings, record=False, real_call=None):
        self.recordings = list(recordings)
        self.record, self.real_call = record, real_call
        self.calls, self.misses, self.drifted = [], [], []

    @classmethod
    def load(cls, path, **kw):
        return cls(json.loads(Path(path).read_text(encoding="utf-8"))["recordings"], **kw)

    def save(self, path, source=""):
        Path(path).write_text(json.dumps({"source": source, "recordings": self.recordings},
                                         ensure_ascii=False, indent=1) + "\n", encoding="utf-8")

    def _find(self, question, sha, number):
        """Khop theo ANH (sha256 hoac so the cho). Cau hoi chi de phat hien TROI:
        prompt vision doi gan nhu hang ngay (LOW-201, 219, 273...), khop cung theo
        cau hoi thi moi lan sua prompt la ca bo ban ghi thanh vo dung. Cau hoi
        khac ban ghi -> van phat lai, ghi vao `.drifted` de test nao can thi xet."""
        same = [r for r in self.recordings
                if r.get("image_sha256") == sha or (number is not None and r.get("number") == number)]
        if not same:
            return None
        qk = _question_key(question)
        exact = [r for r in same if _question_key(r["question"]) == qk]
        if not exact:
            self.drifted.append({"number": number, "question": question})
        return (exact or same)[0]

    def __call__(self, req, _ngu=None):
        body = json.loads(req.data.decode("utf-8"))
        parts = body["messages"][0]["content"]
        question = next(p["text"] for p in parts if p["type"] == "text")
        url = next(p["image_url"]["url"] for p in parts if p["type"] == "image_url")
        sha, number = _image_identity(base64.b64decode(url.split(",", 1)[1]))
        self.calls.append({"question": question, "number": number, "image_sha256": sha,
                           "model": body.get("model")})
        rec = self._find(question, sha, number)
        if rec is None and self.record and self.real_call:
            raw = self.real_call(req).read().decode("utf-8").strip()
            if raw.startswith("data:"):
                raw = raw.split("data: [DONE]")[0].strip()[5:].strip()
            rec = {"question": question, "image_sha256": sha,
                   "answer": json.loads(raw)["choices"][0]["message"]["content"]}
            self.recordings.append(rec)
        if rec is None:
            self.misses.append({"number": number, "image_sha256": sha, "question": question[:120]})
            raise ReplayMiss(f"khong co ban ghi vision cho anh so {number} / {sha[:12]} "
                             f"voi cau hoi {_question_key(question)}")
        return _Response(json.dumps({"choices": [{"message": {"content": rec["answer"]}}]}))

    def install(self, vision_module, environ):
        """Gan vao module vision; tra ham `undo()`. Dat OPENAI_API_KEY gia vi
        `description_image` bo cuoc som khi thieu key (khong bao gio toi router)."""
        old_call, old_key = vision_module._call_router, environ.get("OPENAI_API_KEY")
        vision_module._call_router = self
        environ["OPENAI_API_KEY"] = old_key or "replay-no-network"

        def undo():
            vision_module._call_router = old_call
            if old_key is None:
                environ.pop("OPENAI_API_KEY", None)
            else:
                environ["OPENAI_API_KEY"] = old_key
        return undo


def harvest_vision(manifest_path, ids=None) -> dict:
    """manifest.json THAT -> ban ghi. Khong chep anh: chi giu cau hoi/tra loi va
    nhung so do engine da ghi (de test dung the cho dung kich thuoc)."""
    import ast
    m = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    out = []
    for n, im in enumerate(m.get("images", []), 1):
        raw = im.get("vision_raw")
        if isinstance(raw, str):                 # manifest ghi repr(dict) o vai phien ban
            try:
                raw = ast.literal_eval(raw)
            except (ValueError, SyntaxError):
                raw = None
        if not isinstance(raw, dict) or (ids and im.get("id") not in ids):
            continue
        out.append({"number": n, "id": im.get("id"), "w": im.get("w"), "h": im.get("h"),
                    "source": im.get("source"), "model": raw.get("model"),
                    "question": raw["question"], "answer": raw["answer"],
                    "expected": {k: im.get(k) for k in (
                        "relevant", "description", "cluttered", "has_keywords", "subject_box",
                        "subject_kind", "empty_share", "printed_name")}})
    return {"source": f"{m.get('brand')}/{m.get('draft_id')} ({m.get('created_at')})",
            "title": m.get("title"), "recordings": out}


# =========================================================================
# 2. playwright
# =========================================================================
RECORD_BLOCK = ("**/*.{mp4,webm,woff,woff2,ttf,otf}", "**/*doubleclick*", "**/*googletag*",
                "**/*google-analytics*", "**/*analytics*")


def replay_session(har_path, record=False, block_scripts=False):
    """`BrowserSession` ma moi context deu phat lai (hoac ghi) tep HAR.

    Tra ve mot LOP CON tao tai cho de khong import playwright/browser_session
    luc import tep nay (test chi dung vision khong can Chromium)."""
    import contextlib

    from browser_session import ARGS_DEFAULT, BrowserSession

    class ReplayBrowserSession(BrowserSession):
        @contextlib.contextmanager
        def trang(self, args=ARGS_DEFAULT, **ctx):
            c = self.browser(args).new_context(**ctx)
            try:
                if record:
                    for pattern in RECORD_BLOCK + (("**/*.js", "**/load.php?*only=scripts*",
                                                    "**/load.php?*modules=startup*")
                                                   if block_scripts else ()):
                        c.route(pattern, lambda route: route.abort())
                    # .zip: playwright nen noi dung vao tep zip (nho hon ~3 lan so voi embed)
                    c.route_from_har(str(har_path), update=True,
                                     update_content="attach" if str(har_path).endswith(".zip") else "embed")
                else:
                    c.route_from_har(str(har_path), not_found="abort")
                yield c.new_page()
            finally:
                with contextlib.suppress(Exception):
                    c.close()                    # ghi HAR xay ra luc dong context

    return ReplayBrowserSession()


def _main(argv):
    if len(argv) >= 3 and argv[0] == "harvest-vision":
        ids = set(argv[3].split(",")) if len(argv) > 3 else None
        data = harvest_vision(argv[1], ids)
        Path(argv[2]).write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n",
                                 encoding="utf-8")
        print(f"{len(data['recordings'])} ban ghi -> {argv[2]}")
        return 0
    if len(argv) in (3, 4) and argv[0] == "record-har":
        import capture_page
        with replay_session(argv[2], record=True, block_scripts="--no-js" in argv) as session:
            ok = capture_page.capture(argv[1], Path(argv[2]).with_suffix(".record.png"), phien=session)
        Path(argv[2]).with_suffix(".record.png").unlink(missing_ok=True)
        print(f"ghi {'duoc' if ok else 'KHONG duoc'} -> {argv[2]} "
              f"({Path(argv[2]).stat().st_size // 1024} KB)")
        return 0 if ok else 1
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(_main(sys.argv[1:]))
