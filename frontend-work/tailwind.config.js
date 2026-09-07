/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        'site-bg': '#F5F3EE',
        'site-ink': '#1C2B45',
        'site-accent-delayed': '#C1541F',
        'site-accent-active': '#2F6B4F',
        'site-grey': '#AAB2B9',
      },
      fontFamily: {
        headline: ['"Space Grotesk"', 'sans-serif'],
        body: ['Inter', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'monospace'],
      },
      borderRadius: {
        'site': '8px',
      },
      borderWidth: {
        'hairline': '1px',
      }
    },
  },
  plugins: [],
}
