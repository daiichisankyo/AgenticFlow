"""Declaration vs Execution - Core concept example."""

import agentic_flow as af

assistant = af.Agent(name="assistant", instructions="Help the user.", model="gpt-5.2")

# Declaration - creates a specification, NOT executed
spec = assistant("Hello")

# Execution - happens here, and ONLY here
# result = await spec
