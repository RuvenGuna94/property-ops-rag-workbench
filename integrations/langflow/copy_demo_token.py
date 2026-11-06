"""WSL-only clipboard helper. Copies one operator credential; never prints it."""
import argparse
import json
from pathlib import Path
import subprocess

if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--credentials', required=True)
    p.add_argument('--identity', choices=['operator_a', 'operator_b'], required=True)
    a = p.parse_args()
    token = json.loads(Path(a.credentials).read_text(encoding='utf-8'))[a.identity]['token']
    subprocess.run(['/mnt/c/Windows/System32/clip.exe'], input=token.encode('utf-16le'), check=True)
    print('Operator credential copied. Paste only into the intended masked credential field, then clear clipboard history.')
