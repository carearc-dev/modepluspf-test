#!/usr/bin/env python3
"""Static checks for the client-facing Mode Plus TOP A/B comparison preview."""
from __future__ import annotations

from html.parser import HTMLParser
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]


class Page(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.sections: list[str] = []
        self.ids: list[str] = []
        self.links: list[str] = []
        self.images: list[str] = []
        self.h1_count = 0
        self.course_cards = 0
        self.pickup_cards = 0
        self.number_text = ""
        self.body_text = ""
        self.in_numbers = False
        self.in_body = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr = dict(attrs)
        classes = set((attr.get("class") or "").split())
        if tag == "body":
            self.in_body = True
        if tag == "section" and attr.get("id"):
            self.sections.append(attr["id"])
        if attr.get("id"):
            self.ids.append(attr["id"])
        if tag == "a" and attr.get("href"):
            self.links.append(attr["href"])
        if tag == "img" and attr.get("src"):
            self.images.append(attr["src"])
        if tag == "h1":
            self.h1_count += 1
        if "course-card" in classes:
            self.course_cards += 1
        if "pickup-card" in classes:
            self.pickup_cards += 1
        if "numbers" in classes:
            self.in_numbers = True

    def handle_endtag(self, tag: str) -> None:
        if tag == "body":
            self.in_body = False
        if tag == "dl":
            self.in_numbers = False

    def handle_data(self, data: str) -> None:
        if self.in_body:
            self.body_text += data
        if self.in_numbers:
            self.number_text += data


def parse(name: str) -> tuple[str, Page]:
    text = (ROOT / name).read_text(encoding="utf-8")
    parser = Page()
    parser.feed(text)
    return text, parser


def require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def compact(value: str) -> str:
    return re.sub(r"\s+", "", value)


def main() -> int:
    errors: list[str] = []
    a_text, a = parse("index.html")
    b_text, b = parse("top-b.html")
    compare_text = (ROOT / "top-compare.html").read_text(encoding="utf-8")
    css_text = (ROOT / "top-compare.css").read_text(encoding="utf-8")
    js_text = (ROOT / "top-compare.js").read_text(encoding="utf-8")

    for name, text, page in (("A", a_text, a), ("B", b_text, b)):
        require('name="robots" content="noindex, nofollow"' in text, f"{name}: noindex preview metadata is missing", errors)
        require(page.h1_count == 1, f"{name}: expected exactly one H1", errors)
        values_photo = re.search(r'<div class="values-photo">\s*(<img\b[^>]*>)', text)
        require(bool(values_photo) and 'src="img/renewal/kiyosumi-classroom.webp"' in values_photo.group(1),
                f"{name}: About must use the approved unoccupied classroom photo", errors)
        require(bool(values_photo) and 'height="556"' in values_photo.group(1) and '教室のレッスン空間' in values_photo.group(1),
                f"{name}: About photo dimensions or descriptive alt are outdated", errors)
        require("img/renewal/adult-lesson.webp" not in page.images,
                f"{name}: the replaced instructor photo must not return to TOP", errors)
        hero_match = re.search(r'<div class="hero-media">\s*<img\b[^>]*>\s*</div>', text)
        require(bool(hero_match), f"{name}: expected one photo-only hero", errors)
        require(page.pickup_cards == 3, f"{name}: expected exactly three pickup cards", errors)
        require(page.course_cards == 6, f"{name}: expected exactly six course cards", errors)
        require(page.sections == ["top", "news", "courses", "about", "teachers", "voices", "access", "experience"], f"{name}: section sequence changed: {page.sections}", errors)
        require("数字で見るモードプラス" in text, f"{name}: stats heading is missing", errors)
        require(len(page.ids) == len(set(page.ids)), f"{name}: duplicate id found", errors)

    require(a.sections == b.sections, "A/B: section sequence must match", errors)
    require(a.course_cards == b.course_cards == 6, "A/B: course counts must match", errors)
    require(a.pickup_cards == b.pickup_cards == 3, "A/B: pickup counts must match", errors)
    require(compact(a.number_text) == compact(b.number_text), "A/B: Mode Plus stats must match", errors)
    require(a.links == b.links, "A/B: all page links must match in the same order", errors)
    require(a.images == b.images, "A/B: all image sources must match in the same order", errors)
    require(compact(a.body_text) == compact(b.body_text), "A/B: body copy must match", errors)
    for href in ("group.html", "https://modepluspf.com/greeting/", "https://modepluspf.com/teacher/", "https://modepluspf.com/faq/"):
        require(href in a.links and href in b.links, f"A/B: required route missing or different: {href}", errors)

    for filename in ("top-compare.html", "top-compare.css", "top-compare.js"):
        require((ROOT / filename).is_file(), f"comparison asset missing: {filename}", errors)
    require('src="index.html"' in compare_text and 'data-src="top-b.html"' in compare_text, "comparison: A/B iframe sources are missing", errors)
    require('<iframe' in compare_text and 'id="site-preview"' in compare_text, "comparison: iframe preview is missing", errors)
    require('aria-pressed="true"' in compare_text and 'aria-pressed="false"' in compare_text, "comparison: selected state is not exposed", errors)
    require('target="_blank"' in compare_text and 'Aを単体で開く' in compare_text and 'Bを単体で開く' in compare_text, "comparison: standalone links are missing", errors)
    require('.compare-shell .device-frame.is-mobile{width:406px}' in css_text and 'border:8px solid' in css_text, "comparison: expected 390px inner mobile frame is missing", errors)
    require('max-width:100%' in css_text, "comparison: small-screen overflow guard is missing", errors)
    require('prefers-reduced-motion:reduce' in css_text, "comparison: reduced-motion support is missing", errors)
    require('preview.src = variant.src' in js_text and 'preview.title = variant.title' in js_text, "comparison: variant switching logic is missing", errors)
    require('frame.classList.toggle(\'is-mobile\', mobile)' in js_text, "comparison: device switching logic is missing", errors)
    require('<script>' not in compare_text, "comparison: inline scripts are not allowed", errors)
    require('http://' not in compare_text and 'https://' not in css_text and 'https://' not in js_text, "comparison: unexpected external dependency", errors)

    for relative in b.images:
        if not relative.startswith(("http://", "https://", "data:")):
            require((ROOT / relative).is_file(), f"B: missing image asset: {relative}", errors)
    b_styles = re.findall(r'<link[^>]+href="([^"]+\.css)"', b_text)
    require("home-b.css" in b_styles and (ROOT / "home-b.css").is_file(), "B: dedicated stylesheet is missing", errors)

    if errors:
        print("FAIL:")
        print("\n".join(f"- {error}" for error in errors))
        return 1
    print("PASS: A/B sections, routes, photo heroes, comparison UI, and local assets")
    return 0


if __name__ == "__main__":
    sys.exit(main())
