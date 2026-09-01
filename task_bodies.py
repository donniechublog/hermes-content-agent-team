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
cd {goc} && venv/bin/python anh_bai.py \\
  --tieu-de "{title}" --link "{link}" --json \\
  --tu-nguon {goc}/state/nguon_{draft_id}.json

Finn DA tim nguon san va ghi vao tep tren — day la ket qua research cua cau ay.
Ban dung lai bo nguon do, khong tu di tim. Miles cung doc chinh tep nay de viet,
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

Truoc khi dung lai, xem link co phai arxiv khong (arxiv.org/abs/... hoac /pdf/...).
Neu phai, "anh that" cua bai la CHINH TRANG DAU PAPER — ten cong trinh va nhom
tac gia in tren nen trang that. Do khong phai hinh bia dat, nen chup no khong
vi pham nguyen tac. Chay:

venv/bin/python arxiv_bia.py \
  --link "{link}" --out /tmp/src_{draft_id}.png

Chay xong (thoat 0) thi coi nhu DA CO anh chinh, di tiep buoc 4 binh thuong.
Khong co anh phu.

Neu KHONG phai arxiv, hoac arxiv_bia.py thoat khac 0 (khong tai duoc PDF):
Dung lai. Bao dung mot cau: "Khong tim duoc anh that cho tin nay" kem link da thu.
KHONG tao the, KHONG ve SVG, KHONG chay card.py. Ong Chu se quyet dinh bo tin
hay tu dua anh vao.

BUOC 4 — dung the anh (chi khi buoc 2 co anh). MAC DINH LA KIEU QUOTE (the HOOK).

--kieu quote la mot CAU LON trong khung dau " sao cho DAP VAO MAT trong 3 GIAY
dau, khien nguoi ta phai doc tiep. Cau nay KHONG nhat thiet la loi ai noi trong
bai — dung may moc. No co the la:
 - chinh TIEU DE / mot goc giat cua tin (manh nhat khi co CON SO soc), HOAC
 - mot cau noi CO THAT cua nguoi trong bai (neu bai co cau du dat).
Chon cai nao gay an tuong hon. Doc {source_note} / {summary} / bai goc ({link}).

--tagline la CHIP CATEGORY goc tren-trai (nhan ngan TIENG ANH): MODEL RELEASE /
FUNDING / ROBOTICS / CYBERSECURITY / APPS / OPEN SOURCE / RESEARCH / M&A / IN
BRIEF... Chon nhan dung chu de tin. (KHONG con mac dinh "daily AI update".)

--attrib la dong nguon o duoi khung:
 - Cau la LOI CO THAT cua mot nguoi  -> "Phat bieu cua <ten>, <chuc/hang>".
 - Cau la tieu de/hook (khong phai loi ai) -> ghi NGUON: "via <bao>" hoac
   "<Chu de>, via <bao>". TUYET DOI KHONG gan cau minh tu viet thanh loi mot
   nguoi cu the — bia loi la sai. Hook thi ghi nguon, dung ghi "phat bieu".

cd {goc} && {hermes_py} card.py \\
  --kieu quote --ratio 4:5 \\
  --tagline "<CATEGORY ngan TIENG ANH>" \\
  --image /tmp/src_{draft_id}.png \\
  --title "<CAU HOOK co dau, dap vao mat trong 3s>" \\
  --attrib "<'via <bao>' hoac 'Phat bieu cua <ten>' neu la loi that>"{co_brand} \\
  --out {out_png}

Kieu tran (--kieu tran, kicker + tieu de mono, layout bang-tin co dien) van dung
duoc khi ban muon doi khong khi thay vi the hook — nhung MAC DINH la quote/hook.

Cac anh phu KHONG dung the — giu nguyen ban goc, chi doi ten thanh
{out_png_goc}_2.png, _3.png... de buoc dang sau gui thanh album.

