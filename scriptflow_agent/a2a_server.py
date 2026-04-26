"""
Expose the ScriptFlow root agent as an A2A server.
Run:  python -m scriptflow_agent.a2a_server

When running inside the platform, Prompt Opinion will fetch the agent card at
/.well-known/agent.json and invoke skills via A2A.
"""

import os
from google.adk.a2a.utils.agent_to_a2a import to_a2a
from scriptflow_agent.agent import root_agent
from scriptflow_agent.config import A2A_PUBLIC_URL


def _parse_host_port(public_url: str) -> tuple[str, int, str]:
    # public_url example: https://abcd-12-34-56-78.ngrok-free.app
    # to_a2a needs the host, port, and protocol used in the agent card.
    if "://" in public_url:
        proto, rest = public_url.split("://", 1)
    else:
        proto, rest = "http", public_url
    host_port = rest.split("/", 1)[0]
    if ":" in host_port:
        host, port_str = host_port.split(":", 1)
        port = int(port_str)
    else:
        host = host_port
        port = 443 if proto == "https" else 8000
    return host, port, proto


host, port, proto = _parse_host_port(A2A_PUBLIC_URL)

# to_a2a returns a Starlette app pre-configured with A2A endpoints
# and an auto-generated agent card derived from the agent's name/description/skills.
app = to_a2a(agent=root_agent, host=host, port=port, protocol=proto)


if __name__ == "__main__":
    import uvicorn
    # Bind to 0.0.0.0:8000 locally; ngrok will tunnel a public URL to this port.
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("LOCAL_PORT", "8000")))
