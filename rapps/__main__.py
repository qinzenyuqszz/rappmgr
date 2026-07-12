"""Allow running with: python -m rapps"""
import sys
import os

# Ensure the python/ directory is on sys.path
_script_dir = os.path.dirname(os.path.abspath(__file__))
_python_dir = os.path.dirname(_script_dir)
if _python_dir not in sys.path:
    sys.path.insert(0, _python_dir)

from rapps.main import main

if __name__ == "__main__":
    main()
