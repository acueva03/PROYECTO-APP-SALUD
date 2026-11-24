import os
import sys

# Asegurar que 'backend' y 'backend/tests' estén en sys.path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
tests_dir = os.path.dirname(os.path.abspath(__file__))

if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

if tests_dir not in sys.path:
    sys.path.insert(0, tests_dir)
