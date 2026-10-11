"""Read-only regression checks for the current Mode Plus TOP. Python stdlib only."""
from collections import Counter
from datetime import date, datetime
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit
from zoneinfo import ZoneInfo

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


def has_class(attrs, name):
    return name in attrs.get('class', '').split()


def elements_with_class(document, name):
    return [(tag, attrs) for tag, attrs in document.elements if has_class(attrs, name)]


html = (ROOT / 'index.html').read_text()
page = Page(html)
assert all(v == 1 for v in Counter(page.ids).values()), 'Duplicate IDs'
assert sum(tag == 'h1' for tag, _ in page.elements) == 1, 'Exactly one H1 required'

# One hero image, followed by dated news and clearly labelled evergreen picks.
hero_media = elements_with_class(page, 'hero-media')
assert len(hero_media) == 1, 'Exactly one hero media container required'
# HTMLParser stores only flat elements, so inspect the source interval instead of relying on a DOM tree.
hero_start = html.index('<div class="hero-media">')
hero_end = html.index('</div>', hero_start)
hero_markup = html[hero_start:hero_end]
assert hero_markup.count('<img ') == 1, 'Hero must use one image only'
assert '<video' not in hero_markup, 'Unapproved video must not be added to the hero'

pickups = elements_with_class(page, 'pickup-card')
assert len(pickups) == 3, 'Exactly three curated pickup cards required'
dated_pickups = [attrs for _, attrs in pickups if 'data-valid-until' in attrs]
assert len(dated_pickups) == 1, 'Exactly one pickup must have a validity date'
valid_until = date.fromisoformat(dated_pickups[0]['data-valid-until'])
assert valid_until >= datetime.now(ZoneInfo('Asia/Tokyo')).date(), f'Expired pickup must be replaced: {valid_until.isoformat()}'

cards = [attrs for _, attrs in elements_with_class(page, 'course-card')]
assert len(cards) == 6, 'Exactly six course entrances required'
assert cards[0]['href'] == 'group.html', 'Group course must open its intermediate page'
assert (ROOT / 'group.html').is_file(), 'Group course page is missing'

order = ['top', 'news', 'courses', 'about', 'teachers', 'voices', 'access', 'experience', 'faq']
assert [page.ids.index(x) for x in order] == sorted(page.ids.index(x) for x in order)
assert any(t == 'meta' and a.get('name') == 'robots' and 'noindex' in a.get('content', '') for t, a in page.elements), 'Preview must remain noindex'
assert any(a.get('id') == 'brand-intro' for _, a in page.elements)

faq_details = [attrs for tag, attrs in page.elements if tag == 'details']
assert len(faq_details) == 3, 'Exactly three TOP FAQ items required'
visit_steps = elements_with_class(page, 'visit-steps')
assert len(visit_steps) == 1, 'First visit steps are missing'
visit_start = html.index('<ol class="visit-steps">')
visit_end = html.index('</ol>', visit_start)
assert html[visit_start:visit_end].count('<li>') == 3, 'Exactly three first-visit steps required'

values_index = html.index('<div class="values">')
about_link_index = html.index('モードプラスについて詳しく')
assert about_link_index > values_index, 'About detail link must follow the values section'

school_hours = elements_with_class(page, 'school-hours')
assert len(school_hours) == 2, 'Both schools must show reception hours'
illustrations = {'img/illustrations/piano-line.svg', 'img/illustrations/music-conversation.svg'}
referenced_illustrations = {
    attrs.get('src') for tag, attrs in page.elements
    if tag == 'img' and attrs.get('src') in illustrations
}
assert referenced_illustrations == illustrations, 'Both bespoke illustration assets must be used'

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
print(
    'PASS: structure, one hero image, 3 pickups, 6 courses, 3 FAQ items, '
    f'3 visit steps, {images} images, assets, anchors, safe links, preview metadata'
)
