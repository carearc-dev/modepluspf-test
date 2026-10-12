#!/usr/bin/env python3
"""Regression checks for the anonymous teacher introduction on both TOP variants.

The TOP is deliberately an introduction to the breadth of the teaching team.
Individual names and biographies belong to the official teacher listing, not here.
Uses only the Python standard library so it can run with the other static checks.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from html.parser import HTMLParser
from pathlib import Path
import re
import sys


ROOT = Path(__file__).resolve().parents[1]
OFFICIAL_TEACHER_URL = "https://modepluspf.com/teacher/"
PERSONAL_NAMES = ("和田 蕗子", "和田蕗子", "永本 志帆", "永本志帆", "後藤 亜季", "後藤亜季")
EXPECTED_DISCIPLINES = ("ピアノ", "うた", "リトミック", "ソルフェージュ")
EXPECTED_PORTRAITS = (
    "img/teacher-wada-fukiko.webp",
    "img/teacher-nagamoto-shiho.webp",
    "img/teacher-goto-aki.webp",
)
VOID_TAGS = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}


def class_names(attrs: dict[str, str | None]) -> set[str]:
    return set((attrs.get("class") or "").split())


@dataclass
class TeacherIntro:
    elements: list[tuple[str, dict[str, str | None]]] = field(default_factory=list)
    text: list[str] = field(default_factory=list)
    images: list[dict[str, str | None]] = field(default_factory=list)
    links: list[dict[str, str | None]] = field(default_factory=list)
    gallery_images: list[dict[str, str | None]] = field(default_factory=list)
    gallery_links: list[dict[str, str | None]] = field(default_factory=list)
    gallery_tag: str | None = None
    gallery_attrs: dict[str, str | None] | None = None
    gallery_text: list[str] = field(default_factory=list)
    disciplines: list[str] = field(default_factory=list)
    expertise_text: list[str] = field(default_factory=list)
    summary_text: list[str] = field(default_factory=list)
    gallery_depth: int | None = None
    disciplines_depth: int | None = None
    expertise_depth: int | None = None
    summary_depth: int | None = None


class TeacherSectionParser(HTMLParser):
    """Extract only the section whose id is ``teachers`` with structural context."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.depth = 0
        self.teacher_depth: int | None = None
        self.result = TeacherIntro()

    @property
    def in_teachers(self) -> bool:
        return self.teacher_depth is not None

    def handle_starttag(self, tag: str, attrs_list: list[tuple[str, str | None]]) -> None:
        attrs = dict(attrs_list)
        starts_teachers = tag == "section" and attrs.get("id") == "teachers"
        if starts_teachers:
            if self.teacher_depth is not None:
                raise AssertionError("Nested teachers section is not supported")
            self.teacher_depth = self.depth

        if self.in_teachers:
            result = self.result
            result.elements.append((tag, attrs))
            classes = class_names(attrs)
            if "teacher-portraits" in classes:
                result.gallery_depth = self.depth
                result.gallery_tag = tag
                result.gallery_attrs = attrs
            if "teacher-disciplines" in classes:
                result.disciplines_depth = self.depth
            if "teacher-expertise" in classes:
                result.expertise_depth = self.depth
            if "teacher-summary" in classes:
                result.summary_depth = self.depth
            if tag == "img":
                result.images.append(attrs)
                if result.gallery_depth is not None and self.depth > result.gallery_depth:
                    result.gallery_images.append(attrs)
            if tag == "a":
                result.links.append(attrs)
                if result.gallery_depth is not None and self.depth > result.gallery_depth:
                    result.gallery_links.append(attrs)

        if tag not in VOID_TAGS:
            self.depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag in VOID_TAGS:
            return
        self.depth -= 1
        if self.in_teachers:
            result = self.result
            if result.gallery_depth == self.depth:
                result.gallery_depth = None
            if result.disciplines_depth == self.depth:
                result.disciplines_depth = None
            if result.expertise_depth == self.depth:
                result.expertise_depth = None
            if result.summary_depth == self.depth:
                result.summary_depth = None
            if tag == "section" and self.depth == self.teacher_depth:
                self.teacher_depth = None

    def handle_data(self, data: str) -> None:
        if not self.in_teachers:
            return
        clean = re.sub(r"\s+", " ", data).strip()
        if not clean:
            return
        self.result.text.append(clean)
        if self.result.disciplines_depth is not None:
            self.result.disciplines.append(clean)
        if self.result.expertise_depth is not None:
            self.result.expertise_text.append(clean)
        if self.result.summary_depth is not None:
            self.result.summary_text.append(clean)
        if self.result.gallery_depth is not None:
            self.result.gallery_text.append(clean)


def parse_page(filename: str) -> TeacherIntro:
    parser = TeacherSectionParser()
    parser.feed((ROOT / filename).read_text(encoding="utf-8"))
    parser.close()
    return parser.result


