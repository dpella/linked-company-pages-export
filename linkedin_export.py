#!/usr/bin/env python3
"""Download LinkedIn Pages Data Portability data for your company page.

Fetches posts (with comments, reactions, social metadata, analytics) and
followers, writing raw JSON responses under ./out/<org>/<timestamp>/.

Auth: 3-legged OAuth. The script prints a URL you open in a browser, then
prompts you to paste the redirected URL or just the `code` value back.
Tokens are cached in ./.token.json and refreshed automatically.
"""

import argparse
import json
import os
import os.path
import re
import secrets
import sys
import time
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path

import requests

API_BASE = "https://api.linkedin.com"
LINKEDIN_VERSION = "202604"
RESTLI_VERSION = "2.0.0"
SCOPE = "r_dma_admin_pages_content"

AUTH_URL = "https://www.linkedin.com/oauth/v2/authorization"
TOKEN_URL = "https://www.linkedin.com/oauth/v2/accessToken"

ROOT = Path(__file__).parent.resolve()
TOKEN_FILE = ROOT / ".token.json"
ENV_FILE = ROOT / ".env"


# ------------------------------- env / token -------------------------------

def load_env() -> None:
    if not ENV_FILE.exists():
        return
    for line in ENV_FILE.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        v = v.strip().strip('"').strip("'")
        os.environ.setdefault(k.strip(), v)


def save_token(tok: dict) -> None:
    tok["_saved_at"] = int(time.time())
    TOKEN_FILE.write_text(json.dumps(tok, indent=2))
    os.chmod(TOKEN_FILE, 0o600)


def load_token() -> dict | None:
    if TOKEN_FILE.exists():
        return json.loads(TOKEN_FILE.read_text())
    return None


def is_expired(tok: dict, slack: int = 300) -> bool:
    return tok.get("_saved_at", 0) + tok.get("expires_in", 0) - slack < time.time()


# ------------------------------- OAuth flow --------------------------------

def oauth_authorize(client_id: str, redirect_uri: str) -> str:
    state = secrets.token_urlsafe(16)
    params = {
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "state": state,
        "scope": SCOPE,
    }
    url = f"{AUTH_URL}?{urllib.parse.urlencode(params)}"
    print("\n" + "=" * 60)
    print("LinkedIn OAuth — authorize this app")
    print("=" * 60)
    print("\n1. Open this URL in your browser:\n")
    print(url)
    print("\n2. Sign in and click 'Allow'.")
    print(f"\n3. You'll be redirected to {redirect_uri}?code=...&state=...")
    print("   The page may not load — that's fine, just copy the URL.")
    print("\n4. Paste the FULL redirect URL here (or just the `code` value):\n")
    pasted = input("> ").strip()

    if pasted.startswith("http"):
        qs = urllib.parse.urlparse(pasted).query
        parsed = urllib.parse.parse_qs(qs)
        if "error" in parsed:
            err = parsed["error"][0]
            desc = parsed.get("error_description", [""])[0]
            sys.exit(f"OAuth error: {err} — {desc}")
        if parsed.get("state", [None])[0] != state:
            sys.exit("State mismatch — possible CSRF, aborting.")
        code = parsed.get("code", [None])[0]
    else:
        code = pasted
    if not code:
        sys.exit("No authorization code received.")
    return code


def exchange_code(code: str, client_id: str, client_secret: str, redirect_uri: str) -> dict:
    r = requests.post(TOKEN_URL, data={
        "grant_type": "authorization_code",
        "code": code,
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": redirect_uri,
    }, timeout=30)
    if not r.ok:
        sys.exit(f"Token exchange failed [{r.status_code}]: {r.text}")
    return r.json()


def refresh_token(refresh_token: str, client_id: str, client_secret: str) -> dict:
    r = requests.post(TOKEN_URL, data={
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
        "client_id": client_id,
        "client_secret": client_secret,
    }, timeout=30)
    if not r.ok:
        raise RuntimeError(f"Refresh failed [{r.status_code}]: {r.text}")
    return r.json()


def get_access_token(force_reauth: bool = False) -> str:
    if os.environ.get("LINKEDIN_ACCESS_TOKEN"):
        return os.environ["LINKEDIN_ACCESS_TOKEN"]

    cid = os.environ.get("LINKEDIN_CLIENT_ID")
    csec = os.environ.get("LINKEDIN_CLIENT_SECRET")
    redir = os.environ.get("LINKEDIN_REDIRECT_URI", "http://localhost:8000/callback")

    if not force_reauth:
        tok = load_token()
        if tok and not is_expired(tok):
            return tok["access_token"]
        if tok and tok.get("refresh_token") and cid and csec:
            try:
                new = refresh_token(tok["refresh_token"], cid, csec)
                new.setdefault("refresh_token", tok["refresh_token"])
                save_token(new)
                print("Refreshed access token.")
                return new["access_token"]
            except Exception as e:
                print(f"Refresh failed ({e}); running full OAuth.")

    if not cid or not csec:
        sys.exit("Missing LINKEDIN_CLIENT_ID / LINKEDIN_CLIENT_SECRET. Copy .env.example to .env and fill in.")

    code = oauth_authorize(cid, redir)
    new = exchange_code(code, cid, csec, redir)
    save_token(new)
    print(f"Saved access token ({TOKEN_FILE.relative_to(ROOT)}). Expires in {new.get('expires_in', '?')}s.")
    return new["access_token"]


# ------------------------------- HTTP client -------------------------------

class LinkedInClient:
    def __init__(self, token: str):
        self.s = requests.Session()
        self.s.headers.update({
            "Authorization": f"Bearer {token}",
            "LinkedIn-Version": LINKEDIN_VERSION,
            "X-Restli-Protocol-Version": RESTLI_VERSION,
        })

    def get(self, path: str, params: dict | None = None, raw_query: str | None = None) -> dict:
        """GET a JSON endpoint. `raw_query` overrides params (used for rest.li 2.0 List(...) syntax)."""
        url = f"{API_BASE}{path}"
        if raw_query is not None:
            url = f"{url}?{raw_query}"
            params = None
        for attempt in range(5):
            r = self.s.get(url, params=params, timeout=60)
            if r.status_code == 429:
                wait = int(r.headers.get("Retry-After", "60"))
                print(f"  rate limited; sleeping {wait}s")
                time.sleep(wait)
                continue
            if 500 <= r.status_code < 600:
                wait = 2 ** attempt
                print(f"  {r.status_code}; retrying in {wait}s")
                time.sleep(wait)
                continue
            if not r.ok:
                raise RuntimeError(f"GET {url} -> {r.status_code}: {r.text[:500]}")
            return r.json()
        raise RuntimeError(f"GET {url}: too many retries")


def encode_urn_list(urns: list[str]) -> str:
    """Build a rest.li 2.0 List(...) value with URL-encoded URN elements."""
    return "List(" + ",".join(urllib.parse.quote(u, safe="") for u in urns) + ")"


