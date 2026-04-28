import dayjs, { Dayjs } from 'dayjs';

export const toIsoDate = (value: Dayjs | string): string =>
  (typeof value === 'string' ? dayjs(value) : value).format('YYYY-MM-DD');

export const weekStartOf = (value: Dayjs = dayjs()): Dayjs => {
  const day = value.day();
  const shift = day === 0 ? 6 : day - 1;
  return value.subtract(shift, 'day').startOf('day');
};

export const formatDate = (value: string): string => dayjs(value).format('DD.MM.YYYY');
