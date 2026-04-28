export const formatMoney = (value: string | number): string => {
  const amount = typeof value === 'string' ? Number(value) : value;
  return new Intl.NumberFormat('ru-RU', {
    style: 'currency',
    currency: 'RUB',
    maximumFractionDigits: 0,
  }).format(Number.isNaN(amount) ? 0 : amount);
};

export const formatNumber = (value: string | number, digits = 2): string => {
  const amount = typeof value === 'string' ? Number(value) : value;
  return new Intl.NumberFormat('ru-RU', {
    maximumFractionDigits: digits,
    minimumFractionDigits: 0,
  }).format(Number.isNaN(amount) ? 0 : amount);
};
