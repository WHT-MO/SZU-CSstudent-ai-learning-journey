n = int(input())
s = n - 4
text = [6, 2, 5, 5, 4, 5, 6, 3, 7, 6]

def match_count(numbers):
    count = 0

    for a in range(max_nums + 1):
        for b in range(max_nums + 1):
            c = a + b

            if (counts[a] + counts[b] + counts[c] == numbers):
                count += 1
    return count

def x_nums(number):
    if number == 0:
        return text[0]
    
    total = 0
    
    while number > 0:
        total += text[number % 10]
        number //= 10

    return total

max_nums = 1111

counts = [
    x_nums(number)
    for number in range(max_nums * 2 + 1)
]
answer = match_count(s)
print(answer)
