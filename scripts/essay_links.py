#!/usr/bin/env python3
"""Match blog.kindel.com links to Essays-category posts.

Same rules as kindelwww static/js/essay-links.js: a dated
/YYYY/MM/DD/<slug>/ permalink, or a bare /?p=<id> link, and only when
that slug or id is in the Essays category. Other blog posts stay put.

The browser script rewrites to /essays/<slug>/ on the apex host. These
repos are also read off kindel.com, so the link to store is
https://kindel.com/essays/<slug>/. That string has to match exactly,
and the slug has to be in the catalog. A typo, a missing trailing
slash, a root-relative path, a path with no leading slash, an extra
segment, a doubled slash, a dot segment, or an encoded slash fails the
same way a blog.kindel.com essay URL does. The path is decoded once and
dot segments are folded before that check. One terminal DNS dot on
the host is ignored. A kindel.com or blog.kindel.com link with no
scheme is judged the same way. A stored field is judged
before trailing punctuation is removed. A url or href value is one
stored link, so extra text in that field fails the same check. Space
around that value fails too. A note that is only a Markdown link is
still scanned. The destination is read on its own, including balanced
parentheses, angle brackets, and a backslash before ASCII punctuation.
A backslash before any other character stays in the link. A title after
the destination is not part of the link. A url or href value is judged
whole before it is split. Only a parsed kindel.com host whose path is
under essays has to be the canonical catalog URL. JSON files
are read as decoded values. A sentence may end with a period.

scripts/essay_catalog.json is the offline copy of that category
(WordPress id 448). Refresh it from
https://blog.kindel.com/wp-json/wp/v2/posts?categories=448
Fetch every page (per_page=100, follow X-WP-TotalPages). Keep id and
slug. Sort by slug.

  python3 scripts/essay_links.py

Exits non-zero when a product file (everything except tests/) links an
essay on blog.kindel.com, or names an essays path in any form other
than https://kindel.com/essays/<slug>/. Tests plant bad URLs on purpose, so
they are not scanned. The principles validator checks teaching records
directly.
"""

import json
import os
import posixpath
import re
import sys
from urllib.parse import parse_qsl, unquote, urljoin, urlparse

_SLUG = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_DATED = re.compile(r"^/(\d{4})/(\d{2})/(\d{2})/([^/]+)/?$")
_INDEX_PHP = re.compile(r"^/index\.php$", re.IGNORECASE)
_CANDIDATE = re.compile(
    r"(?:https?:)?//[^\s<>\"'`()\[\]]+", re.IGNORECASE)
# Any path-like token, so a percent-encoded prefix is still found.
# Brackets and parentheses stay outside the token so Markdown can wrap a URL.
# The encoded-slash alternative is split so this file is not a candidate.
_PATHY = re.compile(
    r"(?<![A-Za-z0-9@])((?:\.\./|\./)?[^\s<>\"'`()\[\]]*"
    + r"(?:/|%2" + "f)"
    + r"[^\s<>\"'`()\[\]]+)",
    re.IGNORECASE)
_TRAILING = ".,;:)]}>`"
# CommonMark ASCII punctuation. A backslash escapes only these.
_ASCII_PUNCT = set("!\"#$%&'()*+,-./:;<=>?@[\\]^_`{|}~")
_BASE = "https://kindel.com/"
# kindel.com, www.kindel.com, blog.kindel.com, and one terminal DNS dot.
_SCHEMELESS = re.compile(
    r"^(?:www\.)?(?:blog\.)?kindel\.com\.?(?=/|\?|#|$)",
    re.IGNORECASE)
_OK = ("ok",)
_INDEX_HREF = (
    "https://kindel.com/essays/",
    "https://kindel.com/essays",
    "/essays/",
    "/essays",
    "essays/",
    "essays",
)

SKIP_DIRS = {".git", "tests", "__pycache__", "node_modules"}
BINARY_EXT = {
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico", ".pdf",
    ".woff", ".woff2",
}


def safe_slug(raw):
    slug = unquote(str(raw or "")).strip().lower()
    if not _SLUG.match(slug):
        return ""
    return slug


def _id_key(value):
    raw = str("" if value is None else value).strip()
    if not re.match(r"^\d+$", raw):
        return ""
    n = int(raw)
    if n <= 0:
        return ""
    return str(n)


