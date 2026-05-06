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
    print(f"  wrote {path.relative_to(ROOT)} ({path.stat().st_size:,} bytes)")


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
    page_urn = f"urn:li:organizationalPage:{org_id}"
    params = {"q": "postsByAuthor", "author": page_urn}
    pages = []
    urns: list[str] = []
    urn_meta: list[dict] = []  # parallel: {urn, year?, ts_ms?}
    seen: set[str] = set()
    earliest_wanted = min(years) if years else None
    short_circuit = False
    for i, page in enumerate(paginate_start(client, "/rest/dmaFeedContentsExternal", params, page_size=50, sleep_between=1)):
        pages.append(page)
        page_new = 0
        page_skipped_year = 0
        for el in page.get("elements", []):
            urn = None
            for k in ("ugcUrn", "instantRepostUrn", "shareUrn", "postUrn", "urn"):
                v = el.get(k)
                if isinstance(v, str):
                    urn = v
                    break
            if not urn or urn in seen:
                continue
            ts_ms = _extract_timestamp_ms(el)
            year = datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc).year if ts_ms else None
            # year filter
            if years is not None and year is not None and year not in years:
                page_skipped_year += 1
                # Short-circuit: results are creation-desc, so once we're below
                # the earliest wanted year we can stop entirely.
                if earliest_wanted is not None and year < earliest_wanted:
                    short_circuit = True
                continue
            if years is not None and year is None:
                # No timestamp on the listing element — keep it; we'll filter
                # again after hydration if needed.
                pass
            seen.add(urn)
            urns.append(urn)
            urn_meta.append({"urn": urn, "year": year, "ts_ms": ts_ms})
            page_new += 1
            if ts_ms is not None:
                date_label = datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc).strftime("%Y-%m-%d")
            else:
                date_label = "????-??-??"
            print(f"    {len(urns):>4}. [{date_label}] {urn}")
        msg = f"  page {i + 1}: +{page_new} kept"
        if page_skipped_year:
            msg += f", {page_skipped_year} skipped (year)"
        msg += f"  (total {len(urns)})"
        print(msg)
        if short_circuit:
            print(f"  short-circuit: page contained items older than earliest wanted year ({earliest_wanted})")
            break
        if max_pages and i + 1 >= max_pages:
            print(f"  stopping at --max-pages={max_pages}")
            break
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
        for i, page in enumerate(paginate_start(
            client, "/rest/dmaFeedContentsExternal",
            {"q": "commentsOnEntity", "entity": urn},
            page_size=50, sleep_between=1,
        )):
            for el in page.get("elements", []):
                for k in ("commentUrn", "urn"):
                    if k in el and isinstance(el[k], str):
                        comment_urns.append(el[k])
                        break
            if max_pages_per_post and i + 1 >= max_pages_per_post:
                break
        if comment_urns:
            comment_urns = list(dict.fromkeys(comment_urns))
            write_json(post_dir / "comments.json", batch_get(client, "/rest/dmaComments", comment_urns))
        # reactions
        reaction_urns: list[str] = []
        for i, page in enumerate(paginate_start(
            client, "/rest/dmaFeedContentsExternal",
            {"q": "reactionsOnEntity", "entity": urn},
            page_size=50, sleep_between=1,
        )):
            for el in page.get("elements", []):
                for k in ("reactionUrn", "urn"):
                    if k in el and isinstance(el[k], str):
                        reaction_urns.append(el[k])
                        break
            if max_pages_per_post and i + 1 >= max_pages_per_post:
                break
        if reaction_urns:
            reaction_urns = list(dict.fromkeys(reaction_urns))
            write_json(post_dir / "reactions.json", batch_get(client, "/rest/dmaReactions", reaction_urns))
        # social metadata (counts)
        write_json(post_dir / "social_metadata.json",
                   batch_get(client, "/rest/dmaSocialMetadata", [urn]))


def collect_analytics(client: LinkedInClient, org_id: str, post_urns: list[str], out_dir: Path,
                       start_ms: int | None, end_ms: int | None) -> None:
    """Org-level trend + per-post trend via /rest/dmaOrganizationalPageContentAnalytics."""
    print("\n[analytics] org-level trend")
    metric_types = "List(IMPRESSIONS,UNIQUE_IMPRESSIONS,CLICKS,COMMENTS,REACTIONS,REPOSTS,ENGAGEMENT_RATE,CTR)"
    if start_ms is None:
        start_ms = int((datetime.now(timezone.utc).timestamp() - 365 * 24 * 3600) * 1000)
    if end_ms is None:
        end_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
    time_intervals = f"(timeRange:(start:{start_ms},end:{end_ms}),timeGranularityType:DAY)"
    org_urn = f"urn:li:organizationalPage:{org_id}"
    raw = (
        f"q=trend"
        f"&sourceEntity={urllib.parse.quote(org_urn, safe='')}"
        f"&metricTypes={metric_types}"
        f"&timeIntervals={time_intervals}"
    )
    org_trend = client.get("/rest/dmaOrganizationalPageContentAnalytics", raw_query=raw)
    write_json(out_dir / "analytics_org_trend.json", org_trend)

    if not post_urns:
        return
    print(f"[analytics] per-post trend for {len(post_urns)} posts")
    per_post_dir = out_dir / "per_post"
    for n, urn in enumerate(post_urns, 1):
        slug = urn.replace(":", "_")
        raw = (
            f"q=trend"
            f"&sourceEntity={urllib.parse.quote(urn, safe='')}"
            f"&metricTypes={metric_types}"
            f"&timeIntervals={time_intervals}"
        )
        try:
            data = client.get("/rest/dmaOrganizationalPageContentAnalytics", raw_query=raw)
            write_json(per_post_dir / slug / "analytics.json", data)
        except Exception as e:
            print(f"  ({n}/{len(post_urns)}) {urn}: error {e}")
        time.sleep(0.5)


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

    p.add_argument("--year", default="all",
                   help="Filter posts by creation year. Examples: '2025', '2024,2025', '2022-2024', 'all' (default).")
    p.add_argument("--max-pages", type=int, default=None,
                   help="Cap pages per listing (debug).")
    p.add_argument("--analytics-start-ms", type=int, default=None,
                   help="Analytics window start (epoch ms). Default: derived from --year, else now - 365 days.")
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
    if args.engagement or args.analytics:
        args.posts = True
    if args.list_only:
        args.posts = True
    if not (args.posts or args.engagement or args.analytics or args.followers):
        sys.exit("Nothing to do — pass --posts / --engagement / --analytics / --followers / --all / --list-only.")

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
    if args.posts:
        post_urns = collect_post_urns(client, args.org_id, out_dir, args.max_pages, years)
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

    print(f"\nDone. Output in {out_dir}")


if __name__ == "__main__":
    main()
