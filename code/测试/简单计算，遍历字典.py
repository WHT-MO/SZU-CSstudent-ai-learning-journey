#c1
nums = int(input())
print(nums * 2)
#c2
nums = list(map(int,input().split()))
total = 0
for x in (nums):
     total = x + total
print(total)
#c3
freq = {}
words = input()                  

for ch in words:                 
    freq[ch] = freq.get(ch,0)+1  
                                 

for k, v in freq.items():        
    print(k, v)                  