import os
import sys
import subprocess

def main():
    """Run administrative tasks."""
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "laserforce_ranking.settings")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc

    # start tailwind watcher
    try:
        if os.name == "nt":
            subprocess.Popen(
                ["./assets/css/tailwindcss.exe", "-i", "assets/css/input.css", "-o", "assets/css/output.css", "--watch"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
        else:
            subprocess.Popen(
                ["./assets/css/tailwindcss", "-i", "assets/css/input.css", "-o", "assets/css/output.css", "--watch"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
    except Exception as e:
        print(f"Error starting tailwind watcher: {e}")

    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