def write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False))
    try:
        rel = path.resolve().relative_to(ROOT)
    except ValueError:
        rel = path
    print(f"  wrote {rel} ({path.stat().st_size:,} bytes)")


# ----------------------------- pagination helpers --------------------------

def paginate_cursor(client: LinkedInClient, path: str, params: dict, sleep_between: float = 0.0):
    """Cursor-based pagination via metadata.nextPaginationCursor."""
    cursor = None
    while True:
        p = dict(params)
        if cursor:
            p["paginationCursor"] = cursor
        page = client.get(path, params=p)
        yield page
        cursor = (page.get("metadata") or {}).get("nextPaginationCursor")
        if not cursor:
            return
        if sleep_between:
            time.sleep(sleep_between)


def paginate_start(client: LinkedInClient, path: str, params: dict, page_size: int = 50, sleep_between: float = 0.0):
    """Standard rest.li start/count pagination."""
    start = 0
    while True:
        p = dict(params)
        p["start"] = start
        p["count"] = page_size
        page = client.get(path, params=p)
        yield page
        elements = page.get("elements", [])
        if len(elements) < page_size:
            return
        start += page_size
        if sleep_between:
            time.sleep(sleep_between)


# ----------------------------- collectors ----------------------------------

def collect_followers(client: LinkedInClient, org_id: str, out_dir: Path, max_pages: int | None) -> None:
    """Followers via /rest/dmaOrganizationalPageFollows (cursor pagination, 1 req / 60s)."""
    print("\n[followers] fetching MEMBER_FOLLOWS_ORGANIZATIONAL_PAGE edges")
    page_urn = f"urn:li:organizationalPage:{org_id}"
    params = {
        "q": "followee",
        "followee": page_urn,
        "edgeType": "MEMBER_FOLLOWS_ORGANIZATIONAL_PAGE",
        "maxPaginationCount": 1000,
    }
    pages = []
    elements = []
    for i, page in enumerate(paginate_cursor(client, "/rest/dmaOrganizationalPageFollows", params, sleep_between=61)):
        pages.append(page)
        els = page.get("elements", [])
        elements.extend(els)
        print(f"  page {i + 1}: +{len(els)} (total {len(elements)})")
        if max_pages and i + 1 >= max_pages:
            print(f"  stopping at --max-pages={max_pages}")
            break
    write_json(out_dir / "followers.json", elements)
    write_json(out_dir / "followers_raw_pages.json", pages)


def parse_year_arg(s: str | None) -> set[int] | None:
    """Parse a --year value: 'all' / '' / None -> no filter. '2024' -> {2024}.
    '2023,2025' -> {2023,2025}. '2022-2024' -> {2022,2023,2024}."""
    if not s or s.strip().lower() == "all":
        return None
    out: set[int] = set()
    for part in s.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            a, b = part.split("-", 1)
            lo, hi = int(a), int(b)
            if lo > hi:
                lo, hi = hi, lo
            out.update(range(lo, hi + 1))
        else:
            out.add(int(part))
    return out or None


def _extract_timestamp_ms(el: dict) -> int | None:
    for k in ("createdAt", "firstPublishedAt", "publishedAt", "lastModifiedAt", "createdTime"):
        v = el.get(k)
        if isinstance(v, int) and v > 10**12:  # plausibly an epoch-ms
            return v
        if isinstance(v, dict):
            for kk in ("time", "value", "timestamp"):
                vv = v.get(kk)
                if isinstance(vv, int) and vv > 10**12:
                    return vv
    return None


def urn_timestamp_ms(urn: str) -> int | None:
    """Decode the embedded epoch-ms from a LinkedIn share/ugcPost URN.

    LinkedIn IDs are Snowflake-like: the high bits encode a Unix epoch-ms.
    Empirically `int(numeric_part) >> 22` gives the creation timestamp in ms.

    Handles both simple URNs (urn:li:share:123) and compound URNs like
    urn:li:instantRepost:(urn:li:share:abc,123) or
    urn:li:reaction:(urn:li:organization:abc,urn:li:activity:123) — the
    most-recent numeric id is taken.
    """
    if not isinstance(urn, str):
        return None
    candidates: list[int] = []
    if "(" in urn:
        # Compound URN — pull last segment from inside the parens
        inside = urn.split("(", 1)[1].rsplit(")", 1)[0]
        for piece in inside.split(","):
            piece = piece.strip()
            tail = piece.rsplit(":", 1)[-1] if ":" in piece else piece
            if tail.isdigit():
                candidates.append(int(tail))
    else:
        tail = urn.rsplit(":", 1)[-1]
        if tail.isdigit():
            candidates.append(int(tail))
    for n in candidates:
        ts = n >> 22
        if 1_200_000_000_000 < ts < 2_500_000_000_000:
            return ts
    return None


