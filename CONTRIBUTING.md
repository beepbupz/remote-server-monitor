# Contributing to Remote Server Monitor

Thank you for your interest in contributing to Remote Server Monitor! This document provides guidelines for contributing to the project.

## 🚀 Getting Started

### Prerequisites
- Python 3.9 or higher
- Git
- SSH access to test servers (for testing)

### Setting up Development Environment

1. **Fork the repository** on GitHub
2. **Clone your fork**:
   ```bash
   git clone https://github.com/yourusername/remote-server-monitor.git
   cd remote-server-monitor
   ```
3. **Create a virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
4. **Install in development mode**:
   ```bash
   pip install -e ".[dev]"
   ```

## 🎯 How to Contribute

### Reporting Bugs
- Use GitHub Issues to report bugs
- Include detailed steps to reproduce
- Provide system information (OS, Python version)
- Include relevant log output

### Suggesting Features
- Check existing issues first
- Create a GitHub Issue with the "enhancement" label
- Describe the use case and expected behavior
- Consider if it fits the project's scope

### Code Contributions

1. **Find an issue** to work on or create one
2. **Create a feature branch**:
   ```bash
   git checkout -b feature/your-feature-name
   ```
3. **Make your changes** following the coding standards
4. **Add tests** for new functionality
5. **Run the test suite**:
   ```bash
   pytest
   black --check rsm/
   ruff check rsm/
   mypy rsm/
   ```
6. **Commit your changes**:
   ```bash
   git commit -m "feat: add your feature description"
   ```
7. **Push to your fork**:
   ```bash
   git push origin feature/your-feature-name
   ```
8. **Create a Pull Request** on GitHub

## 📋 Development Guidelines

### Code Style
- Follow PEP 8 style guidelines
- Use Black for code formatting: `black rsm/`
- Use Ruff for linting: `ruff check rsm/`
- Use type hints and run mypy: `mypy rsm/`

### Commit Messages
Follow [Conventional Commits](https://www.conventionalcommits.org/):
- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation changes
- `style:` Code style changes (no logic changes)
- `refactor:` Code refactoring
- `test:` Adding or updating tests
- `chore:` Build/tool changes

Examples:
- `feat: add MySQL collector for database monitoring`
- `fix: handle SSH timeout errors gracefully`
- `docs: update installation instructions`

### Testing
- Write tests for new features
- Ensure existing tests pass
- Aim for good test coverage
- Use pytest for testing framework

### Documentation
- Update README.md if needed
- Add docstrings to new functions/classes
- Update CHANGELOG.md for significant changes
- Keep inline comments minimal but clear

## 🏗️ Project Structure

```
rsm/
├── core/              # Core functionality
├── collectors/        # Metric collectors
├── ui/               # Terminal interface
└── utils/            # Utility functions
```

### Adding New Collectors
1. Create a new file in `rsm/collectors/`
2. Inherit from `MetricCollector` base class
3. Implement the `collect()` method
4. Add appropriate parsing for different platforms
5. Register the collector in the main application
6. Add configuration options
7. Write tests

### Adding New UI Components
1. Create widgets in `rsm/ui/widgets/`
2. Follow existing widget patterns
3. Use Rich for rendering
4. Ensure responsive design
5. Add keyboard shortcuts if needed

## 🔍 Code Review Process

### Pull Request Requirements
- [ ] Passes all tests
- [ ] Follows code style guidelines
- [ ] Includes appropriate tests
- [ ] Updates documentation if needed
- [ ] Has clear commit messages
- [ ] Addresses a specific issue

### Review Criteria
- Code quality and maintainability
- Performance implications
- Security considerations
- Compatibility with supported platforms
- User experience impact

## 🚫 What We Don't Accept

- Breaking changes without discussion
- Code that doesn't follow style guidelines
- Features that significantly increase complexity
- Contributions without tests
- Commercial features (due to Commons Clause)

## 📚 Resources

- [Project README](README.md)
- [Development Guide](DEVELOPMENT.md)
- [TODO List](TODO.md)
- [Textual Documentation](https://textual.textualize.io/)
- [asyncssh Documentation](https://asyncssh.readthedocs.io/)

## 🤝 Community

- Be respectful and inclusive
- Help others learn and grow
- Focus on constructive feedback
- Follow the [Code of Conduct](CODE_OF_CONDUCT.md)

## ❓ Getting Help

- Create a GitHub Issue for bugs
- Use GitHub Discussions for questions
- Check existing documentation first
- Provide context when asking for help

## 📄 License

By contributing, you agree that your contributions will be licensed under the same license as the project (Apache 2.0 with Commons Clause).

Thank you for contributing! 🎉