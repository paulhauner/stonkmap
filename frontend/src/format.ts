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

export function formatRelativeAge(value: string | null, now = new Date()) {
  if (!value) {
    return null;
  }

  const timestamp = new Date(value);
  const diffMs = Math.max(0, now.getTime() - timestamp.getTime());
  const minuteMs = 60 * 1000;
  const hourMs = 60 * minuteMs;
  const dayMs = 24 * hourMs;

  if (diffMs < minuteMs) {
    return 'less than a minute';
  }

  if (diffMs < hourMs) {
    const minutes = Math.floor(diffMs / minuteMs);
    return `${minutes} minute${minutes === 1 ? '' : 's'}`;
  }

  if (diffMs < dayMs) {
    const hours = Math.floor(diffMs / hourMs);
    return `${hours} hour${hours === 1 ? '' : 's'}`;
  }

  const days = Math.floor(diffMs / dayMs);
  return `${days} day${days === 1 ? '' : 's'}`;
}