def collect_post_urns(client: LinkedInClient, org_id: str, out_dir: Path,
                      max_pages: int | None, years: set[int] | None) -> list[str]:
    """List post URNs via /rest/dmaFeedContentsExternal?q=postsByAuthor.

    Prints each URN as it's discovered so the full listing is visible
    before hydration / engagement / analytics calls run. Optionally
    filters by post creation year and short-circuits pagination once the
    listing drops below the earliest requested year (results are sorted
    by creation time descending per the API contract).
    """
    if years is None:
        print("\n[posts:list] listing post URNs (postsByAuthor) — all years")
    else:
        print(f"\n[posts:list] listing post URNs (postsByAuthor) — years {sorted(years)}")
    # Posts are authored by the organization entity, not the organizationalPage.
    org_urn = f"urn:li:organization:{org_id}"
    pages = []
    urns: list[str] = []
    urn_meta: list[dict] = []  # parallel: {urn, year?, ts_ms?, source}
    seen: set[str] = set()
    earliest_wanted = min(years) if years else None
    short_circuit = False

    finders: list[tuple[str, dict, str]] = [
        ("postsByAuthor", {"q": "postsByAuthor", "author": org_urn, "maxPaginationCount": 100}, "post"),
        ("repostsByReposter", {"q": "repostsByReposter", "reposter": org_urn, "maxPaginationCount": 100}, "repost"),
    ]
    for finder_name, params, kind in finders:
        print(f"\n  finder: {finder_name}")
        short_circuit = False
        try:
            iterator = enumerate(paginate_cursor(client, "/rest/dmaFeedContentsExternal", params, sleep_between=1))
            for i, page in iterator:
                pages.append({"finder": finder_name, "page": page})
                page_new = 0
                page_skipped_year = 0
                page_no_urn = 0
                elements = page.get("elements", [])
                if i == 0 and elements:
                    sample_keys = sorted(elements[0].keys()) if isinstance(elements[0], dict) else []
                    print(f"  [debug] first element keys: {sample_keys}")
                for el in elements:
                    urn = None
                    for k in ("id", "ugcUrn", "instantRepostUrn", "shareUrn", "postUrn", "urn",
                              "feedContentUrn", "objectUrn", "entityUrn", "contentUrn"):
                        v = el.get(k) if isinstance(el, dict) else None
                        if isinstance(v, str) and v.startswith("urn:"):
                            urn = v
                            break
                    if not urn:
                        if isinstance(el, dict):
                            for v in el.values():
                                if isinstance(v, str) and v.startswith("urn:li:"):
                                    urn = v
                                    break
                    if not urn:
                        page_no_urn += 1
                        continue
                    if urn in seen:
                        continue
                    ts_ms = _extract_timestamp_ms(el) or urn_timestamp_ms(urn)
                    year = datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc).year if ts_ms else None
                    if years is not None and year is not None and year not in years:
                        page_skipped_year += 1
                        if earliest_wanted is not None and year < earliest_wanted:
                            short_circuit = True
                        continue
                    seen.add(urn)
                    urns.append(urn)
                    urn_meta.append({"urn": urn, "year": year, "ts_ms": ts_ms, "source": kind, "finder": finder_name})
                    page_new += 1
                    if ts_ms is not None:
                        date_label = datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc).strftime("%Y-%m-%d")
                    else:
                        date_label = "????-??-??"
                    tag = "" if kind == "post" else f" ({kind})"
                    print(f"    {len(urns):>4}. [{date_label}]{tag} {urn}")
                msg = f"  page {i + 1}: {len(elements)} elements, +{page_new} kept"
                if page_skipped_year:
                    msg += f", {page_skipped_year} skipped (year)"
                if page_no_urn:
                    msg += f", {page_no_urn} no-urn"
                msg += f"  (total {len(urns)})"
                print(msg)
                if short_circuit:
                    print(f"  short-circuit: page contained items older than earliest wanted year ({earliest_wanted})")
                    break
                if max_pages and i + 1 >= max_pages:
                    print(f"  stopping at --max-pages={max_pages}")
                    break
        except Exception as e:
            print(f"  finder {finder_name} failed: {e}")
            continue
    write_json(out_dir / "post_urns.json", urns)
    write_json(out_dir / "post_urns_meta.json", urn_meta)
    write_json(out_dir / "post_listing_raw_pages.json", pages)
    print(f"[posts:list] done — {len(urns)} unique post URN(s)")
    return urns


def batch_get(client: LinkedInClient, path: str, ids: list[str], chunk: int = 50) -> list[dict]:
    """BATCH_GET helper using rest.li 2.0 ids=List(<urn>,<urn>,...) syntax."""
    out: list[dict] = []
    for i in range(0, len(ids), chunk):
        batch = ids[i:i + chunk]
        raw = "ids=" + encode_urn_list(batch)
        page = client.get(path, raw_query=raw)
        out.append(page)
        time.sleep(0.5)
    return out


def collect_posts(client: LinkedInClient, urns: list[str], out_dir: Path) -> None:
    if not urns:
        print("\n[posts:fetch] no URNs to hydrate")
        return
    print(f"\n[posts:fetch] hydrating {len(urns)} posts via /rest/dmaPosts BATCH_GET")
    pages = batch_get(client, "/rest/dmaPosts", urns)
    write_json(out_dir / "posts.json", pages)


def collect_engagement_for_posts(client: LinkedInClient, urns: list[str], out_dir: Path, max_pages_per_post: int | None) -> None:
    """For each post: list comment/reaction URNs via dmaFeedContentsExternal, then BATCH_GET them."""
    if not urns:
        return
    per_post_dir = out_dir / "per_post"
    print(f"\n[engagement] fetching comments + reactions for {len(urns)} posts")
    for n, urn in enumerate(urns, 1):
        slug = urn.replace(":", "_")
        post_dir = per_post_dir / slug
        print(f"  ({n}/{len(urns)}) {urn}")

        # comments
        comment_urns: list[str] = []
        comment_pages: list[dict] = []
        for i, page in enumerate(paginate_cursor(
            client, "/rest/dmaFeedContentsExternal",
            {"q": "commentsOnEntity", "entity": urn, "maxPaginationCount": 100},
            sleep_between=1,
        )):
            comment_pages.append(page)
            for el in page.get("elements", []):
                if not isinstance(el, dict):
                    continue
                for k in ("id", "commentUrn", "urn"):
                    v = el.get(k)
                    if isinstance(v, str) and v.startswith("urn:"):
                        comment_urns.append(v)
                        break
                else:
                    for v in el.values():
                        if isinstance(v, str) and v.startswith("urn:li:"):
                            comment_urns.append(v)
                            break
            if max_pages_per_post and i + 1 >= max_pages_per_post:
                break
        write_json(post_dir / "comment_listing_raw_pages.json", comment_pages)
        comment_urns = list(dict.fromkeys(comment_urns))
        if comment_urns:
            write_json(post_dir / "comment_urns.json", comment_urns)
            write_json(post_dir / "comments.json", batch_get(client, "/rest/dmaComments", comment_urns))
        else:
            print(f"    no comment URNs (listing returned {sum(len(p.get('elements') or []) for p in comment_pages)} elements)")

        # reactions
        reaction_urns: list[str] = []
        reaction_pages: list[dict] = []
        for i, page in enumerate(paginate_cursor(
            client, "/rest/dmaFeedContentsExternal",
            {"q": "reactionsOnEntity", "entity": urn, "maxPaginationCount": 100},
            sleep_between=1,
        )):
            reaction_pages.append(page)
            for el in page.get("elements", []):
                if not isinstance(el, dict):
                    continue
                for k in ("id", "reactionUrn", "urn"):
                    v = el.get(k)
                    if isinstance(v, str) and v.startswith("urn:"):
                        reaction_urns.append(v)
                        break
                else:
                    for v in el.values():
                        if isinstance(v, str) and v.startswith("urn:li:"):
                            reaction_urns.append(v)
                            break
            if max_pages_per_post and i + 1 >= max_pages_per_post:
                break
        write_json(post_dir / "reaction_listing_raw_pages.json", reaction_pages)
        reaction_urns = list(dict.fromkeys(reaction_urns))
        if reaction_urns:
            write_json(post_dir / "reaction_urns.json", reaction_urns)
            write_json(post_dir / "reactions.json", batch_get(client, "/rest/dmaReactions", reaction_urns))
        else:
            print(f"    no reaction URNs (listing returned {sum(len(p.get('elements') or []) for p in reaction_pages)} elements)")

        # social metadata (counts)
        write_json(post_dir / "social_metadata.json",
                   batch_get(client, "/rest/dmaSocialMetadata", [urn]))


_ANALYTICS_MAX_MS = int(360 * 24 * 3600 * 1000)  # ~12 months; well under the 14-month API cap


