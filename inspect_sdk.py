import inspect
import cryptomarket

print("\n--- Classes in top level ---")
for name, obj in inspect.getmembers(cryptomarket):
    if inspect.isclass(obj):
        print(f"Class: {name}")

print("\n--- Classes in cryptomarket.client ---")
try:
    import cryptomarket.client
    for name, obj in inspect.getmembers(cryptomarket.client):
        if inspect.isclass(obj):
            print(f"Class: {name}")
except ImportError:
    print("Could not import .client")
