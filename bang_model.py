#!/usr/bin/env python3
"""Ban dang ky BANG XEP HANG cua Nova — MOT dong cho MOT bang.

Vi sao la mot tep rieng: truoc 07/09/2026 them mot bang phai khai o SAU cho,
o hai tep khac nhau:

  1. `scan_models.ARENA_BOARDS`  (chi bang arena)
  2. `scan_models.KHOA_BANG`     (ban ke khai de main() tu doi chieu)
  3. `scan_models.NHAN_BANG`     (nhan ngan cho muc "leo hang" / "nguon hong")
  4. khoi `bang_so` trong `scan_models.main`
  5. mot loi goi `_in_bang` rieng trong `scan_models._in_bao_cao`
  6. `bat_buoc.LINK_BANG`        (link cho muc BAT BUOC)

Va do la kieu loi KHONG BAO GI CA — script van chay, bao cao van in, chi la
Nova mat mot bang hoac muc BAT BUOC ra link rong. Chinh ma nguon da ghi lai hai
lan bi dinh: "danh sach bang bi chep LAM HAI o hai cho... them bang ma quen mot
cho thi no khong bao gio sinh duoc tin 'leo hang'" (06/09), va `test_bang_nova`
sinh ra sau khi mo tu 12 len 20 bang lam mat nhan va mat link.

Nay 1, 2, 3, 5, 6 deu dan xuat tu day. Rieng 4 (`bang_so`) van viet tay vi moi
fetcher tra ve mot hinh khac nhau — nhung `main()` tu doi chieu
`set(bang_so) ^ set(KHOA_BANG)` nen quen mot bang o do thi co dong canh bao.

Tep nay KHONG import gi cua du an: ca `scan_models` lan `bat_buoc` deu doc no,
ma `scan_models` da import `bat_buoc`.

THU TU trong `BANG` la thu tu IN RA bao cao.
"""
from typing import Callable, NamedTuple

ARENA = "https://arena.ai/leaderboard/"
AA = "https://artificialanalysis.ai/leaderboards/models"
SWE = "https://www.swebench.com/"


class Bang(NamedTuple):
    """Mot bang xep hang.

    khoa      — khoa trong `bang_so`, trong moc state, va trong muc BAT BUOC
    nhan      — nhan NGAN, dung o muc "vua leo hang" va "nguon khong lay duoc"
    tieu_de   — tieu de DAY DU khi in ca bang
    link      — link bang, de muc BAT BUOC khong ra link rong
    nguon     — lay hang tu dau trong tep ket qua: arena | aa | media | top
    duong_dan — rieng bang arena: duong dan API
    ket_khoa  — khoa trong tep ket qua neu khac `khoa`
    diem_hau  — hau to sau cot diem khi in ("%" hoac rong)
    them      — ham nhan mot hang, tra chuoi in them mot cot
    in_bang   — False neu bang do in theo khuon RIENG, khong qua `_in_bang`
    """
    khoa: str
    nhan: str
    tieu_de: str
    link: str
    nguon: str
    duong_dan: str = ""
    ket_khoa: str = ""
    diem_hau: str = ""
    them: Callable = None
    in_bang: bool = True


