import sys
import os
from pathlib import Path

def check_collisions():
    print(f"Python Version: {sys.version}")
    print(f"Executable: {sys.executable}")
    print("\n--- sys.path ---")
    for p in sys.path:
        print(p)
    
    print("\n--- Potential Collisions in Current Directory ---")
    conflicting_names = ['sqlalchemy', 'util', 'database', 'models', 'utils']
    for name in conflicting_names:
        py_file = Path(name + ".py")
        folder = Path(name)
        if py_file.exists():
            print(f"FOUND: {py_file} (File)")
        if folder.exists() and folder.is_dir():
            print(f"FOUND: {folder}/ (Directory)")

    print("\n--- SQLAlchemy Info ---")
    try:
        import sqlalchemy
        print(f"SQLAlchemy Location: {sqlalchemy.__file__}")
    except Exception as e:
        print(f"SQLAlchemy Import Failed: {e}")

if __name__ == "__main__":
    check_collisions()