def _analytics_windows(start_ms: int, end_ms: int) -> list[tuple[int, int]]:
    """Split [start, end] into <=12-month chunks (the trend endpoint refuses >14 months)."""
    if end_ms <= start_ms:
        return [(start_ms, end_ms)]
    windows = []
    cur = start_ms
    while cur < end_ms:
        nxt = min(cur + _ANALYTICS_MAX_MS, end_ms)
        windows.append((cur, nxt))
        cur = nxt
    return windows


def _fetch_trend_chunked(client: LinkedInClient, source_entity: str, metric_types: str,
                         start_ms: int, end_ms: int) -> dict:
    """Run /dmaOrganizationalPageContentAnalytics?q=trend in <=12-month windows
    and merge their `elements` into a single response.

    A window that fails persistently (e.g. an old span where the page had no
    activity, which the endpoint sometimes returns 500 for instead of an empty
    list) is skipped — the remaining windows still produce data.
    """
    merged: dict = {"elements": [], "metadata": {}, "paging": {"start": 0, "count": 0, "links": []}}
    failed: list[dict] = []
    windows = _analytics_windows(start_ms, end_ms)
    for w_start, w_end in windows:
        time_intervals = f"(timeRange:(start:{w_start},end:{w_end}),timeGranularityType:DAY)"
        raw = (
            f"q=trend"
            f"&sourceEntity={urllib.parse.quote(source_entity, safe='')}"
            f"&metricTypes={metric_types}"
            f"&timeIntervals={time_intervals}"
        )
        try:
            page = client.get("/rest/dmaOrganizationalPageContentAnalytics", raw_query=raw)
        except Exception as e:
            label_s = datetime.fromtimestamp(w_start / 1000, tz=timezone.utc).strftime("%Y-%m-%d")
            label_e = datetime.fromtimestamp(w_end / 1000, tz=timezone.utc).strftime("%Y-%m-%d")
            print(f"    skipping window {label_s}..{label_e}: {str(e)[:200]}")
            failed.append({"start_ms": w_start, "end_ms": w_end, "error": str(e)[:500]})
            continue
        elements = page.get("elements") or []
        merged["elements"].extend(elements)
        merged["paging"]["count"] = len(merged["elements"])
    if failed:
        merged["metadata"]["failedWindows"] = failed
    return merged


def collect_analytics(client: LinkedInClient, org_id: str, post_urns: list[str], out_dir: Path,
                       start_ms: int | None, end_ms: int | None) -> None:
    """Org-level trend + per-post trend via /rest/dmaOrganizationalPageContentAnalytics."""
    metric_types = "List(IMPRESSIONS,UNIQUE_IMPRESSIONS,CLICKS,COMMENTS,REACTIONS,REPOSTS,ENGAGEMENT_RATE,CTR)"
    if start_ms is None:
        # Default to the earliest post timestamp present (decoded from URN), else
        # 2010-01-01 — wide enough to cover the org's full history.
        candidates: list[int] = []
        for u in post_urns or []:
            t = urn_timestamp_ms(u)
            if t:
                candidates.append(t)
        if candidates:
            start_ms = min(candidates) - 24 * 3600 * 1000  # 1 day of slack
        else:
            start_ms = int(datetime(2010, 1, 1, tzinfo=timezone.utc).timestamp() * 1000)
    if end_ms is None:
        end_ms = int(datetime.now(timezone.utc).timestamp() * 1000)

    n_windows = len(_analytics_windows(start_ms, end_ms))
    print(f"\n[analytics] org-level trend ({n_windows} windows of <=12 months)")
    org_urn = f"urn:li:organizationalPage:{org_id}"
    org_trend = _fetch_trend_chunked(client, org_urn, metric_types, start_ms, end_ms)
    write_json(out_dir / "analytics_org_trend.json", org_trend)

    if not post_urns:
        return
    print(f"[analytics] per-post trend for {len(post_urns)} posts")
    per_post_dir = out_dir / "per_post"
    for n, urn in enumerate(post_urns, 1):
        slug = urn.replace(":", "_")
        # For per-post analytics, narrow the window to [post_date - 1d, post_date + 12 months]
        # — most engagement lands in that span and it always fits in a single API call.
        post_ms = urn_timestamp_ms(urn) or start_ms
        post_start = max(start_ms, post_ms - 24 * 3600 * 1000)
        post_end = min(end_ms, post_ms + _ANALYTICS_MAX_MS)
        try:
            data = _fetch_trend_chunked(client, urn, metric_types, post_start, post_end)
            write_json(per_post_dir / slug / "analytics.json", data)
        except Exception as e:
            print(f"  ({n}/{len(post_urns)}) {urn}: error {e}")
        time.sleep(0.5)


# --------------------------------- render ---------------------------------

def _localized(field) -> str:
    """Try to extract a string from a LinkedIn-style localized field."""
    if isinstance(field, str):
        return field
    if isinstance(field, dict):
        # {"localized": {"en_US": "..."}} or direct mapping
        loc = field.get("localized") if "localized" in field else field
        if isinstance(loc, dict) and loc:
            # Prefer en_US if available, else first.
            return loc.get("en_US") or next(iter(loc.values()), "")
    return ""


_RX_HASHTAG = re.compile(r"\{hashtag\|\\?#\|([^}]+)\}")
_RX_MENTION_ORG = re.compile(r"@\[([^\]]+)\]\(urn:li:organization:(\d+)\)")
_RX_MENTION_PERSON = re.compile(r"@\[([^\]]+)\]\(urn:li:person:[^)]+\)")
_RX_BACKSLASH_PUNCT = re.compile(r"\\([()|\[\]])")


def _clean_post_text(text: str) -> str:
    """Translate LinkedIn's inline markup into readable markdown.

    - {hashtag|\\#|NAME}  -> [#NAME](https://www.linkedin.com/feed/hashtag/?keywords=NAME)
    - @[Name](urn:li:organization:123) -> [Name](https://www.linkedin.com/company/123/)
    - @[Name](urn:li:person:xxx) -> **Name**  (person URN can't be turned into a public URL)
    - Unescape \\( \\) \\| \\[ \\] back to literal punctuation.
    """
    if not text:
        return text
    text = _RX_HASHTAG.sub(
        lambda m: f"[#{m.group(1)}](https://www.linkedin.com/feed/hashtag/?keywords={urllib.parse.quote(m.group(1))})",
        text,
    )
    text = _RX_MENTION_ORG.sub(
        lambda m: f"[{m.group(1)}](https://www.linkedin.com/company/{m.group(2)}/)",
        text,
    )
    text = _RX_MENTION_PERSON.sub(lambda m: f"**{m.group(1)}**", text)
    text = _RX_BACKSLASH_PUNCT.sub(r"\1", text)
    return text


