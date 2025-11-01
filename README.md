# Graphiti-Memory MCP Server

A [Model Context Protocol (MCP)](https://modelcontextprotocol.io) server that provides memory and knowledge graph operations using Neo4j and the Graphiti framework.

## Features

- 📝 **Add Memories**: Store episodes and information in the knowledge graph with automatic entity extraction
- 🧠 **Search Nodes**: Query entities in your knowledge graph using natural language
- 🔗 **Search Facts**: Find relationships and connections between entities
- 📚 **Retrieve Episodes**: Get historical episodes and memories
- 🗑️ **Management Tools**: Delete episodes, edges, and clear the graph
- 🤖 **AI-Powered**: Optional OpenAI integration for enhanced entity extraction
- 📊 **Real-time Data**: Direct connection to your Neo4j database
- 🛠️ **Built-in Diagnostics**: Comprehensive error messages and troubleshooting

## Installation

### Prerequisites

1. **Neo4j Database**: You need a running Neo4j instance
   ```bash
   # Install Neo4j (via Homebrew on macOS)
   brew install neo4j
   
   # Start Neo4j
   neo4j start
   ```

2. **Python 3.10+**: Required for the MCP server

### Install from PyPI

```bash
pip install graphiti-memory
```

### Install from Source

```bash
git clone https://github.com/alankyshum/graphiti-memory.git
cd graphiti-memory
pip install -e .
```

## Configuration

### MCP Configuration

Add to your MCP client configuration file (e.g., Claude Desktop config):

```json
{
  "mcpServers": {
    "graphiti-memory": {
      "command": "graphiti-mcp-server",
      "env": {
        "NEO4J_URI": "neo4j://127.0.0.1:7687",
        "NEO4J_USER": "neo4j",
        "NEO4J_PASSWORD": "your-password-here",
        "OPENAI_API_KEY": "your-openai-key-here",
        "GRAPHITI_GROUP_ID": "default"
      }
    }
  }
}
```

### Neo4j Setup

1. **Set Password** (first-time setup):
   ```bash
   neo4j-admin dbms set-initial-password YOUR_PASSWORD
   ```

2. **Test Connection**:
   ```bash
   # HTTP interface
   curl http://127.0.0.1:7474
   
   # Bolt protocol
   nc -zv 127.0.0.1 7687
   ```

## Available Tools

### 1. search_memory_nodes

Search for nodes in the Neo4j knowledge graph.

**Example**:
```python
{
  "name": "search_memory_nodes",
  "arguments": {
    "query": "machine learning"
  }
}
```

**Returns**: List of nodes with IDs, labels, and properties.

### 2. search_memory_facts

Search for facts and relationships in the knowledge graph.

**Example**:
```python
{
  "name": "search_memory_facts",
  "arguments": {
    "query": "related concepts"
  }
}
```

**Returns**: Fact triples (subject-predicate-object) with metadata.

### 3. test_neo4j_auth

Test Neo4j authentication and return connection diagnostics.

**Example**:
```python
{
  "name": "test_neo4j_auth",
  "arguments": {}
}
```

**Returns**: Connection status, URI, user, and diagnostic information.

## Usage

### With Claude Desktop

Configure in `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "graphiti-memory": {
      "command": "graphiti-mcp-server",
      "env": {
        "NEO4J_URI": "neo4j://127.0.0.1:7687",
        "NEO4J_USER": "neo4j",
        "NEO4J_PASSWORD": "your-password"
      }
    }
  }
}
```

### Standalone Testing

Test the server directly from command line:

```bash
export NEO4J_URI="neo4j://127.0.0.1:7687"
export NEO4J_USER="neo4j"
export NEO4J_PASSWORD="your-password"

echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}' | graphiti-mcp-server
```

## Troubleshooting

### Connection Failed

**Error**: `Connection refused` or `ServiceUnavailable`

**Solutions**:
1. Check Neo4j is running: `neo4j status`
2. Start Neo4j: `neo4j start`
3. Verify port 7687 is accessible: `nc -zv 127.0.0.1 7687`

### Authentication Failed

**Error**: `Unauthorized` or `authentication failure`

**Solutions**:
1. Verify password is correct
2. Reset password: `neo4j-admin dbms set-initial-password NEW_PASSWORD`
3. Update password in MCP configuration
4. Use test tool to verify: `test_neo4j_auth`

### Package Not Found

**Error**: `neo4j package not installed`

This package automatically installs the `neo4j` dependency. If you see this error:

```bash
pip install neo4j
```

## Development

### Setup Development Environment

```bash
git clone https://github.com/alankyshum/graphiti-memory.git
cd graphiti-memory
pip install -e ".[dev]"
```

### Running Tests

```bash
# Test the server
python -m graphiti_memory.server << 'EOF'
{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}
EOF
```

## Architecture

```
MCP Client (Claude Desktop / Cline / etc.)
    ↓
Graphiti-Memory Server
    ↓
Neo4j Database
```

The server:
- Listens on stdin for JSON-RPC messages
- Logs diagnostics to stderr
- Responds on stdout with JSON-RPC
- Maintains persistent Neo4j connection

## Contributing

Contributions welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## License

MIT License - see LICENSE file for details.

## Links

- **GitHub**: https://github.com/alankyshum/graphiti-memory
- **PyPI**: https://pypi.org/project/graphiti-memory/
- **Issues**: https://github.com/alankyshum/graphiti-memory/issues
- **MCP Specification**: https://modelcontextprotocol.io

## Credits

Built for use with:
- [Model Context Protocol (MCP)](https://modelcontextprotocol.io)
- [Neo4j](https://neo4j.com)
- [Graphiti](https://github.com/getzep/graphiti) - Knowledge graph framework
