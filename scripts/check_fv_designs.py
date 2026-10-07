"""Static checks for the three local Mode Plus first-view design concepts.

Uses only the Python standard library so it can run before the preview server is
started. It verifies the comparison shell, the three documents and their local
assets/fragment targets without opening or publishing anything.
"""

from __future__ import annotations

from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit


ROOT = Path(__file__).resolve().parents[1]
VOID = frozenset("area base br col embed hr img input link meta param source track wbr".split())
OFFSITE_SCHEMES = frozenset(("http", "https", "mailto", "tel", "data", "javascript"))
CONCEPTS = ("a", "b", "c")
RESERVATION_URL = "https://modepluspf.resv.jp/reserve/calendar.php"


@dataclass(frozen=True)
class Element:
    tag: str
    attrs: dict[str, str]
    ancestors: tuple[tuple[str, dict[str, str]], ...]


class Page(HTMLParser):
    def __init__(self, path: Path):
        super().__init__(convert_charrefs=True)
        self.path = path
        self.elements: list[Element] = []
        self.ids: list[str] = []
        self.stack: list[tuple[str, dict[str, str]]] = []
        self.feed(path.read_text(encoding="utf-8"))
        self.close()
        if self.stack:
            raise ValueError(f"{path.relative_to(ROOT)}: unclosed elements {self.stack!r}")

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = {key: value or "" for key, value in attrs}
        self.elements.append(Element(tag, attributes, tuple(self.stack)))
        if attributes.get("id"):
            self.ids.append(attributes["id"])
        if tag not in VOID:
            self.stack.append((tag, attributes))

    def handle_endtag(self, tag: str) -> None:
        if tag in VOID:
            return
        if not self.stack or self.stack[-1][0] != tag:
            expected = self.stack[-1][0] if self.stack else "nothing"
            raise ValueError(f"{self.path.relative_to(ROOT)}: closing </{tag}> while <{expected}> is open")
        self.stack.pop()

    def count_descendant_anchors(self, class_name: str) -> int:
        def has_class(ancestor: tuple[str, dict[str, str]]) -> bool:
            return class_name in ancestor[1].get("class", "").split()

        return sum(
            item.tag == "a" and any(has_class(ancestor) for ancestor in item.ancestors)
            for item in self.elements
        )

    def has_noindex(self) -> bool:
        return any(
            item.tag == "meta"
            and item.attrs.get("name", "").lower() == "robots"
            and "noindex" in item.attrs.get("content", "").lower()
            for item in self.elements
        )


def is_offsite(value: str) -> bool:
    parsed = urlsplit(value)
    return bool(parsed.netloc or parsed.scheme.lower() in OFFSITE_SCHEMES)


def local_target(source: Path, value: str) -> tuple[Path | None, str]:
    parsed = urlsplit(value)
    if is_offsite(value):
        return None, parsed.fragment
    target = source if not parsed.path else (source.parent / unquote(parsed.path)).resolve()
    return target, parsed.fragment


def check_local_references(page: Page, cache: dict[Path, Page], errors: list[str]) -> None:
    for item in page.elements:
        for attribute in ("href", "src"):
            value = item.attrs.get(attribute)
            if not value:
                continue
            target, fragment = local_target(page.path, value)
            if target is None:
                if (
                    item.attrs.get("target") == "_blank"
                    and urlsplit(value).scheme.lower() in {"http", "https"}
                    and "noopener" not in item.attrs.get("rel", "").split()
                ):
                    errors.append(f"{page.path.relative_to(ROOT)}: external _blank link needs noopener: {value}")
                continue
            if not target.is_file():
                errors.append(f"{page.path.relative_to(ROOT)}: missing local {attribute}: {value}")
                continue
            if not fragment:
                continue
            if target.suffix.lower() != ".html":
                errors.append(f"{page.path.relative_to(ROOT)}: fragment targets a non-HTML file: {value}")
                continue
            target_page = cache.setdefault(target, Page(target))
            if fragment not in target_page.ids:
                errors.append(f"{page.path.relative_to(ROOT)}: missing fragment #{fragment} in {target.relative_to(ROOT)}")


def require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def main() -> None:
    paths = [ROOT / "fv-designs.html", *(ROOT / "designs" / f"fv-{name}.html" for name in CONCEPTS)]
    cache = {path.resolve(): Page(path.resolve()) for path in paths}
    errors: list[str] = []

    compare = cache[(ROOT / "fv-designs.html").resolve()]
    require(compare.has_noindex(), "fv-designs.html: noindex metadata is required", errors)
    compare_ids = set(compare.ids)
    required_compare_ids = {"tab-a", "tab-b", "tab-c", "preview-panel", "concept-preview", "concept-note", "open-concept", "replay"}
    require(not (required_compare_ids - compare_ids), f"fv-designs.html: missing IDs {sorted(required_compare_ids - compare_ids)}", errors)
    tab_values = {
        item.attrs.get("data-concept")
        for item in compare.elements
        if item.tag == "button" and item.attrs.get("role") == "tab"
    }
    require(tab_values == set(CONCEPTS), f"fv-designs.html: expected A/B/C tabs, got {sorted(tab_values)}", errors)
    require(any(item.tag == "iframe" and item.attrs.get("id") == "concept-preview" for item in compare.elements), "fv-designs.html: comparison iframe is required", errors)
    require(any(item.tag == "script" and item.attrs.get("src") == "designs/compare.js" for item in compare.elements), "fv-designs.html: designs/compare.js is required", errors)

    for concept in CONCEPTS:
        path = (ROOT / "designs" / f"fv-{concept}.html").resolve()
        page = cache[path]
        require(len(page.ids) == len(set(page.ids)), f"designs/fv-{concept}.html: duplicate IDs", errors)
        require(sum(item.tag == "h1" for item in page.elements) == 1, f"designs/fv-{concept}.html: exactly one H1 is required", errors)
        require(page.has_noindex(), f"designs/fv-{concept}.html: noindex metadata is required", errors)
        require(
            any(item.tag == "a" and item.attrs.get("href") == RESERVATION_URL for item in page.elements),
            f"designs/fv-{concept}.html: official trial reservation CTA is required",
            errors,
        )
        require(
            any(item.tag == "script" and item.attrs.get("src") == "fv-common.js" for item in page.elements),
            f"designs/fv-{concept}.html: shared fv-common.js is required",
            errors,
        )

    require(cache[(ROOT / "designs" / "fv-a.html").resolve()].count_descendant_anchors("a-course-links") == 6, "A案: 6つのコース入口が必要です", errors)
    require(cache[(ROOT / "designs" / "fv-b.html").resolve()].count_descendant_anchors("b-courses__links") == 6, "B案: 6つのコース入口が必要です", errors)

    for page in list(cache.values()):
        check_local_references(page, cache, errors)

    if errors:
        raise SystemExit("FV design checks failed:\n- " + "\n- ".join(errors))
    print("PASS: comparison shell, A/B/C structure, local assets/fragments, CTA, safe external links")


if __name__ == "__main__":
    main()
