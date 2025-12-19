/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{vue,js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // 灰度系统 (iOS风格)
        'base': '#F2F2F7',      // 全局背景
        'cold-gray': '#F9F9FB',  // 冷灰调背景
        'glass-white': '#FAFAFA', // 组件白色
        'deep-black': '#1C1C1E',  // 深空黑 (主按钮)
        'graphite': '#3A3A3C',    // 石墨色 (次级文字)

        // 功能色
        primary: {
          DEFAULT: '#1C1C1E',
          light: '#3A3A3C',
        },
        secondary: {
          DEFAULT: '#FAFAFA',
          dark: '#E5E7EB',
        },
      },
      fontFamily: {
        sans: ['Inter', 'SF Pro Display', 'system-ui', 'sans-serif'],
      },
      fontSize: {
        'tag': ['10px', { lineHeight: '14px', letterSpacing: '0.08em' }], // 标签/次要信息
      },
      boxShadow: {
        // 悬浮阴影
        'float': '0 24px 48px -12px rgba(0, 0, 0, 0.08)',
        'float-lg': '0 32px 64px -16px rgba(0, 0, 0, 0.12)',

        // 内阴影 (凹陷效果)
        'inset-soft': 'inset 0 2px 4px rgba(0, 0, 0, 0.06)',

        // 玻璃边缘
        'glass': '0 0 0 1px rgba(229, 231, 235, 0.4)',
        'glass-inner': 'inset 0 0 0 1px rgba(255, 255, 255, 0.6)',
      },
      backdropBlur: {
        'xs': '2px',
        '3xl': '40px',
        '4xl': '60px',
        '5xl': '80px',
      },
      borderRadius: {
        'ios-lg': '28px',
        'ios-xl': '40px',
        'ios-2xl': '50px',
      },
      spacing: {
        'safe': '20px', // 安全距离
      },
      animation: {
        'press': 'press 0.15s ease-out',
      },
      keyframes: {
        press: {
          '0%, 100%': { transform: 'scale(1)' },
          '50%': { transform: 'scale(0.98)' },
        },
      },
    },
  },
  plugins: [],
}
