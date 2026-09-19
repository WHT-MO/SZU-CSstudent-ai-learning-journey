M,N = map(int,input().split())
treq = {}
for x in range(M,N + 1):
    for ch in str(x):
        treq[ch] = treq.get(ch,0) + 1
print(treq.get("0",0),treq.get("1",0),treq.get("2",0),treq.get("3",0),treq.get("4",0),treq.get("5",0),treq.get("6",0),treq.get("7",0),treq.get("8",0),treq.get("9",0),)