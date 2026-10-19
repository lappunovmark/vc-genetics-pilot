"""Print contexts of patterns in a text file. Usage: ctx.py FILE WIDTH PATTERN [PATTERN ...]  (case-insensitive regex)"""
import re, sys
f, w = sys.argv[1], int(sys.argv[2])
t = open(f, errors='ignore').read()
t = re.sub(r'[ \t]+', ' ', t)
t = re.sub(r'\s*\n\s*', ' ', t)
for p in sys.argv[3:]:
    ms = list(re.finditer(p, t, flags=re.I))
    print(f'=== {p!r}: {len(ms)} hits')
    last = -10 ** 9
    for m in ms[:12]:
        if m.start() - last < w:
            continue
        last = m.start()
        print('  …' + t[max(0, m.start() - w):m.end() + w] + '…')