BUOC 5 — GUI ANH LEN TOPIC CUA MINH NGAY (KHONG cho nguoi viet):
Dung xong the anh la viec cua ban da XONG — day anh ra topic cua chinh minh
ngay, KHONG cho writer viet xong roi moi co anh trong bai. Ong Chu ngoi o
Telegram, chi thay ket qua khi anh len topic; de anh nam trong drafts/ ma khong
gui thi voi Ong Chu y het nhu ban im lang.
cd {goc} && venv/bin/python gui_telegram.py \\
  --vai {vai} --anh {out_png} --duyet {draft_id} --mo-ta "<mot cau anh nay la gi>"
Co anh phu ({out_png_goc}_2.png, _3.png...) thi lap them --anh cho tung tam de
gui thanh album. Gui xong moi ghi ket qua task.

`--duyet {draft_id}` gan BA nut duoi anh: "Duyet" (nguoi viet writer moi
viet caption), "Lam lai" (tao lai dung task nay, ban se dung ANH KHAC), "Bo han"
(giet tin). Vay nen viec cua ban chi la ra ANH cho that dat — dung cho, cung
dung tu di goi nguoi viet. Neu bi giao "lam lai", doc ghi chu cuoi task va chon
anh khac han lan truoc.

LUU Y — doc skill `hero-image` (muc "Kieu quote" la mac dinh, phan hero tran la
du phong). Day chi la phan hay sai nhat:

Chung ca hai kieu:
- Anh va chu la MOT mat phang lien. KHONG khung, KHONG vach, KHONG phu de.
- Chu TIENG VIET CO DAU. Nua duoi/vung dat chu phai TRONG; anh chup man hinh
  day chu thi doi anh khac.
- Ten hang trong chu duoc TO MAU tu dong, ban khong phai lam gi. Gap hang chua
  duoc to thi bao lai de them vao danh sach.

Kieu quote / hook (mac dinh):
- --title la CAU HOOK — dap vao mat trong 3 giay. Co the la tieu de/goc giat
  HOAC loi that cua nguoi trong bai. Cau NGAN de doc lon (cham 7 dong la cat).
- --tagline = CHIP CATEGORY (MODEL RELEASE / FUNDING / ROBOTICS / IN BRIEF...).
- --attrib: loi that -> "Phat bieu cua <ten>"; hook -> "via <bao>". Khong gan
  cau tu viet thanh loi mot nguoi cu the.
- Dau " trong khung tu doi mau theo hang duoc nhac, tu dong.

Kieu tran (layout bang-tin co dien, khi muon doi khong khi):
- KHONG --subtitle, KHONG --via, KHONG nhan category. Tren anh chi co bon thu:
  anh, kicker, tieu de, ten kenh.
- TIEU DE LA MOT CAU HOAN CHINH bao quat ca tin, khong gioi han so dong/ky tu;
  tin co so thi dua so vao chinh cau do.
- Kicker TIENG ANH, toi da hai tu: BREAKING / MODEL RELEASE / AGENT / FUNDING /
  BENCHMARK / OPEN SOURCE / M&A / RESEARCH / INFRA / POLICY.

- Nguon anh ({via}) KHONG con in tren anh nua. Bao lai nguon do trong ket qua
  task de nguoi viet caption dua vao bai — day la viec SONG SONG, KHONG phai
  dieu kien de gui anh. Ban da gui anh o buoc 5 roi moi ghi nguon cho ho.
- Ket qua bat buoc: file {out_png} phai ton tai VA da gui len topic (buoc 5)
  sau khi chay (tru truong hop buoc 3 — khong co anh that)."""


# Body cho Dre — dung carousel nhieu slide thay vi mot the bia. Khac ILLU_BODY
# o cho: khong chay card.py, ma viet copy tung slide roi chay carousel.py. Van
# dung anh_bai.py de tim anh that, van cong chan "khong tu ve minh hoa".
CAROUSEL_BODY = """Nguon: {source_note}
Link: {link}
Nguon anh (via): {via}
Chu de: {title}
Tom tat: {summary}

NHIEM VU: dung mot CAROUSEL nhieu slide ke tin nay, kieu bang tin — anh full be
ngang o tren TAN dan vao nen den, khoi chu trang o duoi, watermark nghieng o day.
Anh va chu la MOT mat phang lien: KHONG vien, KHONG vach, KHONG khung chia hai vung.

