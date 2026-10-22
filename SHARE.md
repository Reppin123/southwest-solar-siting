# How to share this project

There are three things to share. Most people only need the first one.

| What | Link | Who can open it |
|---|---|---|
| **Live dashboards** | https://southwest-solar-siting.akshitbansal1313.workers.dev/ | Anyone with the link (the site is public today) |
| **GitHub repo** (code, all CSVs, processed data, deliverables) | https://github.com/Reppin123/southwest-solar-siting | Only people you invite (the repo is private) |
| **Large data files** (release v1.0-data) | https://github.com/Reppin123/southwest-solar-siting/releases/tag/v1.0-data | Same as the repo: invited people only |

## Recommended way

1. Send the live site link. It needs no account and no install, and it works on a phone. Start with Dashboard v2 and its "How to Read This" tab.
2. If the person wants the files (CSVs, Excel, maps, code), invite them to the private repo (see below). Then send the repo link.
3. They can download the Excel ranking, site memos and BLM brief from the site itself, from the landing page or the Deliverables tab. That works without GitHub.

## Invite someone to the private repo

You need their GitHub username or the email address on their GitHub account. They also need a GitHub account (free).

**On the website:** open https://github.com/Reppin123/southwest-solar-siting/settings/access, click **Add people**, and type their username or email. They get an email invite and must accept it. The invite expires after 7 days.

**From the terminal** (username only):

```
gh api -X PUT repos/Reppin123/southwest-solar-siting/collaborators/THEIR_USERNAME -f permission=pull
```

`permission=pull` gives read-only access. Use `push` if they should be able to make changes.

To remove someone later: the same settings page, then **Remove**.

If you would rather not use GitHub invites, you can make the repo public (Settings > General > Danger Zone > Change visibility). Before you do, choose a licence (see `LICENSES.md`). Note that OpenStreetMap-derived data must then follow ODbL terms (see `DATA.md`).

## What the other person does

**Look only:** open the live link.

**Get everything:**

```
git clone https://github.com/Reppin123/southwest-solar-siting.git
cd southwest-solar-siting
uv run --script app/serve.py          # opens the dashboards locally
```

The clone is about 130 MB to download, about 420 MB on disk. It already includes every CSV (`data/processed/**/*.csv`, `deliverables/Southwest_Solar_Sites.xlsx`) and the dashboard data. Without git, they can use **Code > Download ZIP** on the repo page instead.

**Large processed files** (only needed to rerun the site screening): download them from the release page, or run `gh release download v1.0-data -R Reppin123/southwest-solar-siting`. Then unpack them as shown in `DATA.md`, which also lists the checksums.

**Raw data** (about 11 GB, not stored anywhere): run `uv run --script pipeline/run_all.py` in the repo. It downloads every public source again and rebuilds everything. See README.md, "Rerun the pipeline".

## Make the live site private (optional)

Today anyone with the link can open the site. To limit it to named email addresses, use Cloudflare Access (free for up to 50 users). The steps are in `deploy-site/LIVE.md`, under "Making it private". If you do this, the WhatsApp recipient will need to enter a one-time code sent to their email.

## WhatsApp message (copy and paste)

```
Hi! Sharing my Southwest solar siting project. It screens about 25,700 possible sites for large solar farms (100 MW to 1 GW), and for data centers next to them, across CA, AZ, NV, NM and UT. It uses public grid, BLM land, sun and environmental data.

Live dashboards (opens in any browser, no login):
https://southwest-solar-siting.akshitbansal1313.workers.dev/

Start with Dashboard v2 and the "How to Read This" tab. The Excel ranking, top 15 site memos and BLM application brief are under Deliverables.

Full project with all the code and CSV files:
https://github.com/Reppin123/southwest-solar-siting

The GitHub repo is private, so send me your GitHub username or email and I will invite you. The big data files are on the repo's Releases page (v1.0-data).

Note: this is a screening study from public data, not an engineering study. Grid capacity still needs to be confirmed with the utility.
```
