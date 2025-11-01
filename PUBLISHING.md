# Publishing to PyPI

This guide explains how to publish the `graphiti-memory` package to PyPI.

## Prerequisites

1. **PyPI Account**: Create an account at https://pypi.org
2. **API Token**: Generate an API token from https://pypi.org/manage/account/token/
3. **Build Tools**: Install build dependencies

```bash
pip install build twine
```

## First-Time Setup

### 1. Configure PyPI Credentials

Create or edit `~/.pypirc`:

```ini
[distutils]
index-servers =
    pypi

[pypi]
username = __token__
password = pypi-YOUR-API-TOKEN-HERE
```

Or use environment variable:
```bash
export TWINE_PASSWORD=pypi-YOUR-API-TOKEN-HERE
```

### 2. Verify Package Name

Check if `graphiti-memory` is available on PyPI:
```bash
pip search graphiti-memory  # or check https://pypi.org/project/graphiti-memory/
```

## Publishing Steps

### 1. Update Version

Edit `pyproject.toml` and update the version:
```toml
version = "0.1.0"  # Update this
```

Also update `graphiti_memory/__init__.py`:
```python
__version__ = "0.1.0"  # Keep in sync
```

### 2. Clean Previous Builds

```bash
rm -rf build/ dist/ *.egg-info
```

### 3. Build the Package

```bash
python -m build
```

This creates:
- `dist/graphiti_memory-0.1.0-py3-none-any.whl`
- `dist/graphiti-memory-0.1.0.tar.gz`

### 4. Test the Build Locally

```bash
# Install in a virtual environment
python -m venv test_env
source test_env/bin/activate
pip install dist/graphiti_memory-0.1.0-py3-none-any.whl

# Test the CLI
graphiti-mcp-server --help || echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}' | graphiti-mcp-server
```

### 5. Upload to Test PyPI (Optional but Recommended)

```bash
# Upload to TestPyPI first
python -m twine upload --repository testpypi dist/*

# Test installation
pip install --index-url https://test.pypi.org/simple/ graphiti-memory
```

### 6. Upload to PyPI

```bash
python -m twine upload dist/*
```

Enter your API token when prompted (or use configured credentials).

### 7. Verify Published Package

```bash
pip install graphiti-memory
graphiti-mcp-server --help || echo "Server installed successfully"
```

## Subsequent Releases

For version updates (e.g., 0.1.0 → 0.1.1):

1. Update version in `pyproject.toml` and `__init__.py`
2. Update `README.md` with changelog/new features
3. Commit changes
4. Create git tag:
   ```bash
   git tag -a v0.1.1 -m "Release v0.1.1"
   git push origin v0.1.1
   ```
5. Clean, build, and upload:
   ```bash
   rm -rf build/ dist/ *.egg-info
   python -m build
   python -m twine upload dist/*
   ```

## Troubleshooting

### "The user 'alankyshum' isn't allowed to upload"

Use API token instead of username/password:
```bash
export TWINE_USERNAME=__token__
export TWINE_PASSWORD=pypi-YOUR-API-TOKEN
```

### "File already exists"

You cannot re-upload the same version. Increment version number.

### Build Errors

```bash
# Upgrade build tools
pip install --upgrade build twine setuptools wheel
```

### Import Errors After Install

Check that package structure is correct:
```bash
python -c "import graphiti_memory; print(graphiti_memory.__version__)"
```

## Best Practices

1. **Version Numbering**: Follow [Semantic Versioning](https://semver.org/)
   - MAJOR.MINOR.PATCH (e.g., 1.0.0)
   - Bug fixes: increment PATCH (0.1.0 → 0.1.1)
   - New features: increment MINOR (0.1.0 → 0.2.0)
   - Breaking changes: increment MAJOR (0.1.0 → 1.0.0)

2. **Git Tags**: Tag releases in git
   ```bash
   git tag -a v0.1.0 -m "Initial release"
   git push origin v0.1.0
   ```

3. **Changelog**: Maintain a CHANGELOG.md file

4. **Testing**: Always test in a clean environment before publishing

5. **Documentation**: Keep README.md up to date

## Automation (Optional)

Create a GitHub Action for automated releases:

```yaml
# .github/workflows/publish.yml
name: Publish to PyPI

on:
  release:
    types: [created]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v2
    - uses: actions/setup-python@v2
      with:
        python-version: '3.x'
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install build twine
    - name: Build and publish
      env:
        TWINE_USERNAME: __token__
        TWINE_PASSWORD: ${{ secrets.PYPI_API_TOKEN }}
      run: |
        python -m build
        twine upload dist/*
```

## Links

- **PyPI**: https://pypi.org/project/graphiti-memory/
- **TestPyPI**: https://test.pypi.org/project/graphiti-memory/
- **Packaging Guide**: https://packaging.python.org/
- **Twine**: https://twine.readthedocs.io/