DOC SKILL `carousel` TRUOC khi lam — no co day du khung ke chuyen, cach viet copy
tung slide, luat chon anh, va cong chan. Duoi day chi la phan hay sai nhat.

NGUYEN TAC TREN HET: KHONG BAO GIO tu ve minh hoa. Moi slide phai co mot ANH THAT
lay tu nguon. Khong du anh that thi chia lai slide hoac gop y; cung lam thi bao
lai — tuyet doi khong dung hinh gia.

BUOC 1 — hieu tin du sau de chia slide. Finn DA research san, doc bo nguon nay:
  {goc}/state/nguon_{draft_id}.json

BUOC 2 — tim anh that (BAT BUOC chay lenh nay):
cd {goc} && venv/bin/python anh_bai.py \\
  --tieu-de "{title}" --link "{link}" --json \\
  --tu-nguon {goc}/state/nguon_{draft_id}.json
Tai cac anh diem cao ve /tmp: /tmp/src_{draft_id}.png, /tmp/src_{draft_id}_2.png...
Bai arxiv khong co anh minh hoa thi chup bia paper:
  venv/bin/python arxiv_bia.py --link "{link}" --out /tmp/src_{draft_id}.png

BUOC 3 — chia tin thanh 4-8 slide va viet copy (theo khung ke chuyen trong skill):
  - BIA: mot cau HOOK giat khien nguoi ta dung luot (thuong la nghich ly hoac con
    so), kem mot NHAN NGAN. Cover can goc duoi-trai thoang de hook doc ro.
  - Cac slide sau: moi slide MOT y moi day nguoi doc sang slide sau (cai gi vua
    xay ra, con so gay soc, y nghia that, doi thu, cai can theo doi).
  - Slide cuoi de lai mot moc hoac cau hoi, khong chot cut.
  - Chu TIENG VIET CO DAU, cau ngan, moi doan 2-4 dong, tach doan bang dong trong.
  - CA CAU QUOTE (trich dan) cung phai DICH sang tieng Viet co dau — bai goc
    tieng Anh thi DICH cau trich, giu ten rieng/thuat ngu/so lieu; DUNG chep
    nguyen van tieng Anh vao quote.

BUOC 4 — ghi spec JSON roi dung (cac anh o BUOC 2 chia cho tung slide theo y):
cat > /tmp/carousel_{draft_id}.json <<'JSON'
{{
  "cover":  {{"image": "/tmp/src_{draft_id}.png", "hook": "<cau giat co dau>", "label": "<NHAN NGAN>"}},
  "slides": [
    {{"image": "/tmp/src_{draft_id}_2.png", "text": "doan mot.\\n\\ndoan hai."}},
    {{"image": "/tmp/src_{draft_id}_3.png", "text": "..."}}
  ]
}}
JSON
cd {goc} && venv/bin/python carousel.py \\
  --spec /tmp/carousel_{draft_id}.json --out {out_png} --brand {brand}

Ra {out_png} (bia) + {out_png_goc}_2.png, _3.png... — draft_write.py tu gom thanh
album khi Miles ghep draft, ban KHONG phai lam gi them o khau dang.

CONG CHAN: tieng Viet khong dau bi chan (chi tiếng Anh moi them --bo-qua-dau);
toi da 10 slide ke ca bia; thieu image/text mot slide thi dung.

BUOC 5 — GUI CAROUSEL LEN TOPIC CUA MINH NGAY (KHONG cho nguoi viet):
Dung xong bo slide la viec cua ban da XONG — day ca album ra topic cua chinh
minh ngay, KHONG cho writer viet xong roi moi co anh trong bai. Ong Chu
ngoi o Telegram, chi thay ket qua khi anh len topic.
cd {goc} && venv/bin/python gui_telegram.py \\
  --vai {vai} --anh {out_png} --anh {out_png_goc}_2.png --anh {out_png_goc}_3.png \\
  --duyet {draft_id} --mo-ta "<mot cau carousel nay ve gi>"
Lap --anh cho DU so slide that su dung ra (bo bot cac dong _N.png khong ton tai,
them vao neu nhieu hon 3). Gui xong moi ghi ket qua task.

