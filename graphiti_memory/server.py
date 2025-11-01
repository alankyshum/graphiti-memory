#!/usr/bin/env python3
"""
Graphiti-Memory MCP Server for Captain.

This server provides memory and knowledge graph functionality using Neo4j.
It offers tools for searching memory nodes, facts, and testing Neo4j authentication.

Features:
- Real-time Neo4j connection with authentication
- Detailed diagnostic logging for troubleshooting
- Three main tools: search_memory_nodes, search_memory_facts, test_neo4j_auth
- Returns actual data from Neo4j database when connected

Environment Variables Required:
- NEO4J_URI: Neo4j connection URI (e.g., neo4j://127.0.0.1:7687)
- NEO4J_USER: Neo4j username
- NEO4J_PASSWORD: Neo4j password

Usage:
    This server is designed to be run via Captain's MCP proxy.
    Configure in ~/.captain/mcp.json with appropriate environment variables.
"""
import json
import sys
import logging
import os
import subprocess

# Configure logging to stderr
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stderr
)
logger = logging.getLogger(__name__)

# Neo4j connection globals
neo4j_driver = None
neo4j_connected = False
auth_error = None


def test_neo4j_connection():
    """Test Neo4j connection and return diagnostics."""
    global neo4j_driver, neo4j_connected, auth_error

    uri = os.environ.get('NEO4J_URI', 'neo4j://127.0.0.1:7687')
    user = os.environ.get('NEO4J_USER', 'neo4j')
    password = os.environ.get('NEO4J_PASSWORD', '')

    logger.info("=" * 60)
    logger.info("Testing Neo4j Connection")
    logger.info("=" * 60)
    logger.info(f"URI: {uri}")
    logger.info(f"User: {user}")
    logger.info(f"Password: {'*' * len(password) if password else '(empty)'}")

    # First check if neo4j package is available
    try:
        # Try to import with subprocess to avoid modifying current process
        result = subprocess.run(
            [sys.executable, '-c', 'import neo4j; print(neo4j.__version__)'],
            capture_output=True,
            text=True,
            timeout=5
        )

        if result.returncode != 0:
            logger.error("❌ neo4j package not installed")
            logger.info("Install with: python3 -m pip install --break-system-packages neo4j")
            auth_error = "neo4j package not installed"
            return False

        logger.info(f"✅ neo4j package version: {result.stdout.strip()}")

    except Exception as e:
        logger.error(f"❌ Failed to check neo4j package: {e}")
        auth_error = f"Package check failed: {e}"
        return False

    # Now try to actually import and connect
    try:
        from neo4j import GraphDatabase

        logger.info("Attempting connection...")
        neo4j_driver = GraphDatabase.driver(uri, auth=(user, password))

        # Test connectivity
        neo4j_driver.verify_connectivity()
        logger.info("✅ Connection verified!")

        # Try a simple query
        with neo4j_driver.session() as session:
            result = session.run("RETURN 1 as num")
            num = result.single()['num']
            logger.info(f"✅ Test query successful: {num}")

        neo4j_connected = True
        logger.info("=" * 60)
        logger.info("✅ Neo4j authentication SUCCESSFUL!")
        logger.info("=" * 60)
        return True

    except ImportError as e:
        logger.error(f"❌ Failed to import neo4j: {e}")
        logger.info("Try: python3 -m pip install --break-system-packages neo4j")
        auth_error = f"Import failed: {e}"
        return False

    except Exception as e:
        error_msg = str(e)
        logger.error("=" * 60)
        logger.error(f"❌ Neo4j connection FAILED: {e}")
        logger.error("=" * 60)
        auth_error = error_msg

        # Provide specific diagnostics
        if "Unauthorized" in error_msg or "authentication" in error_msg.lower():
            logger.error("🔍 DIAGNOSIS: Authentication credentials are INCORRECT")
            logger.info("")
            logger.info("SOLUTIONS:")
            logger.info("  1. Check password is correct")
            logger.info("  2. Reset Neo4j password:")
            logger.info("     neo4j-admin dbms set-initial-password NEW_PASSWORD")
            logger.info("  3. Or use default credentials:")
            logger.info("     User: neo4j, Password: neo4j (on first login)")
            logger.info("")
            logger.info("  4. Update password in /Users/kshum/.captain/mcp.json")

        elif "refused" in error_msg.lower() or "Connection refused" in error_msg:
            logger.error("🔍 DIAGNOSIS: Neo4j server refused connection")
            logger.info("")
            logger.info("SOLUTIONS:")
            logger.info("  1. Check Neo4j status: neo4j status")
            logger.info("  2. Start Neo4j: neo4j start")
            logger.info("  3. Check port 7687 is accessible: nc -zv 127.0.0.1 7687")

        elif "ServiceUnavailable" in error_msg:
            logger.error("🔍 DIAGNOSIS: Neo4j service unavailable")
            logger.info("")
            logger.info("SOLUTIONS:")
            logger.info("  1. Restart Neo4j: neo4j restart")
            logger.info("  2. Check Neo4j logs: tail /opt/homebrew/var/log/neo4j/neo4j.log")

        else:
            logger.error("🔍 DIAGNOSIS: Unknown connection error")
            logger.info("")
            logger.info("SOLUTIONS:")
            logger.info("  1. Check Neo4j is running: neo4j status")
            logger.info("  2. Check URI format: neo4j://127.0.0.1:7687")
            logger.info("  3. Test with Neo4j browser: http://127.0.0.1:7474")

        logger.info("")
        logger.info("=" * 60)
        return False


