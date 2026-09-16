// Fixed categorical slots (see dataviz skill palette.md) - assign by compound
// identity, never by rank, and never reorder across charts.
export const COMPOUND_COLOR_ORDER = ['PFOA', 'PFOS', 'PFHxS'] as const

const CATEGORICAL_LIGHT = ['#2a78d6', '#eb6834', '#1baf7a'] // blue, orange, aqua
const CATEGORICAL_DARK = ['#3987e5', '#d95926', '#199e70']

export function compoundColor(compound: string, dark = false): string {
  const idx = COMPOUND_COLOR_ORDER.indexOf(compound as (typeof COMPOUND_COLOR_ORDER)[number])
  const palette = dark ? CATEGORICAL_DARK : CATEGORICAL_LIGHT
  return idx >= 0 ? palette[idx] : (dark ? CATEGORICAL_DARK : CATEGORICAL_LIGHT)[3 % palette.length]
}

// Slots 4-7 of the same palette (deliberately distinct from the compound
// colors above, since these two categorical dimensions could appear near
// each other in the UI): yellow, magenta, green, violet.
export const REGWATCH_CATEGORY_ORDER = ['Regulation', 'Litigation', 'Science', 'Industry'] as const

const CATEGORY_LIGHT = ['#eda100', '#e87ba4', '#008300', '#4a3aa7']
const CATEGORY_DARK = ['#c98500', '#d55181', '#008300', '#9085e9']

export function categoryColor(category: string, dark = false): string {
  const idx = REGWATCH_CATEGORY_ORDER.indexOf(category as (typeof REGWATCH_CATEGORY_ORDER)[number])
  const palette = dark ? CATEGORY_DARK : CATEGORY_LIGHT
  return idx >= 0 ? palette[idx] : palette[0]
}

export const STATUS_COLORS = {
  good: '#0ca30c',
  warning: '#fab219',
  serious: '#ec835a',
  critical: '#d03b3b',
}

// Chart chrome & ink (palette.md "Chart chrome & ink" table) - light/dark pairs.
// Legend/tooltip TEXT must always use these ink tokens, never a series color
// (marks-and-anatomy.md: "text never wears the data color").
const CHART_CHROME = {
  light: { gridline: '#e1e0d9', axis: '#c3c2b7', mutedText: '#898781', primaryText: '#0b0b0b', secondaryText: '#52514e' },
  dark: { gridline: '#2c2c2a', axis: '#383835', mutedText: '#898781', primaryText: '#ffffff', secondaryText: '#c3c2b7' },
}

export function chartInk(dark: boolean) {
  return dark ? CHART_CHROME.dark : CHART_CHROME.light
}