`--duyet {draft_id}` gan BA nut duoi album: "Duyet" (nguoi viet writer moi
viet caption), "Lam lai" (tao lai dung task nay, ban dung BO SLIDE khac), "Bo
han" (giet tin). Viec cua ban chi la ra BO SLIDE cho that dat — dung cho writer,
cung dung tu di goi nguoi viet. Neu bi giao "lam lai", doc ghi chu cuoi task va
lam khac lan truoc.

BAN GIAO: watermark tren slide KHONG phai ghi nguon. Bao lai nguon tin va nguon
tung anh ({via}) trong ket qua task de Miles dua vao chu thich bai dang — viec
SONG SONG, KHONG phai dieu kien de gui anh.
Ket qua bat buoc: {out_png} phai ton tai VA da gui len topic (buoc 5)."""


# Body cho Kite (role carousel.edu) — dung render_edu.py: art VECTOR GOC tu ve,
# KHONG anh that. Khac han CAROUSEL_BODY (khong anh_bai.py, khong carousel.py).
EDU_BODY = """Nguon: {source_note}
Link: {link}
Chu de: {title}
Tom tat: {summary}

NHIEM VU: dung mot CAROUSEL tech-editorial (magazine, vibe TechCrunch/The Verge)
ke tin nay bang ART VECTOR GOC tu ve — KHONG anh that, KHONG nen AI.

DOC SKILL `carousel-edu` TRUOC khi lam — no co he thiet ke (mau, font, khung
magazine, hero art), 5 kind slide, ranh gioi ngoai le voi luat khong-tu-ve, va
lenh dung. Doc `reference/boost.spec.json` de biet khuon spec day du.

RANH GIOI: duoc ve art truu tuong / so do khai niem; CAM anh gia, screenshot gia,
logo hang that, so lieu bia, quote bia. Goi ten san pham bang CHU thi duoc.

BUOC 1 — hieu tin du sau. Finn DA research san, doc bo nguon:
  {goc}/state/nguon_{draft_id}.json

BUOC 2 — chia tin thanh 5-8 slide, viet copy TIENG VIET CO DAU. 5 kind:
cover / statement / steps / loop / cta. Toi thieu 5 slide (cong chan dung neu it
hon). Moi slide mot y moi; bia HOOK giat; slide cuoi CTA + nguon.

BUOC 3 — ghi spec JSON roi dung:
cat > /tmp/sli_{draft_id}.json <<'JSON'
{{
  "brand": "{brand}",
  "section": "AI TOOLING",
  "folio": "<CHU DE NGAN>",
  "slides": [
    {{"kind": "cover", "eyebrow": "<CHUYEN MUC>", "title": "<tieu de>", "accent": "<cum nhan>", "standfirst": "<mot cau standfirst>", "byline": ["{brand}", "Phan tich", "N phut doc"]}},
    {{"kind": "statement", "eyebrow": "BOI CANH", "title": "...", "standfirst": "..."}},
    {{"kind": "steps", "eyebrow": "CACH VAN HANH", "title": "...", "steps": [{{"title": "...", "desc": "..."}}]}},
    {{"kind": "loop", "eyebrow": "CO CHE", "title": "...", "accent": "...", "chips": ["...", "..."], "standfirst": "...", "callout": "..."}},
    {{"kind": "cta", "eyebrow": "AP DUNG", "title": "...", "checks": ["...", "..."], "readmore": {{"label": "DOC THEM", "text": "..."}}, "follow": "Theo doi @{brand}"}}
  ]
}}
JSON
cd {goc} && venv/bin/python render_edu.py \\
  --spec /tmp/sli_{draft_id}.json --out {out_png}{co_brand}

Ra {out_png} (bia) + {out_png_goc}_2.png... — draft_write.py tu gom thanh album.
CONG CHAN render_edu: tieng Viet co dau; 5..10 slide; slide 1 phai la `cover`.

BUOC 4 — GUI LEN TOPIC CUA MINH NGAY (KHONG cho writer):
cd {goc} && venv/bin/python gui_telegram.py \\
  --vai {vai} --anh {out_png} --anh {out_png_goc}_2.png --anh {out_png_goc}_3.png \\
  --duyet {draft_id} --mo-ta "<mot cau carousel nay ve gi>"