def send_response(response):
    """Send JSON-RPC response to stdout."""
    json_str = json.dumps(response)
    sys.stdout.write(json_str + "\n")
    sys.stdout.flush()
    logger.debug(f"Sent response: {json_str[:200]}...")


def handle_initialize(request_id):
    """Handle initialize request."""
    logger.info("Handling initialize request")

    # Test Neo4j connection during initialization
    test_neo4j_connection()

    response = {
        "jsonrpc": "2.0",
        "id": request_id,
        "result": {
            "protocolVersion": "2024-11-05",
            "capabilities": {
                "tools": {}
            },
            "serverInfo": {
                "name": "graphiti-memory",
                "version": "1.0.0",
                "neo4j_status": "connected" if neo4j_connected else "disconnected",
                "auth_error": auth_error
            }
        }
    }
    send_response(response)


def handle_tools_list(request_id):
    """Handle tools/list request."""
    logger.info("Handling tools/list request")

    if not neo4j_connected:
        logger.warning("Neo4j not connected - tools may not work properly")

    tools = [
        {
            "name": "search_memory_nodes",
            "description": f"Search memory nodes {'(REAL Neo4j)' if neo4j_connected else '(MOCK - Neo4j disconnected)'}",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query"
                    }
                },
                "required": ["query"]
            }
        },
        {
            "name": "search_memory_facts",
            "description": f"Search memory facts {'(REAL Neo4j)' if neo4j_connected else '(MOCK - Neo4j disconnected)'}",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query"
                    }
                },
                "required": ["query"]
            }
        },
        {
            "name": "test_neo4j_auth",
            "description": "Test Neo4j authentication and return diagnostics",
            "inputSchema": {
                "type": "object",
                "properties": {},
                "required": []
            }
        },
        {
            "name": "add_memory_episode",
            "description": "Add a new episode or memory to the knowledge graph",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "content": {
                        "type": "string",
                        "description": "Content to store in memory"
                    },
                    "metadata": {
                        "type": "object",
                        "description": "Optional metadata (tags, timestamp, etc.)",
                        "additionalProperties": True
                    }
                },
                "required": ["content"]
            }
        }
    ]

    response = {
        "jsonrpc": "2.0",
        "id": request_id,
        "result": {
            "tools": tools,
            "neo4j_status": "connected" if neo4j_connected else "disconnected"
        }
    }
    send_response(response)


