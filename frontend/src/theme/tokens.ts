import type { GlobalThemeOverrides } from 'naive-ui'

export interface ThemeTokens {
  fontFamily: string
  radiusSm: string
  radiusMd: string
  radiusLg: string
  radiusXl: string
  shadowSm: string
  shadowMd: string
  shadowLg: string
  durationFast: string
  durationBase: string
  durationSlow: string
  easeStandard: string
  easeEmphasized: string
}

export interface ThemeSemanticMap {
  bgPage: string
  bgSurface: string
  bgElevated: string
  textPrimary: string
  textSecondary: string
  textTertiary: string
  borderDefault: string
  brandPrimary: string
  brandPrimaryHover: string
  brandSoft: string
  success: string
  warning: string
  error: string
  info: string
}

export const themeTokens: ThemeTokens = {
  fontFamily: "'Inter', 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', sans-serif",
  radiusSm: '8px',
  radiusMd: '12px',
  radiusLg: '16px',
  radiusXl: '24px',
  shadowSm: '0 4px 12px rgba(14, 23, 38, 0.06)',
  shadowMd: '0 10px 30px rgba(14, 23, 38, 0.1)',
  shadowLg: '0 18px 50px rgba(20, 32, 56, 0.16)',
  durationFast: '160ms',
  durationBase: '240ms',
  durationSlow: '360ms',
  easeStandard: 'cubic-bezier(0.4, 0, 0.2, 1)',
  easeEmphasized: 'cubic-bezier(0.2, 0.7, 0.2, 1)',
}

export const semanticMap: ThemeSemanticMap = {
  bgPage: '#f4f7ff',
  bgSurface: '#ffffff',
  bgElevated: '#eef3ff',
  textPrimary: '#192238',
  textSecondary: '#4c5874',
  textTertiary: '#75829f',
  borderDefault: '#dbe3f3',
  brandPrimary: '#2c6bff',
  brandPrimaryHover: '#2356cc',
  brandSoft: '#dbe6ff',
  success: '#0f9d58',
  warning: '#f29900',
  error: '#e53935',
  info: '#1473e6',
}

export const applyThemeCssVariables = (target: HTMLElement | null = typeof document !== 'undefined' ? document.documentElement : null) => {
  if (!target) return

  const semanticVars: Record<keyof ThemeSemanticMap, string> = {
    bgPage: '--ds-bg-page',
    bgSurface: '--ds-bg-surface',
    bgElevated: '--ds-bg-elevated',
    textPrimary: '--ds-text-primary',
    textSecondary: '--ds-text-secondary',
    textTertiary: '--ds-text-tertiary',
    borderDefault: '--ds-border',
    brandPrimary: '--ds-brand',
    brandPrimaryHover: '--ds-brand-hover',
    brandSoft: '--ds-brand-soft',
    success: '--ds-success',
    warning: '--ds-warning',
    error: '--ds-error',
    info: '--ds-info',
  }

  const tokenVars: Record<keyof ThemeTokens, string> = {
    fontFamily: '--ds-font-family',
    radiusSm: '--ds-radius-sm',
    radiusMd: '--ds-radius-md',
    radiusLg: '--ds-radius-lg',
    radiusXl: '--ds-radius-xl',
    shadowSm: '--ds-shadow-sm',
    shadowMd: '--ds-shadow-md',
    shadowLg: '--ds-shadow-lg',
    durationFast: '--ds-duration-fast',
    durationBase: '--ds-duration-base',
    durationSlow: '--ds-duration-slow',
    easeStandard: '--ds-ease-standard',
    easeEmphasized: '--ds-ease-emphasized',
  }

  ;(Object.keys(semanticVars) as (keyof ThemeSemanticMap)[]).forEach((key) => {
    target.style.setProperty(semanticVars[key], semanticMap[key])
  })

  ;(Object.keys(tokenVars) as (keyof ThemeTokens)[]).forEach((key) => {
    target.style.setProperty(tokenVars[key], themeTokens[key])
  })
}

export const buildNaiveThemeOverrides = (): GlobalThemeOverrides => ({
  common: {
    primaryColor: semanticMap.brandPrimary,
    primaryColorHover: semanticMap.brandPrimaryHover,
    primaryColorPressed: '#1d49ae',
    primaryColorSuppl: semanticMap.brandPrimaryHover,
    infoColor: semanticMap.info,
    successColor: semanticMap.success,
    warningColor: semanticMap.warning,
    errorColor: semanticMap.error,
    textColorBase: semanticMap.textPrimary,
    textColor1: semanticMap.textPrimary,
    textColor2: semanticMap.textSecondary,
    textColor3: semanticMap.textTertiary,
    bodyColor: semanticMap.bgPage,
    cardColor: semanticMap.bgSurface,
    modalColor: semanticMap.bgSurface,
    popoverColor: semanticMap.bgSurface,
    borderColor: semanticMap.borderDefault,
    tableColor: semanticMap.bgSurface,
    fontFamily: themeTokens.fontFamily,
    borderRadius: themeTokens.radiusMd,
    borderRadiusSmall: themeTokens.radiusSm,
  },
  Button: {
    borderRadiusTiny: themeTokens.radiusSm,
    borderRadiusSmall: themeTokens.radiusSm,
    borderRadiusMedium: themeTokens.radiusMd,
    borderRadiusLarge: themeTokens.radiusMd,
    boxShadowHoverPrimary: themeTokens.shadowSm,
    boxShadowPressedPrimary: themeTokens.shadowSm,
  },
  Card: {
    borderRadius: themeTokens.radiusLg,
    borderColor: semanticMap.borderDefault,
    color: semanticMap.bgSurface,
    boxShadow: themeTokens.shadowSm,
  },
  Input: {
    borderRadius: themeTokens.radiusMd,
    color: semanticMap.bgSurface,
    colorFocus: semanticMap.bgSurface,
    colorFocusError: semanticMap.bgSurface,
  },
  Drawer: {
    color: semanticMap.bgSurface,
  },
  Modal: {
    borderRadius: themeTokens.radiusLg,
  },
  DataTable: {
    thColor: semanticMap.bgElevated,
    tdColor: semanticMap.bgSurface,
    borderColor: semanticMap.borderDefault,
  },
  Scrollbar: {
    color: '#c6d2f0',
    colorHover: '#a8b9e8',
  },
})
