#变式
def week(days):
    x = days // 7
    y = days % 7
    return x,y
a,b = input().split()
b = int(b)
w,d = week(b)
print(a,w,d)