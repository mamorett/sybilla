#!/usr/bin/env python3
import asyncio
import sys
import os
import subprocess
from pathlib import Path

# Add the app directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

from app.services.mcp_client import MCPClient
from app.config import settings

async def test_mcp_server_directly():
    """Test running the MCP server directly to see what happens"""
    print("🧪 Testing MCP Server Direct Execution")
    print(f"📁 MCP Server Script: {settings.MCP_SERVER_SCRIPT_PATH}")
    print(f"📁 Script exists: {os.path.exists(settings.MCP_SERVER_SCRIPT_PATH)}")
    print(f"📁 Working directory: {os.getcwd()}")
    print("-" * 50)
    
    # Test running the server directly
    try:
        print("🚀 Attempting to run MCP server directly...")
        cmd = [sys.executable, settings.MCP_SERVER_SCRIPT_PATH]
        print(f"Command: {' '.join(cmd)}")
        
        process = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=os.path.dirname(settings.MCP_SERVER_SCRIPT_PATH) or "."
        )
        
        # Wait a moment
        await asyncio.sleep(2)
        
        # Check if it's still running
        if process.poll() is None:
            print("✅ MCP server process is running!")
            
            # Try to send a simple message
            try:
                test_message = '{"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2024-11-05", "capabilities": {"tools": {}}, "clientInfo": {"name": "test", "version": "1.0.0"}}}\n'
                print("📤 Sending initialize message...")
                
                process.stdin.write(test_message)
                process.stdin.flush()
                
                # Try to read response with timeout
                try:
                    response = await asyncio.wait_for(
                        asyncio.get_event_loop().run_in_executor(None, process.stdout.readline),
                        timeout=5.0
                    )
                    print(f"📥 Received response: {response.strip()}")
                except asyncio.TimeoutError:
                    print("⏰ No response received within 5 seconds")
                
            except Exception as e:
                print(f"❌ Error communicating with server: {e}")
            
            # Terminate the test process
            process.terminate()
            
        else:
            # Process exited
            stdout, stderr = process.communicate()
            print(f"❌ MCP server process exited immediately")
            print(f"Exit code: {process.returncode}")
            print(f"STDOUT: {stdout}")
            print(f"STDERR: {stderr}")
            
            # Let's try to understand why it failed
            if stderr:
                print("\n🔍 Analyzing error...")
                if "ModuleNotFoundError" in stderr:
                    print("💡 Looks like a missing module. Make sure all dependencies are installed.")
                elif "ImportError" in stderr:
                    print("💡 Import error. Check if all required files are in the right place.")
                elif "SyntaxError" in stderr:
                    print("💡 Syntax error in the Python code.")
                else:
                    print("💡 Unknown error. Check the stderr output above.")
    
    except Exception as e:
        print(f"❌ Failed to start MCP server: {e}")
        import traceback
        traceback.print_exc()

async def test_mcp_client():
    """Test the MCP client"""
    print("\n" + "="*50)
    print("🧪 Testing MCP Client")
    print("="*50)
    
    client = MCPClient()
    
    try:
        # Test connection
        print("🔌 Testing client connection...")
        connected = await client.test_connection()
        print(f"Connection result: {'✅ Success' if connected else '❌ Failed'}")
        
        if connected:
            # List tools
            print("\n📋 Listing available tools...")
            tools = await client.list_tools()
            
            if "tools" in tools:
                for tool in tools["tools"]:
                    print(f"  🔧 {tool.get('name', 'Unknown')}: {tool.get('description', 'No description')}")
            else:
                print(f"❌ Error listing tools: {tools}")
        
    except Exception as e:
        print(f"❌ Client test failed: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        await client.close()

async def check_environment():
    """Check the environment and dependencies"""
    print("🔍 Environment Check")
    print("-" * 30)
    
    # Check Python version
    print(f"🐍 Python version: {sys.version}")
    
    # Check current directory
    print(f"📁 Current directory: {os.getcwd()}")
    
    # List files in current directory
    print("📂 Files in current directory:")
    for item in os.listdir("."):
        if os.path.isfile(item):
            print(f"  📄 {item}")
        else:
            print(f"  📁 {item}/")
    
    # Check if main.py exists and show its content
    if os.path.exists("main.py"):
        print("\n📄 Content of main.py (first 20 lines):")
        try:
            with open("main.py", "r") as f:
                lines = f.readlines()[:20]
                for i, line in enumerate(lines, 1):
                    print(f"  {i:2d}: {line.rstrip()}")
        except Exception as e:
            print(f"❌ Error reading main.py: {e}")
    
    # Check if server.py exists
    if os.path.exists("server.py"):
        print("\n📄 server.py exists")
    else:
        print("\n❌ server.py not found")
    
    # Check for required modules
    print("\n📦 Checking required modules:")
    required_modules = ["mcp", "asyncio"]
    for module in required_modules:
        try:
            __import__(module)
            print(f"  ✅ {module}")
        except ImportError:
            print(f"  ❌ {module} - NOT FOUND")

async def main():
    """Main test function"""
    await check_environment()
    print("\n")
    await test_mcp_server_directly()
    await test_mcp_client()

if __name__ == "__main__":
    asyncio.run(main())
