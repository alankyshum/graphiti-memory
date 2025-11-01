#!/usr/bin/env python3
"""
Graphiti-Memory MCP Server

A Model Context Protocol (MCP) server that provides memory and knowledge graph
operations using Neo4j and the Graphiti framework.

This server exposes Graphiti's full capabilities through MCP tools including:
- Adding episodes/memories to the knowledge graph
- Searching nodes (entities) and facts (relationships)
- Managing episodes and edges
- Graph maintenance operations

Environment Variables Required:
- NEO4J_URI: Neo4j connection URI (e.g., neo4j://127.0.0.1:7687)
- NEO4J_USER: Neo4j username
- NEO4J_PASSWORD: Neo4j password
- OPENAI_API_KEY: OpenAI API key (optional, for entity extraction)
- GRAPHITI_GROUP_ID: Group ID for organizing data (optional, defaults to 'default')

Usage:
    This server is designed to be run via any MCP client (Claude Desktop, Cline, etc.).
    Configure in your MCP client config with appropriate environment variables.
"""
import asyncio
import json
import sys
import logging
import os
from datetime import datetime, timezone
from typing import Any

# Configure logging to stderr
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stderr
)
logger = logging.getLogger(__name__)

# Graphiti client (initialized later)
graphiti_client = None
graphiti_connected = False
initialization_error = None

# Episode processing queues (for sequential processing per group_id)
episode_queues = {}
queue_workers = {}


async def initialize_graphiti():
    """Initialize the Graphiti client with Neo4j and optional LLM."""
    global graphiti_client, graphiti_connected, initialization_error

    uri = os.environ.get('NEO4J_URI', 'neo4j://127.0.0.1:7687')
    user = os.environ.get('NEO4J_USER', 'neo4j')
    password = os.environ.get('NEO4J_PASSWORD', '')
    openai_key = os.environ.get('OPENAI_API_KEY')

    logger.info("=" * 60)
    logger.info("Initializing Graphiti client")
    logger.info("=" * 60)
    logger.info(f"Neo4j URI: {uri}")
    logger.info(f"Neo4j User: {user}")
    logger.info(f"OpenAI API Key: {'configured' if openai_key else 'not configured'}")

    try:
        # Import Graphiti dependencies
        from graphiti_core import Graphiti
        from graphiti_core.llm_client import OpenAIClient
        from graphiti_core.llm_client.config import LLMConfig
        from graphiti_core.embedder.openai import OpenAIEmbedder, OpenAIEmbedderConfig

        # Create LLM client if API key is available
        llm_client = None
        embedder_client = None

        if openai_key:
            llm_config = LLMConfig(
                api_key=openai_key,
                model=os.environ.get('OPENAI_MODEL', 'gpt-4o-mini'),
                temperature=0.0
            )
            llm_client = OpenAIClient(config=llm_config)

            embedder_config = OpenAIEmbedderConfig(
                api_key=openai_key,
                embedding_model=os.environ.get('OPENAI_EMBEDDING_MODEL', 'text-embedding-3-small')
            )
            embedder_client = OpenAIEmbedder(config=embedder_config)
            logger.info(f"✅ LLM client initialized with model: {llm_config.model}")
        else:
            logger.warning("⚠️ OpenAI API key not found - entity extraction will be limited")

        # Initialize Graphiti client
        graphiti_client = Graphiti(
            uri=uri,
            user=user,
            password=password,
            llm_client=llm_client,
            embedder=embedder_client,
        )

        # Build indices and constraints
        await graphiti_client.build_indices_and_constraints()

        graphiti_connected = True
        logger.info("=" * 60)
        logger.info("✅ Graphiti client initialized successfully!")
        logger.info("=" * 60)
        return True

    except Exception as e:
        error_msg = str(e)
        logger.error("=" * 60)
        logger.error(f"❌ Graphiti initialization FAILED: {e}")
        logger.error("=" * 60)
        initialization_error = error_msg
        graphiti_connected = False

        # Provide helpful diagnostics
        if "Connection refused" in error_msg:
            logger.error("🔍 DIAGNOSIS: Neo4j server not running")
            logger.info("SOLUTIONS:")
            logger.info("  1. Start Neo4j: neo4j start")
            logger.info("  2. Check status: neo4j status")
        elif "Unauthorized" in error_msg or "authentication" in error_msg.lower():
            logger.error("🔍 DIAGNOSIS: Authentication failed")
            logger.info("SOLUTIONS:")
            logger.info("  1. Check NEO4J_PASSWORD in mcp.json")
            logger.info("  2. Reset password: neo4j-admin dbms set-initial-password NEW_PASSWORD")
        elif "No module named" in error_msg:
            logger.error("🔍 DIAGNOSIS: Missing Python package")
            logger.info("SOLUTIONS:")
            logger.info("  1. Install: pip install graphiti-memory")

        return False


