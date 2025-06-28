import type { Config } from 'tailwindcss';
// import flowbitePlugin from 'flowbite/plugin'

export default {
	content: [
		'./src/**/*.{html,js,svelte,ts,md}',
		'./node_modules/flowbite-svelte/**/*.{html,js,svelte,ts}'
	],
  darkMode: 'selector',
  theme: {
    extend: {
      colors: {
        // flowbite-svelte
        primary: {
          50: '#FFF5F2',
          100: '#FFF1EE',
          200: '#FFE4DE',
          300: '#FFD5CC',
          400: '#FFBCAD',
          500: '#FE795D',
          600: '#EF562F',
          700: '#EB4F27',
          800: '#CC4522',
          900: '#A5371B'
        },
        // Semantic colors for consistent usage
        success: {
          50: '#F0FDF4',
          500: '#10B981',
          600: '#059669',
          700: '#047857'
        },
        warning: {
          50: '#FFFBEB',
          500: '#F59E0B',
          600: '#D97706',
          700: '#B45309'
        },
        danger: {
          50: '#FEF2F2',
          500: '#EF4444',
          600: '#DC2626',
          700: '#B91C1C'
        }
      },
      spacing: {
        '18': '4.5rem',
        '72': '18rem',
        '84': '21rem',
        '96': '24rem'
      },
      fontSize: {
        'xs': ['0.75rem', { lineHeight: '1rem' }],
        'sm': ['0.875rem', { lineHeight: '1.25rem' }],
        'base': ['1rem', { lineHeight: '1.5rem' }],
        'lg': ['1.125rem', { lineHeight: '1.75rem' }],
        'xl': ['1.25rem', { lineHeight: '1.75rem' }]
      },
      borderRadius: {
        'card': '0.75rem',
        'button': '0.5rem'
      }
    }
  },
  // plugins: [flowbitePlugin]
} as Config;
