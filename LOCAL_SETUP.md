# Local Setup Tutorial: Contract Testing with Git Pre-Push Hook

This tutorial walks through the exact steps taken to set up contract-based pipeline
testing locally. When a developer pushes code, a git hook automatically runs tests
to verify pipeline outputs match what consumers expect — blocking the push if they don't.

---

## Prerequisites

- Python 3 installed
- Git repo initialised (or cloned)

---

## Step 1: Set Up a Python Virtual Environment

Since macOS manages its system Python, dependencies are installed in a virtual environment.

```bash
python3 -m venv .venv
source .venv/bin/activate
.venv/bin/pip install pandas pyyaml
```

The `.venv` folder is created in the repo root. Use `.venv/bin/python` to run scripts.

---

## Step 2: Create a Pipeline Script

Each pipeline script must expose a `run()` function that returns a pandas DataFrame.
This is the contract the tests will validate against.

**`pipeline.py`**
```python
import pandas as pd

def run():
    data = {
        "user_id": [1, 2, 3],
        "email": ["a@example.com", "b@example.com", "c@example.com"],
        "created_at": pd.to_datetime(["2024-01-01", "2024-01-02", "2024-01-03"]),
        "amount": [100.0, 200.0, 300.0],
    }
    return pd.DataFrame(data)
```

The `run()` function is the entry point the test runner calls. Any pipeline added
to this system must follow this same pattern.

---

## Step 3: Create the Contracts Directory

Contracts are JSON files that describe what columns and data types a consumer
expects from a pipeline's output.

```bash
mkdir -p tests/contracts
```

---

## Step 4: Write a Contract

Each contract maps to one pipeline script. The `script` field points to the pipeline
file, and `output_columns` lists the expected column names and their pandas dtypes.

**`tests/contracts/pipeline.json`**
```json
{
  "script": "pipeline.py",
  "output_columns": [
    { "name": "user_id",    "dtype": "int64"          },
    { "name": "email",      "dtype": "str"            },
    { "name": "created_at", "dtype": "datetime64[us]" }
  ]
}
```

To add a contract for a second pipeline, create another JSON file:

**`tests/contracts/pipeline_b.json`**
```json
{
  "script": "pipeline_b.py",
  "output_columns": [
    { "name": "user_id",    "dtype": "int64"          },
    { "name": "email",      "dtype": "str"            },
    { "name": "created_at", "dtype": "datetime64[us]" }
  ]
}
```

The runner automatically picks up every `*.json` file in `tests/contracts/` —
no registration needed.

---

## Step 5: Write the Contract Runner

The runner loads each contract, executes the pipeline's `run()` function, and
checks the output DataFrame against the expected columns and dtypes.

**`tests/run_contracts.py`**
```python
import json
import sys
import importlib.util
from pathlib import Path


def load_script(path):
    spec = importlib.util.spec_from_file_location("mod", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def validate(contract_path, repo_root):
    contract = json.loads(Path(contract_path).read_text())
    script_path = repo_root / contract["script"]

    mod = load_script(script_path)
    df = mod.run()

    errors = []
    for col in contract["output_columns"]:
        if col["name"] not in df.columns:
            errors.append(f"  missing column: '{col['name']}'")
        elif str(df[col["name"]].dtype) != col["dtype"]:
            errors.append(f"  '{col['name']}': expected {col['dtype']}, got {df[col['name']].dtype}")

    return errors


if __name__ == "__main__":
    repo_root = Path(__file__).parent.parent
    contracts_dir = repo_root / "tests" / "contracts"

    # If changed files are passed as args, only run contracts for those scripts
    changed_files = set(sys.argv[1:])

    failed = False
    for contract_path in sorted(contracts_dir.glob("*.json")):
        contract = json.loads(contract_path.read_text())
        script = contract["script"]

        if changed_files and script not in changed_files:
            print(f"⏭️  {contract_path.name} skipped (no changes in {script})")
            continue

        errors = validate(contract_path, repo_root)
        if errors:
            print(f"❌ {contract_path.name}:")
            print("\n".join(errors))
            failed = True
        else:
            print(f"✅ {contract_path.name} passed")

    sys.exit(1 if failed else 0)
```

**Key behaviour:**
- Run with no args → all contracts are validated
- Run with filenames as args → only contracts for those scripts run, others are skipped

```bash
# run all contracts
.venv/bin/python tests/run_contracts.py

# run only contracts for pipeline_b.py
.venv/bin/python tests/run_contracts.py pipeline_b.py
```

---

## Step 6: Create the Pre-Push Git Hook

Git hooks live in `.git/hooks/`. The `pre-push` hook runs automatically before
every `git push`. If it exits with a non-zero code, the push is blocked.

**`.git/hooks/pre-push`**
```bash
#!/bin/bash
echo "Running contract tests..."

# Detect which Python files changed in this push
CHANGED=$(git diff --name-only HEAD@{1} HEAD 2>/dev/null || git diff --name-only $(git hash-object -t tree /dev/null) HEAD)

# Pass changed files to runner so only relevant contracts are tested
.venv/bin/python tests/run_contracts.py $CHANGED

if [ $? -ne 0 ]; then
  echo "❌ Push blocked: contract tests failed"
  exit 1
fi
echo "✅ All contracts passed"
```

Make it executable:

```bash
chmod +x .git/hooks/pre-push
```

The hook detects which files changed and passes them to the runner. Only contracts
linked to changed scripts are executed — unchanged pipelines are skipped.

---

## Final Repository Structure

```
new_repo/
├── pipeline.py                    ← pipeline A (exposes run() → DataFrame)
├── pipeline_b.py                  ← pipeline B (exposes run() → DataFrame)
├── tests/
│   ├── contracts/
│   │   ├── pipeline.json          ← contract for pipeline.py
│   │   └── pipeline_b.json        ← contract for pipeline_b.py
│   └── run_contracts.py           ← contract runner
└── .git/hooks/pre-push            ← git hook (auto-runs on push)
```

---

## How It Works End to End

```
1. Developer edits pipeline_b.py
2. git push triggered
3. pre-push hook fires
4. Detects only pipeline_b.py changed
5. Passes "pipeline_b.py" to run_contracts.py
6. pipeline.json → skipped
7. pipeline_b.json → runs validation
8a. Pass → push allowed ✅
8b. Fail → push blocked ❌ with error details
```

---

## Adding a New Pipeline

1. Create `my_pipeline.py` with a `run()` function returning a DataFrame
2. Create `tests/contracts/my_pipeline.json` with expected columns and dtypes
3. Done — the hook picks it up automatically on the next push

No changes needed to the hook or runner.