async def process_episode_queue(group_id: str):
    """Process episodes for a specific group_id sequentially."""
    global queue_workers

    logger.info(f"Starting episode queue worker for group_id: {group_id}")
    queue_workers[group_id] = True

    try:
        while True:
            process_func = await episode_queues[group_id].get()
            try:
                await process_func()
            except Exception as e:
                logger.error(f"Error processing queued episode for group_id {group_id}: {e}")
            finally:
                episode_queues[group_id].task_done()
    except asyncio.CancelledError:
        logger.info(f"Episode queue worker for group_id {group_id} was cancelled")
    except Exception as e:
        logger.error(f"Unexpected error in queue worker for group_id {group_id}: {e}")
    finally:
        queue_workers[group_id] = False
        logger.info(f"Stopped episode queue worker for group_id: {group_id}")


def send_response(response):
    """Send JSON-RPC response to stdout."""
    json_str = json.dumps(response)
    sys.stdout.write(json_str + "\n")
    sys.stdout.flush()


def handle_initialize(request_id):
    """Handle initialize request."""
    logger.info("Handling initialize request")

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
                "version": "0.1.2",
                "graphiti_status": "connected" if graphiti_connected else "disconnected",
                "initialization_error": initialization_error
            }
        }
    }
    send_response(response)


def handle_tools_list(request_id):
    """Handle tools/list request."""
    logger.info("Handling tools/list request")

    tools = [
        {
            "name": "add_memory",
            "description": "Add an episode/memory to the knowledge graph. This is the primary way to add information.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Name of the episode"
                    },
                    "episode_body": {
                        "type": "string",
                        "description": "Content of the episode (text, message, or JSON)"
                    },
                    "group_id": {
                        "type": "string",
                        "description": "Optional group ID for organizing data"
                    },
                    "source": {
                        "type": "string",
                        "enum": ["text", "message", "json"],
                        "description": "Source type (default: text)"
                    },
                    "source_description": {
                        "type": "string",
                        "description": "Optional description of the source"
                    }
                },
                "required": ["name", "episode_body"]
            }
        },
        {
            "name": "search_memory_nodes",
            "description": "Search for nodes (entities) in the knowledge graph",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query"
                    },
                    "group_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional list of group IDs to filter results"
                    },
                    "max_nodes": {
                        "type": "integer",
                        "description": "Maximum number of nodes to return (default: 10)"
                    }
                },
                "required": ["query"]
            }
        },
        {
            "name": "search_memory_facts",
            "description": "Search for facts (relationships) in the knowledge graph",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query"
                    },
                    "group_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional list of group IDs to filter results"
                    },
                    "max_facts": {
                        "type": "integer",
                        "description": "Maximum number of facts to return (default: 10)"
                    }
                },
                "required": ["query"]
            }
        },
        {
            "name": "get_episodes",
            "description": "Get recent episodes for a group",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "group_id": {
                        "type": "string",
                        "description": "Group ID to retrieve episodes from"
                    },
                    "last_n": {
                        "type": "integer",
                        "description": "Number of recent episodes to retrieve (default: 10)"
                    }
                },
                "required": []
            }
        },
        {
            "name": "delete_episode",
            "description": "Delete an episode from the knowledge graph",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "uuid": {
                        "type": "string",
                        "description": "UUID of the episode to delete"
                    }
                },
                "required": ["uuid"]
            }
        },
        {
            "name": "delete_entity_edge",
            "description": "Delete an entity edge (fact) from the knowledge graph",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "uuid": {
                        "type": "string",
                        "description": "UUID of the entity edge to delete"
                    }
                },
                "required": ["uuid"]
            }
        },
        {
            "name": "get_entity_edge",
            "description": "Get an entity edge by UUID",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "uuid": {
                        "type": "string",
                        "description": "UUID of the entity edge to retrieve"
                    }
                },
                "required": ["uuid"]
            }
        },
        {
            "name": "clear_graph",
            "description": "Clear all data from the knowledge graph (DESTRUCTIVE)",
            "inputSchema": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    ]

    response = {
        "jsonrpc": "2.0",
        "id": request_id,
        "result": {
            "tools": tools,
            "graphiti_status": "connected" if graphiti_connected else "disconnected"
        }
    }
    send_response(response)


