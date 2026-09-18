#作业
def grade(score):
    if score >= 90:
        return "A"
    elif score >= 80:
        return "B"
    elif score >=60:
        return "C"
    else:
        return "D"

nums = list(map(int,input().split()))
grades = []
for score in nums:
    x = grade(score)
    grades.append(x)
print(" ".join(map(str,grades)))