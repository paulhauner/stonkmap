export function formatMoney(value: string | number | null) {
  if (value === null) {
    return 'Unavailable';
  }
  return new Intl.NumberFormat('en-AU', {
    style: 'currency',
    currency: 'AUD',
    maximumFractionDigits: 2,
  }).format(Number(value));
}

export function formatPercent(value: string | number | null) {
  if (value === null) {
    return 'Unavailable';
  }
  return `${Number(value).toFixed(2)}%`;
}

export function formatDateTime(value: string | null) {
  if (!value) {
    return 'Not refreshed yet';
  }
  return new Intl.DateTimeFormat('en-AU', {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(new Date(value));
}
