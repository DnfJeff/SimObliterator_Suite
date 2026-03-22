# Publishing VitaMooSpace

The origin repo (`DnfJeff/SimObliterator_Suite`) does not have GitHub Pages or
GCP credentials configured. Instead, anyone with a fork can publish their own
copy — as a static site on GitHub Pages, or as a Docker container on Google
Cloud Run. Both workflows are in the repo and work on any fork. All
configuration lives in your fork's repository secrets, never in the origin.

## How It Works

1. The workflow in `.github/workflows/pages.yml` builds the SvelteKit static
   site and deploys it to GitHub Pages using the official `deploy-pages` action.
2. It sets `BASE_PATH` to `/<repo-name>` automatically so asset paths work
   under the GitHub Pages subpath (e.g. `https://you.github.io/SimObliterator_Suite/`).
3. The workflow uses `workflow_dispatch` so it only runs when you manually
   trigger it (Actions tab > "Deploy VitaMooSpace to GitHub Pages" > Run workflow).
4. No secrets from the origin repo are needed. GitHub Pages deployment uses
   the built-in `GITHUB_TOKEN` with `pages: write` and `id-token: write`
   permissions, which every fork gets automatically.

## Setup Your Fork

### 1. Fork the repo

Fork `DnfJeff/SimObliterator_Suite` to your own GitHub account.

### 2. Enable GitHub Pages

Go to your fork's **Settings > Pages**:

- **Source**: select **GitHub Actions**
- That's it. No branch or folder selection needed.

### 3. Enable Actions

If Actions are disabled on your fork (GitHub disables them by default on
forks), go to **Actions** tab and click **I understand my workflows, go
ahead and enable them**.

### 4. Trigger the deploy

Go to **Actions** > **Deploy VitaMooSpace to GitHub Pages** > **Run workflow**
(select your branch, usually `main`).

The site will be published at:

```
https://<your-username>.github.io/SimObliterator_Suite/
```

### 5. (Optional) Custom domain

To use your own domain:

1. Go to **Settings > Pages > Custom domain** and enter your domain.
2. Add a `CNAME` DNS record pointing to `<your-username>.github.io`.
3. GitHub will provision a TLS certificate automatically.
4. Override `BASE_PATH` to `/` (or empty) since you're serving from the root.

To override `BASE_PATH` for a custom domain, add a repository secret:

1. Go to **Settings > Secrets and variables > Actions > New repository secret**.
2. Name: `BASE_PATH`, Value: `` (empty string).
3. Update the workflow step (or just set `BASE_PATH` in the environment):

```yaml
      - name: Build vitamoospace
        env:
          BASE_PATH: ${{ secrets.BASE_PATH || format('/{0}', github.event.repository.name) }}
        run: pnpm --filter vitamoospace run build
```

This way the default still works for `github.io` subpath deploys, but your
fork can override it with a secret.

## Using Secrets in Your Fork

GitHub repository secrets are per-fork and never shared with the origin repo
or other forks. This means you can safely store:

- **`BASE_PATH`** — override the URL base path for custom domains
- **API keys** — for future server-side features (e.g. AI endpoints)
- **Custom config** — anything your fork's deployment needs

Secrets are set at **Settings > Secrets and variables > Actions**.

They are available in workflows as `${{ secrets.SECRET_NAME }}` and are never
exposed in logs or to other repositories.

## Keeping Your Fork in Sync

Your fork is a view-only mirror of origin that also publishes Pages. To stay
current:

```bash
# One-time: add upstream remote
git remote add upstream git@github.com:DnfJeff/SimObliterator_Suite.git

# Sync main
git checkout main
git fetch upstream
git merge upstream/main
git push origin main
```

Or use GitHub's **Sync fork** button on your fork's main page.

After syncing, trigger the Pages workflow again to publish the latest build.

## Deploying to Google Cloud Run (Docker)

