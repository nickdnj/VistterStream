# Codex + Raspberry Pi Deployment Workflow

This guide describes how to collaborate with Codex (or other AI-assisted
workspaces) while keeping the Raspberry Pi in sync using the auto-deploy helper.

## 1. Develop inside Codex

1. **Launch the workspace** – Open the repository in the Codex web IDE.
2. **Choose your branch** – Create or check out the feature branch you want the
   Raspberry Pi to test (e.g., `feature/youtube-oauth`).
3. **Code & test** – Implement changes, run unit tests or linters inside the
   Codex terminal, and review the diff.
4. **Commit locally** – Use the built-in Git tooling (or the terminal) to commit
   your work. Commit early so you always have a recoverable checkpoint.
5. **Push to GitHub** – `git push origin <branch>` so the Raspberry Pi can fetch
   the exact commits you want it to deploy.

> Codex workspaces are disposable. Push every change you care about before you
> close the session so the Pi—and other collaborators—can pull the branch.

## 2. Describe the deployment plan

1. Edit `deploy/auto-deploy.conf` on the control branch (defaults to
   `origin/main`).
2. Set host-specific directives so each environment follows the right branch.
   Example:

   ```
   branch[raspi]=feature/youtube-oauth
   branch[codex]=work
   ```

3. Commit the instruction changes. Every helper reads the same file before it
   checks out the target branch.

### Optional: alternate control branch

If you do not want to modify `main`, create a lightweight coordination branch
(e.g., `deploy/codex`) and push the instruction file there. On the Raspberry Pi
run:

```bash
AUTO_DEPLOY_CONTROL_BRANCH=deploy/codex ./scripts/raspi_auto_deploy.sh
```

The helper reads directives from that branch while still pulling code from the
branch specified in the instruction file.

## 3. Update the Raspberry Pi

1. **Connect to the Pi** – SSH into the device and change directories into the
   repository (`cd ~/VistterStream`).
2. **Run the helper** – Execute `./scripts/raspi_auto_deploy.sh`.
3. **Let the helper sync** – It will:
   - Fetch the latest commits and instruction file from GitHub.
   - Switch to the branch specified for the Pi (for example,
     `feature/youtube-oauth`).
   - Run `deploy.sh` (or the alternative command you specified) to rebuild and
     restart the Docker services.
4. **Confirm the stack** – After the script exits, check service health:

   ```bash
   docker compose -f docker/docker-compose.rpi.yml ps
   ```

   Optionally follow up with the health endpoints listed in
   `RASPBERRY_PI_SETUP.md`.

## 4. Iterate and merge

- Continue pushing updates from Codex (or other agents) as needed.
- Adjust `deploy/auto-deploy.conf` whenever you want the Pi to track a different
  branch.
- Once the feature is validated, merge it into `main` through a pull request.
  Update the instruction file to point the Pi back to `main` (e.g.,
  `branch[raspi]=main`).

## 5. End-to-end example checklist

1. Push your Codex branch to GitHub.
2. Edit `deploy/auto-deploy.conf` so `branch[raspi]` points at that branch.
3. Commit and push the instruction update (same branch or control branch).
4. SSH into the Raspberry Pi and run `./scripts/raspi_auto_deploy.sh`.
5. Validate services with `docker compose -f docker/docker-compose.rpi.yml ps`
   and the API/Frontend health checks.
6. Iterate or merge once testing is complete.

This workflow makes it easy to incorporate contributions from many agents: each
one pushes their branch, updates the coordination file, and the Raspberry Pi
fetches and deploys the correct code automatically.
