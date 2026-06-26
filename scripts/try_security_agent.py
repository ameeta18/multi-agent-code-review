"""Manual smoke test: run the security agent against a sample insecure diff.

Makes a REAL Gemini call. Run with:
    uv run python scripts/try_security_agent.py
"""

from dotenv import load_dotenv
from google import genai

from multi_agent_code_review.agents.security import review_security

load_dotenv()  # load GEMINI_API_KEY from .env into the environment

SAMPLE_DIFF = """\
diff --git a/auth.py b/auth.py
--- a/auth.py
+++ b/auth.py
@@ -1,3 +1,8 @@
 import hashlib
+
+API_KEY = "sk-live-9f8a7b6c5d4e3f2g1h"
+
+def hash_password(password):
+    return hashlib.md5(password.encode()).hexdigest()
+
+def run_query(user_input):
+    cursor.execute("SELECT * FROM users WHERE name = '" + user_input + "'")
"""


def main() -> None:
    client = genai.Client()  # auto-reads GEMINI_API_KEY from the environment
    findings = review_security(
        client=client,
        model="gemini-2.5-flash",
        diff=SAMPLE_DIFF,
    )

    if not findings:
        print("No findings returned.")
        return

    print(f"{len(findings)} finding(s):\n")
    for f in findings:
        print(f"[{f.severity.value.upper()}] {f.file}:{f.line_start}-{f.line_end}")
        print(f"  {f.title}")
        print(f"  {f.explanation}")
        if f.suggested_fix:
            print(f"  Fix: {f.suggested_fix}")
        print()


if __name__ == "__main__":
    main()