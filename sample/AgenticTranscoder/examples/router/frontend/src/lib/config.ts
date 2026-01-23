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

// Start screen prompts - customize these for your agent
export const STARTER_PROMPTS: StartScreenPrompt[] = [
  {
    label: "Hello",
    prompt: "Hello! What can you help me with?",
    icon: "sparkle",
  },
  {
    label: "Get started",
    prompt: "Help me get started",
    icon: "square-code",
  },
  {
    label: "Learn more",
    prompt: "Tell me more about what you can do",
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
