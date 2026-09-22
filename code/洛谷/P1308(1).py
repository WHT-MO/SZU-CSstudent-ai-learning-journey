#解法一
target = input().lower()
text = input().lower()

count = 0
first_pos = -1

n = len(text)
i = 0

while i < n:
    while i < n and text[i] == " ":
        i += 1
    if i == n:
        break
    start = i
    while i < n and text[i] != " ":
        i += 1
    word = text[start:i]
    if word == target:
        count += 1
        if first_pos == -1:
            first_pos = start
if count == 0:
    print(-1)
else:
    print(count,first_pos)