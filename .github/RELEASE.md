# PyPI Release Process

This repository is configured to automatically publish to PyPI when version tags are pushed.

## Setup Required

### 1. Configure PyPI Trusted Publisher (Recommended)

This is the modern, secure method that doesn't require managing API tokens.

1. Go to [PyPI](https://pypi.org) and create an account if needed
2. Create the project `mpy-devices` on PyPI (one-time manual upload or reserve the name)
3. Go to your project's settings: https://pypi.org/manage/project/mpy-devices/settings/
4. Navigate to "Publishing" → "Add a new publisher"
5. Configure the trusted publisher:
   - **PyPI Project Name**: `mpy-devices`
   - **Owner**: `andrewleech` (GitHub organization/username)
   - **Repository name**: `mpy-devices`
   - **Workflow name**: `publish.yml`
   - **Environment name**: `pypi`

### 2. Alternative: API Token Method

If you prefer using API tokens instead:

1. Generate a PyPI API token at https://pypi.org/manage/account/token/
2. Add it as a repository secret:
   - Go to GitHub repository settings → Secrets and variables → Actions
   - Add new secret named `PYPI_API_TOKEN`
3. Modify the workflow to use the token:
   ```yaml
   - name: Publish distribution to PyPI
     uses: pypa/gh-action-pypi-publish@release/v1
     with:
       password: ${{ secrets.PYPI_API_TOKEN }}
   ```

## Release Process

### 1. Update Version

Edit `pyproject.toml` and update the version number:

```toml
[project]
version = "0.2.0"  # Update this
```

Consider using dynamic versioning tools like `hatch-vcs` or `setuptools-scm` for automatic versioning from git tags.

### 2. Commit Changes

```bash
git add pyproject.toml
git commit -m "Bump version to 0.2.0"
git push
```

### 3. Create and Push Tag

```bash
git tag v0.2.0
git push origin v0.2.0
```

The GitHub Action will automatically:
- Build the package (wheel and sdist)
- Publish to PyPI
- Create a GitHub Release
- Sign artifacts with Sigstore

### 4. Verify

- Check the Actions tab for workflow status
- Visit https://pypi.org/project/mpy-devices/ to verify the new version
- Check the GitHub Releases page

## Dynamic Versioning (Optional Enhancement)

To avoid manually updating version numbers, consider using `hatchling`'s VCS versioning:

```toml
[build-system]
requires = ["hatchling", "hatch-vcs"]
build-backend = "hatchling.build"

[tool.hatch.version]
source = "vcs"

[project]
dynamic = ["version"]  # Remove hardcoded version
```

This will automatically derive the version from git tags.

## Troubleshooting

### Build Fails

- Ensure `pyproject.toml` is valid
- Check that all source files are included in the package
- Test locally: `python -m build`

### Publishing Fails

- Verify trusted publisher configuration matches exactly
- Check that the tag follows the `v*` pattern (e.g., `v0.1.0`, not `0.1.0`)
- Ensure PyPI project name matches exactly

### GitHub Release Fails

- Check repository permissions in Settings → Actions → General
- Ensure "Allow GitHub Actions to create and approve pull requests" is enabled
- Verify workflow has `contents: write` permission

## Testing Releases

To test without publishing to PyPI:

1. Use TestPyPI first by modifying the workflow:
   ```yaml
   - name: Publish to TestPyPI
     uses: pypa/gh-action-pypi-publish@release/v1
     with:
       repository-url: https://test.pypi.org/legacy/
   ```

2. Set up TestPyPI trusted publisher at https://test.pypi.org

3. Test installation:
   ```bash
   pip install --index-url https://test.pypi.org/simple/ mpy-devices
   ```
