#!/usr/bin/env python3
"""LOW-321 (20/09/2026) — nguon cua Finn: bo arXiv, them HF Papers + Lobste.rs.

Ong Chu chot: arXiv listing thô khong co tin hieu ai quan tam, ma bo cham cua
Finn song bang "moi + lan" — nen truoc day moi bai arXiv phai duoc cham mot
diem lan GIA (10/20). Thay bang hai nguon co diem THAT:
  - Hugging Face Papers: chinh nhung bai arXiv do nhung da qua binh chon.
  - Lobste.rs tag `ai`: cung co che HN, cong dong hep hon.

Cai de hong nhat va vi sao khoa o day:
  1. TUOI cua HF Papers phai tinh theo `submittedOnDailyAt` (luc len danh sach
     daily). Do that 20/09: danh sach daily mang bai arXiv dang tu 74h toi 386h
     truoc, ma cua so cua Finn la 72h — lay `paper.publishedAt` la vut gan sach
     nguon nay ma khong ai thay.
  2. Link phai la arxiv.org/abs/<id>: chong trung (`seen_keys`) va `NO_HAS_IMAGE`
     deu doc duong do.
  3. Lobste.rs tra moc thoi gian co offset that ("-05:00"), khong phai "Z".

Chay:  venv/bin/python tests/test_low321_finn_sources.py
"""
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import scan_sources as ss  # noqa: E402


def _iso(gio_truoc: float, tz=timezone.utc) -> str:
    return (datetime.now(timezone.utc) - timedelta(hours=gio_truoc)).astimezone(tz).isoformat()


def _hf(**them):
    """Mot muc daily_papers, khoa y het ban that (do 20/09/2026)."""
    p = {"id": "2609.17496", "title": "Verifiable Social Reasoning for LLM Assistants",
         "upvotes": 33, "publishedAt": _iso(122), "submittedOnDailyAt": _iso(50)}
    p.update(them.pop("paper", {}))
    d = {"paper": p, "numComments": 3, "publishedAt": _iso(126)}
    d.update(them)
    return d


def _lob(**them):
    d = {"title": "Laya — 33ms Multilingual System 1 Decision Engine",
         "url": "https://laya.convaiinnovations.com/", "score": 3, "comment_count": 3,
         "created_at": _iso(9, timezone(timedelta(hours=-5))),
         "comments_url": "https://lobste.rs/s/ojukrw/laya_33ms",
         "short_id_url": "https://lobste.rs/s/ojukrw"}
    d.update(them)
    return d


# ------------------------------------------------------------ HF Papers
def test_hf_age_follows_daily_list_not_arxiv_publish_date():
    """Bai arXiv dang 122h truoc nhung MOI len daily 50h truoc: phai GIU."""
    ra = ss.hf_papers_items([_hf()])
    assert len(ra) == 1, ra
    assert 49 <= ra[0]["age_hours"] <= 51, ra[0]["age_hours"]


def test_hf_drops_item_off_the_daily_list_for_too_long():
    ra = ss.hf_papers_items([_hf(paper={"submittedOnDailyAt": _iso(ss.MAX_AGE_HOURS + 2)})])
    assert ra == []


def test_hf_link_is_arxiv_so_dedup_and_image_rules_still_work():
    ra = ss.hf_papers_items([_hf()])[0]
    assert ra["link"] == "https://arxiv.org/abs/2609.17496"
    assert ra["discussion"] == "https://huggingface.co/papers/2609.17496"
    assert ss.NO_HAS_IMAGE.search(ra["link"]), "van phai bi coi la bai khong co anh"


def test_hf_carries_real_vote_numbers():
    ra = ss.hf_papers_items([_hf()])[0]
    assert (ra["points"], ra["comments"]) == (33, 3)
    assert ra["source"] == "huggingface-papers"


def test_hf_skips_broken_entries_without_raising():
    xau = [{}, {"paper": {}}, {"paper": {"id": "", "title": "x"}},
           {"paper": {"id": "1", "title": "x", "submittedOnDailyAt": "khong-phai-ngay"}}]
    assert ss.hf_papers_items(xau) == []
    assert ss.hf_papers_items(None) == []


# ------------------------------------------------------------ Lobste.rs
def test_lobsters_reads_offset_timestamp_and_scores():
    ra = ss.lobsters_items([_lob()])
    assert len(ra) == 1, ra
    it = ra[0]
    assert 8 <= it["age_hours"] <= 10, it["age_hours"]
    assert (it["points"], it["comments"]) == (3, 3)
    assert it["source"] == "lobsters" and it["via"]


def test_lobsters_discussion_only_post_falls_back_to_its_own_page():
    it = ss.lobsters_items([_lob(url="")])[0]
    assert it["link"].startswith("https://lobste.rs/")


def test_lobsters_drops_old_and_broken():
    assert ss.lobsters_items([_lob(created_at=_iso(ss.MAX_AGE_HOURS + 1))]) == []
    assert ss.lobsters_items([{"title": ""}, {}, None]) == []


# ------------------------------------------------------------ bo arXiv / doi sub
def test_arxiv_branch_is_gone():
    src = (ROOT / "scan_sources.py").read_text(encoding="utf-8")
    assert not hasattr(ss, "fetch_arxiv") and not hasattr(ss, "ARXIV_CATS")
    assert "score_spread\"] = 10" not in src, "khong con cham diem lan GIA cho arXiv"


def test_subs_swapped_image_branch_for_agents():
    assert "StableDiffusion" not in ss.SUBS
    assert "AI_Agents" in ss.SUBS
    assert ss.SUBS[:4] == ["MachineLearning", "LocalLLaMA", "singularity", "OpenAI"]


if __name__ == "__main__":
    from tam import chay_tat_ca          # runner chung: bat ca Exception, luon in N/M (E-r2-2)
    chay_tat_ca(globals())
