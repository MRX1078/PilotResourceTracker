import { useMemo, useState } from 'react';
import dayjs, { Dayjs } from 'dayjs';

import { weekStartOf } from '../utils/date';

export const useWeekState = (initial?: string) => {
  const [weekDate, setWeekDate] = useState<Dayjs>(initial ? dayjs(initial) : weekStartOf(dayjs()));

  const weekStart = useMemo(() => weekStartOf(weekDate), [weekDate]);

  return {
    weekDate,
    setWeekDate,
    weekStart,
  };
};
