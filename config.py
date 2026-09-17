"""
config.py
Shared constants used by both conftest.py and the test module.
Having them here avoids the fragile `import conftest` pattern.
"""
import os
from pathlib import Path

REPO_ROOT     = Path(__file__).parent
CREDENTIALS   = REPO_ROOT / "user-for-test_credentials.csv"
TEMPLATE_FILE = REPO_ROOT / "template.yaml"

REGION     = "eu-north-1"
STACK_NAME = "stack-test"

