"""Non-mutating HR deployment report; credentials are read only from service configuration."""
import argparse
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--expected-revision', required=True, help='Full reviewed Git commit SHA.')
    parser.add_argument('--probe-adapters', action='store_true',
                        help='Authenticate TLS SMTP (no send) and test actual ClamAV acceptance/EICAR detection.')
    args = parser.parse_args()
    try:
        from backend.config import get_settings
        from backend.modules.hr.readiness import report
        result = report(get_settings(), args.expected_revision, args.probe_adapters)
    except Exception:
        # Settings validation can include secret values in its exception text.
        result = dict(checks_passed=False, production_ready=False,
                      error='Cannot load deployment configuration or dependencies; check them privately.')
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result['checks_passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
