// tailwind.config.js
module.exports = {
  content: [
    "./src/**/*.{js,jsx,ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        'coles-red': '#E60000',
        'coles-yellow': '#FFD500',
      },
      animation: {
        'pulse': 'pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite',
      },
    },
  },
  plugins: [
    // Typography plugin improves text formatting for recipes
    require('@tailwindcss/typography'),
  ],
}