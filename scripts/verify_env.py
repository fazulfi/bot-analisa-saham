# scripts/verify_env.py
import pandas as pd, numpy as np
from datetime import datetime
print("Python:", __import__('sys').version.split()[0])
print("pandas:", pd.__version__)
print("numpy:", np.__version__)
try:
    import ta
    print("ta library: OK")
except Exception as e:
    print("ta import error:", e)
