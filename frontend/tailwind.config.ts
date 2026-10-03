import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        bg: "#0b1020",
        panel: "#121a2f",
        soft: "#1a2440",
        accent: "#60a5fa",
      },
    },
  },
  plugins: [],
};

export default config;

