# Development Guide

> **Community Project**: This is an independent, fan-made project. Not affiliated with or endorsed by Grinding Gear Games.

## Getting Started

### Prerequisites
```bash
python --version  # 3.9+ required
pip --version
git --version
```

### Initial Setup

**Option A: Development Install (Recommended)**
```bash
git clone https://github.com/HivemindOverlord/poe2-mcp.git
cd poe2-mcp
pip install -e ".[dev]"  # Installs with dev dependencies
```

**Option B: Standard Install**
```bash
pip install poe2-mcp
```

### Verify Installation
```bash
# Test MCP import
python -c "import mcp; print('MCP installed')"

# Run the server
poe2-mcp  # or: python launch.py
```

## Project Structure

```
poe2-mcp/
├── src/
│   ├── mcp_server.py       # Main MCP server (32 tools)
│   ├── config.py           # Configuration management
│   ├── api/                # API clients
│   │   ├── character_fetcher.py  # Multi-source fetching
│   │   ├── poe_ninja_api.py      # poe.ninja integration
│   │   ├── trade_api.py          # Trade site API
│   │   ├── rate_limiter.py       # Rate limiting
│   │   └── cache_manager.py      # Multi-tier caching
│   ├── data/               # Data providers
│   │   ├── mod_data_provider.py  # Item mods (14,269)
│   │   └── fresh_data_provider.py # Game data
│   ├── database/           # Database layer
│   │   ├── models.py       # SQLAlchemy models
│   │   └── manager.py      # Async operations
│   ├── calculator/         # Build calculations
│   │   ├── ehp_calculator.py
│   │   ├── spirit_calculator.py
│   │   ├── stun_calculator.py
│   │   └── resource_calculator.py
│   ├── analyzer/           # Analysis components
│   │   ├── character_analyzer.py
│   │   └── weakness_detector.py
│   ├── optimizer/          # Optimization engines
│   │   ├── gear_optimizer.py
│   │   └── gem_synergy_calculator.py
│   ├── knowledge/          # Game mechanics
│   │   └── poe2_mechanics.py
│   └── parsers/            # Data parsers
│       └── passive_tree_resolver.py
├── data/                   # Game data files (JSON)
├── tests/                  # Test suite
├── docs/                   # Documentation
├── scripts/                # Utility scripts
├── launch.py               # Quick launcher
├── pyproject.toml          # Package configuration
├── requirements.txt        # Dependencies
└── config.yaml             # Runtime configuration
```

## Development Workflow

### 1. Making Changes

```bash
# Create a feature branch
git checkout -b feature/your-feature-name

# Make changes in src/

# Run tests
pytest tests/ -v

# Run the server locally
python launch.py
```

### 2. Adding a New MCP Tool

```python
# In src/mcp_server.py

# 1. Add tool definition in _register_tools()
types.Tool(
    name="your_tool_name",
    description="Description of what the tool does",
    inputSchema={
        "type": "object",
        "properties": {
            "param_name": {
                "type": "string",
                "description": "Parameter description"
            }
        },
        "required": ["param_name"]
    }
)

# 2. Add handler dispatch in handle_call_tool()
elif name == "your_tool_name":
    return await self._handle_your_tool_name(arguments)

# 3. Implement the handler
async def _handle_your_tool_name(self, args: dict) -> List[types.TextContent]:
    """Handle your tool request"""
    try:
        param = args.get("param_name")

        # Your implementation here
        result = await self.some_component.do_work(param)

        return [types.TextContent(
            type="text",
            text=f"Result: {result}"
        )]
    except Exception as e:
        logger.error(f"Tool error: {e}")
        return [types.TextContent(
            type="text",
            text=f"Error: {str(e)}"
        )]
```

**Important**: Never raise exceptions to MCP layer - always catch and return error TextContent.

### 3. Adding Database Models

```python
# In src/database/models.py

class NewModel(Base):
    """Description of the model"""
    __tablename__ = "new_table"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False, index=True)
    data = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)

# Apply with alembic
# alembic revision --autogenerate -m "Add new model"
# alembic upgrade head
```

## Testing

