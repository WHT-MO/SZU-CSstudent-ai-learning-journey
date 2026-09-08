nums = input("输入一串数字：")
items = nums.split()
items = list(map(int,items))
unique = set(items)
print(len(unique),",".join(map(str,sorted(unique))))

words = input("输入一串英文：")
sen = words.split()
print(len(sen),words.strip().lower())
#运行输出
#输入一串数字：1 10 2 3
#4 1,2,3,10
#输入一串英文：daldj WIDJA
#2 daldj widja