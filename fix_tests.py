import sys
import re
from pathlib import Path

def process_file(filepath):
    p = Path(filepath)
    if not p.exists():
        return
    text = p.read_text("utf-8")
    
    # Remove _reset_db definition block
    text = re.sub(r'def _reset_db\(\):.*?(?=(def |# \-\-\-))', '', text, flags=re.DOTALL)
    
    # Remove all _reset_db() calls
    text = re.sub(r'^[ \t]*_reset_db\(\)\n', '', text, flags=re.MULTILINE)
    
    p.write_text(text, "utf-8")

for f in ["tests/test_phase3.py", "tests/test_phase4.py", "tests/test_phase5.py"]:
    process_file(f)