def normalise(items: list[str]) -> str:
    return re.sub(r"\s+", "", " ".join(items))


def require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def validate(label: str, intro: TeacherIntro, errors: list[str]) -> None:
    classes = [class_names(attrs) for _, attrs in intro.elements]
    all_text = normalise(intro.text)
    image_sources = tuple(attrs.get("src") for attrs in intro.gallery_images)

    require(bool(intro.elements), f"{label}: teachers section is missing", errors)
    require(sum("teacher-portraits" in names for names in classes) == 1,
            f"{label}: expected one non-link teacher-portraits gallery", errors)
    require(intro.gallery_tag != "a" and not intro.gallery_links,
            f"{label}: portrait gallery must not be an individual link", errors)
    require((intro.gallery_attrs or {}).get("role") == "img" and bool((intro.gallery_attrs or {}).get("aria-label")),
            f"{label}: portrait gallery must have one collective accessible label", errors)
    require(image_sources == EXPECTED_PORTRAITS,
            f"{label}: expected the three approved teacher portraits in gallery order", errors)
    require(len(intro.gallery_images) == 3,
            f"{label}: expected exactly three portrait images", errors)
    require(all(attrs.get("alt") == "" for attrs in intro.gallery_images),
            f"{label}: portrait images must use the collective gallery label, not individual alts", errors)
    require(not any(attrs.get("alt", "") and any(name in attrs.get("alt", "") for name in PERSONAL_NAMES)
                    for attrs in intro.images),
            f"{label}: a portrait alt must not expose an individual name", errors)
    require(not any(name in all_text for name in PERSONAL_NAMES),
            f"{label}: individual names must not be displayed on TOP", errors)

    require(sum("teacher-disciplines" in names for names in classes) == 1,
            f"{label}: teacher-disciplines list is missing", errors)
    require(tuple(dict.fromkeys(intro.disciplines)) == EXPECTED_DISCIPLINES,
            f"{label}: disciplines must be exactly {'・'.join(EXPECTED_DISCIPLINES)}", errors)
    require(sum("teacher-expertise" in names for names in classes) == 1 and bool(normalise(intro.expertise_text)),
            f"{label}: teacher-expertise heading is missing or empty", errors)
    require(sum("teacher-summary" in names for names in classes) == 1 and bool(normalise(intro.summary_text)),
            f"{label}: teacher-summary description is missing or empty", errors)

    require(len(intro.links) == 1 and intro.links[0].get("href") == OFFICIAL_TEACHER_URL,
            f"{label}: expected exactly one link to the official teacher listing", errors)
    require(not any(tag == "a" and attrs in intro.links and attrs.get("href") != OFFICIAL_TEACHER_URL
                    for tag, attrs in intro.elements),
            f"{label}: teacher section has an unexpected individual link", errors)
    require(not any(tag == "button" for tag, _ in intro.elements),
            f"{label}: teacher section must not contain an individual popup button", errors)
    require(not any("tabindex" in attrs for _, attrs in intro.elements),
            f"{label}: teacher section must not add tabindex", errors)
    require(not any("teacher-card" in names or "teacher-profile" in names or "profile" in names
                    for names in classes),
            f"{label}: individual teacher card/profile markup must not remain", errors)
    require(not any("↗" in text or "→" in text for text in intro.gallery_text),
            f"{label}: portrait gallery must not include individual arrows", errors)

    for source in image_sources:
        require(source is not None and (ROOT / source).is_file(),
                f"{label}: portrait asset is missing: {source}", errors)


def main() -> int:
    errors: list[str] = []
    a = parse_page("index.html")
    b = parse_page("top-b.html")
    validate("A", a, errors)
    validate("B", b, errors)

    require(tuple(attrs.get("src") for attrs in a.gallery_images) == tuple(attrs.get("src") for attrs in b.gallery_images),
            "A/B: portrait gallery sources must match", errors)
    require(tuple(dict.fromkeys(a.disciplines)) == tuple(dict.fromkeys(b.disciplines)),
            "A/B: teaching disciplines must match", errors)
    require(normalise(a.expertise_text) == normalise(b.expertise_text),
            "A/B: teacher expertise heading must match", errors)
    require(normalise(a.summary_text) == normalise(b.summary_text),
            "A/B: teacher summary must match", errors)
    require([link.get("href") for link in a.links] == [link.get("href") for link in b.links],
            "A/B: teacher listing route must match", errors)

    if errors:
        print("FAIL:")
        print("\n".join(f"- {error}" for error in errors))
        return 1
    print("PASS: anonymous teacher overview, disciplines, portrait gallery, and official listing route")
    return 0


if __name__ == "__main__":
    sys.exit(main())
