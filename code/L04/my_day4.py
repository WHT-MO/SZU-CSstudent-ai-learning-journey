scores = [85,92,78,90]
print(scores)
print(scores[0])
print(scores[3])
print(scores[-1])
print(len(scores))

nums = []
nums.append(10)
nums.append(20)
nums[0] = 99
print(nums)

for n in nums:
    print(n)

print(scores[1:3])

line = input()
parts = line.split()
a = int(parts[0])
b = int(parts[1])
c = int(parts[2])
print(a,b,c)

a,b,c = map(int,input().split())
print(a,b,c)

nums = list(map(int,input().split()))
total = 0
for n in nums:
    total = total + n
print("总和",total)
print("平均",total/len(nums))
print("最大最小",max(nums),min(nums))

n = int(input())
scores = list(map(int,input().split()))
total = 0
for x in scores:
    total = total + x
print("总分",total)
print("平均分",total/n)
print("最高最低分",max(scores),min(scores))
#运行输出
# [85, 92, 78, 90]
#85
#90
#90
#4
#[99, 20]
#99
#20
#[92, 78]
#1 2 3
#1 2 3
#1 22 33
#1 22 33
#12 12 12
#总和 36
#平均 12.0
#最大最小 12 12
#6
#88 98 68 45 56 99
#总分 454
#平均分 75.66666666666667
#最高最低分 99 45