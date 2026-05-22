import type { Config } from 'tailwindcss'

export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        primary: '#0F172A',
        accent: '#F59E0B',
        success: '#10B981',
        danger: '#EF4444',
      },
    },
  },
  plugins: [],
} satisfies Config
