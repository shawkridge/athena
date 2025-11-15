/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        'athena-dark': '#0f172a',
        'athena-blue': '#0369a1',
        'athena-green': '#16a34a',
      },
    },
  },
  plugins: [],
}
