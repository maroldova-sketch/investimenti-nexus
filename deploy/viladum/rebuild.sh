#!/usr/bin/env bash
set -euo pipefail
BUNDLE=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)
PYTHON_BIN=${VILADUM_PYTHON:-python3}
command -v "$PYTHON_BIN" >/dev/null
"$PYTHON_BIN" -c 'import sys; assert sys.version_info >= (3,12), "Use Python 3.12+; set VILADUM_PYTHON to its command if needed"'
if [[ ! -x "$BUNDLE/.venv/bin/python" ]]; then "$PYTHON_BIN" -m venv "$BUNDLE/.venv"; fi
"$BUNDLE/.venv/bin/python" -c 'import sys; assert sys.version_info >= (3,12), "Existing .venv needs Python 3.12+"'
"$BUNDLE/.venv/bin/python" -m pip install -r "$BUNDLE/requirements-build.txt"
"$BUNDLE/.venv/bin/python" "$BUNDLE/source/build_brochure.py"
"$BUNDLE/.venv/bin/python" "$BUNDLE/source/build_pdf.py"
"$BUNDLE/.venv/bin/python" "$BUNDLE/scripts/manifest.py"
"$BUNDLE/.venv/bin/python" "$BUNDLE/scripts/verify.py" --bundle
