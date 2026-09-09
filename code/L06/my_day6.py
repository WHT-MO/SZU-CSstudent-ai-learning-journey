L = ["深", "大", "计", "软"]
print(L[0], L[2])
for x in L:
    print(x)

scores = {"张三":92, "李四":88}
print(scores["张三"])

scores["王五"] = 95
scores["张三"] = 90
print(scores.get("赵六"))
print("张三" in scores)
for name, score in scores.items():
    print(name, score)
#深 计
#深
#大
#计
#软
#92
#None
#True
#张三 90
#李四 88
#王五 95    

book = {}
for _ in range(3):
    name,phone = input("姓名，电话：").split()
    book[name] = phone 
name = input("查谁？")
print(book.get(name,"查无此人"))
#姓名，电话：张三 1380
#姓名，电话：李四 139
#姓名，电话：王五 137
#查谁？王五
#137