def _host(hostname):
    """Lowercase host, one terminal DNS dot removed, www stripped.

    The hostname is decoded once. The dot comes off before www, so
    www.kindel.com. is still kindel.com.
    """
    host = unquote(hostname or "").strip().lower()
    if host.endswith("."):
        host = host[:-1]
    if host.startswith("www."):
        host = host[4:]
    return host


def _parse_href(original):
    """Parsed URL. A scheme-less Kindel host is given https first.

    urljoin would otherwise treat the hostname as a relative path.
    """
    target = original
    if _SCHEMELESS.match(original):
        target = "https://" + original
    return urlparse(urljoin(_BASE, target))


def _norm_path(path):
    """Decode once, collapse extra slashes, and fold dot segments.

    A trailing slash is preserved. posixpath.normpath would drop it, and
    it would also keep a leading pair of slashes, so those are fixed here.
    """
    decoded = unquote(path or "")
    if decoded in ("", "/"):
        return "/"
    trailing = decoded.endswith("/")
    collapsed = "/" + decoded.lstrip("/")
    norm = posixpath.normpath(collapsed)
    if not norm.startswith("/"):
        norm = "/" + norm
    if norm != "/" and trailing:
        norm += "/"
    return norm


def catalog_path():
    return os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "essay_catalog.json")


def load_catalog(path=None):
    """Return (catalog, None) or (None, error).

    catalog maps by_slug and by_id the way essay-links.js does. A slug
    that fails the same safe-slug test, or an id that is not a positive
    integer, fails the load. An empty list would let every essay URL
    through, so that fails too.
    """
    path = path or catalog_path()
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, ValueError) as exc:
        return None, "unreadable (%s)" % exc
    posts = data.get("posts") if isinstance(data, dict) else None
    if not isinstance(posts, list) or not posts:
        return None, "posts must be a non-empty list"
    by_slug = {}
    by_id = {}
    for i, post in enumerate(posts):
        if not isinstance(post, dict):
            return None, "posts[%d] must be an object" % i
        slug = safe_slug(post.get("slug"))
        if not slug:
            return None, "posts[%d] has no usable slug" % i
        key = _id_key(post.get("id"))
        if not key:
            return None, "posts[%d] has no usable id" % i
        by_slug[slug] = slug
        by_id[key] = slug
    return {"by_slug": by_slug, "by_id": by_id}, None


def canonical_essay_url(slug):
    return "https://kindel.com/essays/" + slug + "/"


def _blog_slug(path, query, catalog):
    """Catalog slug for a normalized blog path, else ""."""
    dated = _DATED.match(path or "")
    if dated:
        candidate = safe_slug(dated.group(4))
        found = catalog["by_slug"].get(candidate, "") if candidate else ""
        if isinstance(found, str) and safe_slug(found):
            return found
        return ""
    if path not in ("/", "") and not _INDEX_PHP.match(path or ""):
        return ""
    pid = ""
    for key, value in parse_qsl(query or "", keep_blank_values=True):
        if key == "p":
            pid = _id_key(value)
            break
    if not pid:
        return ""
    found = catalog["by_id"].get(pid, "")
    if isinstance(found, str) and safe_slug(found):
        return found
    return ""


def _essay_parts(path):
    """(kind, segment) for a normalized path. kind is no, index, slug, or bad."""
    raw = path or ""
    lower = raw.lower()
    if lower in ("/essays", "/essays/"):
        return ("index", "")
    if not lower.startswith("/essays/"):
        return ("no", "")
    parts = raw[len("/essays/"):].split("/")
    if len(parts) == 1 or (len(parts) == 2 and parts[1] == ""):
        return ("slug", parts[0])
    for part in parts:
        if part:
            return ("bad", part)
    return ("bad", "")


def _judge(href, catalog):
    """Classify one href. No punctuation trimming.

    Returns _OK when the href is allowed, None when it is not an essay
    link, or (href, slug) when it is an essay link that is not the
    canonical string. slug is "" when the path does not name a catalog slug.
    """
    original = "" if href is None else str(href).strip()
    if not original or not catalog:
        return None
    if original in _INDEX_HREF:
        return _OK
    try:
        url = _parse_href(original)
    except ValueError:
        return None
    if url.scheme not in ("http", "https"):
        return None
    host = _host(url.hostname)
    path = _norm_path(url.path)
    if host == "blog.kindel.com":
        slug = _blog_slug(path, url.query, catalog)
        if slug:
            return (original, slug)
        return None
    if host != "kindel.com":
        return None
    kind, segment = _essay_parts(path)
    if kind == "no":
        return None
    if kind == "index":
        return (original, "")
    slug = safe_slug(segment)
    if slug and slug in catalog["by_slug"]:
        if original == canonical_essay_url(slug):
            return _OK
        return (original, slug)
    return (original, "")