def _post_text(post: dict) -> str:
    if not isinstance(post, dict):
        return ""
    # Try common shapes for post body text.
    for k in ("commentary", "text", "body", "content"):
        v = post.get(k)
        if isinstance(v, str) and v.strip():
            return v
    sc = post.get("specificContent")
    if isinstance(sc, dict):
        ugc = sc.get("com.linkedin.ugc.ShareContent") or {}
        sc_text = (ugc.get("shareCommentary") or {}).get("text")
        if isinstance(sc_text, str):
            return sc_text
    return ""


def _post_created_ms(post: dict, urn: str) -> int | None:
    if isinstance(post, dict):
        for k in ("firstPublishedAt", "publishedAt", "createdAt", "lastModifiedAt"):
            v = post.get(k)
            if isinstance(v, int) and v > 10**12:
                return v
            if isinstance(v, dict):
                t = v.get("time") or v.get("value") or v.get("timestamp")
                if isinstance(t, int) and t > 10**12:
                    return t
    return urn_timestamp_ms(urn)


def _flatten_batch_results(pages) -> dict:
    """BATCH_GET pages -> single {urn: object} dict."""
    out: dict[str, dict] = {}
    if not isinstance(pages, list):
        pages = [pages]
    for p in pages:
        if not isinstance(p, dict):
            continue
        results = p.get("results")
        if isinstance(results, dict):
            out.update(results)
    return out


def _post_url(urn: str) -> str:
    return f"https://www.linkedin.com/feed/update/{urllib.parse.quote(urn, safe=':')}/"


def _iter_media(post: dict):
    """Yield (kind, alt_text, download_url) tuples for each downloadable media item.

    kind is one of: image, video, video-thumb, document, article-thumb.
    Non-downloadable post artefacts (article cards, polls, event references)
    are rendered separately by the caller via _render_post_extras().
    """
    content = (post or {}).get("content") or {}
    if not isinstance(content, dict):
        return

    media = content.get("media")
    if isinstance(media, dict):
        alt = media.get("altText", "") or ""
        inner = media.get("media")
        if isinstance(inner, dict):
            img = inner.get("image")
            if isinstance(img, dict):
                url = img.get("downloadUrl")
                if isinstance(url, str) and url.startswith("http"):
                    yield ("image", alt, url)
            vid = inner.get("video")
            if isinstance(vid, dict):
                vurl = vid.get("downloadUrl") or vid.get("playbackUrl")
                if isinstance(vurl, str) and vurl.startswith("http"):
                    yield ("video", alt, vurl)
                # Save the highest-res thumbnail too so the markdown has a poster frame.
                thumbs = vid.get("thumbnails") or []
                if isinstance(thumbs, list):
                    for t in thumbs:
                        if isinstance(t, dict):
                            turl = t.get("downloadUrl")
                            if isinstance(turl, str) and turl.startswith("http"):
                                yield ("video-thumb", alt, turl)
                                break
            doc = inner.get("document")
            if isinstance(doc, dict):
                durl = doc.get("downloadUrl")
                if isinstance(durl, str) and durl.startswith("http"):
                    yield ("document", alt, durl)

    multi = content.get("multiImage")
    if isinstance(multi, dict):
        for wrap in multi.get("images") or []:
            if isinstance(wrap, dict):
                inner = wrap.get("media") or {}
                img = inner.get("image") if isinstance(inner, dict) else None
                url = img.get("downloadUrl") if isinstance(img, dict) else None
                if isinstance(url, str) and url.startswith("http"):
                    yield ("image", wrap.get("altText", "") or "", url)

    article = content.get("article")
    if isinstance(article, dict):
        for k in ("thumbnail", "thumbnailUrl"):
            t = article.get(k)
            if isinstance(t, str) and t.startswith("http"):
                yield ("article-thumb", article.get("title") or "", t)


def _render_post_extras(post: dict) -> list[str]:
    """Return additional markdown lines for content types that aren't a downloadable file:
    article cards, polls, and event/entity references."""
    out: list[str] = []
    content = (post or {}).get("content") or {}
    if not isinstance(content, dict):
        return out

    article = content.get("article")
    if isinstance(article, dict):
        title = article.get("title") or article.get("source") or "Article"
        source = article.get("source") or ""
        desc = article.get("description") or ""
        out.append("## Linked article")
        out.append("")
        if source:
            out.append(f"**[{title}]({source})**")
        else:
            out.append(f"**{title}**")
        if desc:
            out.append("")
            for line in desc.splitlines():
                out.append(f"> {line}")
        out.append("")

    poll = content.get("poll")
    if isinstance(poll, dict):
        question = poll.get("question") or "Poll"
        options = poll.get("options") or []
        total = poll.get("uniqueVotersCount")
        out.append(f"## Poll: {question}")
        out.append("")
        if isinstance(options, list):
            for opt in options:
                if isinstance(opt, dict):
                    label = opt.get("text") or ""
                    votes = opt.get("voteCount")
                    suffix = f" — {votes} vote{'s' if votes != 1 else ''}" if isinstance(votes, int) else ""
                    out.append(f"- {label}{suffix}")
        if isinstance(total, int):
            out.append("")
            out.append(f"_Total voters: {total}_")
        out.append("")

    ref = content.get("reference")
    if isinstance(ref, dict):
        ref_id = ref.get("id") or ref.get("urn")
        if isinstance(ref_id, str):
            out.append("## Reference")
            out.append("")
            out.append(f"`{ref_id}`")
            out.append("")

    return out


def _ext_for_url(url: str, kind: str) -> str:
    path = urllib.parse.urlparse(url).path
    if "." in path:
        ext = path.rsplit(".", 1)[-1].lower()
        if ext in {"jpg", "jpeg", "png", "gif", "webp", "mp4", "mov", "webm", "pdf"}:
            return ext
    if kind in ("image", "article-thumb", "video-thumb"):
        return "jpg"
    if kind == "video":
        return "mp4"
    if kind == "document":
        return "pdf"
    return "bin"


def _download_media(url: str, dest: Path) -> bool:
    if dest.exists() and dest.stat().st_size > 0:
        return True
    try:
        r = requests.get(url, stream=True, timeout=120)
    except Exception as e:
        print(f"    media download failed ({e})")
        return False
    if not r.ok:
        print(f"    media {dest.name}: HTTP {r.status_code}")
        return False
    dest.parent.mkdir(parents=True, exist_ok=True)
    with open(dest, "wb") as f:
        for chunk in r.iter_content(8192):
            f.write(chunk)
    return True


