from ai_drama_runtime.store import RuntimeStore
from pathlib import Path
import re

DATA_ROOT = Path("/tmp/ai-drama-real-model-test")
REV_ID = "01c323cadbc44a05ba81ac7e2eee716b"

store = RuntimeStore(DATA_ROOT / "runtime.db", DATA_ROOT / "objects")

rev = store.get_revision(REV_ID)
text = store.read_text(rev.content_object_id)

print("Revision ID:", REV_ID)
print("Total length:", len(text))
print("\n=== ALL H2 HEADERS ===")
h2 = re.findall(r'^##\s*(.+)$', text, re.MULTILINE)
for h in h2[:30]:
    print(f"  ## {h}")
print(f"\nTotal H2 headers: {len(h2)}")

print("\n=== SCRIPT LAST 1500 CHARS ===")
print(text[-1500:])

store.close()