def essay_slug(href, catalog):
    """Slug when href is a blog.kindel.com essay link, else ""."""
    original = "" if href is None else str(href).strip()
    if not original or not catalog:
        return ""
    try:
        url = _parse_href(original)
    except ValueError:
        return ""
    if url.scheme not in ("http", "https"):
        return ""
    if _host(url.hostname) != "blog.kindel.com":
        return ""
    verdict = _judge(original, catalog)
    if not verdict or verdict == _OK:
        return ""
    return verdict[1]


def _classify(href, catalog, strict):
    """(href, slug) when href is a non-canonical essay link, else None.

    The raw string is judged first. Trailing punctuation is considered
    only after that. In prose, punctuation that leaves a clean canonical
    URL is decoration. A stored field (strict) keeps the punctuation, so
    the field has to be the canonical string exactly.
    """
    verdict = _judge(href, catalog)
    trimmed = href.rstrip(_TRAILING) if href else href
    if verdict == _OK:
        return None
    if verdict is None:
        if not trimmed or trimmed == href:
            return None
        again = _judge(trimmed, catalog)
        if not again or again == _OK:
            return None
        return again
    if trimmed and trimmed != href:
        again = _judge(trimmed, catalog)
        if not again or again == _OK:
            if strict:
                return verdict
            return None
        if not strict:
            return again
    return verdict


def format_problem(href, slug):
    """slug is the catalog slug the link should use, or "" when it has none."""
    if slug:
        return "essay link %s belongs at %s" % (href, canonical_essay_url(slug))
    return "essay link %s is not in scripts/essay_catalog.json" % href


def _tokens(text):
    """(raw href, end index) for absolute URLs and path-like tokens.

    The raw href keeps trailing punctuation. The caller judges it before
    deciding whether that punctuation is prose.
    """
    spans = []
    found = []
    seen = set()

    def add(raw, end):
        if not raw or (raw, end) in seen:
            return
        seen.add((raw, end))
        found.append((raw, end))

    for match in _CANDIDATE.finditer(text):
        spans.append((match.start(), match.end()))
        add(match.group(0), match.end())
    for match in _PATHY.finditer(text):
        start = match.start(1)
        if any(a <= start < b for a, b in spans):
            continue
        add(match.group(1), match.end(1))
    return found


def _looks_like_destination(raw):
    """True when an angle-bracket span is a link, not a placeholder."""
    text = (raw or "").strip()
    if not text or any(ch.isspace() for ch in text):
        return False
    lower = text.lower()
    if lower.startswith("http://") or lower.startswith("https://"):
        return True
    if lower.startswith("/") or lower.startswith("./") or lower.startswith("../"):
        return True
    return lower.startswith("essays/") or "/essays" in lower


def _punct_escape(text, i):
    """The punctuation a backslash escapes, or "" when it stays literal."""
    if i + 1 < len(text) and text[i] == "\\" and text[i + 1] in _ASCII_PUNCT:
        return text[i + 1]
    return ""


def _skip_spaces(text, i):
    """Index after spaces and tabs. A newline ends the link."""
    n = len(text)
    while i < n and text[i] in " \t":
        i += 1
    return i


def _read_title(text, i):
    """Index past a CommonMark link title, or None."""
    if i >= len(text) or text[i] not in "\"'(":
        return None
    closer = ")" if text[i] == "(" else text[i]
    i += 1
    n = len(text)
    while i < n:
        ch = text[i]
        if ch == "\\" and i + 1 < n:
            i += 2
            continue
        if ch == "\n":
            return None
        if ch == closer:
            return i + 1
        i += 1
    return None


def _finish_link(text, i, dest, dest_start, dest_end):
    """(dest, dest_start, dest_end, next) when a ')' closes the link."""
    i = _skip_spaces(text, i)
    if i < len(text) and text[i] in "\"'(":
        title_end = _read_title(text, i)
        if title_end is None:
            return None
        i = _skip_spaces(text, title_end)
    if i < len(text) and text[i] == ")":
        return (dest, dest_start, dest_end, i + 1)
    return None


