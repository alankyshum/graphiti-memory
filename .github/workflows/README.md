# GitHub Actions Workflows

## Publish to PyPI

The `publish.yml` workflow automatically publishes the package to PyPI when you create a new GitHub release.

### Setup Instructions

1. **Create a PyPI API Token**
   - Go to https://pypi.org/manage/account/token/
   - Create a new API token with upload permissions
   - Copy the token (it starts with `pypi-`)

2. **Add Token to GitHub Secrets**
   - Go to your repository: https://github.com/alankyshum/graphiti-memory
   - Navigate to Settings → Secrets and variables → Actions
   - Click "New repository secret"
   - Name: `PYPI_API_TOKEN`
   - Value: Paste your PyPI token
   - Click "Add secret"

3. **Create a Release to Trigger Publishing**
   ```bash
   # Update version in pyproject.toml and __init__.py
   # Commit and push changes
   git add pyproject.toml graphiti_memory/__init__.py
   git commit -m "Bump version to 0.1.2"
   git push origin main
   
   # Create and push a tag
   git tag -a v0.1.2 -m "Release v0.1.2"
   git push origin v0.1.2
   ```

4. **Create GitHub Release**
   - Go to: https://github.com/alankyshum/graphiti-memory/releases/new
   - Choose the tag you just created: `v0.1.2`
   - Title: `v0.1.2`
   - Description: Add release notes (what's new, bug fixes, etc.)
   - Click "Publish release"

5. **Automatic Publishing**
   - The workflow will automatically trigger
   - Monitor progress at: https://github.com/alankyshum/graphiti-memory/actions
   - If successful, the package will be available at: https://pypi.org/project/graphiti-memory/

## Manual Publishing (Alternative)

If you prefer to publish manually or the workflow fails:

```bash
# Build the package
python -m build

# Upload to PyPI
python -m twine upload dist/*
```

See [PUBLISHING.md](../../PUBLISHING.md) for detailed manual publishing instructions.

## Troubleshooting

### Workflow fails with "Invalid or non-existent authentication"
- Verify the `PYPI_API_TOKEN` secret is set correctly in GitHub
- Make sure the token hasn't expired
- Token must start with `pypi-`

### Workflow fails with "File already exists"
- The version already exists on PyPI
- Update the version in `pyproject.toml` and `__init__.py`
- Create a new tag and release

### Workflow doesn't trigger
- Make sure you created a "Release", not just a tag
- The release type must be "created" (not draft or pre-release)