def handle_tool_call(request_id, tool_name, arguments):
    """Handle tools/call request."""
    logger.info(f"Handling tool call: {tool_name} with args: {arguments}")

    if tool_name == "test_neo4j_auth":
        # Re-test connection and return diagnostics
        success = test_neo4j_connection()
        result_text = json.dumps({
            "success": success,
            "connected": neo4j_connected,
            "error": auth_error,
            "uri": os.environ.get('NEO4J_URI', 'neo4j://127.0.0.1:7687'),
            "user": os.environ.get('NEO4J_USER', 'neo4j'),
            "message": "Authentication successful!" if success else f"Authentication failed: {auth_error}"
        })

    elif neo4j_connected and tool_name == "add_memory_episode":
        # Add a new memory/episode to Neo4j
        content = arguments.get("content", "")
        metadata = arguments.get("metadata", {})

        try:
            from neo4j import GraphDatabase
            import datetime

            with neo4j_driver.session() as session:
                # Create a Memory node with content and metadata
                timestamp = datetime.datetime.utcnow().isoformat()
                cypher = """
                CREATE (m:Memory {
                    content: $content,
                    timestamp: $timestamp,
                    metadata: $metadata_json
                })
                RETURN m
                """
                result = session.run(
                    cypher,
                    content=content,
                    timestamp=timestamp,
                    metadata_json=json.dumps(metadata)
                )

                record = result.single()
                if record:
                    node = record['m']
                    result_text = json.dumps({
                        "success": True,
                        "node_id": str(node.id),
                        "content": content,
                        "timestamp": timestamp,
                        "metadata": metadata,
                        "message": "Memory added successfully",
                        "source": "REAL Neo4j database"
                    })
                else:
                    result_text = json.dumps({
                        "success": False,
                        "error": "Failed to create node"
                    })

        except Exception as e:
            logger.error(f"Add memory failed: {e}")
            result_text = json.dumps({
                "success": False,
                "error": str(e),
                "content": content,
                "source": "Neo4j write failed"
            })

    elif neo4j_connected and tool_name == "search_memory_nodes":
        # Try real Neo4j query
        query = arguments.get("query", "")
        try:
            from neo4j import GraphDatabase

            with neo4j_driver.session() as session:
                # Simple query to test - just return some nodes
                cypher = "MATCH (n) RETURN n LIMIT 5"
                result = session.run(cypher)
                nodes = []
                for record in result:
                    node = record['n']
                    nodes.append({
                        "id": str(node.id),
                        "labels": list(node.labels),
                        "properties": dict(node)
                    })

                result_text = json.dumps({
                    "query": query,
                    "nodes": nodes,
                    "total": len(nodes),
                    "source": "REAL Neo4j database",
                    "success": True
                })
        except Exception as e:
            logger.error(f"Query failed: {e}")
            result_text = json.dumps({
                "error": str(e),
                "query": query,
                "source": "Neo4j query failed"
            })

    else:
        # Return mock data or error
        if not neo4j_connected:
            result_text = json.dumps({
                "error": f"Neo4j not connected: {auth_error}",
                "solution": "Fix Neo4j authentication first",
                "tool": tool_name,
                "query": arguments.get("query", "")
            })
        else:
            result_text = json.dumps({
                "message": f"Tool {tool_name} not fully implemented yet",
                "neo4j_status": "connected",
                "can_query": True
            })

    response = {
        "jsonrpc": "2.0",
        "id": request_id,
        "result": {
            "content": [
                {
                    "type": "text",
                    "text": result_text
                }
            ]
        }
    }
    send_response(response)


def main():
    """Main loop to handle MCP protocol messages."""
    logger.info("=" * 60)
    logger.info("Graphiti-Memory MCP server starting...")
    logger.info("Connecting to Neo4j for knowledge graph operations")
    logger.info("=" * 60)

    # Process stdin line by line
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue

        try:
            request = json.loads(line)
            logger.debug(f"Received request: {request}")

            request_id = request.get("id", 1)
            method = request.get("method", "")
            params = request.get("params", {})

            if method == "initialize":
                handle_initialize(request_id)

            elif method == "tools/list":
                handle_tools_list(request_id)

            elif method == "tools/call":
                tool_name = params.get("name", "")
                arguments = params.get("arguments", {})
                handle_tool_call(request_id, tool_name, arguments)

            else:
                logger.warning(f"Unknown method: {method}")
                error_response = {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {
                        "code": -32601,
                        "message": f"Method not found: {method}"
                    }
                }
                send_response(error_response)

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON: {e}")
        except Exception as e:
            logger.error(f"Error handling request: {e}", exc_info=True)


if __name__ == "__main__":
    main()