def _read_destination(text, i):
    """(destination, dest_start, dest_end, next) after a Markdown ']('.

    The destination is separate from an optional title. A backslash
    escapes ASCII punctuation only, and parentheses in the destination
    are balanced. dest_end is the end of the destination, not the title.
    None when the link does not close.
    """
    n = len(text)
    i = _skip_spaces(text, i)
    if i >= n:
        return None
    if text[i] == "<":
        i += 1
        dest_start = i
        buf = []
        while i < n:
            ch = text[i]
            if ch == "\n":
                return None
            escaped = _punct_escape(text, i)
            if escaped:
                buf.append(escaped)
                i += 2
                continue
            if ch == "<":
                return None
            if ch == ">":
                return _finish_link(text, i + 1, "".join(buf), dest_start, i)
            buf.append(ch)
            i += 1
        return None
    dest_start = i
    buf = []
    depth = 0
    while i < n:
        ch = text[i]
        escaped = _punct_escape(text, i)
        if escaped:
            buf.append(escaped)
            i += 2
            continue
        if ch == "(":
            depth += 1
            buf.append(ch)
            i += 1
            continue
        if ch == ")":
            if depth == 0:
                return ("".join(buf), dest_start, i, i + 1)
            depth -= 1
            buf.append(ch)
            i += 1
            continue
        if ch in " \t" and depth == 0:
            return _finish_link(text, i, "".join(buf), dest_start, i)
        if ch == "\n":
            return None
        buf.append(ch)
        i += 1
    return None


def _markdown_destinations(text):
    """(destination, start, end) for link targets and autolinks.

    start and end bound the destination text, not an optional title.
    Balanced parentheses stay inside it. A backslash escapes ASCII
    punctuation only.
    Absolute and relative targets are both returned.
    """
    found = []
    i = 0
    n = len(text)
    while i < n:
        paren = text.find("](", i)
        angle = text.find("<", i)
        if paren == -1 and angle == -1:
            break
        if paren != -1 and (angle == -1 or paren < angle):
            parsed = _read_destination(text, paren + 2)
            if parsed:
                dest, start, end, nxt = parsed
                if dest:
                    found.append((dest, start, end))
                i = nxt
                continue
            i = paren + 2
            continue
        end = text.find(">", angle + 1)
        if end == -1 or "\n" in text[angle + 1:end]:
            i = angle + 1
            continue
        inner = text[angle + 1:end]
        if _looks_like_destination(inner):
            found.append((inner.strip(), angle + 1, end))
            i = end + 1
            continue
        i = angle + 1
    return found


def _overlaps(start, end, spans):
    for left, right in spans:
        if start < right and end > left:
            return True
    return False


def problems_in_text(text, catalog):
    """(href, slug) pairs for essay links that are not canonical.

    slug is the catalog slug the link should use, or "" when the path
    does not name one. A Markdown destination is classified on its own,
    so a title after it is neither part of the link nor inside the
    covered span. Parentheses stay in the destination. A backslash
    escapes ASCII punctuation only. A token inside quotes is stored
    the same way.
    Elsewhere punctuation is prose and is dropped only after the raw
    token has been judged.
    """
    if not text or not catalog:
        return []
    found = []
    seen = set()
    covered = []
    for dest, start, end in _markdown_destinations(text):
        covered.append((start, end))
        issue = _classify(dest, catalog, True)
        if not issue or issue[0] in seen:
            continue
        seen.add(issue[0])
        found.append(issue)
    for href, end in _tokens(text):
        start = end - len(href)
        if _overlaps(start, end, covered):
            continue
        nxt = text[end:end + 1]
        strict = nxt in ('"', "'")
        issue = _classify(href, catalog, strict)
        if not issue or issue[0] in seen:
            continue
        seen.add(issue[0])
        found.append(issue)
    return found


# Keys whose value is one link, not prose. The field name has to survive
# the walk so extra text in that value is judged with the link.
_LINK_KEYS = {"url", "href"}


def _collect(obj, out):
    """Append (text, as_field). as_field is true for a url or href string."""
    if isinstance(obj, dict):
        for key, value in obj.items():
            if isinstance(value, str) and key in _LINK_KEYS:
                out.append((value, True))
            else:
                _collect(value, out)
    elif isinstance(obj, list):
        for value in obj:
            _collect(value, out)
    elif isinstance(obj, str):
        out.append((obj, False))


def _exact_slug(href, catalog):
    """Slug when href is the canonical essay URL, else ""."""
    for slug in catalog["by_slug"]:
        if href == canonical_essay_url(slug):
            return slug
    return ""


