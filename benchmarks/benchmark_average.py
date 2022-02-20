import sys

labels = set()


def Number(s: str, suffix: str = '') -> int | float:
    assert s.endswith(suffix)
    s = s[:len(s) - len(suffix)]
    if '.' in s:
        return float(s)
    return int(s)


records = {}


def add_record(index, *values: int):
    if index in records:
        records[index].append(values)
    else:
        records[index] = [values]


for line in sys.stdin:
    if line.startswith('Benchmark'):
        line = [s.strip() for s in line.split('\t')]
        assert len(line) == 5
        assert line[0].startswith('Benchmark')
        add_record(line[0], Number(line[1]), Number(line[2], ' ns/op'), Number(line[3], ' B/op'),
                   Number(line[4], ' allocs/op'))

N = {k: sum(t[0] for t in v) for k, v in records.items()}
summary = {k: list(sum(t[i] * t[0] for t in v) / N[k] for i in range(1, len(v[0]))) for k, v in records.items()}
index = sorted(summary.keys(), key=lambda k: summary[k][0])
summary[index[0]].append('')
for k in index[1:]:
    summary[k].append(f'({summary[k][0]/summary[index[0]][0]:.1f}x slower)')


def print_table(rows: list, just: list[int]):
    assert all(len(row) == len(rows[0]) for row in rows)
    assert len(just) == len(rows[0])
    m = len(rows)
    n = len(rows[0])
    rows = [[str(rows[i][j]) for j in range(n)] for i in range(m)]
    max_len = [max(len(rows[i][j]) for i in range(m)) for j in range(n)]
    for i in range(m):
        for j in range(n):
            if just[j] > 0:
                rows[i][j] = rows[i][j].ljust(max_len[j] + just[j])
            else:
                rows[i][j] = rows[i][j].rjust(max_len[j] - just[j])
            print(rows[i][j], end='')
        print()


print_table([
    [k, N[k], f'{summary[k][0]:.1f} ns/op', summary[k][3], f'{summary[k][1]:.1f} B/op', f'{summary[k][2]:.1f} allocs/op'] for k in index
], [4, 0, -4, -1, -4, -4])
