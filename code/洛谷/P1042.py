words = []
a,b = 0,0
while True:
    line = input()
    for x in line:
        if x != "E":
            words.append(x)
        else:
            break
    if x == "E":
        break
for s in words:
    if s == "W":
        a += 1
        if a >= 11 and abs(a - b) >= 2:
            print(f"{a}:{b}")
            a,b = 0,0
    if s == "L":
        b += 1
        if b >= 11 and abs(a - b) >= 2:
            print(f"{a}:{b}")
            a,b = 0,0
print(f"{a}:{b}")
print()
a,b = 0,0
for s in words:
    if s == "W":
        a += 1
        if a >= 21 and abs(a - b) >= 2:
            print(f"{a}:{b}")
            a,b = 0,0
    if s == "L":
        b += 1
        if b >= 21 and abs(a - b) >= 2:
            print(f"{a}:{b}")
            a,b = 0,0
print(f"{a}:{b}")