def _actor_label(actor_urn: str | None, people: dict, orgs: dict) -> str:
    """Render a clickable label for a person or organization URN, with privacy fallbacks."""
    if not actor_urn:
        return "_(private)_"
    if actor_urn.startswith("urn:li:person:"):
        info = people.get(actor_urn) or {}
        first = _localized(info.get("firstName")) or info.get("localizedFirstName") or ""
        last = _localized(info.get("lastName")) or info.get("localizedLastName") or ""
        name = f"{first} {last}".strip()
        vanity = info.get("vanityName") or info.get("publicIdentifier")
        public_url = info.get("publicProfileUrl")
        if not public_url and vanity:
            public_url = f"https://www.linkedin.com/in/{vanity}/"
        if name and public_url:
            return f"[{name}]({public_url})"
        if name:
            return f"{name} (`{actor_urn}`)"
        return f"`{actor_urn}`"
    if actor_urn.startswith("urn:li:organization:"):
        info = orgs.get(actor_urn) or {}
        name = (
            _localized(info.get("localizedName"))
            or _localized(info.get("name"))
            or info.get("vanityName")
            or ""
        )
        vanity = info.get("vanityName")
        org_id = actor_urn.rsplit(":", 1)[-1]
        url = f"https://www.linkedin.com/company/{vanity or org_id}/"
        if name:
            return f"[{name}]({url})"
        return f"[{actor_urn}]({url})"
    return f"`{actor_urn}`"


def _comment_text(c: dict) -> str:
    if not isinstance(c, dict):
        return ""
    msg = c.get("message")
    if isinstance(msg, dict):
        t = msg.get("text") or msg.get("attributedText", {}).get("text")
        if isinstance(t, str):
            return t
    for k in ("commentary", "text", "content"):
        v = c.get(k)
        if isinstance(v, str):
            return v
    return ""


def _actor_in(obj) -> str | None:
    """Pull an actor URN from an object — direct field or nested in created/lastModified."""
    if not isinstance(obj, dict):
        return None
    for k in ("actor", "reactor", "agent", "author", "creator", "from"):
        v = obj.get(k)
        if isinstance(v, str) and v.startswith("urn:li:"):
            return v
    for k in ("created", "lastModified"):
        sub = obj.get(k)
        if isinstance(sub, dict):
            v = sub.get("actor")
            if isinstance(v, str) and v.startswith("urn:li:"):
                return v
    return None


def _comment_actor(c: dict) -> str | None:
    return _actor_in(c)


def _reaction_actor(r: dict, urn: str | None = None) -> str | None:
    a = _actor_in(r)
    if a:
        return a
    # Compound reaction URN: urn:li:reaction:(<actor_urn>,<entity_urn>)
    if urn and "(" in urn:
        inside = urn.split("(", 1)[1].rsplit(")", 1)[0]
        first = inside.split(",", 1)[0].strip()
        if first.startswith("urn:li:"):
            return first
    return None


def _reaction_type(r: dict) -> str:
    if not isinstance(r, dict):
        return ""
    return r.get("reactionType") or r.get("type") or ""


def _ts_to_str(ms) -> str:
    if not isinstance(ms, int) or ms < 10**12:
        return ""
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def _impressions(analytics: dict) -> dict[str, int | None]:
    """Pull totals for IMPRESSIONS/REACTIONS/COMMENTS/REPOSTS from a trend response."""
    out: dict[str, int | None] = {"IMPRESSIONS": None, "REACTIONS": None, "COMMENTS": None, "REPOSTS": None, "CLICKS": None}
    if not isinstance(analytics, dict):
        return out
    for el in analytics.get("elements") or []:
        t = el.get("type")
        if t not in out:
            continue
        m = el.get("metric") or {}
        v = (m.get("value") or {}).get("totalCount") or {}
        n = v.get("long")
        if n is None:
            bd = v.get("bigDecimal")
            try:
                n = int(float(bd)) if bd is not None else None
            except ValueError:
                n = None
        if n is not None:
            out[t] = (out[t] or 0) + n
    return out


def collect_people(client: LinkedInClient, urns: list[str]) -> dict:
    """BATCH_GET /rest/dmaPeople for the given person URNs."""
    if not urns:
        return {}
    print(f"\n[render] resolving {len(urns)} person URN(s) via /rest/dmaPeople")
    try:
        pages = batch_get(client, "/rest/dmaPeople", urns)
    except Exception as e:
        print(f"  /rest/dmaPeople failed: {e}")
        return {}
    return _flatten_batch_results(pages)


def collect_orgs(client: LinkedInClient, urns: list[str]) -> dict:
    """BATCH_GET /rest/dmaOrganizationLookup for the given organization URNs.

    The endpoint expects integer IDs in `ids=List(...)`, not full URNs;
    we strip the URN prefix and re-key the response back to URN form.
    """
    if not urns:
        return {}
    ids = []
    id_to_urn: dict[str, str] = {}
    for u in urns:
        n = u.rsplit(":", 1)[-1]
        if n.isdigit():
            ids.append(n)
            id_to_urn[n] = u
    if not ids:
        return {}
    print(f"[render] resolving {len(ids)} organization URN(s) via /rest/dmaOrganizationLookup")
    out: list[dict] = []
    chunk = 50
    for i in range(0, len(ids), chunk):
        batch = ids[i:i + chunk]
        raw = "ids=" + "List(" + ",".join(urllib.parse.quote(x, safe="") for x in batch) + ")"
        try:
            page = client.get("/rest/dmaOrganizationLookup", raw_query=raw)
        except Exception as e:
            print(f"  /rest/dmaOrganizationLookup failed: {e}")
            return {}
        out.append(page)
        time.sleep(0.5)
    flat = _flatten_batch_results(out)
    # Re-key from numeric ID (string) to full URN so _actor_label can find them.
    rekeyed: dict[str, dict] = {}
    for k, v in flat.items():
        # Some BATCH_GETs key by string of int; ensure both forms work.
        if k in id_to_urn:
            rekeyed[id_to_urn[k]] = v
        else:
            rekeyed[k] = v
    return rekeyed


