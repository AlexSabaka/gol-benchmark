from sympy import IndexedBase, sympify, evaluate

# ... inside your function ...

pattern = "a[0]**2 + a[1] + a[2]" # Example pattern
a = IndexedBase('a') # This 'a' is created here

# Parse the pattern
expr = sympify(pattern, locals={'a': a})

with evaluate(False):
    print(expr.subs({'a': tuple([3, 4, 5])}))

# Find all indexed variables in the pattern that belong to the base 'a'
# Check the NAME of the base, not the object identity

print(f"Expression: {expr}")