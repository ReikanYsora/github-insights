# GitHub Insights for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)
[![Validate](https://github.com/ReikanYsora/github-insights/actions/workflows/validate.yml/badge.svg)](https://github.com/ReikanYsora/github-insights/actions/workflows/validate.yml)
[![Tests](https://github.com/ReikanYsora/github-insights/actions/workflows/test.yml/badge.svg)](https://github.com/ReikanYsora/github-insights/actions/workflows/test.yml)

A Home Assistant custom integration that exposes rich activity metrics for any
public GitHub repository — commits, releases, download counts, stars, followers
and issues — using a personal access token to benefit from the full API rate
limit.

> **How is this different from the built-in `github` integration?**
> Home Assistant core already ships a `github` integration (stars, forks,
> issues, latest release, latest commit…). GitHub Insights focuses on the
> metrics core does **not** provide: **total commit count, number of releases,
> release download counts (latest and total), followers, and open/closed issue
> counts**.

## Entities

Each configured repository is exposed as a device with the following sensors:

| Sensor | Description | State class |
| --- | --- | --- |
| Commits | Total number of commits on the default branch | `total_increasing` |
| Releases | Number of published releases | `measurement` |
| Latest release | Tag of the latest published release (name & URL as attributes) | – |
| Latest release downloads | Downloads of the latest release assets | `total_increasing` |
| Total downloads | Downloads across every release asset | `total_increasing` |
| Stars | Number of stargazers | `measurement` |
| Followers | Followers of the repository owner | `measurement` |
| Open issues | Open issues, excluding pull requests | `measurement` |
| Closed issues | Closed issues, excluding pull requests | `total_increasing` |

## Installation

### HACS (recommended)

1. In HACS, open the three-dot menu → **Custom repositories**.
2. Add `https://github.com/ReikanYsora/github-insights` with category
   **Integration**.
3. Install **GitHub Insights** and restart Home Assistant.

### Manual

Copy `custom_components/github_insights` into your Home Assistant
`config/custom_components` directory and restart Home Assistant.

## Configuration

1. Go to **Settings → Devices & Services → Add Integration**.
2. Search for **GitHub Insights**.
3. Provide:
   - a **GitHub personal access token** — a fine-grained token with public read
     access, or a classic token (no scope required for public repositories),
     is enough to raise the rate limit to 5000 requests/hour;
   - the **repository** to track, in `owner/name` format
     (e.g. `home-assistant/core`).

Add the integration again for each additional repository you want to track.

Data is refreshed every 15 minutes.

## Notes

- Only public repositories are supported out of the box; a token with `repo`
  scope is required for private repositories.
- Issue counts use the GitHub Search API and exclude pull requests, unlike the
  raw `open_issues_count` field.

## License

Released under the [MIT License](LICENSE). Data is provided by the GitHub API.
