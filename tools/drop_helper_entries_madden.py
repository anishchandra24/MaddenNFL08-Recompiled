# Removes manifest entries that sit exactly on a register save/restore helper
# (the __savegprlr_14 style functions the recompiler names itself).
# usage: python -I drop_helper_entries_madden.py <project> <old_generated_default>
import glob, os, re, sys

proj, old_dir = sys.argv[1], sys.argv[2]
man_path = os.path.join(proj, "madden08_manifest.toml")
helpers = {}
pat = re.compile(r'\{\s*0x([0-9A-Fa-f]{8}),\s*(__\w+)\s*\}')
for path in glob.glob(os.path.join(old_dir, "madden08_init*.cpp")):
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            m = pat.search(line)
            if m:
                helpers[int(m.group(1), 16)] = m.group(2)
print("helper functions found in the old code: %d" % len(helpers))
for a in sorted(helpers):
    print("  0x%08X %s" % (a, helpers[a]))

raw = open(man_path, "rb").read().decode("utf-8")
nl = "\r\n" if "\r\n" in raw else "\n"
out = []
removed = []
for line in raw.splitlines():
    m = re.match(r'^\s*0x([0-9A-Fa-f]{8})\s*=', line)
    if m and int(m.group(1), 16) in helpers:
        removed.append((int(m.group(1), 16), line.strip()))
        continue
    out.append(line)
print()
print("manifest entries removed: %d" % len(removed))
for a, l in removed:
    print("  %s   (%s)" % (l, helpers[a]))
if removed:
    with open(man_path, "wb") as f:
        f.write((nl.join(out) + nl).encode("utf-8"))
    print("manifest saved.")
else:
    print("nothing to remove.")