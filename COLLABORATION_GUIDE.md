# ML Model Project — GitHub Collaboration Guide

Repository:  
[https://github.com/Atharva-cell-web/ml-model-v3](https://github.com/Atharva-cell-web/ml-model-v3)

## 0. First, accept the collaboration invite
Open GitHub notifications/email and accept the invite to `Atharva-cell-web/ml-model-v3`.

## 1. Install tools
- Git: https://git-scm.com/downloads
- (Optional) VS Code: https://code.visualstudio.com

## 2. Clone repo (first time only)
```bash
git clone https://github.com/Atharva-cell-web/ml-model-v3.git
cd ml-model-v3
```

## 3. Get latest changes before starting work
```bash
git checkout main
git pull origin main
```

## 4. Create your feature branch (don’t work on main)
```bash
git checkout -b vishnu-feature
```

## 5. Make code changes
Edit files normally.

## 6. Commit your changes
```bash
git status
git add .
git commit -m "Describe what you changed"
```

## 7. Push your branch
```bash
git push origin vishnu-feature
```

## 8. Open Pull Request
On GitHub, click **Compare & pull request** and submit PR to `main`.

## 9. Sync your branch with latest main
```bash
git checkout main
git pull origin main
git checkout vishnu-feature
git merge main
```

## 10. Useful commands
- History: `git log --oneline --graph --decorate --all`
- File changes: `git diff`
- Restore one file: `git restore <filename>`
- Switch branch: `git checkout main` / `git checkout vishnu-feature`
- Delete merged branch: `git branch -d vishnu-feature`

## 11. Safer recovery rules
- If not committed yet and you want to discard local changes:
```bash
git restore <filename>
```
- If you need to undo a bad commit already pushed, use `git revert` (safe for team history).
- Avoid `git reset --hard` unless absolutely sure, because it permanently deletes uncommitted work.

## 12. Daily workflow (short version)
1. `git checkout main && git pull origin main`
2. `git checkout -b feature-name`
3. Edit code
4. `git add . && git commit -m "Meaningful message"`
5. `git push origin feature-name`
6. Open PR

## 13. Team rules
- Pull latest before starting.
- Never push directly to `main`.
- Use one branch per feature/fix.
- Use clear commit messages.
