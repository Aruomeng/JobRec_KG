
import subprocess
import sys

print("Running train.py wrapper...")
try:
    result = subprocess.run(
        ['python3', 'train.py'],
        capture_output=True,
        text=True,
        check=True
    )
    print("STDOUT:", result.stdout)
    print("STDERR:", result.stderr)
except subprocess.CalledProcessError as e:
    print("Execution failed!")
    print("STDOUT:", e.stdout)
    print("STDERR:", e.stderr)
except Exception as e:
    print(f"Wrapper error: {e}")
