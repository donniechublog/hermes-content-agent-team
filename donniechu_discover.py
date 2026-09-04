#!/usr/bin/env python3
"""Phat hien bai moi/chua dang tren donniechu.com, tao task kanban cho Mai.

Tat dinh, khong dung LLM. So sanh sitemap voi so da-dang (state/donniechu_posted.json),
tao mot task kanban moi cho moi bai chua xu ly, danh dau ngay sau khi tao task
de chay lan lai khong bi trung.

Hai che do:
  --daily     (mac dinh) chi xu ly bai MOI xuat hien tu lan chay truoc, khong
              gioi han so luong (thuong 0-1 bai/ngay).
  --backfill N  xu ly toi da N bai CU con ton trong kho 824 bai chua dang,
              theo dung thu tu xuat hien trong sitemap. Dung de nhap kho
              tu tu, khong don het mot luc.
"""
import argparse
import json
import subprocess
from pathlib import Path

import os

import httpx
from bs4 import BeautifulSoup

import env_load

ROOT = Path.home() / "content-team"
LEDGER = env_load.state_dir() / "donniechu_posted.json"
SITEMAP = "https://donniechu.com/sitemap.xml"
HERMES_PY = Path.home() / "hermes-agent" / "venv" / "bin" / "python"
HERMES_HOME = os.environ.get("HERMES_HOME", str(Path.home() / ".hermes"))


def fetch_article_urls() -> list:
    r = httpx.get(SITEMAP, timeout=30, follow_redirects=True)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "xml")
    urls = []
    for loc in soup.find_all("loc"):
        u = loc.get_text(strip=True)
        if "/posts/" in u and u.rstrip("/") != "https://www.donniechu.com/posts":
            urls.append(u)
    # loai trung, giu thu tu xuat hien dau tien trong sitemap
    seen, ordered = set(), []
    for u in urls:
        if u not in seen:
            seen.add(u)
            ordered.append(u)
    return ordered


def load_ledger() -> dict:
    if LEDGER.exists():
        return json.loads(LEDGER.read_text(encoding="utf-8"))
    return {}


def save_ledger(ledger: dict):
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    LEDGER.write_text(json.dumps(ledger, ensure_ascii=False, indent=2),
                      encoding="utf-8")


def create_task(url: str) -> tuple:
    body = (
        "Bai tren donniechu.com can viet teaser.\n\n"
        "URL: {}\n\n"
        "Lam dung quy trinh trong SOUL cua ban: chay article_extract.py lay du "
        "lieu, viet teaser 500-800 tu bao quat het outline, xin emoji tu "
        "emoji_deck.py (KHONG tu bia), lay 2 anh dau tien lam album, ghi draft "
        "JSON, roi push vao hang duyet."
    ).format(url)
    env = {"HERMES_HOME": HERMES_HOME}
    import os
    full_env = dict(os.environ, **env)
    args = [str(HERMES_PY), "-m", "hermes_cli.main", "kanban", "create",
            "Teaser: " + url.rsplit("/", 1)[-1],
            "--assignee", "teaser", "--max-runtime", "20m",
            "--idempotency-key", "teaser-" + url.rsplit("/", 1)[-1],
            "--body", body, "--json"]
    r = subprocess.run(args, cwd=str(Path.home() / "hermes-agent"),
                        env=full_env, capture_output=True, text=True, timeout=60)
    if r.returncode != 0:
        return None, (r.stderr[-300:] or r.stdout[-300:])
    try:
        return json.loads(r.stdout)["id"], None
    except Exception:                                        # noqa: BLE001
        return None, r.stdout[-300:]


def main():
    ap = argparse.ArgumentParser(description="Phat hien bai donniechu.com cho Mai")
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--seed", action="store_true",
                   help="Chay MOT LAN DUY NHAT truoc khi bat cron: danh dau "
                        "toan bo bai hien co la 'ton kho cho backfill', "
                        "KHONG tao task nao. Sau buoc nay, che do daily chi "
                        "con thay bai thuc su moi xuat ban sau moc nay.")
    g.add_argument("--backfill", type=int, metavar="N",
                   help="Xu ly toi da N bai trong kho ton (da --seed truoc do)")
    a = ap.parse_args()

    all_urls = fetch_article_urls()
    ledger = load_ledger()

    if a.seed:
        added = 0
        for u in all_urls:
            if u not in ledger:
                ledger[u] = {"status": "queued_backlog", "task_id": None}
                added += 1
        save_ledger(ledger)
        print("[seed] danh dau {} bai vao kho ton (khong tao task nao). "
              "Tu gio 'daily' chi bat bai xuat ban sau moc nay.".format(added))
        return

    if a.backfill:
        backlog = [u for u, v in ledger.items()
                  if v.get("status") == "queued_backlog"]
        batch = backlog[:a.backfill]
        print("[backfill] con {} bai trong kho ton, xu ly {} bai lan nay".format(
            len(backlog), len(batch)))
    else:
        # daily: chi bat url CHUA TUNG thay (khong co trong ledger duoi bat
        # ky trang thai nao) -- tuc bai xuat ban sau lan --seed.
        batch = [u for u in all_urls if u not in ledger]
        print("[daily] {} bai moi phat hien".format(len(batch)))

    if not batch:
        print("Khong co bai nao can xu ly.")
        return

    ok, fail = 0, 0
    for url in batch:
        task_id, err = create_task(url)
        if err:
            print("  LOI ({}): {}".format(url, err))
            fail += 1
            continue
        ledger[url] = {"status": "posted", "task_id": task_id}
        save_ledger(ledger)
        print("  OK  {} -> {}".format(url, task_id))
        ok += 1

    print("Hoan tat: {} task tao thanh cong, {} loi.".format(ok, fail))


if __name__ == "__main__":
    main()
