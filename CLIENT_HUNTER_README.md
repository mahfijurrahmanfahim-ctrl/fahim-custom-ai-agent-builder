# FAHIM Client Hunter

A daily GitHub Actions workflow that discovers candidate businesses for Fahim Graphic Design.

## What it does

- Runs daily and can also be started manually from the Actions tab.
- Searches Portugal first and checks UK only if Portugal returns fewer than the target.
- Targets independent restaurants, cafés, bakeries, salons, gyms and boutiques.
- Fetches candidate public websites and checks their page content before including them.
- Extracts email addresses and phone numbers only when published on the checked page.
- Produces Markdown, CSV and JSON reports as a downloadable GitHub Actions artifact.
- Does not send messages, create accounts, buy anything or contact businesses.

## Start it manually

1. Open the repository on GitHub.
2. Select Actions.
3. Select Daily Client Discovery.
4. Press Run workflow.
5. Open the completed run and read its summary or download the artifact named fahim-client-prospects-*.

## Schedule

Daily at 08:30 UTC (09:30 in Portugal during winter and 10:30 during summer). GitHub Actions cron uses UTC.

## Limitations

- Search results and page checks do not prove a business wants design services.
- Suggested opportunities are sales angles, not claims that the business has a design problem.
- Search engines may rate-limit requests; fewer than eight results is possible.
- Contact information is included only when found on the checked public website.
- No Apollo credits or paid API keys are required.
- Artifacts are retained for 30 days and visible to people with repository access.

Portfolio: https://mahfijurrahmanfahim-ctrl.github.io/fahim-graphic-design-portfolio/
