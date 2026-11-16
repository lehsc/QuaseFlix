import re
import unittest
from html.parser import HTMLParser
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "frontend"


class AssetParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.assets = []
        self.scripts = []

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        attribute = "href" if tag in {"a", "link"} else "src" if tag in {"script", "source"} else None
        if attribute and values.get(attribute):
            self.assets.append(values[attribute])
        if tag == "script" and values.get("src"):
            self.scripts.append(values["src"])


class GitHubPagesTests(unittest.TestCase):
    def test_every_page_loads_adapter_before_application_scripts(self):
        for page in [FRONTEND / "index.html", *sorted((FRONTEND / "pages").glob("*.html"))]:
            parser = AssetParser()
            parser.feed(page.read_text(encoding="utf-8"))
            adapter = next((index for index, src in enumerate(parser.scripts) if src.endswith("pages-api.js")), None)
            self.assertIsNotNone(adapter, f"{page.name} does not load pages-api.js")
            local_scripts = [index for index, src in enumerate(parser.scripts) if not src.startswith(("http://", "https://"))]
            self.assertEqual(adapter, min(local_scripts), f"{page.name} loads app code before the Pages adapter")

    def test_relative_assets_exist_and_project_paths_are_portable(self):
        for page in [FRONTEND / "index.html", *sorted((FRONTEND / "pages").glob("*.html"))]:
            parser = AssetParser()
            parser.feed(page.read_text(encoding="utf-8"))
            for asset in parser.assets:
                if asset.startswith(("http://", "https://", "#", "data:")):
                    continue
                relative = asset.split("?", 1)[0]
                if not relative:
                    continue
                target = (page.parent / relative).resolve()
                self.assertTrue(target.is_file(), f"Missing asset referenced by {page.name}: {asset}")
                self.assertTrue(target.is_relative_to(FRONTEND.resolve()), f"Asset escapes frontend/: {asset}")

    def test_demo_covers_all_frontend_api_routes(self):
        adapter = (FRONTEND / "scripts" / "pages-api.js").read_text(encoding="utf-8")
        frontend_calls = "\n".join(path.read_text(encoding="utf-8") for path in (FRONTEND / "scripts").glob("*.js") if path.name != "pages-api.js")
        required_prefixes = {
            "/api/accounts/", "/api/auth/login", "/api/catalog", "/api/genres", "/api/plans",
            "/api/profiles", "/api/registration", "/api/streaming/", "/api/subscription",
        }
        normalized_adapter = adapter.replace("\\/", "/")
        for prefix in required_prefixes:
            self.assertIn(prefix.rstrip("/"), normalized_adapter, f"Pages adapter does not cover {prefix}")
        api_origins = set(re.findall(r"https?://[^/'\"`]+(?=/api)", frontend_calls))
        self.assertEqual(api_origins, {"http://localhost:8000"})
        self.assertIn('const API_ORIGIN = "http://localhost:8000"', adapter)

    def test_demo_video_is_bundled(self):
        video = FRONTEND / "media" / "quaseflix-demo.mp4"
        self.assertTrue(video.is_file(), "The demo player must not depend on a third-party video host")
        self.assertGreater(video.stat().st_size, 10_000)


if __name__ == "__main__":
    unittest.main()
