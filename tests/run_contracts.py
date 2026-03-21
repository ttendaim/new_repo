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

    # If changed files passed as args, only run contracts for those scripts
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
