# Read-only. Compares two folders of generated code function by function.
# usage: python -I compare_generated_madden.py <old_generated_default> <new_generated_default> <out_file>
import glob, hashlib, os, re, sys

old_dir, new_dir, outp = sys.argv[1], sys.argv[2], sys.argv[3]
fn_re = re.compile(r'^DEFINE_REX_FUNC\((\w+)\)')

def load(d):
    funcs = {}
    files = sorted(glob.glob(os.path.join(d, "madden08_recomp.*.cpp")))
    for path in files:
        name = None
        h = None
        n = 0
        with open(path, encoding="utf-8", errors="replace") as f:
            for line in f:
                m = fn_re.match(line)
                if m:
                    if name:
                        funcs[name] = (h.hexdigest(), n)
                    name = m.group(1)
                    h = hashlib.md5()
                    n = 0
                    continue
                if name:
                    h.update(line.encode("utf-8", "replace"))
                    n += 1
        if name:
            funcs[name] = (h.hexdigest(), n)
    return funcs, len(files)

old, fo = load(old_dir)
new, fn = load(new_dir)
print("old: %d files, %d functions" % (fo, len(old)))
print("new: %d files, %d functions" % (fn, len(new)))
only_old = sorted(k for k in old if k not in new)
only_new = sorted(k for k in new if k not in old)
changed = sorted(k for k in old if k in new and old[k][0] != new[k][0])
print("functions only in OLD (disappeared): %d" % len(only_old))
print("functions only in NEW (added): %d" % len(only_new))
print("functions in both whose code CHANGED: %d" % len(changed))
print()
print("CHANGED (first 40):")
for k in changed[:40]:
    print("  %s  lines %d -> %d" % (k, old[k][1], new[k][1]))
print("DISAPPEARED (first 20):")
for k in only_old[:20]:
    print("  %s" % k)
with open(outp, "w") as o:
    o.write("CHANGED\n")
    for k in changed:
        o.write("%s %d %d\n" % (k, old[k][1], new[k][1]))
    o.write("DISAPPEARED\n")
    for k in only_old:
        o.write(k + "\n")
print()
print("full list written to " + outp)