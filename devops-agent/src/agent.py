import sys
import os
import argparse
import logging
import requests
import uuid
import json
from src.db import AgentDB
from src.scenarios.deploy_verify_deny import run_scenario

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("devops-agent")

TALOS_URL = os.getenv("TALOS_GATEWAY_URL", "http://talos-node:8000")

class AgentClient:
    def __init__(self):
        self.session_id = str(uuid.uuid4())
        self.db = None
        try:
            self.db = AgentDB()
            # Try to restore last session if interactive (simplified: just use new for now)
            # In a real app we'd ask user which session to resume
        except Exception as e:
            logger.warning(f"DB Connection failed, running in memory-only mode: {e}")

    def chat(self, prompt: str):
        # 1. Save User Message
        if self.db:
            history = self.db.load_session(self.session_id)
            history.append({"role": "user", "content": prompt})
            self.db.save_session(self.session_id, history)
        
        # 2. Call Talos Gateway (LLM)
        # Note: We use Ollama-compatible /v1/chat/completions endpoint exposed by Talos
        payload = {
            "model": "llama3.2", # Default, Talos might enforce policy
            "messages": [{"role": "user", "content": prompt}]
        }
        
        try:
            r = requests.post(f"{TALOS_URL}/v1/chat/completions", json=payload, stream=True)
            r.raise_for_status()
            
            # Simply print chunks for interactive mode
            full_response = ""
            print("Agent: ", end="", flush=True)
            for line in r.iter_lines():
                if line:
                    decoded = line.decode('utf-8')
                    if decoded.startswith("data: "):
                        json_str = decoded[6:]
                        if json_str == "[DONE]":
                            break
                        try:
                            chunk = json.loads(json_str)
                            content = chunk.get("choices", [{}])[0].get("delta", {}).get("content", "")
                            print(content, end="", flush=True)
                            full_response += content
                        except:
                            pass
            print() # Newline
            
            # 3. Save Assistant Message
            if self.db:
                history.append({"role": "assistant", "content": full_response})
                self.db.save_session(self.session_id, history)
                
        except Exception as e:
            logger.error(f"Chat Error: {e}")

    def call_tool(self, tool_name: str, args: dict):
        """
        Calls a tool via Talos Gateway (MCP Proxy).
        Returns the JSON result (or error).
        """
        payload = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": args
            },
            "id": str(uuid.uuid4())
        }
        
        try:
            r = requests.post(f"{TALOS_URL}/mcp", json=payload, timeout=30)
            # We don't raise_for_status immediately because 403 denied is a valid result we want to parse
            if r.status_code == 403:
                return r.json() # Should contain error from Talos
            r.raise_for_status()
            return r.json()
        except Exception as e:
            logger.error(f"Tool Call Failed: {e}")
            return {"error": {"message": str(e)}}

def main():
    parser = argparse.ArgumentParser(description="Talos DevOps Agent")
    parser.add_argument("--mode", choices=["interactive", "scenario"], default="interactive")
    args = parser.parse_args()

    client = AgentClient()

    if args.mode == "scenario":
        logger.info("Running Deterministic Scenario...")
        try:
            run_scenario(client)
            sys.exit(0)
        except Exception as e:
            logger.error(f"Scenario Failed: {e}")
            sys.exit(1)
        
    else:
        print("=== Talos DevOps Agent (Interactive) ===")
        print(f"Session ID: {client.session_id}")
        print("Type 'exit' to quit.")
        
        while True:
            try:
                user_input = input("\nYou: ")
                if user_input.lower() in ["exit", "quit"]:
                    break
                
                # For demo simplicity, interactive mode just chats. 
                # To invoke tools interactively, we'd need a ReAct loop or function calling logic in client.
                # For this SECURITY DEMO, the interactive mode is for checking history/chat connectivity.
                # The SCENARIO mode is the primary verification.
                client.chat(user_input)
                
            except KeyboardInterrupt:
                break

if __name__ == "__main__":
    main()