Lap --anh cho DU so slide that su dung ra. Gui xong moi ghi ket qua task.

`--duyet {draft_id}` gan nut Duyet / Lam lai / Bo han. Viec cua ban chi la ra BO
SLIDE cho that dat — dung cho writer, cung dung tu di goi nguoi viet. Neu bi giao
"lam lai", doc ghi chu cuoi task va lam khac lan truoc.

BAN GIAO: bao lai nguon tin cho writer de dua vao chu thich bai dang.
Ket qua bat buoc: {out_png} phai ton tai VA da gui len topic (buoc 4)."""


WRITER_BODY = """Bai goc: {title}
Link: {link}
Nguon: {source_note}
Via: {via}
Diem Finn cham: {score}/100 -- ly do: {score_reason}
(Dung ly do diem nay de viet phan Y NGHIA — vi sao chuyen nay quan trong; noi thang
bang thong tin cu the, dung tu y suy dien, va KHONG dung cum "dang chu y / dang quan tam")

Du kien (Finn da tom tat — CHI la diem khoi dau, KHONG du de viet):
{summary}

BUOC 1 — DOC TU LIEU THAT (bat buoc, lam truoc khi viet mot chu nao):
cd {goc} && venv/bin/python tu_lieu.py \\
  --tieu-de "{title}" --link "{link}" --out /tmp/tulieu_{draft_id}.md \\
  --tu-nguon {goc}/state/nguon_{draft_id}.json

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

TIEU CHUAN BIEN TAP:
- Moi CAU xuong dong rieng: het mot cau thi xuong dong roi moi viet cau tiep
  theo. Moi DOAN cach nhau MOT dong trong.
- KHONG de link song trong caption (script tu choi, ke ca ten mien tran nhu
  z.ai). Buoc phai nhac ten mien thi viet dau cham thanh " . " (vd z . ai) de
  no khong thanh link.
- KHONG dung cum sao rong "dang chu y", "dang quan tam" va bien the ("ly do
  dang chu y", "dang chu y vi", "dang quan tam vi"...). Script tu choi. Noi
  thang y nghia bang thong tin cu the.

Bon y BAT BUOC co, moi y mot cau la du:
- Chuyen gi vua xay ra, kem SO quan trong nhat
- So sanh: hon hay kem cai gi, cach biet bao nhieu. Neu nguon co noi cho THUA
  thi phai noi — bo di la thien lech, khong con khach quan
- Han che hoac dieu kien kem theo, neu nguon co noi
- Y NGHIA: vi sao chuyen nay quan trong (dung ly do Finn cham diem) — noi thang,
  KHONG dung cum "dang chu y / dang quan tam vi..."

Do dai: tan dung TOI DA 1024 ky tu, do la gioi han chu thich anh cua Telegram.
Vua trong muc do thi anh va chu di chung MOT tin nhan, doc gia thay ca hai cung
luc. Vuot qua la Telegram tach lam hai, anh mot noi chu mot noi.

Nham 800-1000 ky tu. Ngan gon nam o CACH VIET chu khong o viec cat bot y: moi
cau phai mang mot thong tin moi, khong cau nao lap lai cau truoc.

YEU CAU KY THUAT:
- Toi da 900 ky tu, HTML Telegram (chi <b> <i> <code>), dung cau truc SOUL.
- Ghi caption ra file tam /tmp/caption_{draft_id}.txt (CHI caption, khong kem gi khac).
- Tu kiem truoc khi ghep draft:
    cd {goc} && venv/bin/python caption_check.py \\
      --caption-file /tmp/caption_{draft_id}.txt --tu-lieu /tmp/tulieu_{draft_id}.md
- Ghep draft bang lenh sau — script tu dien source_url / category / via / duong dan anh,
  BAN KHONG CAN go lai nhung gia tri do:
    cd {goc} && venv/bin/python draft_write.py {draft_id} --caption-file /tmp/caption_{draft_id}.txt --tu-lieu /tmp/tulieu_{draft_id}.md
- Day vao hang duyet:
    cd {goc} && venv/bin/python approve_service.py push {draft_id}
- KHONG tu dang len channel."""
