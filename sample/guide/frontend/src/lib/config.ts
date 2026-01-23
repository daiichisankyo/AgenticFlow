import type { StartScreenPrompt, ThemeOption } from "@openai/chatkit";

const readEnvString = (value: unknown): string | undefined =>
  typeof value === "string" && value.trim().length > 0
    ? value.trim()
    : undefined;

export const CHATKIT_API_URL =
  readEnvString(import.meta.env.VITE_CHATKIT_API_URL) ?? "/chatkit";

/**
 * ChatKit requires a domain key at runtime. Use the local fallback while
 * developing, and register a production domain key for deployment:
 * https://platform.openai.com/settings/organization/security/domain-allowlist
 */
export const CHATKIT_API_DOMAIN_KEY =
  readEnvString(import.meta.env.VITE_CHATKIT_API_DOMAIN_KEY) ??
  "domain_pk_localhost_dev";

// Start screen prompts
export const STARTER_PROMPTS: StartScreenPrompt[] = [
  {
    label: "What is AF?",
    prompt: "What is AF (Agentic Flow Framework) and how does it differ from the OpenAI Agents SDK?",
    icon: "sparkle",
  },
  {
    label: "Show me the syntax",
    prompt: "Show me the basic syntax for agent calls with streaming and isolation",
    icon: "square-code",
  },
  {
    label: "Explain phase()",
    prompt: "Explain how phase() works and when to use share_context",
    icon: "compass",
  },
];

// Theme configuration
export type ColorScheme = "light" | "dark";

export const getThemeConfig = (theme: ColorScheme): ThemeOption => ({
  color: {
    grayscale: {
      hue: 220,
      tint: 6,
      shade: theme === "dark" ? -1 : -4,
    },
    accent: {
      primary: theme === "dark" ? "#5b9bd5" : "#2563a8",
      level: 1,
    },
  },
  radius: "round",
});
