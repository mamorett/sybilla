#!/usr/bin/env python3
"""
Check the structure of server.py to understand why it's not running
"""
import os
import ast

def analyze_server_py():
    """Analyze the structure of server.py"""
    if not os.path.exists("server.py"):
        print("❌ server.py not found")
        return
    
    print("🔍 Analyzing server.py structure...")
    
    try:
        with open("server.py", "r") as f:
            content = f.read()
        
        # Parse the AST to understand the structure
        tree = ast.parse(content)
        
        classes = []
        functions = []
        has_main_block = False
        imports = []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                classes.append(node.name)
            elif isinstance(node, ast.FunctionDef):
                functions.append(node.name)
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                for alias in node.names:
                    imports.append(f"{module}.{alias.name}")
        
        # Check for main block
        if 'if __name__ == "__main__":' in content:
            has_main_block = True
        
        print(f"📊 Analysis Results:")
        print(f"  📦 Imports: {len(imports)}")
        for imp in imports[:10]:  # Show first 10 imports
            print(f"    - {imp}")
        if len(imports) > 10:
            print(f"    ... and {len(imports) - 10} more")
        
        print(f"  🏗️  Classes: {classes}")
        print(f"  🔧 Functions: {len(functions)} total")
        print(f"  🚀 Has main block: {'✅' if has_main_block else '❌'}")
        
        # Check for MCP-specific imports
        mcp_imports = [imp for imp in imports if 'mcp' in imp.lower()]
        print(f"  📡 MCP imports: {mcp_imports}")
        
        # Check for stdio_server usage
        if 'stdio_server' in content:
            print("  ✅ Contains stdio_server")
        else:
            print("  ❌ Missing stdio_server")
        
        # Check for asyncio.run
        if 'asyncio.run' in content:
            print("  ✅ Contains asyncio.run")
        else:
            print("  ❌ Missing asyncio.run")
        
        if not has_main_block:
            print("\n💡 ISSUE FOUND: server.py has no main execution block!")
            print("   This is why it exits immediately when run directly.")
            print("   You need to add a main block to make it executable.")
        
        # Show the end of the file
        print(f"\n📄 Last 10 lines of server.py:")
        lines = content.split('\n')
        for i, line in enumerate(lines[-10:], len(lines) - 9):
            print(f"  {i:3d}: {line}")
        
    except Exception as e:
        print(f"❌ Error analyzing server.py: {e}")

def test_import_server():
    """Test if we can import the server class"""
    print("\n🧪 Testing server import...")
    try:
        from server import OracleLogsMCPServer
        print("✅ Successfully imported OracleLogsMCPServer")
        
        # Try to create an instance
        server_instance = OracleLogsMCPServer()
        print("✅ Successfully created server instance")
        print(f"   Server name: {server_instance.server.name if hasattr(server_instance, 'server') else 'Unknown'}")
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
    except Exception as e:
        print(f"❌ Error creating server instance: {e}")

if __name__ == "__main__":
    analyze_server_py()
    test_import_server()
