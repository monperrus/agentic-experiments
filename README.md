# agentic-experiments
exploiting copilot to do science

## Important Settings

### Internet Access (Firewall)

When using the Copilot cloud agent, configuring Internet access is an important setting.

> **Enable firewall** *(Recommended)*
> Limit Copilot cloud agent's Internet access to only allow access to allowlisted locations.

Enabling the firewall ensures that the agent only accesses approved network resources during code generation and execution. This is the recommended configuration for security.

To configure this, go to your repository (or organization) settings → Copilot → and enable the **firewall** option to restrict the agent's outbound Internet access to allowlisted locations only.

See the [GitHub documentation](https://docs.github.com/en/copilot/customizing-copilot/customizing-the-development-environment-for-copilot-coding-agent) for more details on customizing network access for the Copilot cloud agent.
