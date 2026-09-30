m = input()
n = input()
num1 = m[::-1]
num2 = n[::-1]
a = ""
carry = 0
for i in range(max( len(num1), len(num2))):
    d1 = 0
    d2 = 0
    if len(num1) > i:
        d1 = int(num1[i])
    if len(num2) > i:
        d2 = int(num2[i])
    total = d1 + d2 + carry
    carry = 0
    t = total % 10
    if total >= 10:
        carry = 1
    a += str(t)
if carry != 0:
    a += str(carry)
b = a[::-1]
print(b)