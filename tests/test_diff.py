from multi_agent_code_review.diff import added_lines_by_file

SINGLE_FILE_DIFF = """\
diff --git a/auth.py b/auth.py
--- a/auth.py
+++ b/auth.py
@@ -1,3 +1,5 @@
 import hashlib
+API_KEY = "secret"
+
 def f():
     pass
"""


def test_added_lines_are_extracted():
    assert added_lines_by_file(SINGLE_FILE_DIFF) == {"auth.py": {2, 3}}


def test_context_and_removed_lines_excluded():
    diff = """\
diff --git a/m.py b/m.py
--- a/m.py
+++ b/m.py
@@ -1,3 +1,3 @@
 a = 1
-b = 2
+b = 3
 c = 4
"""
    # only the replacement (new line 2) counts; context and the removed line don't
    assert added_lines_by_file(diff) == {"m.py": {2}}


def test_multiple_files():
    diff = """\
diff --git a/x.py b/x.py
--- a/x.py
+++ b/x.py
@@ -1,1 +1,3 @@
 base
+one
+two
diff --git a/y.py b/y.py
--- a/y.py
+++ b/y.py
@@ -1,1 +1,2 @@
 keep
+added
"""
    assert added_lines_by_file(diff) == {"x.py": {2, 3}, "y.py": {2}}


def test_empty_diff_returns_empty():
    assert added_lines_by_file("") == {}