import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: ["class"],
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./lib/**/*.{ts,tsx}",
    "./hooks/**/*.{ts,tsx}"
  ],
  theme: {
    extend: {
      colors: {
        "surface-bg": "var(--surface-bg)",
        "surface-fg": "var(--surface-fg)",
        "surface-muted": "var(--surface-muted)",
        "surface-card": "var(--surface-card)",
        "surface-border": "var(--surface-border)",
        "surface-accent": "var(--surface-accent)",
        "surface-accent-fg": "var(--surface-accent-fg)",
        bg: "#0B0F14",
        panel: "#0F1722",
        line: "#1D2733",
        neon: {
          cyan: "#22D3EE",
          violet: "#8B5CF6",
          green: "#34D399",
          amber: "#F59E0B",
          red: "#F43F5E"
        }
      },
      boxShadow: {
        glow: "0 0 0 1px rgba(34,211,238,.25), 0 0 30px rgba(34,211,238,.15)",
        critical: "0 0 0 1px rgba(244,63,94,.35), 0 0 28px rgba(244,63,94,.18)"
      },
      backgroundImage: {
        "grid-subtle": "linear-gradient(rgba(34,211,238,0.06) 1px, transparent 1px), linear-gradient(90deg, rgba(34,211,238,0.06) 1px, transparent 1px)",
        "scan-gradient": "linear-gradient(90deg, rgba(34,211,238,.12), rgba(139,92,246,.22), rgba(52,211,153,.12))"
      },
      keyframes: {
        pulseGlow: {
          "0%, 100%": { boxShadow: "0 0 0 0 rgba(34,211,238,.0)" },
          "50%": { boxShadow: "0 0 0 10px rgba(34,211,238,.14)" }
        },
        drift: {
          "0%": { transform: "translateY(0px)", opacity: "0.15" },
          "50%": { opacity: "0.35" },
          "100%": { transform: "translateY(-18px)", opacity: "0.1" }
        }
      },
      animation: {
        "pulse-glow": "pulseGlow 2.2s ease-in-out infinite",
        drift: "drift 6s ease-in-out infinite"
      }
    }
  },
  plugins: []
};

export default config;
