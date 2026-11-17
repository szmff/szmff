#!/usr/bin/env python3
"""Generate self-hosted GitHub profile SVG cards using GitHub's API."""
import json
import os
import urllib.request
from collections import Counter
from html import escape
from pathlib import Path

USER = "szmff"
TOKEN = os.environ.get("GITHUB_TOKEN", "")
HEADERS = {"Accept": "application/vnd.github+json", "User-Agent": "zeyad-profile-cards"}
if TOKEN:
    HEADERS["Authorization"] = f"Bearer {TOKEN}"

def api(path):
    req = urllib.request.Request("https://api.github.com" + path, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=30) as response:
        return json.load(response)

def contributions():
    query = """query($login:String!) { user(login:$login) { contributionsCollection {
      contributionCalendar { totalContributions }
    } } }"""
    data = json.dumps({"query": query, "variables": {"login": USER}}).encode()
    req = urllib.request.Request("https://api.github.com/graphql", data=data,
                                 headers={**HEADERS, "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            payload = json.load(response)
        return payload["data"]["user"]["contributionsCollection"]["contributionCalendar"]["totalContributions"]
    except (KeyError, ValueError, OSError):
        return None

def svg_wrap(body, height=215):
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="490" height="{height}" viewBox="0 0 490 {height}">
<rect x="1" y="1" width="488" height="{height-2}" rx="14" fill="#0d1117" stroke="#303044" stroke-width="2"/>
{body}</svg>'''

def label(x, y, title, value):
    return f'''<text x="{x}" y="{y}" font-family="Arial,sans-serif" font-size="12" fill="#9ca3af">{escape(title)}</text>
<text x="{x}" y="{y+32}" font-family="Arial,sans-serif" font-size="27" font-weight="bold" fill="#f4f4f5">{escape(str(value))}</text>'''

def main():
    user = api("/users/" + USER)
    repos = []
    page = 1
    while page <= 10:
        chunk = api(f"/users/{USER}/repos?per_page=100&page={page}&type=owner")
        repos.extend(chunk)
        if len(chunk) < 100:
            break
        page += 1
    public = [r for r in repos if not r.get("private") and not r.get("fork")]
    stars = sum(r.get("stargazers_count", 0) for r in public)
    total = contributions()
    title = '<text x="24" y="39" font-family="Arial,sans-serif" font-size="19" font-weight="bold" fill="#a78bfa">GitHub Stats</text>'
    body = title + '<path d="M24 52 H466" stroke="#303044"/>'
    body += label(30, 84, "Public repositories", user.get("public_repos", len(public)))
    body += label(260, 84, "Stars earned", stars)
    body += label(30, 155, "Followers", user.get("followers", 0))
    body += label(260, 155, "Contributions (last year)", total if total is not None else "N/A")
    languages = Counter()
    for repo in public:
        try:
            for language, count in api("/repos/" + USER + "/" + repo["name"] + "/languages").items():
                languages[language] += count
        except (OSError, ValueError):
            continue
    top = languages.most_common(5)
    lang_title = '<text x="24" y="39" font-family="Arial,sans-serif" font-size="19" font-weight="bold" fill="#a78bfa">Most Used Languages</text>'
    lang_body = lang_title + '<path d="M24 52 H466" stroke="#303044"/>'
    palette = ["#a78bfa", "#60a5fa", "#34d399", "#fbbf24", "#fb7185"]
    total_bytes = sum(count for _, count in top)
    if total_bytes:
        offset = 24
        for i, (name, count) in enumerate(top):
            width = 442 * count / total_bytes
            lang_body += f'<rect x="{offset:.2f}" y="65" width="{width:.2f}" height="12" fill="{palette[i]}"/>'
            offset += width
            y = 106 + i * 23
            pct = count / total_bytes * 100
            lang_body += f'<circle cx="32" cy="{y-4}" r="5" fill="{palette[i]}"/>'
            lang_body += f'<text x="47" y="{y}" font-family="Arial,sans-serif" font-size="13" fill="#e5e7eb">{escape(name)}</text>'
            lang_body += f'<text x="451" y="{y}" text-anchor="end" font-family="Arial,sans-serif" font-size="13" fill="#9ca3af">{pct:.1f}%</text>'
    else:
        lang_body += '<text x="24" y="106" font-family="Arial,sans-serif" font-size="14" fill="#9ca3af">No language data available yet</text>'
    out = Path("assets")
    out.mkdir(exist_ok=True)
    (out / "github-stats.svg").write_text(svg_wrap(body), encoding="utf-8")
    (out / "top-languages.svg").write_text(svg_wrap(lang_body), encoding="utf-8")
    print("Generated profile SVG cards from GitHub API")

if __name__ == "__main__":
    main()