The workflow `.github/workflows/deploy-cloud-run.yml` builds a Docker container
and deploys it to Cloud Run. This gives you a real server (adapter-node) with
the health endpoint and future backend capabilities.

### Prerequisites

1. A GCP project with Cloud Run and Artifact Registry APIs enabled.
2. A service account with these roles:
   - Artifact Registry Writer
   - Cloud Run Admin
   - Service Account User
3. Switch `vitamoo/vitamoospace/svelte.config.js` from `adapter-static` to
   `adapter-node` (see comments in that file).

### Fork Secrets for Cloud Run

Set these in your fork's **Settings > Secrets and variables > Actions**:

| Secret | Required | Description |
|--------|----------|-------------|
| `GCP_PROJECT_ID` | yes | Your GCP project ID |
| `GCP_SA_KEY` | yes | Service account JSON key (full contents) |
| `GCP_REGION` | no | Default region (default: `us-central1`) |
| `BASE_PATH` | no | URL base path (empty for root domain) |

These secrets are per-fork. The origin repo never sees them.

### Trigger the deploy

Go to **Actions** > **Build & Deploy to Cloud Run** > **Run workflow**.

You can override the region and service name in the workflow inputs dialog.

The workflow will:

1. Authenticate to GCP using your service account key.
2. Build the Docker image from the repo root using
   `vitamoo/vitamoospace/Dockerfile`.
3. Push to Artifact Registry (`<region>-docker.pkg.dev/<project>/vitamoospace/`).
4. Deploy to Cloud Run with sensible defaults (256Mi, 0-3 instances, port 3000).
5. Print the live service URL.

### Health check

Once deployed, the health endpoint is live at:

```
https://<your-cloud-run-url>/api/health
```

Returns:

```json
{"status": "ok", "service": "vitamoospace", "version": "0.1.0", "timestamp": "..."}
```

### Local Docker testing

```bash
# From repo root (adapter-node must be active in svelte.config.js)
docker build -f vitamoo/vitamoospace/Dockerfile -t vitamoospace .
docker run -p 3000:3000 vitamoospace
# Visit http://localhost:3000
# Health: http://localhost:3000/api/health
```

## Security Model

All deployment credentials live in your fork's repository secrets:

| What | Where | Who can see it |
|------|-------|----------------|
| GitHub Pages token | Built-in `GITHUB_TOKEN` | Automatic, no setup needed |
| `GCP_SA_KEY` | Your fork's secrets | Only your fork's admins |
| `GCP_PROJECT_ID` | Your fork's secrets | Only your fork's admins |
| `BASE_PATH` | Your fork's secrets | Only your fork's admins |
| API keys (future) | Your fork's secrets | Only your fork's admins |

The origin repo has no access to any fork's secrets. Forks cannot see each
other's secrets. GitHub never exposes secret values in logs.

This means the origin repo stays clean (no credentials, no deployment config)
while every fork independently controls where and how it deploys.

## Publishing on a Production Domain

When the site is ready for a production domain (e.g. `simobliterator.com`):

**Static (GitHub Pages)**:
1. Set custom domain in fork settings.
2. Add `BASE_PATH` secret with empty value.
3. Optionally add a push trigger to auto-deploy.

**Server (Cloud Run)**:
1. Map your custom domain in Cloud Run settings.
2. Switch to `adapter-node` in `svelte.config.js`.
3. Deploy via the Cloud Run workflow.

Either path works from any fork. Pick whichever fits.

## Deploying Other Branches

To deploy a feature branch to Pages (e.g. for previewing):

1. Go to **Actions** > **Deploy VitaMooSpace to GitHub Pages** > **Run workflow**.
2. Select your branch from the dropdown.
3. The site will be built from that branch and deployed to the same Pages URL.

Only one branch can be live on Pages at a time (the last deployed one wins).
For parallel previews, use separate forks or a PR preview service.

For Cloud Run, each deploy overwrites the service. To run multiple versions,
use different service names in the workflow input dialog.
