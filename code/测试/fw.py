with open("demo.txt","w",encoding="utf-8") as f:
    last,d = map(int,input().split())
    f.write(f"上次打卡第{last}天\n连续打卡{d}天")

with open("demo.txt","r",encoding="utf-8") as f:
    print(f.read())