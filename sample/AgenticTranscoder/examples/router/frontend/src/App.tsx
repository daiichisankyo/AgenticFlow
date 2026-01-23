import { useState, useEffect } from "react";
import { ChatKitPanel } from "./components/ChatKitPanel";
import type { ColorScheme } from "./lib/config";

const PROJECT_ICON = "🔀";
const PROJECT_TITLE = "Router Agent";

export default function App() {
  const [scheme, setScheme] = useState<ColorScheme>("light");

  useEffect(() => {
    const mediaQuery = window.matchMedia("(prefers-color-scheme: dark)");
    setScheme(mediaQuery.matches ? "dark" : "light");

    const handler = (e: MediaQueryListEvent) => {
      setScheme(e.matches ? "dark" : "light");
    };
    mediaQuery.addEventListener("change", handler);
    return () => mediaQuery.removeEventListener("change", handler);
  }, []);

  useEffect(() => {
    document.documentElement.setAttribute("data-color-scheme", scheme);
  }, [scheme]);

  return (
    <main className="relative flex min-h-screen flex-col items-center justify-center overflow-hidden dark:bg-slate-950">
      {/* Background gradient */}
      <div
        className="absolute inset-0"
        style={{
          background: `
            radial-gradient(ellipse 120% 80% at 50% -20%, rgba(125, 185, 232, 0.6) 0%, transparent 50%),
            radial-gradient(ellipse 100% 60% at 80% 100%, rgba(59, 130, 180, 0.5) 0%, transparent 40%),
            radial-gradient(ellipse 80% 50% at 20% 90%, rgba(100, 160, 210, 0.4) 0%, transparent 35%),
            linear-gradient(180deg, #4A9AD4 0%, #3178B5 35%, #2860A0 65%, #1E4C8A 100%)
          `,
        }}
      />

      {/* Subtle texture */}
      <div
        className="absolute inset-0 opacity-[0.015]"
        style={{
          backgroundImage: `url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noise'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noise)'/%3E%3C/svg%3E")`,
        }}
      />

      {/* Glowing orbs for depth */}
      <div className="absolute top-[-10%] left-[20%] h-[500px] w-[500px] rounded-full bg-[#6BB5E0]/30 blur-[100px]" />
      <div className="absolute bottom-[-5%] right-[10%] h-[400px] w-[400px] rounded-full bg-[#5A9FD0]/25 blur-[80px]" />
      <div className="absolute top-[40%] right-[-10%] h-[300px] w-[300px] rounded-full bg-[#4B8BC4]/20 blur-[60px]" />

      {/* Header */}
      <div className="absolute top-6 left-8 z-20 flex items-center gap-3">
        <div
          className="flex h-11 w-11 items-center justify-center rounded-2xl shadow-lg"
          style={{
            background: 'linear-gradient(135deg, rgba(255,255,255,0.25) 0%, rgba(255,255,255,0.1) 100%)',
            backdropFilter: 'blur(10px)',
            border: '1px solid rgba(255,255,255,0.2)',
          }}
        >
          <span className="text-lg drop-shadow-sm">{PROJECT_ICON}</span>
        </div>
        <div className="flex flex-col">
          <span className="text-sm font-semibold tracking-wide text-white drop-shadow-sm">{PROJECT_TITLE}</span>
        </div>
      </div>

      {/* Main content */}
      <div className="relative z-10 mx-auto w-full max-w-5xl">
        <ChatKitPanel theme={scheme} />
      </div>
    </main>
  );
}
