# Model Context Protocol

The Model Context Protocol (MCP) is an open standard for connecting AI
assistants to external tools and data. An MCP server exposes
capabilities, and an MCP client, such as an AI assistant, calls them.

A server can offer tools, which are functions the assistant may call,
and resources, which are data the assistant may read. Each tool has a
name, a description, and a typed list of inputs.

Because the protocol is standard, one server works with any compatible
client without custom integration code.
