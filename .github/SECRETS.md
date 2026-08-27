# Required GitHub Secrets

## `WEBSCRAPER_READ_TOKEN`

A fine-grained Personal Access Token (PAT) with **read-only** access to the
`nhs-webscraper` repository.

### How to create it

1. Go to **GitHub → Settings → Developer settings → Personal access tokens →
   Fine-grained tokens** and click **Generate new token**.
2. Set a token name, e.g. `nhs-webscraper-ci-read`.
3. Under **Resource owner**, select your account (`Hydaspex`).
4. Under **Repository access**, choose **Only select repositories** and pick
   `nhs-webscraper`.
5. Under **Permissions → Repository permissions**, set **Contents** to
   **Read-only**.  No other permissions are needed.
6. Click **Generate token** and copy it immediately.
7. In the `nhs-intelligence-mcp` repository, go to **Settings → Secrets and
   variables → Actions → New repository secret**.
8. Name it `WEBSCRAPER_READ_TOKEN` and paste the token value.

The token only ever lets the CI job read the `nhs-webscraper` source code; it
cannot write to either repository.

---

## `GITHUB_TOKEN`

This secret is **built-in** — GitHub Actions injects it automatically for
every workflow run.  No setup is required.

The `publish_db.yml` workflow uses it to create releases and upload assets on
`nhs-intelligence-mcp`.  The `permissions: contents: write` key in the
workflow file grants the necessary scope.
