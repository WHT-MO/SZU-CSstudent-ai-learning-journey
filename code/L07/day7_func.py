#示范
def average(a,b,c):
    total = a + b + c
    return total / 3
print(average(90,80,100))
x = average(70,60,50)
print(x)
print(average(x,90,60))

def f1(a,b):
    print(a + b)

def f2(a,b):
    return a + b
f1(1,2)
r1 = f1(1,2)
r2 = f2(1,2)
print(r1,r2)

def g():
    inner = 10
g()
#print(inner)  没定义

def greet(name):
    return "你好，" + name
print(greet("小明"))
print(greet("淘淘"))