def render_markdown(client: LinkedInClient, out_dir: Path, post_urns: list[str],
                     repost_urns: list[str] | None = None) -> None:
    """Build per-post markdown files under posts_md/<year>/<date>_<short-id>.md."""
    posts_path = out_dir / "posts.json"
    if not posts_path.exists():
        print("[render] posts.json missing; skipping render")
        return
    posts_pages = json.loads(posts_path.read_text())
    posts = _flatten_batch_results(posts_pages)

    # Hydrate instant reposts so we can render them with the same date/link structure.
    reposts: dict = {}
    repost_actor_orgs: set[str] = set()
    if repost_urns:
        try:
            print(f"\n[render] hydrating {len(repost_urns)} instant repost(s) via /rest/dmaInstantReposts")
            rp_pages = batch_get(client, "/rest/dmaInstantReposts", repost_urns)
            write_json(out_dir / "instant_reposts.json", rp_pages)
            reposts = _flatten_batch_results(rp_pages)
            for r in reposts.values():
                a = _actor_in(r)
                if a and a.startswith("urn:li:organization:"):
                    repost_actor_orgs.add(a)
        except Exception as e:
            print(f"  /rest/dmaInstantReposts BATCH_GET failed: {e}")

    # Collect actor URNs (people + orgs) from comments + reactions.
    per_post: dict[str, dict] = {}
    person_urns: set[str] = set()
    org_urns: set[str] = set()
    for urn in post_urns:
        slug = urn.replace(":", "_")
        d = out_dir / "per_post" / slug
        comments_pages = json.loads((d / "comments.json").read_text()) if (d / "comments.json").exists() else []
        reactions_pages = json.loads((d / "reactions.json").read_text()) if (d / "reactions.json").exists() else []
        analytics = json.loads((d / "analytics.json").read_text()) if (d / "analytics.json").exists() else {}
        comments = _flatten_batch_results(comments_pages) if comments_pages else {}
        reactions = _flatten_batch_results(reactions_pages) if reactions_pages else {}
        for c in comments.values():
            a = _comment_actor(c)
            if a and a.startswith("urn:li:person:"):
                person_urns.add(a)
            elif a and a.startswith("urn:li:organization:"):
                org_urns.add(a)
        for r_urn, r in reactions.items():
            a = _reaction_actor(r, r_urn)
            if a and a.startswith("urn:li:person:"):
                person_urns.add(a)
            elif a and a.startswith("urn:li:organization:"):
                org_urns.add(a)
        per_post[urn] = {
            "comments": comments,
            "reactions": reactions,
            "analytics": analytics,
        }

    people = collect_people(client, sorted(person_urns))
    orgs = collect_orgs(client, sorted(org_urns | repost_actor_orgs))
    write_json(out_dir / "people.json", people)
    write_json(out_dir / "orgs.json", orgs)

    md_root = out_dir / "posts_md"
    print(f"\n[render] writing {len(post_urns)} markdown post(s) under {md_root}")
    for urn in post_urns:
        post = posts.get(urn)
        ms = _post_created_ms(post or {}, urn)
        if not ms:
            print(f"  skip {urn}: no timestamp")
            continue
        dt = datetime.fromtimestamp(ms / 1000, tz=timezone.utc)
        date_s = dt.strftime("%Y-%m-%d")
        short_id = urn.rsplit(":", 1)[-1][-7:]
        target = md_root / str(dt.year) / f"{date_s}_{short_id}.md"

        bundle = per_post.get(urn) or {}
        analytics_totals = _impressions(bundle.get("analytics") or {})
        text = _clean_post_text(_post_text(post or {}))

        # Download media (images/videos/documents) and build relative paths for the markdown.
        slug = urn.replace(":", "_")
        images_dir = out_dir / "images" / slug
        media_items = list(_iter_media(post or {}))
        local_media: list[tuple[str, str, Path]] = []
        for idx, (kind, alt, url) in enumerate(media_items):
            ext = _ext_for_url(url, kind)
            dest = images_dir / f"{idx:02d}_{kind}.{ext}"
            if _download_media(url, dest):
                local_media.append((kind, alt, dest))

        lines: list[str] = []
        first_line = (text.strip().splitlines() or [""])[0][:80].strip() or urn
        lines.append(f"# {first_line}")
        lines.append("")
        lines.append(f"- **Date:** {date_s} ({_ts_to_str(ms)})")
        lines.append(f"- **URN:** `{urn}`")
        lines.append(f"- **Link:** {_post_url(urn)}")
        lines.append("")
        lines.append("## Stats")
        lines.append("")
        for k in ("IMPRESSIONS", "REACTIONS", "COMMENTS", "REPOSTS", "CLICKS"):
            v = analytics_totals.get(k)
            lines.append(f"- {k.title()}: {v if v is not None else '—'}")
        lines.append("")

        lines.append("## Content")
        lines.append("")
        lines.append(text.strip() if text else "_(no text body found in dmaPosts response — see posts.json)_")
        lines.append("")

        if local_media:
            lines.append(f"## Media ({len(local_media)})")
            lines.append("")
            md_path_parent = md_root / str(dt.year)
            for kind, alt, path in local_media:
                try:
                    rel = os.path.relpath(path, md_path_parent)
                except ValueError:
                    rel = str(path)
                if kind in ("image", "article-thumb", "video-thumb"):
                    lines.append(f"![{alt}]({rel})")
                elif kind == "video":
                    label = alt or "video"
                    lines.append(f"[▶ Watch {label} (mp4)]({rel})")
                elif kind == "document":
                    label = alt or "document"
                    lines.append(f"[📄 {label} (download)]({rel})")
                else:
                    label = alt or kind
                    lines.append(f"- [{label} ({kind})]({rel})")
                lines.append("")

        lines.extend(_render_post_extras(post or {}))

        reactions = bundle.get("reactions") or {}
        lines.append(f"## Reactions ({len(reactions)})")
        lines.append("")
        if not reactions:
            lines.append("_None._")
        else:
            for r_urn, r in reactions.items():
                rtype = _reaction_type(r) or "REACT"
                actor = _reaction_actor(r, r_urn)
                lines.append(f"- **{rtype}** — {_actor_label(actor, people, orgs)}")
        lines.append("")

        comments = bundle.get("comments") or {}
        lines.append(f"## Comments ({len(comments)})")
        lines.append("")
        if not comments:
            lines.append("_None._")
        else:
            def _comment_ts(c):
                if not isinstance(c, dict):
                    return 0
                v = c.get("createdAt")
                if isinstance(v, int):
                    return v
                cv = c.get("created")
                if isinstance(cv, dict) and isinstance(cv.get("time"), int):
                    return cv["time"]
                return 0
            ordered = sorted(comments.items(), key=lambda kv: _comment_ts(kv[1]))
            for c_urn, c in ordered:
                actor = _comment_actor(c)
                created_ms = _comment_ts(c)
                ctext = _clean_post_text(_comment_text(c).strip())
                lines.append(f"### {_actor_label(actor, people, orgs)} — {_ts_to_str(created_ms) or 'unknown date'}")
                lines.append("")
                lines.append(ctext if ctext else "_(content not shared — commenter has not opted in)_")
                lines.append("")

        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("\n".join(lines))
        try:
            rel = target.resolve().relative_to(ROOT)
        except ValueError:
            rel = target
        print(f"  wrote {rel}")

    # Render instant reposts as their own short markdown files.
    for urn in (repost_urns or []):
        repost = reposts.get(urn) or {}
        # Extract the underlying share/ugcPost URN from the compound key:
        # urn:li:instantRepost:(<original_urn>,<repost_id>)
        original = ""
        if "(" in urn:
            inside = urn.split("(", 1)[1].rsplit(")", 1)[0]
            original = inside.split(",", 1)[0].strip()
        # Try to read createdAt from the repost object; fall back to URN-decoded ms
        # of the repost id (second element of the compound).
        ms = None
        if isinstance(repost, dict):
            for k in ("createdAt", "created"):
                v = repost.get(k)
                if isinstance(v, int) and v > 10**12:
                    ms = v
                    break
                if isinstance(v, dict):
                    t = v.get("time")
                    if isinstance(t, int) and t > 10**12:
                        ms = t
                        break
        if not ms and "(" in urn:
            tail = urn.split(",", 1)[-1].rstrip(")")
            try:
                ms = int(tail) >> 22
                if not (1_200_000_000_000 < ms < 2_500_000_000_000):
                    ms = None
            except ValueError:
                ms = None
        if not ms:
            ms = urn_timestamp_ms(original) if original else None
        if not ms:
            print(f"  skip repost {urn}: no timestamp")
            continue
        dt = datetime.fromtimestamp(ms / 1000, tz=timezone.utc)
        date_s = dt.strftime("%Y-%m-%d")
        short_id = urn.rstrip(")").rsplit(",", 1)[-1][-7:]
        target = md_root / str(dt.year) / f"{date_s}_repost_{short_id}.md"
        actor = _actor_in(repost) if isinstance(repost, dict) else None
        original_link = _post_url(original) if original else "—"

        lines: list[str] = [
            f"# Repost — {date_s}",
            "",
            f"- **Date:** {date_s} ({_ts_to_str(ms)})",
            f"- **Repost URN:** `{urn}`",
            f"- **Original:** `{original}`",
            f"- **Original link:** {original_link}",
        ]
        if actor:
            lines.append(f"- **Reposter:** {_actor_label(actor, people, orgs)}")
        lines += [
            "",
            "_(This is an instant repost — engagement and analytics live on the original post.)_",
        ]
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("\n".join(lines))
        try:
            rel = target.resolve().relative_to(ROOT)
        except ValueError:
            rel = target
        print(f"  wrote {rel}")


