# Branch Naming Convention

This document defines the branch naming conventions for the DataGod project.

## Branch Types

### 1. Feature Branches
**Prefix:** `feature/`
**Purpose:** Development of new features
**Examples:**
- `feature/user-authentication`
- `feature/advanced-search`
- `feature/data-export`

### 2. Bugfix Branches
**Prefix:** `bugfix/`
**Purpose:** Fixing bugs and issues
**Examples:**
- `bugfix/login-error`
- `bugfix/search-crash`
- `bugfix/data-import-issue`

### 3. Hotfix Branches
**Prefix:** `hotfix/`
**Purpose:** Critical production fixes that need immediate attention
**Examples:**
- `hotfix/security-vulnerability`
- `hotfix/database-connection`
- `hotfix/api-outage`

### 4. Release Branches
**Prefix:** `release/`
**Purpose:** Preparation for production releases
**Examples:**
- `release/v1.0.0`
- `release/v2.1.0`
- `release/hotfix-patch`

## Branch Naming Rules

1. **Use lowercase letters only**
2. **Use hyphens (-) to separate words**
3. **Keep branch names descriptive but concise**
4. **Include issue numbers when applicable** (e.g., `feature/issue-123-user-profile`)
5. **Avoid special characters** (except hyphens)
6. **Maximum length: 50 characters**

## Workflow

1. **Create branch from appropriate base:**
   - Feature branches: branch from `development`
   - Bugfix branches: branch from `development`
   - Hotfix branches: branch from `master`
   - Release branches: branch from `development`

2. **Push branch to remote:**
   ```bash
   git push -u origin your-branch-name
   ```

3. **Create Pull Request:**
   - Target branch: `development` (for features/bugfixes)
   - Target branch: `master` (for hotfixes/releases)

4. **Merge and cleanup:**
   - After PR is merged, delete the branch
   - Update local branches: `git fetch --prune`

## Examples

```bash
# Create a new feature branch
git checkout -b feature/user-dashboard
git push -u origin feature/user-dashboard

# Create a bugfix branch
git checkout -b bugfix/search-error
git push -u origin bugfix/search-error

# Create a hotfix branch
git checkout -b hotfix/security-patch
git push -u origin hotfix/security-patch
```

## Branch Protection

- `master` branch: Protected, requires PR reviews
- `development` branch: Protected, requires PR reviews
- Feature/bugfix branches: No protection, can be force-pushed

## Version Tags

For releases, use semantic versioning tags:
```bash
git tag -a v1.0.0 -m "Release version 1.0.0"
git push origin v1.0.0