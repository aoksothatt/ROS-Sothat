import sys
import os

# Ensure prototype root is in sys.path for test discovery
prototype_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if prototype_root not in sys.path:
    sys.path.insert(0, prototype_root)
