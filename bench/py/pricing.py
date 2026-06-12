def price(base, tax, discount, qty):
    return (base + base * tax - discount) * qty

print(price(base=100, tax=0.1, discount=5, qty=3))
