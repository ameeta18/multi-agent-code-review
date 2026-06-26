"""Manual smoke test: run the full review graph on a sample diff.

Makes real Gemini calls (three specialists + one synthesizer). Run with:
    uv run python scripts/try_graph.py
"""

from dotenv import load_dotenv
from google import genai

from multi_agent_code_review.graph import build_graph

load_dotenv()

SAMPLE_DIFF = """\
diff --git a/payments.py b/payments.py
--- a/payments.py
+++ b/payments.py
@@ -1,2 +1,16 @@
 import hashlib
+import pickle
+
+STRIPE_KEY = "sk_live_51H8xQ2eZvKYlo3"
+
+def process(data, user, amount, currency, retries, discount, tax, region):
+    obj = pickle.loads(data)
+    token = hashlib.md5(str(amount).encode()).hexdigest()
+    total = amount
+    if amount > 0:
+        if currency == "USD":
+            if region == "US":
+                if discount:
+                    total = amount - discount
+    return total
 x = 1
"""


def main() -> None:
    client = genai.Client()
    graph = build_graph(
        client=client,
        specialist_model="gemini-2.5-flash",
        synthesizer_model="gemini-2.5-flash",  # dev: Flash for cost; Pro later
    )
    result = graph.invoke({"diff": SAMPLE_DIFF})

    raw, filtered = result["findings"], result["filtered"]
    print(f"Raw findings from all three specialists: {len(raw)}")
    print(f"After deterministic filters: {len(filtered)}")
    print("\n" + "=" * 70)
    print("FINAL PR COMMENT")
    print("=" * 70 + "\n")
    print(result["comment"])


if __name__ == "__main__":
    main()