def _field_essay_hits(text, catalog):
    """(href, slug) for every essay token in a url or href value.

    Canonical links are included. slug is "" when the path names none.
    """
    hits = []
    seen = set()
    for href, _end in _tokens(text):
        verdict = _judge(href, catalog)
        if verdict == _OK:
            slug = _exact_slug(href, catalog)
            verdict = (href, slug) if slug else None
        if not verdict or verdict[0] in seen:
            continue
        seen.add(verdict[0])
        hits.append(verdict)
    return hits


def _field_host_is_kindel_essays(text):
    """True when the field's own host and path are a kindel.com essays URL.

    The hostname is parsed. www is ignored. An essay URL buried in
    another host's path or query does not count.
    """
    raw = (text or "").strip()
    try:
        url = urlparse(raw)
    except ValueError:
        return False
    if url.scheme not in ("http", "https") or not url.hostname:
        return False
    if _host(url.hostname) != "kindel.com":
        return False
    path = _norm_path(url.path).lower()
    return path == "/essays" or path.startswith("/essays/")


def _stored_link_problem(text, catalog):
    """(href, slug) when a url or href value is not exactly one essay link.

    The whole field is classified before any token is taken, so a
    parenthesis or a space in the path cannot hide behind the essays
    index. Only a parsed kindel.com host whose path is under essays
    has to be the canonical catalog URL. None means the value is not
    an essay link.
    """
    stripped = text.strip()
    issue = _classify(stripped, catalog, True)
    if issue:
        return issue if text == stripped else (text, issue[1])
    if _field_host_is_kindel_essays(text):
        if text == stripped and _exact_slug(stripped, catalog):
            return None
        hits = _field_essay_hits(stripped, catalog)
        slug = hits[0][1] if hits else _exact_slug(stripped, catalog)
        return (text, slug)
    hits = _field_essay_hits(stripped, catalog)
    if not hits:
        return None
    slug = hits[0][1]
    only = len(hits) == 1 and stripped == hits[0][0]
    if only and text == stripped:
        return None
    return (text, slug)


def check_value(obj, where, catalog, errs):
    """Append an error for each essay link in obj that is not canonical.

    A string with no whitespace is judged whole first. When that check
    finds nothing, the tokens inside are still scanned, so a Markdown
    link that is the whole note cannot hide an essay URL. A url or href
    value is exactly one link: other text in that field fails, and so
    does space around the link. A sentence may end with a period.
    """
    items = []
    _collect(obj, items)
    seen = set()
    for text, as_field in items:
        if as_field:
            issue = _stored_link_problem(text, catalog)
        else:
            issue = None
            whole = text.strip()
            if whole and not any(ch.isspace() for ch in whole):
                issue = _classify(whole, catalog, True)
        if issue and issue[0] not in seen:
            seen.add(issue[0])
            errs.append("%s: %s" % (where, format_problem(issue[0], issue[1])))
        if issue:
            continue
        for href, slug in problems_in_text(text, catalog):
            if href in seen:
                continue
            seen.add(href)
            errs.append("%s: %s" % (where, format_problem(href, slug)))


def _read_text(path):
    try:
        with open(path, encoding="utf-8") as fh:
            return fh.read()
    except (OSError, UnicodeDecodeError):
        return None


def _json_problems(text, rel, catalog):
    """Errors for one JSON document, using decoded values."""
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        return ["%s: invalid JSON (%s)" % (rel, exc.msg)]
    errs = []
    check_value(data, rel, catalog, errs)
    return errs


def repo_problems(root, catalog):
    """Essay links under root, skipping tests/ and binary files.

    JSON is parsed and checked as values, so a quote after a sentence
    is not part of the link. Other files are scanned as text.
    """
    problems = []
    root = os.path.abspath(root)
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for name in filenames:
            if name.startswith("."):
                continue
            ext = os.path.splitext(name)[1].lower()
            if ext in BINARY_EXT:
                continue
            path = os.path.join(dirpath, name)
            text = _read_text(path)
            if text is None:
                continue
            rel = os.path.relpath(path, root)
            if ext == ".json":
                problems.extend(_json_problems(text, rel, catalog))
                continue
            seen = set()
            for href, slug in problems_in_text(text, catalog):
                if href in seen:
                    continue
                seen.add(href)
                problems.append("%s: %s" % (rel, format_problem(href, slug)))
    problems.sort()
    return problems


def main():
    catalog, err = load_catalog()
    if err:
        print("scripts/essay_catalog.json: %s" % err)
        return 1
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    problems = repo_problems(root, catalog)
    if problems:
        for line in problems:
            print(line)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
