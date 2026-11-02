#!/usr/bin/env python
"""
Production Pre-Flight Diagnostic Script for FC Barcelona Intelligence Platform (Culer)
Executes system readiness checks for database, caching, static assets, environment variables,
and external intelligence API providers.
"""

import os
import sys
from pathlib import Path

# Set up project path and Django environment
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

try:
    from dotenv import load_dotenv
    load_dotenv(BASE_DIR / ".env")
except ImportError:
    pass

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "culer.settings")

try:
    import django
    django.setup()
    from django.conf import settings
    from django.db import connection
    from django.db.migrations.executor import MigrationExecutor
    from django.core.cache import cache
except Exception as exc:
    print(f"\n[FATAL] Failed to initialize Django environment: {exc}")
    sys.exit(1)


def mask_key(key: str) -> str:
    """Safely mask API key or secret for reporting."""
    if not key:
        return ""
    if len(key) <= 8:
        return "•" * len(key)
    return f"{key[:4]}••••••••{key[-4:]}"


class PreFlightCheck:
    def __init__(self):
        self.results = []
        self.has_critical_failure = False

    def add_result(self, name: str, status: str, details: str):
        self.results.append({
            "name": name,
            "status": status,
            "details": details,
        })
        if status == "FAIL":
            self.has_critical_failure = True

    def check_environment(self):
        # 1. SECRET_KEY
        secret_key = getattr(settings, "SECRET_KEY", "")
        if not secret_key or "django-insecure" in secret_key:
            self.add_result(
                "SECRET_KEY",
                "WARN" if settings.DEBUG else "FAIL",
                "Using insecure/default secret key. Must be a high-entropy secret in production."
            )
        elif len(secret_key) < 50:
            self.add_result(
                "SECRET_KEY",
                "WARN",
                f"Secret key length is {len(secret_key)} chars (>= 50 recommended for production)."
            )
        else:
            self.add_result("SECRET_KEY", "PASS", f"Cryptographically strong key configured ({len(secret_key)} chars).")

        # 2. DEBUG
        if settings.DEBUG:
            self.add_result("DEBUG Mode", "WARN", "DEBUG=True is active. Set DEBUG=False for production deployment.")
        else:
            self.add_result("DEBUG Mode", "PASS", "DEBUG=False verified for production.")

        # 3. ALLOWED_HOSTS
        allowed = getattr(settings, "ALLOWED_HOSTS", [])
        if not allowed or allowed == ["*"]:
            status = "WARN" if settings.DEBUG else "FAIL"
            self.add_result("ALLOWED_HOSTS", status, f"Hosts configured: {allowed}. Wildcards unsafe in production.")
        else:
            self.add_result("ALLOWED_HOSTS", "PASS", f"Configured hosts: {', '.join(allowed)}")

    def check_database(self):
        try:
            connection.ensure_connection()
            vendor = connection.vendor
            db_name = connection.settings_dict.get("NAME", "unknown")
            db_host = connection.settings_dict.get("HOST", "localhost") or "localhost"

            if vendor == "postgresql":
                self.add_result("Database (PostgreSQL)", "PASS", f"Connected to PostgreSQL ({db_name}@{db_host}).")
            else:
                status = "WARN" if not settings.DEBUG else "PASS"
                self.add_result(
                    f"Database ({vendor})",
                    status,
                    f"Connected to {vendor} ({db_name}). PostgreSQL recommended for production."
                )

            # Check migrations
            try:
                executor = MigrationExecutor(connection)
                targets = executor.loader.graph.leaf_nodes()
                plan = executor.migration_plan(targets)
                if plan:
                    self.add_result("Database Migrations", "WARN", f"{len(plan)} unapplied migration(s) detected.")
                else:
                    self.add_result("Database Migrations", "PASS", "All migrations up-to-date.")
            except Exception as mig_err:
                self.add_result("Database Migrations", "WARN", f"Could not inspect migrations: {mig_err}")

        except Exception as err:
            self.add_result("Database Connection", "FAIL", f"Failed to connect to database: {err}")

    def check_cache_and_redis(self):
        redis_url = getattr(settings, "REDIS_URL", None)
        backend = settings.CACHES.get("default", {}).get("BACKEND", "")
        test_key = "__preflight_test_ping__"

        try:
            cache.set(test_key, "pong", timeout=10)
            val = cache.get(test_key)
            cache.delete(test_key)

            if val == "pong":
                if "redis" in backend.lower() or redis_url:
                    self.add_result("Cache / Redis", "PASS", f"Redis cache responsive ({backend}).")
                else:
                    self.add_result(
                        "Cache Backend",
                        "PASS" if settings.DEBUG else "WARN",
                        f"Cache operational using {backend.split('.')[-1]}. (Redis recommended in prod)."
                    )
            else:
                self.add_result("Cache / Redis", "FAIL", "Cache write/read test failed to retrieve expected value.")
        except Exception as err:
            if redis_url:
                self.add_result("Cache / Redis", "FAIL", f"Failed connecting to Redis cache at {redis_url}: {err}")
            else:
                self.add_result("Cache Backend", "WARN", f"Cache backend check raised: {err}")

    def check_static_files(self):
        static_root = Path(getattr(settings, "STATIC_ROOT", BASE_DIR / "staticfiles"))
        dirs = getattr(settings, "STATICFILES_DIRS", [])

        if not static_root.exists() or not any(static_root.iterdir()):
            self.add_result(
                "Static Assets",
                "WARN",
                f"STATIC_ROOT '{static_root.name}' empty or uncollected. Run 'python manage.py collectstatic'."
            )
        else:
            manifest = static_root / "staticfiles.json"
            if manifest.exists():
                self.add_result("Static Assets", "PASS", "WhiteNoise manifest (staticfiles.json) generated.")
            else:
                self.add_result("Static Assets", "PASS", f"Static assets present in {static_root.name}/.")

    def check_ai_intelligence(self):
        openrouter_key = os.environ.get("OPENROUTER_API_KEY") or os.environ.get("AI_API_KEY")
        if openrouter_key and openrouter_key.strip():
            self.add_result(
                "OpenRouter AI Agent",
                "PASS",
                f"Key detected ({mask_key(openrouter_key)}). Generative intelligence active."
            )
        else:
            self.add_result(
                "OpenRouter AI Agent",
                "WARN",
                "OPENROUTER_API_KEY not configured. Rule-based offline intelligence fallback active."
            )

    def check_football_api(self):
        football_key = os.environ.get("FOOTBALL_DATA_API_KEY")
        if football_key and football_key.strip():
            self.add_result(
                "Football-Data.org API",
                "PASS",
                f"Key detected ({mask_key(football_key)}). Live match data sync enabled."
            )
        else:
            self.add_result(
                "Football-Data.org API",
                "WARN",
                "FOOTBALL_DATA_API_KEY not set. Offline seed & matchday simulation active."
            )

    def run_all(self):
        self.check_environment()
        self.check_database()
        self.check_cache_and_redis()
        self.check_static_files()
        self.check_ai_intelligence()
        self.check_football_api()

    def print_summary(self):
        title = "CULER FC BARCELONA PLATFORM — PRODUCTION PRE-FLIGHT DIAGNOSTIC"
        divider = "=" * 80
        sub_divider = "-" * 80

        print(f"\n{divider}")
        print(f" {title}")
        print(f"{divider}")
        print(f"{'CHECK':<25} | {'STATUS':<7} | {'DETAILS'}")
        print(sub_divider)

        for res in self.results:
            status = res["status"]
            # Color coding for terminal output
            if status == "PASS":
                status_formatted = "\033[92mPASS\033[0m" if sys.stdout.isatty() else "PASS"
            elif status == "WARN":
                status_formatted = "\033[93mWARN\033[0m" if sys.stdout.isatty() else "WARN"
            else:
                status_formatted = "\033[91mFAIL\033[0m" if sys.stdout.isatty() else "FAIL"

            name = res["name"]
            details = res["details"]
            print(f"{name:<25} | {status_formatted:<7} | {details}")

        print(divider)

        pass_count = sum(1 for r in self.results if r["status"] == "PASS")
        warn_count = sum(1 for r in self.results if r["status"] == "WARN")
        fail_count = sum(1 for r in self.results if r["status"] == "FAIL")

        print(f"Summary: {pass_count} Passed, {warn_count} Warnings, {fail_count} Failed.")

        if self.has_critical_failure:
            print("Status: \033[91mPRE-FLIGHT CHECKS FAILED\033[0m (resolve critical failures before deployment).")
            print(f"{divider}\n")
            return 1
        else:
            print("Status: \033[92mSYSTEM READY FOR OPERATION\033[0m")
            print(f"{divider}\n")
            return 0


def main():
    checker = PreFlightCheck()
    checker.run_all()
    exit_code = checker.print_summary()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
