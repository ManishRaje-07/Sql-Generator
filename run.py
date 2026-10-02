"""
Convenience launcher for Multilingual Natural Language to SQL Query Generator.
Run with: python run.py
"""

import sys
import uvicorn

# Set UTF-8 encoding on Windows consoles
if sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

if __name__ == "__main__":
    print("=" * 70)
    print("  Multilingual Natural Language to SQL Query Generator")
    print("  Supported Languages: English | हिन्दी (Hindi) | मराठी (Marathi)")
    print("=" * 70)
    
    host = "127.0.0.1"
    port = 8000
    print(f"\nLaunching SQL generator at: http://{host}:{port}")
    print("      Press Ctrl + C to stop the server.\n")

    uvicorn.run("app:app", host=host, port=port, reload=True)