BANG = (
    # --- 7 bang arena.ai -----------------------------------------------------
    Bang("text", "van ban", "VAN BAN (arena.ai)", ARENA + "text", "arena", "text"),
    Bang("webdev", "webdev", "CODE WEBDEV (arena.ai)", ARENA + "code/webdev",
         "arena", "code/webdev"),
    Bang("vision", "vision", "VISION (arena.ai)", ARENA + "vision", "arena", "vision"),
    Bang("search", "search", "SEARCH (arena.ai)", ARENA + "search", "arena", "search"),
    Bang("image", "tao anh", "TAO ANH (arena.ai)", ARENA + "text-to-image",
         "arena", "text-to-image"),
    Bang("image_edit", "sua anh", "SUA ANH (arena.ai)", ARENA + "image-edit",
         "arena", "image-edit"),
    Bang("video", "tao video", "TAO VIDEO (arena.ai)", ARENA + "text-to-video",
         "arena", "text-to-video"),
    # --- artificialanalysis ---------------------------------------------------
    Bang("tri_tue", "tri tue AA",
         "TRI TUE (artificialanalysis intelligence index)", AA, "aa"),
    # Bang agentic: so DA co san trong payload AA tu lau, chua bao gio duoc xep
    # hang nen so_hang() khong bat duoc "leo hang agentic". Them tu 06/09/2026.
    Bang("agentic", "agentic AA",
         "AGENTIC (artificialanalysis agentic index)", AA, "aa"),
    # --- benchmark rieng ------------------------------------------------------
    Bang("eci", "Epoch ECI",
         "EPOCH ECI (ghep ~50 benchmark bang IRT, co khoang tin cay)",
         "https://epoch.ai/data/ai-benchmarking-dashboard", "top",
         them=lambda r: f"[{r.get('ci_thap')}-{r.get('ci_cao')}]"),
    Bang("hle", "HLE", "HUMANITY'S LAST EXAM (cau hoi do chuyen gia PhD dat)",
         "https://scale.com/leaderboard/humanitys_last_exam", "top", diem_hau="%"),
    Bang("arcagi", "ARC-AGI-2", "ARC-AGI-2 (bai CHUA TUNG THAY, khong hoc thuoc duoc)",
         "https://arcprize.org/leaderboard", "top", diem_hau="%",
         them=lambda r: (f"${r['gia_moi_bai']:.2f}/bai" if r.get("gia_moi_bai") else "")),
    Bang("tbench", "Terminal-B",
         "TERMINAL-BENCH 4.0 (agent go lenh trong container that)",
         "https://www.tbench.ai/leaderboard", "top", diem_hau="%",
         them=lambda r: str(r.get("agent") or "")[:16]),
    Bang("swebench", "SWE-bench", "SWE-BENCH VERIFIED (moi he thong agent)",
         SWE, "top", diem_hau="%"),
    Bang("swe_bash", "SWE-b bash",
         "SWE-BENCH VERIFIED — CHI BASH (so sanh model that)", SWE, "top", diem_hau="%"),
    Bang("swe_da_ngon_ngu", "SWE-b da nn",
         "SWE-BENCH DA NGON NGU (C/C++/Go/Java/PHP/Ruby/Rust)", SWE, "top", diem_hau="%"),
    Bang("opencompass", "CompassBench",
         "COMPASSBENCH (de DONG cua OpenCompass, phan lon lab TQ)",
         "https://rank.opencompass.org.cn/home", "top",
         them=lambda r: "mo nguon" if r.get("mo_nguon") else ""),
    Bang("livebench", "LiveBench", "LIVEBENCH", "https://livebench.ai/", "top"),
    # --- media (artificialanalysis) -------------------------------------------
    Bang("tts", "giong doc", "GIONG DOC — TTS (artificialanalysis, Elo)",
         "https://artificialanalysis.ai/text-to-speech", "media"),
    Bang("stt", "nghe chep", "NGHE CHEP — STT (artificialanalysis, do chinh xac)",
         "https://artificialanalysis.ai/speech-to-text", "media", diem_hau="%"),
    Bang("i2v", "anh->video", "ANH -> VIDEO (artificialanalysis, Elo)",
         "https://artificialanalysis.ai/video/leaderboard/image-to-video", "media"),
    # --- hai bang co khuon in RIENG ------------------------------------------
    # coding AA: khong in ca bang, muc "TOP CODING" o tren da la no. Van phai
    # co mat o day vi VAN duoc so hang (GPT-6 Astra vao #8 coding ngay ra mat
    # ma khong ai hay — do la ly do no vao bo nho tu 04/09/2026).
    Bang("coding", "coding AA", "CODING (artificialanalysis)", AA, "aa", in_bang=False),
    # openrouter usage: in kem cot token/ngay va % doi, khong vua khuon chung.
    Bang("openrouter", "OpenRouter usage", "OPENROUTER USAGE",
         "https://openrouter.ai/rankings", "top", ket_khoa="openrouter_usage",
         in_bang=False),
)

KHOA_BANG = tuple(b.khoa for b in BANG)
NHAN_BANG = {b.khoa: b.nhan for b in BANG}
NHAN_BANG["hf"] = "HuggingFace"          # khong phai bang, nhung co muc BAT BUOC
SO_BANG = len(BANG)
LINK_BANG = {b.khoa: b.link for b in BANG}
ARENA_BOARDS = tuple((b.khoa, b.duong_dan, b.tieu_de.replace(" (arena.ai)", ""))
                     for b in BANG if b.nguon == "arena")


def hang_va_ngay(ket: dict, b: Bang) -> tuple:
    """Lay (rows, ngay) cua mot bang tu tep ket qua cua `scan_models`.

    Bon hinh khac nhau vi bon nguon khac nhau, va do la ly do ban dang ky phai
    ghi `nguon` chu khong doan duoc tu khoa."""
    if b.nguon == "arena":
        return (ket.get("bang_xep_hang") or {}).get(b.khoa), None
    if b.nguon == "aa":
        return (ket.get("cham_diem") or {}).get(f"bang_{b.khoa}_goc"), None
    if b.nguon == "media":
        return (ket.get("media") or {}).get(b.khoa), None
    o = ket.get(b.ket_khoa or b.khoa) or {}
    return o.get("rows"), o.get("ngay")
