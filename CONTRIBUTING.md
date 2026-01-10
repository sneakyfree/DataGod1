# Contributing to DataGod

Thank you for your interest in contributing to DataGod! We welcome contributions from everyone.

## Code of Conduct

By participating in this project, you agree to abide by our [Code of Conduct](CODE_OF_CONDUCT.md).

## How Can I Contribute?

### Reporting Bugs

- **Search existing issues** before creating a new one
- **Use the bug report template** when creating issues
- **Provide detailed information**:
  - Steps to reproduce
  - Expected behavior
  - Actual behavior
  - Screenshots if applicable
  - Environment details (OS, Python version, etc.)

### Suggesting Enhancements

- **Search existing feature requests** before suggesting a new one
- **Use the feature request template**
- **Provide detailed information**:
  - Use case
  - Proposed solution
  - Alternatives considered
  - Benefits

### Pull Requests

1. **Fork the repository** and create your branch from `development`
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Follow our coding standards**:
   - Use consistent indentation (4 spaces)
   - Follow PEP 8 style guide for Python
   - Use descriptive variable and function names
   - Add docstrings to all functions and classes
   - Write comprehensive unit tests

3. **Make your changes** and ensure:
   - All tests pass
   - Code is properly formatted
   - Documentation is updated
   - No breaking changes are introduced

4. **Commit your changes** with clear, descriptive messages:
   ```bash
   git commit -m "Add feature: brief description of changes"
   ```

5. **Push to your fork** and submit a pull request to the `development` branch

## Development Setup

### Prerequisites
- Python 3.9+
- PostgreSQL 13+
- Node.js 16+ (for frontend)
- Git

### Installation
```bash
# Clone the repository
git clone https://github.com/yourusername/datagod.git
cd datagod

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
cd frontend && npm install && cd ..

# Set up database
createdb datagod
alembic upgrade head
```

## Coding Standards

### Python
- Follow [PEP 8](https://www.python.org/dev/peps/pep-0008/) style guide
- Use type hints where appropriate
- Maximum line length: 120 characters
- Use snake_case for variables and functions
- Use CamelCase for class names
- Add docstrings to all public functions and classes

### JavaScript/TypeScript
- Follow [Airbnb JavaScript Style Guide](https://github.com/airbnb/javascript)
- Use TypeScript for new frontend code
- Use camelCase for variables and functions
- Use PascalCase for React components
- Maximum line length: 120 characters

### SQL
- Use UPPERCASE for SQL keywords
- Use snake_case for table and column names
- Add comments for complex queries
- Use consistent indentation

## Testing

### Running Tests
```bash
# Run all tests
pytest tests/

# Run specific test file
pytest tests/test_module.py

# Run tests with coverage
pytest tests/ --cov=datagod --cov-report=html
```

### Writing Tests
- Write unit tests for all new functionality
- Aim for >80% code coverage
- Test edge cases and error conditions
- Use descriptive test names
- Keep tests isolated and independent

## Documentation

### Updating Documentation
- Update documentation for any changes to functionality
- Keep API documentation in sync with code
- Update README.md for major changes
- Add examples where helpful

### Building Documentation
```bash
# Install MkDocs
pip install mkdocs

# Build documentation
mkdocs build

# Serve documentation locally
mkdocs serve
```

## Issue Templates

### Bug Report Template
```markdown
## Bug Report

**Describe the bug**
A clear and concise description of what the bug is.

**To Reproduce**
Steps to reproduce the behavior:
1. Go to '...'
2. Click on '....'
3. Scroll down to '....'
4. See error

**Expected behavior**
A clear and concise description of what you expected to happen.

**Screenshots**
If applicable, add screenshots to help explain your problem.

**Environment**
- OS: [e.g. Ubuntu 22.04]
- Python version: [e.g. 3.9.7]
- Database: [e.g. PostgreSQL 13.4]
- Browser (if applicable): [e.g. Chrome 96]

**Additional context**
Add any other context about the problem here.
```

### Feature Request Template
```markdown
## Feature Request

**Is your feature request related to a problem? Please describe.**
A clear and concise description of what the problem is. Ex. I'm always frustrated when [...]

**Describe the solution you'd like**
A clear and concise description of what you want to happen.

**Describe alternatives you've considered**
A clear and concise description of any alternative solutions or features you've considered.

**Additional context**
Add any other context or screenshots about the feature request here.
```

## Pull Request Process

1. Ensure your code follows our coding standards
2. Update documentation for any changes
3. Add tests for new functionality
4. Ensure all tests pass
5. Update the CHANGELOG.md with your changes
6. Submit your pull request to the `development` branch
7. Wait for code review and address any feedback
8. Once approved, your changes will be merged

## Community

- **Slack**: Join our community Slack for discussions
- **GitHub Discussions**: For general questions and ideas
- **Weekly Meetings**: Join our community meetings (check GitHub for schedule)

## License

By contributing to DataGod, you agree that your contributions will be licensed under the MIT License.