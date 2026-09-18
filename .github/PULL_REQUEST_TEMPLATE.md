## Description

<!-- Briefly describe the changes introduced by this pull request and the rationale behind them. -->

## Type of Change

- [ ] 🐛 Bug fix (non-breaking change fixing an issue)
- [ ] ✨ New feature (non-breaking change adding functionality)
- [ ] 🔬 Reverse-engineering / Protocol discovery (new Lorax paths, GATT endpoints)
- [ ] ⚡ Performance improvement / Refactor
- [ ] 📝 Documentation update or example script
- [ ] 🧪 Test suite improvement
- [ ] 💥 Breaking change (fix or feature causing existing functionality to not work as expected)

## Related Issues

<!-- If applicable, link to related issues: e.g. Fixes #123 -->

## Quality Checklist

- [ ] I have read the [Contributing Guide](CONTRIBUTING.md) and [Code of Conduct](CODE_OF_CONDUCT.md).
- [ ] My code follows the repository style guidelines (`ruff format --check .`).
- [ ] Linter passes with no errors (`ruff check .`).
- [ ] Static type-checker passes (`mypy puffco_py/`).
- [ ] All unit tests pass locally (`pytest tests/ -v`).
- [ ] If I added new Lorax endpoints, I updated `puffco_py/constants.py` and `MockLoraxBLEDevice` in `puffco_py/mock.py`.
- [ ] Any public method or class added has clear docstrings and typing annotations.
