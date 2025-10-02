from pathlib import Path
import re

# --- 保留 ass_to_lrc 的逻辑 ---
TIME_RE = re.compile(r"(\d+):(\d{2}):(\d{2})\.(\d{1,2})")

def parse_ass_time(t: str):
    m = TIME_RE.match(t.strip())
    if not m:
        return None, None
    h, mm, ss, cs = int(m.group(1)), int(m.group(2)), int(m.group(3)), int(m.group(4).ljust(2, "0"))
    total = h * 3600 + mm * 60 + ss + cs / 100.0
    minutes = int(total // 60)
    seconds = int(total % 60)
    hundredths = int(round((total - int(total)) * 100))
    if hundredths >= 100:
        hundredths -= 100
        seconds += 1
    if seconds >= 60:
        seconds -= 60
        minutes += 1
    return f"{minutes:02d}:{seconds:02d}.{hundredths:02d}", total

def format_time_from_total(total: float) -> str:
    minutes = int(total // 60)
    seconds = int(total % 60)
    frac = total - (minutes * 60 + seconds)
    hundredths = int(round(frac * 100))
    if hundredths >= 100:
        hundredths -= 100
        seconds += 1
    if seconds >= 60:
        seconds -= 60
        minutes += 1
    return f"{minutes:02d}:{seconds:02d}.{hundredths:02d}"

def clean_ass_text(s: str) -> str:
    # 移除 ASS 标签 & 改换行标记
    s = re.sub(r"\{.*?\}", "", s)
    s = s.replace(r"\N", " ").replace(r"\n", " ")
    return s.strip()

def convert_file(path: Path, out_dir: Path) -> tuple[bool, str | None]:
    text = path.read_text(encoding="utf-8-sig", errors="replace")
    lines = text.splitlines()
    entries = []
    for line in lines:
        if not line.startswith("Dialogue:"):
            continue
        parts = line.split(",", 9)
        if len(parts) < 10:
            continue
        start = parts[1].strip()
        raw_text = parts[9].strip()
        timestamp, total = parse_ass_time(start)
        if timestamp is None:
            continue
        lyric = clean_ass_text(raw_text)
        if not lyric:
            continue
        entries.append((total, timestamp, lyric))

    if not entries:
        return False, "no_entries"

    entries.sort(key=lambda x: x[0])

    out_path = out_dir / (path.stem + ".lrc")
    if out_path.exists():
        print(f"{path.name}未转换（lrc已存在）")
        return False, "exists"

    # 重分配时间戳逻辑（保持原有）
    new_entries, i, n = [], 0, len(entries)
    while i < n:
        j = i + 1
        while j < n and abs(entries[j][0] - entries[i][0]) < 1e-9:
            j += 1
        group_len = j - i
        cur_total = entries[i][0]
        if group_len == 1:
            new_entries.append(entries[i])
        else:
            if j < n:
                next_total = entries[j][0]
                span = next_total - cur_total
                if span <= 1e-6:
                    step = 0.05
                    for k in range(group_len):
                        t = cur_total + step * k
                        ts_str = format_time_from_total(t)
                        new_entries.append((t, ts_str, entries[i + k][2]))
                else:
                    step = span / group_len
                    for k in range(group_len):
                        t = cur_total + step * k
                        ts_str = format_time_from_total(t)
                        new_entries.append((t, ts_str, entries[i + k][2]))
            else:
                step = 0.05
                for k in range(group_len):
                    t = cur_total + step * k
                    ts_str = format_time_from_total(t)
                    new_entries.append((t, ts_str, entries[i + k][2]))
        i = j

    new_entries.sort(key=lambda x: x[0])
    out_lines = [f"[{ts}]{ly}" for _, ts, ly in new_entries]
    out_path.write_text("\n".join(out_lines), encoding="utf-8", errors="replace")
    return True, None

# --- 主流程：直接将当前目录下的 .ass 转换成 lrc ---
def main():
    p = Path(".")
    ass_files = list(p.glob("*.ass"))
    if not ass_files:
        print("未找到 .ass 文件")
        return

    total = len(ass_files)
    converted_count = 0

    for f in ass_files:
        converted, reason = convert_file(f, p)
        if converted:
            converted_count += 1
        else:
            if reason != "exists":
                print(f"{f.name}未转换")

    print(f"共{total}个ass文件，成功转换{converted_count}个。")

if __name__ == "__main__":
    main()