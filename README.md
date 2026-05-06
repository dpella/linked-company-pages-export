# LinkedIn Pages Data Portability Export

Download data from your LinkedIn company page using the [Pages Data Portability API](https://learn.microsoft.com/en-us/linkedin/dma/pages-data-portability/pages-data-portability-overview?view=li-dma-data-portability-2025-11) (DMA, EU). Produces raw JSON dumps under `./out/<org>/<timestamp>/` for downstream analysis.

See [`API_REFERENCE.md`](./API_REFERENCE.md) for the full endpoint catalogue.

## Prerequisites

1. A LinkedIn developer app at <https://www.linkedin.com/developers/apps> that has been **approved for the Pages Data Portability API product**.
2. The app's **Client ID** and **Client Secret** (Auth tab).
3. A **Redirect URL** added under the Auth tab. Since this script runs in a terminal, `http://localhost:8000/callback` works fine — the page won't load, you'll just copy the URL out of the browser bar.
4. Your LinkedIn organization ID (the numeric ID of your company page).

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env
# edit .env: fill in LINKEDIN_CLIENT_ID, LINKEDIN_CLIENT_SECRET, LINKEDIN_ORG_ID
```

## OAuth (first run)

```bash
python linkedin_export.py --auth-only
```

The script prints an authorization URL. Open it in a browser, sign in, click **Allow**, then paste either the redirect URL or just the `code=...` value back into the terminal. The token is saved to `./.token.json` (gitignored, mode 600) and refreshed automatically on later runs.

If you already have a token from <https://www.linkedin.com/developers/tools/oauth/token-generator>, set `LINKEDIN_ACCESS_TOKEN` in `.env` and skip the flow.

## Usage

```bash
# Just LIST post URNs + dates (no download). Good first run.
python linkedin_export.py --list-only

# List only posts published in 2025 (creation-time filter).
python linkedin_export.py --list-only --year 2025

# Year ranges and lists are supported.
python linkedin_export.py --list-only --year 2023-2025
python linkedin_export.py --list-only --year 2024,2025

# Posts + analytics for 2024 only (analytics window auto-derived from --year).
python linkedin_export.py --posts --analytics --year 2024

# One-shot: posts + engagement + analytics + followers, all years.
python linkedin_export.py --all

# Just followers (slow — 1 request / 60 seconds rate limit).
python linkedin_export.py --followers

# Cap pages while testing.
python linkedin_export.py --posts --max-pages 1
```

The listing phase prints one line per post like `  42. [2025-03-14] urn:li:share:1234`. Posts with no extractable timestamp on the listing element are kept and shown as `[????-??-??]`. The listing is creation-time-descending, so when filtering by year the script short-circuits pagination once it drops below the earliest requested year.

Flags:

| Flag | Effect |
| --- | --- |
| `--posts` | List post URNs via `dmaFeedContentsExternal?q=postsByAuthor`, then hydrate via `BATCH_GET /rest/dmaPosts`. |
| `--list-only` | Only list post URNs (with dates) and write `post_urns.json`. Skips hydration, engagement, analytics, followers. |
| `--year` | Filter by post creation year. `2025`, `2024,2025`, `2022-2024`, or `all` (default). |
| `--engagement` | Per post: comment URNs + reaction URNs (via `dmaFeedContentsExternal`), hydrated via `BATCH_GET /rest/dmaComments` and `/rest/dmaReactions`; plus `BATCH_GET /rest/dmaSocialMetadata` for counts. Implies `--posts`. |
| `--analytics` | Org-level trend (impressions, reactions, comments, reposts, clicks, engagement rate, CTR) + per-post trend via `/rest/dmaOrganizationalPageContentAnalytics?q=trend`. Implies `--posts`. |
| `--followers` | `dmaOrganizationalPageFollows?q=followee&edgeType=MEMBER_FOLLOWS_ORGANIZATIONAL_PAGE`. Cursor-paginated, **1 request / 60 seconds**, max 1000 per page, up to 48h delayed. |
| `--all` | All of the above. |
| `--analytics-start-ms` / `--analytics-end-ms` | Analytics time window. Defaults: derived from `--year` if set, else last 365 days. |
| `--max-pages N` | Stop after N pages on each listing (debug). |
| `--reauth` | Force a fresh OAuth flow. |
| `--auth-only` | Run OAuth, save the token, then exit. |

## Output layout

```
out/
  org-76457805/
    2026-05-06T...Z/
      post_urns.json
      post_listing_raw_pages.json
      posts.json
      followers.json
      followers_raw_pages.json
      analytics_org_trend.json
      per_post/
        urn_li_share_<id>/
          comments.json
          reactions.json
          social_metadata.json
          analytics.json
```

`*.json` files are the raw API responses (each call's full body, list of pages where pagination was used). No transformation — keep the originals so you can iterate on the analysis.

## Headers / API version

Every call sends:

```
Authorization: Bearer <token>
LinkedIn-Version: 202604
X-Restli-Protocol-Version: 2.0.0
```

OAuth scope requested: `r_dma_admin_pages_content`.

## Caveats

- **Member privacy**: members who have not opted in to the [Page owners exporting your data](https://www.linkedin.com/help/linkedin/answer/a1640638) setting will appear obfuscated (no `actor` / `follower` URN).
- **Analytics randomization**: very small values may be rounded to 0; identical requests can return slightly different values (privacy-preserving randomization).
- **Followers rate limit**: 1 request per 60 seconds. The script sleeps automatically; budget time for many followers.
- **Analytics quotas**: hitting the privacy budget returns 0 values with a quota refresh time in metadata.

## Troubleshooting

- `401 EMPTY_ACCESS_TOKEN` → token expired; rerun, the script will refresh. Or `--reauth`.
- `403 FORBIDDEN` → app not provisioned for `r_dma_admin_pages_content`, or you don't have an admin role on the page.
- `429 TOO_MANY_REQUESTS` → script waits per `Retry-After`; for follows this is intrinsic.
