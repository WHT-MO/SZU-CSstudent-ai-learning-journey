from functools import cmp_to_key

def compare(a, b):
    if a + b > b + a:
        return -1
    if a + b < b + a:
        return 1
    return 0

line = input()
n = list(input().split())
num = sorted(n, key=cmp_to_key(compare))
if num[0] == "0":
    print("0")
else:
    print("".join(num))