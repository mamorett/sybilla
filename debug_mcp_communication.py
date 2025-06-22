#!/usr/bin/env python3
"""
Debug MCP server communication to understand the protocol issue
"""
import asyncio
import subprocess
import sys
import json
import time

async def debug_mcp_server():
    """Debug the MCP server communication step by step"""
    print("🔍 Debugging MCP Server Communication")
    print("=" * 50)
    
    # Start the server
    cmd = [sys.executable, "./server.py"]
    print(f"🚀 Starting server: {' '.join(cmd)}")
    
    process = subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=0  # Unbuffered
    )
    
    try:
        # Wait for server to start
        await asyncio.sleep(2)
        
        if process.poll() is not None:
            stdout, stderr = process.communicate()
            print(f"❌ Server exited: {process.returncode}")
            print(f"STDOUT: {stdout}")
            print(f"STDERR: {stderr}")
            return
        
        print("✅ Server is running")
        
        # Test different message formats
        test_messages = [
            # Standard MCP initialize
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {}},
                    "clientInfo": {"name": "test", "version": "1.0.0"}
                }
            },
            # Simple ping
            {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "ping",
                "params": {}
            },
            # List tools
            {
                "jsonrpc": "2.0",
                "id": 3,
                "method": "tools/list",
                "params": {}
            }
        ]
        
        for i, message in enumerate(test_messages):
            print(f"\n📤 Test {i+1}: Sending {message['method']}")
            
            try:
                # Send message
                message_json = json.dumps(message) + "\n"
                print(f"   Message: {message_json.strip()}")
                
                process.stdin.write(message_json)
                process.stdin.flush()
                
                # Try to read response with shorter timeout
                print("   📥 Waiting for response...")
                
                try:
                    # Read with timeout
                    response = await asyncio.wait_for(
                        asyncio.get_event_loop().run_in_executor(None, process.stdout.readline),
                        timeout=3.0
                    )
                    
                    if response:
                        print(f"   ✅ Response: {response.strip()}")
                        try:
                            parsed = json.loads(response.strip())
                            print(f"   📊 Parsed: {parsed}")
                        except json.JSONDecodeError:
                            print(f"   ⚠️  Not valid JSON")
                    else:
                        print(f"   ❌ Empty response")
                        
                except asyncio.TimeoutError:
                    print(f"   ⏰ Timeout after 3 seconds")
                
                # Check if process is still alive
                if process.poll() is not None:
                    print(f"   💀 Server died during test {i+1}")
                    break
                    
            except Exception as e:
                print(f"   ❌ Error in test {i+1}: {e}")
        
        # Check server stderr for any error messages
        print(f"\n🔍 Checking server stderr...")
        try:
            # Non-blocking read of stderr
            import select
            import os
            
            if hasattr(select, 'select'):
                ready, _, _ = select.select([process.stderr], [], [], 0.1)
                if ready:
                    stderr_data = os.read(process.stderr.fileno(), 1024).decode()
                    if stderr_data:
                        print(f"   📢 Server stderr: {stderr_data}")
                    else:
                        print(f"   ℹ️  No stderr output")
                else:
                    print(f"   ℹ️  No stderr data available")
            else:
                print(f"   ℹ️  Cannot check stderr on this platform")
                
        except Exception as e:
            print(f"   ⚠️  Error checking stderr: {e}")
    
    finally:
        # Clean up
        if process.poll() is None:
            print(f"\n🛑 Terminating server...")
            process.terminate()
            try:
                await asyncio.wait_for(
                    asyncio.get_event_loop().run_in_executor(None, process.wait),
                    timeout=5.0
                )
            except asyncio.TimeoutError:
                print(f"   💀 Force killing server...")
                process.kill()

async def test_server_directly():
    """Test if we can run the server and see what it outputs"""
    print("\n🧪 Testing Server Direct Output")
    print("=" * 40)
    
    cmd = [sys.executable, "./server.py"]
    
    try:
        # Run server for a few seconds and capture all output
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Wait a bit
        await asyncio.sleep(3)
        
        # Terminate and get output
        process.terminate()
        stdout, stderr = process.communicate(timeout=5)
        
        print(f"📤 Server stdout:")
        if stdout:
            for line in stdout.split('\n'):
                if line.strip():
                    print(f"   {line}")
        else:
            print(f"   (empty)")
        
        print(f"📢 Server stderr:")
        if stderr:
            for line in stderr.split('\n'):
                if line.strip():
                    print(f"   {line}")
        else:
            print(f"   (empty)")
            
    except Exception as e:
        print(f"❌ Error testing server: {e}")

if __name__ == "__main__":
    asyncio.run(debug_mcp_server())
    asyncio.run(test_server_directly())
