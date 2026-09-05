"""Khuon body cho cac task kanban ma approve_service.py sinh ra.

Tach rieng khoi approve_service.py: day la ~345 dong VAN BAN thuan (khong logic),
nam chung lam file dich vu phinh gap doi va kho doc. Sua loi van o mot cho —
approve_service import tu day.

Duong dan may chu KHONG hardcode nua: `{goc}` (thu muc content-team) va
`{hermes_py}` (python cua hermes-agent) duoc dien luc .format() tu ROOT/HERMES_PY
cua approve_service — doi ten user Unix khong con lam gay template im lang.
"""

ILLU_BODY = """Nguon: {source_note}
Link: {link}
Chu de: {title}
Tom tat: {summary}

NHIEM VU: dung MOT the anh (hero, mac dinh kieu quote/HOOK 4:5) cho tin nay,
thuong hieu {brand}. Phan CO HOC — tim anh that, tai, do, cat/ghep, cong chan,
dung the, gui Telegram, ban giao cho Miles — DA LA SCRIPT (da chay nen tu luc
Ong Chu chon tin). Viec cua ban chi co MOT: chon anh theo ma va viet cau hook.
Lam dung BA BUOC, khong them lenh nao khac.

BUOC 1 — doc ban chuan bi (anh da tai + xu ly san, tu lieu, khung spec):
cd {goc} && venv/bin/python ethan_chuan_bi.py {draft_id}

BUOC 2 — viet spec: ghi MOT tep JSON vao dung duong dan in o cuoi BUOC 1. Chi
dien MA ANH (A1, A2...) va CHU (hook, tagline, attrib; hoac title+kicker cho
kieu tran). KHONG tai anh, KHONG crop, KHONG mo tung anh, KHONG chay
anh_bai.py/card.py/gui_telegram.py tay. Chu tieng Viet co dau.

BUOC 3 — nop:
cd {goc} && venv/bin/python ethan_nop.py {draft_id}
Script tu ghep/cat theo spec, chay moi cong chan cua card.py, dung the, gui len
topic cua ban kem nut Duyet/Lam lai/Bo, ghi ban giao cho Miles. Bao [LOI] thi
sua DUNG cho do trong spec.json roi chay lai DUNG lenh nay (toi da 2 lan sua).
THIEU ANH THAT (duoi toi thieu, hoac anh chuan bi lac de): goi tool kanban_block voi ly do
ngan (anh nao bi loai, vi sao) — Ong Chu quyet tiep. TUYET DOI KHONG kanban_complete khi
chua gui album: "done" nghia la DA CO san pham tren topic. Khong tu che metadata kieu
"abort"; abort = kanban_block.
Xong: goi tool kanban_complete — summary = dong "Ket qua task", metadata = JSON o
dong "[metadata]" ma script in ra (Miles doc ban giao nay qua kanban). Khong sinh agent
con, khong gui lai anh. Ban chuan bi noi khong co anh that nao thi goi tool kanban_block voi ly do ngan (KHONG kanban_complete — done nghia la
da co the tren topic) — KHONG tao the, KHONG ve."""


# Body cho Dre — CAROUSEL. Tu 04/09/2026 phan CO HOC (tim/tai/do/cat/ghep anh,
# cong chan, dung slide, gui Telegram, ban giao) nam het trong dre_chuan_bi.py
# va dre_nop.py; vai chi CHIA SLIDE + VIET COPY vao mot tep JSON. Truoc do moi
# task Dre ton 51-60 tool call (curl/ls/grep/write_file), gio con ~4.
CAROUSEL_BODY = """Nguon: {source_note}
Link: {link}
Chu de: {title}
Tom tat: {summary}

NHIEM VU: dung mot CAROUSEL nhieu slide ke tin nay cho thuong hieu {brand}.
Toan bo phan CO HOC — tim anh, tai anh, do/crop/ghep, cong chan, dung slide,
gui Telegram, ban giao cho Miles — DA LA SCRIPT. Viec cua ban chi co MOT:
chia tin thanh slide va viet copy. Lam dung BA BUOC, khong them lenh nao khac.

BUOC 1 — doc ban chuan bi (anh da tai + xu ly san, tu lieu, khung spec):
cd {goc} && venv/bin/python dre_chuan_bi.py {draft_id}
(Script da chay nen tu luc Ong Chu chon tin; lenh nay thuong chi in ra. Neu no
bao dang chuan bi thi no tu doi, ban khong lam gi them.)

BUOC 2 — viet spec: ghi MOT tep JSON vao dung duong dan in o cuoi BUOC 1, theo
khung o do. Chi dien CHU (hook, category, label, text/quote/attrib) va MA ANH
(A1, A2...). KHONG tai anh, KHONG crop, KHONG mo tung anh, KHONG chay
anh_bai.py/carousel.py/gui_telegram.py bang tay. Muon nhin anh thi mo DUNG MOT
tam bang_anh.png. Chu tieng Viet co dau, cau quote DICH sang tieng Viet.

BUOC 3 — nop:
cd {goc} && venv/bin/python dre_nop.py {draft_id}
Script tu cat/ghep anh theo spec, chay moi cong chan, dung slide, gui album len
topic cua ban kem nut Duyet/Lam lai/Bo, ghi ban giao cho Miles. No bao [LOI]
thi sua DUNG cho do trong spec.json roi chay lai DUNG lenh nay (toi da 2 lan
sua). THIEU ANH THAT (duoi toi thieu, hoac anh chuan bi lac de): goi tool kanban_block voi ly do
ngan (anh nao bi loai, vi sao) — Ong Chu quyet tiep. TUYET DOI KHONG kanban_complete khi
chua gui album: "done" nghia la DA CO san pham tren topic. Khong tu che metadata kieu
"abort"; abort = kanban_block.
Xong: goi tool kanban_complete — summary = dong "Ket qua task", metadata = JSON o
dong "[metadata]" ma script in ra (Miles doc ban giao nay qua kanban). Khong sinh
agent con, khong gui lai album."""