async def handle_tool_call_async(request_id, tool_name, arguments):
    """Handle tools/call request asynchronously."""
    logger.info(f"Handling tool call: {tool_name} with args: {arguments}")

    if not graphiti_connected:
        result_text = json.dumps({
            "error": f"Graphiti not connected: {initialization_error}",
            "solution": "Check Neo4j connection and credentials"
        })
        response = {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "content": [{"type": "text", "text": result_text}]
            }
        }
        send_response(response)
        return

    try:
        from graphiti_core.nodes import EpisodeType, EpisodicNode
        from graphiti_core.edges import EntityEdge
        from graphiti_core.search.search_config_recipes import NODE_HYBRID_SEARCH_RRF
        from graphiti_core.utils.maintenance.graph_data_operations import clear_data

        default_group_id = os.environ.get('GRAPHITI_GROUP_ID', 'default')

        # ADD_MEMORY tool
        if tool_name == "add_memory":
            name = arguments.get("name", "")
            episode_body = arguments.get("episode_body", "")
            group_id = arguments.get("group_id", default_group_id)
            source = arguments.get("source", "text")
            source_description = arguments.get("source_description", "")

            # Map source type
            source_type = EpisodeType.text
            if source == "message":
                source_type = EpisodeType.message
            elif source == "json":
                source_type = EpisodeType.json

            # Define episode processing function
            async def process_episode():
                try:
                    logger.info(f"Processing episode '{name}' for group_id: {group_id}")
                    await graphiti_client.add_episode(
                        name=name,
                        episode_body=episode_body,
                        source=source_type,
                        source_description=source_description,
                        group_id=group_id,
                        reference_time=datetime.now(timezone.utc),
                    )
                    logger.info(f"Episode '{name}' processed successfully")
                except Exception as e:
                    logger.error(f"Error processing episode '{name}': {e}")

            # Initialize queue for this group_id if needed
            if group_id not in episode_queues:
                episode_queues[group_id] = asyncio.Queue()

            # Add to queue
            await episode_queues[group_id].put(process_episode)

            # Start worker if not running
            if not queue_workers.get(group_id, False):
                asyncio.create_task(process_episode_queue(group_id))

            result_text = json.dumps({
                "success": True,
                "message": f"Episode '{name}' queued for processing",
                "queue_position": episode_queues[group_id].qsize()
            })

        # SEARCH_MEMORY_NODES tool
        elif tool_name == "search_memory_nodes":
            query = arguments.get("query", "")
            group_ids = arguments.get("group_ids", [default_group_id])
            max_nodes = arguments.get("max_nodes", 10)

            search_config = NODE_HYBRID_SEARCH_RRF.model_copy(deep=True)
            search_config.limit = max_nodes

            search_results = await graphiti_client._search(
                query=query,
                config=search_config,
                group_ids=group_ids,
            )

            nodes = []
            if search_results.nodes:
                for node in search_results.nodes:
                    nodes.append({
                        "uuid": node.uuid,
                        "name": node.name,
                        "summary": getattr(node, 'summary', ''),
                        "labels": getattr(node, 'labels', []),
                        "group_id": node.group_id,
                        "created_at": node.created_at.isoformat(),
                    })

            result_text = json.dumps({
                "query": query,
                "nodes": nodes,
                "total": len(nodes),
                "success": True
            })

        # SEARCH_MEMORY_FACTS tool
        elif tool_name == "search_memory_facts":
            query = arguments.get("query", "")
            group_ids = arguments.get("group_ids", [default_group_id])
            max_facts = arguments.get("max_facts", 10)

            relevant_edges = await graphiti_client.search(
                group_ids=group_ids,
                query=query,
                num_results=max_facts,
            )

            facts = []
            if relevant_edges:
                for edge in relevant_edges:
                    facts.append(edge.model_dump(
                        mode='json',
                        exclude={'fact_embedding'}
                    ))

            result_text = json.dumps({
                "query": query,
                "facts": facts,
                "total": len(facts),
                "success": True
            })

        # GET_EPISODES tool
        elif tool_name == "get_episodes":
            group_id = arguments.get("group_id", default_group_id)
            last_n = arguments.get("last_n", 10)

            episodes = await graphiti_client.retrieve_episodes(
                group_ids=[group_id],
                last_n=last_n,
                reference_time=datetime.now(timezone.utc)
            )

            formatted_episodes = []
            if episodes:
                for episode in episodes:
                    formatted_episodes.append(episode.model_dump(mode='json'))

            result_text = json.dumps({
                "group_id": group_id,
                "episodes": formatted_episodes,
                "total": len(formatted_episodes),
                "success": True
            })

        # DELETE_EPISODE tool
        elif tool_name == "delete_episode":
            uuid = arguments.get("uuid", "")
            episodic_node = await EpisodicNode.get_by_uuid(graphiti_client.driver, uuid)
            await episodic_node.delete(graphiti_client.driver)

            result_text = json.dumps({
                "success": True,
                "message": f"Episode with UUID {uuid} deleted successfully"
            })

        # DELETE_ENTITY_EDGE tool
        elif tool_name == "delete_entity_edge":
            uuid = arguments.get("uuid", "")
            entity_edge = await EntityEdge.get_by_uuid(graphiti_client.driver, uuid)
            await entity_edge.delete(graphiti_client.driver)

            result_text = json.dumps({
                "success": True,
                "message": f"Entity edge with UUID {uuid} deleted successfully"
            })

        # GET_ENTITY_EDGE tool
        elif tool_name == "get_entity_edge":
            uuid = arguments.get("uuid", "")
            entity_edge = await EntityEdge.get_by_uuid(graphiti_client.driver, uuid)
            edge_data = entity_edge.model_dump(
                mode='json',
                exclude={'fact_embedding'}
            )

            result_text = json.dumps({
                "success": True,
                "edge": edge_data
            })

        # CLEAR_GRAPH tool
        elif tool_name == "clear_graph":
            await clear_data(graphiti_client.driver)
            await graphiti_client.build_indices_and_constraints()

            result_text = json.dumps({
                "success": True,
                "message": "Graph cleared successfully and indices rebuilt"
            })

        else:
            result_text = json.dumps({
                "error": f"Unknown tool: {tool_name}"
            })

    except Exception as e:
        logger.error(f"Tool call failed: {e}", exc_info=True)
        result_text = json.dumps({
            "error": str(e),
            "tool": tool_name
        })

    response = {
        "jsonrpc": "2.0",
        "id": request_id,
        "result": {
            "content": [{"type": "text", "text": result_text}]
        }
    }
    send_response(response)


async def main_async():
    """Async main loop to handle MCP protocol messages."""
    logger.info("=" * 60)
    logger.info("Graphiti-Memory MCP server starting...")
    logger.info("=" * 60)

    # Initialize Graphiti
    await initialize_graphiti()

    # Process stdin line by line
    loop = asyncio.get_event_loop()

    async def read_stdin():
        """Read from stdin asynchronously."""
        for line in sys.stdin:
            yield line

    async for line in read_stdin():
        line = line.strip()
        if not line:
            continue

        try:
            request = json.loads(line)
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
                # Handle tool call asynchronously
                await handle_tool_call_async(request_id, tool_name, arguments)

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


def main():
    """Main entry point."""
    try:
        asyncio.run(main_async())
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Server error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
