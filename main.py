import sys
from pathlib import Path

ROOT = Path(__file__).parent
APP_DIR = ROOT / "app"
sys.path.insert(0, str(APP_DIR))


def _run_profile(pid: str) -> None:
    import browser_launcher
    import profile_manager

    try:
        resolved_id, profile = profile_manager.get_profile(pid)
    except KeyError as e:
        print(e)
        sys.exit(1)

    try:
        browser_launcher.launch_profile(resolved_id, profile, APP_DIR)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    args = sys.argv[1:]
    if args:
        _run_profile(args[-1])
    else:
        import menu
        menu.run()