# Body cho Kite (role carousel.edu) — render_edu.py: art VECTOR GOC, KHONG anh
# that (tru bieu do/bang co that: kind figure). Ba buoc nhu Dre/Ethan.
EDU_BODY = """Nguon: {source_note}
Link: {link}
Chu de: {title}
Tom tat: {summary}

NHIEM VU: dung mot CAROUSEL tech-editorial (magazine) ke tin nay bang ART VECTOR
GOC — KHONG anh that (tru bieu do/bang co that ma ban chuan bi liet ke), KHONG
nen AI, KHONG logo hang, KHONG so lieu bia, KHONG quote bia. Phan CO HOC (tu
lieu, hinh that, tone, cong chan, render, gui, ban giao) DA LA SCRIPT. Viec cua
ban chi co MOT: chia slide va viet chu. Lam dung BA BUOC, khong them lenh nao.

BUOC 1 — doc ban chuan bi (tu lieu, hinh that neu co, tone goi y, khung spec):
cd {goc} && venv/bin/python kite_chuan_bi.py {draft_id}

BUOC 2 — viet spec: ghi MOT tep JSON vao dung duong dan in o cuoi BUOC 1 (6..10
slide, slide 1 la cover, 6 kind: cover/statement/steps/loop/figure/cta). Chi
dien CHU + theme/hero + ma hinh that (neu dung). KHONG mo tung slide ra xem,
KHONG doc reference, KHONG chay render_edu.py/gui_telegram.py tay.

BUOC 3 — nop:
cd {goc} && venv/bin/python kite_nop.py {draft_id}
Script tu kiem spec, render bang Chromium, gui album len topic kem nut Duyet/Lam
lai/Bo, ghi ban giao cho Miles. Bao [LOI] thi sua DUNG cho do trong spec.json roi
chay lai DUNG lenh nay (toi da 2 lan). THIEU ANH THAT (duoi toi thieu, hoac anh chuan bi lac de): goi tool kanban_block voi ly do
ngan (anh nao bi loai, vi sao) — Ong Chu quyet tiep. TUYET DOI KHONG kanban_complete khi
chua gui album: "done" nghia la DA CO san pham tren topic. Khong tu che metadata kieu
"abort"; abort = kanban_block.
Xong: goi tool kanban_complete — summary = dong "Ket qua task", metadata = JSON o
dong "[metadata]" ma script in ra (Miles doc ban giao nay qua kanban). GUI DUNG MOT LAN: khong sinh agent con, khong gui lai."""


WRITER_BODY = """Bai goc: {title}
Link: {link}
Nguon: {source_note}
Via: {via}
Diem Finn cham: {score}/100 -- ly do: {score_reason}

NHIEM VU: viet caption tieng Viet cho bai nay ({brand}). Tu lieu that, ban giao
anh, moi luat co hoc cua caption DA duoc script gom san. Viec cua ban chi co
MOT: viet caption. Lam dung BA BUOC, khong them lenh nao khac.

BUOC 1 — doc ban chuan bi (tu lieu co so lieu, doan dau bai, hook tren anh, luat):
cd {goc} && venv/bin/python miles_chuan_bi.py {draft_id}

BUOC 2 — viet caption vao DUNG tep in o cuoi BUOC 1 (chi caption, HTML Telegram
<b> <i> <code>, tieng Viet co dau, moi cau xuong dong rieng, doan cach dong
trong, nham 800-1000 ky tu). KHONG tu dem ky tu, KHONG curl doc lai bai, KHONG
chay tu_lieu/caption_check/draft_write/approve_service tay.

BUOC 3 — nop:
cd {goc} && venv/bin/python miles_nop.py {draft_id}
Script tu chuan hoa, do ky tu/cau/so, chay cong chan, ghep draft, day vao hang
duyet. Bao [LOI] thi sua DUNG cho do trong caption.txt roi chay lai DUNG lenh
nay (toi da 2 lan). Xong: goi tool kanban_complete — summary = dong "Ket qua task", metadata = JSON o
dong "[metadata]" ma script in ra (ban giao len bang den kanban).
KHONG tu dang len channel."""
