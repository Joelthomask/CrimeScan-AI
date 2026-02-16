import os.path as osp
import sys
import logging
import warnings

# ------------------------------
# 1. SILENT STDOUT / STDERR
# ------------------------------
class _SilentIO:
    def write(self, *_):
        pass
    def flush(self):
        pass

# Keep a handle in case we want to restore later
_ORIG_STDOUT = sys.stdout
_ORIG_STDERR = sys.stderr

sys.stdout = _SilentIO()
sys.stderr = _SilentIO()

# ------------------------------
# 2. SILENT WARNINGS
# ------------------------------
warnings.filterwarnings("ignore")

# ------------------------------
# 3. IMPORTS (AFTER SILENCE)
# ------------------------------
import basicsr
import hi_diff


if __name__ == '__main__':
    root_path = osp.abspath(osp.join(__file__, osp.pardir))

    # Optional: restore minimal stdout for final status
    sys.stdout = _ORIG_STDOUT


    # Silence again during execution
    sys.stdout = _SilentIO()
    sys.stderr = _SilentIO()

    basicsr.test_pipeline(root_path)

    # Restore stdout for final message
    sys.stdout = _ORIG_STDOUT