### Running Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_ehp_calculator.py

# Run with coverage
pytest --cov=src tests/

# Run with verbose output
pytest -v
```

### Writing Tests

```python
# tests/test_your_feature.py

import pytest
from src.calculator.your_calculator import YourCalculator

@pytest.mark.asyncio
async def test_your_feature():
    """Test description"""
    calculator = YourCalculator(None)  # Mock db_manager if needed

    result = await calculator.calculate(input_data)

    assert "expected_field" in result
    assert result["value"] >= 0
```

## Configuration

### Environment Variables (.env)

```bash
# Optional API keys
ANTHROPIC_API_KEY=sk-ant-...  # For AI features

# Debug settings
DEBUG=true
LOG_LEVEL=DEBUG
```

### YAML Configuration (config.yaml)

```yaml
server:
  port: 8080

cache:
  enabled: true
  ttl: 3600

api:
  poe_ninja_rate_limit: 20
  poe_api_rate_limit: 10
```

### Accessing Config

```python
from src.config import settings

api_key = settings.ANTHROPIC_API_KEY
debug_mode = settings.DEBUG
```

## Database Management

### Migrations

```bash
# Create migration
alembic revision --autogenerate -m "Description"

# Apply migrations
alembic upgrade head

# Rollback
alembic downgrade -1
```

### Direct Database Access

```python
from src.database.manager import DatabaseManager

async def query_data():
    db = DatabaseManager()
    await db.initialize()

    items = await db.search_items("sword")

    await db.close()
```

## Debugging

### Enable Debug Logging

```bash
# In .env
DEBUG=true
LOG_LEVEL=DEBUG
```

### View Logs

```bash
# Unix/Mac
tail -f logs/poe2_optimizer.log

# Windows PowerShell
Get-Content logs/poe2_optimizer.log -Wait
```

### VS Code Debug Config

```json
// .vscode/launch.json
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "Python: MCP Server",
            "type": "python",
            "request": "launch",
            "program": "${workspaceFolder}/launch.py",
            "console": "integratedTerminal"
        }
    ]
}
```

## Code Style

### Formatting

```bash
# Format with black, then sort imports (both are CI gates; versions pinned in ci.yml)
pip install "black==25.11.0" "isort==9.0.2"
black src/ tests/ scripts/
isort src/ tests/ scripts/

# Lint
flake8 src/ tests/

# Type checking
mypy src/
```

### Style Guidelines

- Use type hints on all functions
- Write docstrings for classes and public methods
- All I/O operations must be async
- Handle errors gracefully in MCP handlers
- Use `datetime.utcnow()` not `datetime.now()`

## Building Packages

### PyPI Package

```bash
# Build
python -m build

# Upload (requires PyPI token)
python -m twine upload dist/*
```

### MCP Bundle

```bash
# Bundle is pre-built in releases
# Or create manually:
python -c "
import zipfile
import os
with zipfile.ZipFile('poe2-mcp.mcpb', 'w') as z:
    z.write('mcpb_bundle/manifest.json', 'manifest.json')
    for root, dirs, files in os.walk('mcpb_bundle/server'):
        for f in files:
            src = os.path.join(root, f)
            dst = src.replace('mcpb_bundle/', '')
            z.write(src, dst)
"
```

## Contributing

See [CONTRIBUTING.md](../CONTRIBUTING.md) for contribution guidelines.

### Quick Checklist

1. Fork the repository
2. Create a feature branch
3. Make changes following code style
4. Add/update tests
5. Update documentation
6. Run `pytest` - all tests must pass
7. Submit a pull request

## Resources

- [MCP Protocol Documentation](https://modelcontextprotocol.io/)
- [Python AsyncIO](https://docs.python.org/3/library/asyncio.html)
- [SQLAlchemy](https://docs.sqlalchemy.org/)
- [PyPI Package](https://pypi.org/project/poe2-mcp/)

## Getting Help

- Check the [README](../README.md) for usage
- Review [ARCHITECTURE.md](ARCHITECTURE.md) for system design
- Open an [issue](https://github.com/HivemindOverlord/poe2-mcp/issues) for bugs/questions
