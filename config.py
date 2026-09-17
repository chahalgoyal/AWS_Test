"""
config.py
Shared constants used by both conftest.py and the test module.
Having them here avoids the fragile `import conftest` pattern.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

REPO_ROOT     = Path(__file__).parent
TEMPLATE_FILE = REPO_ROOT / "template.yaml"

REGION     = "eu-north-1"
STACK_NAME = "stack-test"


SIGN_IN_URL = os.getenv("AWS_SIGN_IN_URL")
USERNAME = os.getenv("AWS_USERNAME")
PASSWORD = os.getenv("AWS_PASSWORD")