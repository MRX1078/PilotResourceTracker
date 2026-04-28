import { DatePicker, Space, Typography } from 'antd';
import type { Dayjs } from 'dayjs';
import { weekStartOf } from '../utils/date';

interface WeekPickerProps {
  value: Dayjs;
  onChange: (next: Dayjs) => void;
  label?: string;
}

export const WeekPicker = ({ value, onChange, label = 'Неделя' }: WeekPickerProps) => {
  return (
    <Space>
      <Typography.Text type="secondary">{label}</Typography.Text>
      <DatePicker
        picker="week"
        value={value}
        onChange={(next) => {
          if (next) onChange(weekStartOf(next));
        }}
        format="YYYY-[W]WW"
        allowClear={false}
      />
    </Space>
  );
};
