"""Soi dau hieu rope ghi lech offset: trong cap dong (-a, +b), mot cap doi ten (old->new)
ma b.count(new) > a.count(old) + a.count(new). Chi xet cap doi ten thuc (tu log cac lo).
python3 soi_trung_ten.py <root> <base> <head|WORKTREE> <lo*.log ...>"""
import re
import subprocess
import sys
from pathlib import Path

root = Path(sys.argv[1]).resolve()
base, head = sys.argv[2], sys.argv[3]
cap = set()
for p in sys.argv[4:]:
    for line in Path(p).read_text(encoding="utf-8").splitlines():
        m = re.match(r"\[rename\]   (\w+) -> (\w+)  \(", line)
        if m and not m.group(1).startswith("module"):
            cap.add((m.group(1), m.group(2)))
args = ["git", "-C", str(root), "diff", "-U0", "--no-color", base] + ([] if head == "WORKTREE" else [head]) + ["--", "*.py"]
diff = subprocess.run(args, capture_output=True, text=True).stdout
tep, tru, cong, bao = None, [], [], 0
W = re.compile(r"[A-Za-z_]\w*")


def kiem(tep, tru, cong):
    global bao
    if cong and cong[0].startswith('"""SHIM'):
        return
    for a, b in zip(tru, cong):
        ta, tb = W.findall(a), W.findall(b)
        for old, new in cap:
            if old in ta and tb.count(new) > ta.count(old) + ta.count(new):
                print(f"{tep}: {old}->{new}\n   - {a.strip()[:150]}\n   + {b.strip()[:150]}")
                bao += 1
                break


for line in diff.splitlines():
    if line.startswith("+++ "):
        kiem(tep, tru, cong)
        tep, tru, cong = line[6:], [], []
    elif line.startswith("@@"):
        kiem(tep, tru, cong)
        tru, cong = [], []
    elif line.startswith("-") and not line.startswith("---"):
        tru.append(line[1:])
    elif line.startswith("+") and not line.startswith("+++"):
        cong.append(line[1:])
kiem(tep, tru, cong)
print("nghi ngo:", bao)
