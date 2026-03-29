import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from gemini_helper import generate_dummy_transaction_ai

print("Calling AI...")
res = generate_dummy_transaction_ai([("Sate Ayam", 15000), ("Es Teh Manis", 4000)])
print("Result:")
print(res)
