# Safe GitHub publishing checklist

The repository is initialized but intentionally has no commit or remote. This avoids embedding a
personal Git author email or accidentally pushing to the wrong account.

1. In GitHub email settings, enable **Keep my email addresses private** and copy your GitHub-provided
   `noreply` address.
2. Configure identity for this repository only:

   ```bash
   git config user.name "YOUR_PUBLIC_GITHUB_NAME"
   git config user.email "YOUR_GITHUB_NOREPLY_ADDRESS"
   ```

3. Review staged files and confirm ignored secrets:

   ```bash
   git status
   git diff --cached --check
   git check-ignore -v --no-index .env
   ```

4. Create an empty **private** GitHub repository, with no generated README or license.
5. Commit and push:

   ```bash
   git commit -m "Initial public release"
   git remote add origin YOUR_REPOSITORY_URL
   git push -u origin main
   ```

6. In the repository security settings, enable secret scanning, push protection, and Dependabot
   alerts where available.
7. Review the private GitHub copy one final time before changing its visibility to public.

If GitHub blocks a push because it detects a secret, do not bypass the warning. Remove and rotate
the credential first, then inspect the complete Git history before retrying.
