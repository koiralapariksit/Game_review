import json
import urllib.request
from pathlib import Path
from django.conf import settings
from django.core.management.base import BaseCommand
from players.models import Player
from transfers.models import Transfer


class Command(BaseCommand):
    help = "Downloads and binds the 2026-27 FC Barcelona player image bundle into Django media and updates models."

    def handle(self, *args, **options):
        bundle_path = Path(settings.BASE_DIR) / "barcelona_images_bundle.json"
        if not bundle_path.exists():
            self.stderr.write(self.style.ERROR(f"Missing {bundle_path}"))
            return

        with open(bundle_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        media_dir = Path(settings.MEDIA_ROOT) / data["django_media_subfolder"]
        media_dir.mkdir(parents=True, exist_ok=True)

        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

        success_count = 0
        for p in data["players"]:
            filename = Path(p["django_file_path"]).name
            dest_path = media_dir / filename
            media_url_path = f"{settings.MEDIA_URL}{data['django_media_subfolder']}{filename}"

            try:
                req = urllib.request.Request(p["image_url"], headers=headers)
                with urllib.request.urlopen(req, timeout=15) as response:
                    img_bytes = response.read()

                # 1. Save directly to MEDIA_ROOT/players/barcelona/
                with open(dest_path, "wb") as img_file:
                    img_file.write(img_bytes)

                # 2. Attach to Player model profile_image (serving from media URL)
                updated_player = Player.objects.filter(jersey_number=p["jersey_number"]).update(
                    profile_image=media_url_path
                )

                # 3. Also update transfers model if player is listed in transfers
                Transfer.objects.filter(player_name=p["name"]).update(
                    image_url=media_url_path
                )

                success_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f"[OK] #{p['jersey_number']} {p['name']} -> {media_url_path}")
                )
            except Exception as exc:
                self.stderr.write(
                    self.style.ERROR(f"[ERR] #{p['jersey_number']} {p['name']}: {exc}")
                )

        self.stdout.write(
            self.style.SUCCESS(f"\nSuccessfully downloaded and bound {success_count}/{len(data['players'])} images!")
        )

