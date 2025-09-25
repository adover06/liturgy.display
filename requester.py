

#n = int(input('Enter a number cuh'))
n =10

def using_for_loop(n):
    sum = 0
    for i in range(n+1):
        if i%2 == 0:
            sum += i
    return sum


def using_recursion(n):
    if n <= 0:
        return 0
    elif n%2 == 0:
        new = n + using_recursion(n-1)
        return new
    else:
        return using_recursion(n-1)


print(f"number using for loop: {using_for_loop(n)}")
print(f"number using recuraion: {using_recursion(n)}")


def be_awesome(name):
    return f"{name} EEFOOC"

def greet_carlos(greeting_function):
    return greeting_function("EEFFOC")

#print(greet_carlos(be_awesome))

def fetch_lyrics():
    return str(random.randint(1, 100))

