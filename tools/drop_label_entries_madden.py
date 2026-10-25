# Removes manifest entries whose address is a loc_XXXXXXXX label in the OLD
# generated code, i.e. a block inside an existing function (not a function start).
# usage: python -I drop_label_entries_madden.py <project> <old_generated_default>
import glob, os, re, sys

proj, old_dir = sys.argv[1], sys.argv[2]
man_path = os.path.join(proj, "madden08_manifest.toml")
lab_re = re.compile(r'^loc_([0-9A-F]{8}):')
labels = set()
for path in sorted(glob.glob(os.path.join(old_dir, "madden08_recomp.*.cpp"))):
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            m = lab_re.match(line)
            if m:
                labels.add(int(m.group(1), 16))
print("labels found in the old code: %d" % len(labels))

raw = open(man_path, "rb").read().decode("utf-8")
nl = "\r\n" if "\r\n" in raw else "\n"
out, removed = [], []
for line in raw.splitlines():
    m = re.match(r'^\s*0x([0-9A-Fa-f]{8})\s*=', line)
    if m and int(m.group(1), 16) in labels:
        removed.append(line.strip())
        continue
    out.append(line)
print("manifest entries removed: %d" % len(removed))
for l in removed:
    print("  " + l)
if removed:
    with open(man_path, "wb") as f:
        f.write((nl.join(out) + nl).encode("utf-8"))
    print("manifest saved.")