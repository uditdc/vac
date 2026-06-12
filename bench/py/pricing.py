def price(base, tax, disc, qty):
    return (base + base * tax - disc) * qty

print(price(base=100, tax=0.1, disc=5, qty=3))
