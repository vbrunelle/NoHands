import os
import glob

csrf_origins = os.environ.get("CSRF_TRUSTED_ORIGINS", "")
if csrf_origins:
    origins = [o.strip() for o in csrf_origins.split(",") if o.strip()]
    settings_patterns = ["**/settings.py", "settings.py"]
    for pattern in settings_patterns:
        for settings_file in glob.glob(pattern, recursive=True):
            if "venv" not in settings_file and "site-packages" not in settings_file:
                try:
                    with open(settings_file, "a") as f:
                        f.write("\n")
                        f.write("# Auto-configured by NoHands\n")
                        f.write(f"CSRF_TRUSTED_ORIGINS = {origins}\n")
                    print(f"Configured CSRF in {settings_file}: {origins}")
                    break
                except Exception as e:
                    print(f"Failed to update {settings_file}: {e}")
