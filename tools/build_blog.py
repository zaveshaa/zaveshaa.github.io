#!/usr/bin/env python3
import html
import pathlib
import re
import sys
from datetime import datetime, timezone

ROOT = pathlib.Path(__file__).resolve().parent.parent
NOTES = ROOT / "notes"
INDEX = ROOT / "blog.html"
FEED = ROOT / "feed.xml"

SITE = "https://zaveshaa.github.io"

PLANNED = [
    ("university", "university"),
    ("insurgency1", "insurgency 1"),
    ("insurgency2", "insurgency 2"),
    ("prod", "PROD"),
    ("school1", "school 1"),
    ("school2", "school 2"),
    ("friends", "friends"),
    ("love", "love"),
    ("edc", "edc"),
    ("productivity", "productivity"),
    ("2026setup", "2026 setup"),
    ("favouritebooks", "favourite books"),
    ("favouritedevices", "favourite devices"),
    ("russia", "russia"),
    ("polytics", "polytics"),
    ("games", "games"),
    ("anime", "anime"),
    ("sport", "sport"),
    ("social", "social"),
    ("01", "01"),
    ("goalsplans", "goals/plans"),
    ("music", "music"),
    ("porn", "porn"),
    ("envy", "envy"),
    ("startcondition", "start condition"),
]

META = re.compile(r"<!--(.*?)-->", re.S)
FIELD = re.compile(r"^\s*(\w+)\s*:\s*(.+?)\s*$", re.M)
DATE_FMT = "%Y-%m-%d"


def read_meta(path):
    head = path.read_text(encoding="utf-8")[:4000]
    block = META.search(head)
    if not block:
        return {}
    out = {}
    for key, value in FIELD.findall(block.group(1)):
        out[key.lower()] = value
    return out


def collect():
    posts = {}
    if not NOTES.is_dir():
        return posts
    for path in sorted(NOTES.glob("*.html")):
        if path.name.startswith("_"):
            continue
        meta = read_meta(path)
        posts[path.stem] = {
            "slug": path.stem,
            "title": meta.get("title", path.stem),
            "date": meta.get("date", ""),
            "summary": meta.get("summary", ""),
            "status": meta.get("status", "done").lower(),
        }
    return posts


def sort_key(post):
    date = post.get("date") or "0000-00-00"
    try:
        datetime.strptime(date, DATE_FMT)
    except ValueError:
        return ("0000-00-00", post["slug"])
    return (date, post["slug"])


def card(post, done):
    label = html.escape(post["title"])
    if post.get("summary"):
        label += '<span class="sublabel">%s</span>' % html.escape(post["summary"])
    if not done:
        return '            <div class="note-card pending"><span>%s</span></div>\n' % label
    cls = "note-card"
    if post["status"] in ("done", "published", "closed"):
        cls += " finished"
    return '            <a class="%s" href="notes/%s.html"><span>%s</span></a>\n' % (
        cls,
        html.escape(post["slug"]),
        label,
    )


def render_grid(posts):
    planned_slugs = {s for s, _ in PLANNED}
    out = []
    for slug, title in PLANNED:
        if slug in posts:
            out.append(card(posts[slug], done=True))
        else:
            out.append(card({"slug": slug, "title": title, "status": ""}, done=False))

    extras = [p for slug, p in posts.items() if slug not in planned_slugs]
    extras.sort(key=sort_key, reverse=True)
    for post in extras:
        out.append(card(post, done=True))
    return "".join(out)


def splice(text, start, end, inner):
    if start not in text or end not in text:
        return None
    head, rest = text.split(start, 1)
    _, tail = rest.split(end, 1)
    return head + start + inner + end + tail


def update_index(posts):
    if not INDEX.exists():
        print("error: %s not found" % INDEX, file=sys.stderr)
        return False
    text = INDEX.read_text(encoding="utf-8")

    out = splice(text, "<!-- posts:start -->", "<!-- posts:end -->", "\n" + render_grid(posts) + "        ")
    if out is None:
        print("error: %s has no posts markers" % INDEX, file=sys.stderr)
        return False

    missing = [s for s, _ in PLANNED if not (NOTES / (s + ".html")).exists()]
    line = "%d written / %d planned" % (len(posts), len(missing))
    if missing:
        line += " &mdash; dashed cards have no page yet"
    counted = splice(out, "<!-- count:start -->", "<!-- count:end -->", line)
    if counted is not None:
        out = counted

    INDEX.write_text(out, encoding="utf-8")
    return True


def rfc822(date):
    try:
        dt = datetime.strptime(date, DATE_FMT).replace(tzinfo=timezone.utc)
    except ValueError:
        return ""
    return dt.strftime("%a, %d %b %Y 00:00:00 +0000")


def write_feed(posts):
    live = [p for p in posts.values() if p["status"] != "draft"]
    live.sort(key=sort_key, reverse=True)
    items = []
    for post in live:
        link = "%s/notes/%s.html" % (SITE, post["slug"])
        items.append(
            "    <item>\n"
            "      <title>%s</title>\n"
            "      <link>%s</link>\n"
            "      <guid isPermaLink=\"true\">%s</guid>\n"
            "      <description>%s</description>\n"
            "      <pubDate>%s</pubDate>\n"
            "    </item>"
            % (
                html.escape(post["title"]),
                link,
                link,
                html.escape(post["summary"]),
                rfc822(post.get("date", "")),
            )
        )
    body = "\n".join(items)
    if body:
        body = "\n" + body + "\n"
    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<rss version="2.0">\n'
        "  <channel>\n"
        "    <title>zaveshaa — notes</title>\n"
        "    <link>%s/blog.html</link>\n"
        "    <description>personalia</description>\n"
        "    <language>en</language>\n" % SITE
    ) + body + "  </channel>\n</rss>\n"
    FEED.write_text(xml, encoding="utf-8")
    return len(live)


def main():
    posts = collect()
    if not update_index(posts):
        return 1
    count = write_feed(posts)
    missing = [s for s, _ in PLANNED if not (NOTES / (s + ".html")).exists()]
    print("blog.html: %d written, %d planned" % (len(posts), len(missing)))
    print("feed.xml:  %d items" % count)
    if missing:
        print("not written yet: %s" % ", ".join(missing))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
