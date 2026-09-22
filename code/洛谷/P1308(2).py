#解法二
import re
def solve(target,text):
    pat = re.compile(r"\b" + target + r"\b",re.IGNORECASE)
    m = pat.search(text)
    if m is None:
        return "-1"
    return f"{len(pat.findall(text))} {m.start()}"

if __name__ == "__main__":
    target = input().strip()
    text = input()
    print(solve(target,text))