"""Read-only regression checks for the photo-led TOP. Python standard library only."""
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
VOID = set('area base br col embed hr img input link meta param source track wbr'.split())


class Page(HTMLParser):
    def __init__(self, text):
        super().__init__(convert_charrefs=True)
        self.elements, self.ids, self.stack = [], [], []
        self.feed(text)
        assert not self.stack, f'Unclosed elements: {self.stack}'

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        self.elements.append((tag, attrs))
        if 'id' in attrs:
            self.ids.append(attrs['id'])
        if tag not in VOID:
            self.stack.append(tag)

    def handle_endtag(self, tag):
        assert self.stack and self.stack[-1] == tag, f'Unbalanced {tag}: {self.stack[-3:]}'
        self.stack.pop()


page = Page((ROOT / 'index.html').read_text())
assert all(v == 1 for v in Counter(page.ids).values()), 'Duplicate IDs'
assert sum(tag == 'h1' for tag, _ in page.elements) == 1, 'Exactly one H1 required'
cards = [a for t, a in page.elements if 'course-card' in a.get('class', '').split()]
assert len(cards) == 6, 'Exactly six course entrances required'
assert cards[0]['href'] == 'group.html', 'Group course must open its intermediate page'
order = ['top', 'courses', 'about', 'teachers', 'voices', 'access', 'news', 'experience']
assert [page.ids.index(x) for x in order] == sorted(page.ids.index(x) for x in order)
assert any(t == 'meta' and a.get('name') == 'robots' and 'noindex' in a.get('content', '') for t, a in page.elements), 'Preview must remain noindex'
assert any(a.get('id') == 'brand-intro' for _, a in page.elements)
images = 0
for tag, attrs in page.elements:
    if tag == 'img':
        images += 1
        assert 'alt' in attrs and 'width' in attrs and 'height' in attrs, attrs
    if attrs.get('target') == '_blank':
        assert 'noopener' in attrs.get('rel', ''), 'External new tab without noopener'
    for key in ['src', 'href']:
        if key not in attrs:
            continue
        value = attrs[key]
        assert value and value != '#', f'Empty link: {attrs}'
        parsed = urlsplit(value)
        if parsed.scheme or parsed.netloc:
            continue
        if parsed.path:
            assert (ROOT / unquote(parsed.path)).is_file(), f'Missing file: {value}'
        elif parsed.fragment:
            assert parsed.fragment in page.ids, f'Missing fragment: {value}'

group = Page((ROOT / 'group.html').read_text())
assert not any(t == 'a' and a.get('href') == '#' for t, a in group.elements)
print(f'PASS: structure, {len(cards)} courses, {images} images, assets, anchors, safe links, preview metadata')
