m,n,k = map(int,input().split())
s = (0,1,1)
x,y,z = s #x=数量，y=行，z=列
fied = []
time = 0
total = 0
t = -1

for i in range(m):
    j = list(map(int,input().split()))
    for x in j:
        if x != 0:
            fied.append((x,y,z))
        z += 1
    z = 1
    y += 1
fied.sort(reverse=True)
for x,y,z in fied:
    if t == -1:
        time += y+1
    else:
        time += ( abs(y - fied[t][1]) + abs(z - fied[t][2]) + 1 )
    t += 1
    if k - time >= y:
        total += x
print(total)