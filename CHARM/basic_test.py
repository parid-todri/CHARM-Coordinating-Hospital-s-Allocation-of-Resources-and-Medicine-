#!/usr/bin/env python3
"""Minimal test to check if script execution works."""
import os
import sys

output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "basic_test_output.txt")
with open(output_path, "w") as f:
    f.write(f"Python: {sys.version}\n")
    f.write(f"CWD: {os.getcwd()}\n")
    f.write(f"Script dir: {os.path.dirname(os.path.abspath(__file__))}\n")
    f.write(f"Files: {os.listdir('.')}\n")
    
    # Test basic imports
    try:
        import pandas
        f.write(f"pandas: {pandas.__version__}\n")
    except ImportError as e:
        f.write(f"pandas import error: {e}\n")
    
    try:
        import sklearn
        f.write(f"sklearn: {sklearn.__version__}\n")
    except ImportError as e:
        f.write(f"sklearn import error: {e}\n")
    
    # Test charm import
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import charm
        f.write(f"charm: {charm.__version__}\n")
    except Exception as e:
        f.write(f"charm import error: {e}\n")
    
    f.write("DONE\n")