# ------------------------------- entrypoint --------------------------------

def main() -> None:
    load_env()
    p = argparse.ArgumentParser(description="Export LinkedIn Pages Data Portability data for a company page.")
    p.add_argument("--org-id", default=os.environ.get("LINKEDIN_ORG_ID"),
                   help="Organization ID (numeric). Defaults to $LINKEDIN_ORG_ID.")
    p.add_argument("--out", default="out", help="Output directory (default: ./out)")
    p.add_argument("--auth-only", action="store_true", help="Just run the OAuth flow, don't fetch data.")
    p.add_argument("--reauth", action="store_true", help="Force a fresh OAuth flow (ignore cached token).")

    p.add_argument("--posts", action="store_true", help="Fetch posts (URNs + hydrated objects).")
    p.add_argument("--list-only", action="store_true",
                   help="Only list post URNs (write post_urns.json), then exit. Skips BATCH_GET, engagement, analytics, followers.")
    p.add_argument("--engagement", action="store_true",
                   help="Per post: comments, reactions, social metadata. Implies --posts.")
    p.add_argument("--analytics", action="store_true",
                   help="Org trend analytics + per-post analytics. Implies --posts for per-post.")
    p.add_argument("--followers", action="store_true",
                   help="Fetch follower edges. Note: 1 req / 60s rate limit.")
    p.add_argument("--all", action="store_true",
                   help="Shortcut for --posts --engagement --analytics --followers.")
    p.add_argument("--render", action="store_true",
                   help="After fetching, write per-post markdown files under posts_md/<year>/<YYYY-MM-DD>_<id>.md "
                        "(content + reactions with profile links + threaded comments + impressions). "
                        "Implies --posts --engagement --analytics.")

    p.add_argument("--year", default="all",
                   help="Filter posts by creation year. Examples: '2025', '2024,2025', '2022-2024', 'all' (default).")
    p.add_argument("--max-pages", type=int, default=None,
                   help="Cap pages per listing (debug).")
    p.add_argument("--analytics-start-ms", type=int, default=None,
                   help="Analytics window start (epoch ms). Default: derived from --year, "
                        "else the earliest post date in the listing (so older posts get analytics too).")
    p.add_argument("--analytics-end-ms", type=int, default=None,
                   help="Analytics window end (epoch ms). Default: derived from --year, else now.")
    args = p.parse_args()

    token = get_access_token(force_reauth=args.reauth)
    if args.auth_only:
        print("OAuth done.")
        return

    if not args.org_id:
        sys.exit("--org-id is required (or set LINKEDIN_ORG_ID).")

    if args.all:
        args.posts = args.engagement = args.analytics = args.followers = True
    if args.render:
        args.posts = args.engagement = args.analytics = True
    if args.engagement or args.analytics:
        args.posts = True
    if args.list_only:
        args.posts = True
    if not (args.posts or args.engagement or args.analytics or args.followers):
        sys.exit("Nothing to do — pass --posts / --engagement / --analytics / --followers / --all / --list-only / --render.")

    years = parse_year_arg(args.year)
    # Derive analytics window from --year if not explicitly given.
    if years and args.analytics_start_ms is None:
        args.analytics_start_ms = int(datetime(min(years), 1, 1, tzinfo=timezone.utc).timestamp() * 1000)
    if years and args.analytics_end_ms is None:
        args.analytics_end_ms = int(datetime(max(years) + 1, 1, 1, tzinfo=timezone.utc).timestamp() * 1000) - 1

    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H%M%SZ")
    out_dir = Path(args.out) / f"org-{args.org_id}" / ts
    out_dir.mkdir(parents=True, exist_ok=True)
    print(f"Output: {out_dir}")

    client = LinkedInClient(token)

    post_urns: list[str] = []
    repost_urns: list[str] = []
    if args.posts:
        all_urns = collect_post_urns(client, args.org_id, out_dir, args.max_pages, years)
        # Split off instantRepost URNs — they have a compound key shape that
        # /rest/dmaPosts, comments/reactions endpoints, and per-post analytics
        # all reject. They get their own pipeline (hydrated via dmaInstantReposts
        # in the renderer) and are summarized separately.
        post_urns = [u for u in all_urns if not u.startswith("urn:li:instantRepost:")]
        repost_urns = [u for u in all_urns if u.startswith("urn:li:instantRepost:")]
        if repost_urns:
            print(f"  ({len(repost_urns)} instant repost(s) split off — hydrated via /rest/dmaInstantReposts at render time)")
            write_json(out_dir / "repost_urns.json", repost_urns)
        if args.list_only:
            print(f"\n[list-only] stopping after listing. URNs in {out_dir / 'post_urns.json'}")
            return
        collect_posts(client, post_urns, out_dir)
    if args.engagement:
        collect_engagement_for_posts(client, post_urns, out_dir, args.max_pages)
    if args.analytics:
        collect_analytics(client, args.org_id, post_urns, out_dir,
                          args.analytics_start_ms, args.analytics_end_ms)
    if args.followers:
        collect_followers(client, args.org_id, out_dir, args.max_pages)

    if args.render:
        render_markdown(client, out_dir, post_urns, repost_urns)

    print(f"\nDone. Output in {out_dir}")


if __name__ == "__main__":
    main()
