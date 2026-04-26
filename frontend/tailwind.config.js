/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      fontFamily: {
        sans: ["'IBM Plex Sans'", "sans-serif"],
        mono: ["'IBM Plex Mono'", "monospace"],
      },
      colors: {
        surface: {
          0: "#0a0a0a",
          1: "#111111",
          2: "#1a1a1a",
          3: "#222222",
          4: "#2a2a2a",
        },
        border: "#2e2e2e",
        accent: {
          green: "#00c896",
          red: "#ff4d4d",
          amber: "#f5a623",
          blue: "#3b9eff",
        },
        text: {
          primary: "#f0f0f0",
          secondary: "#888888",
          muted: "#555555",
        },
      },
      keyframes: {
        "fade-in": {
          from: { opacity: "0", transform: "translateY(6px)" },
          to: { opacity: "1", transform: "translateY(0)" },
        },
        "pulse-dot": {
          "0%, 100%": { opacity: "1" },
          "50%": { opacity: "0.3" },
        },
        shimmer: {
          "0%": { backgroundPosition: "-200% 0" },
          "100%": { backgroundPosition: "200% 0" },
        },
      },
      animation: {
        "fade-in": "fade-in 0.2s ease-out forwards",
        "pulse-dot": "pulse-dot 1.4s ease-in-out infinite",
        shimmer: "shimmer 1.6s linear infinite",
      },
    },
  },
  plugins: [],
};
