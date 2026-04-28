import 'antd/dist/reset.css';
import './styles.css';

import { App as AntdApp, ConfigProvider, theme } from 'antd';
import dayjs from 'dayjs';
import isoWeek from 'dayjs/plugin/isoWeek';
import localeData from 'dayjs/plugin/localeData';
import weekOfYear from 'dayjs/plugin/weekOfYear';
import weekday from 'dayjs/plugin/weekday';
import { createRoot } from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';

import { App } from './App';

dayjs.extend(isoWeek);
dayjs.extend(weekOfYear);
dayjs.extend(weekday);
dayjs.extend(localeData);

createRoot(document.getElementById('root')!).render(
  <ConfigProvider
    theme={{
      algorithm: theme.defaultAlgorithm,
      token: {
        colorPrimary: '#0f766e',
        colorInfo: '#0f766e',
        borderRadius: 10,
        fontFamily: '"Manrope", "Segoe UI", sans-serif',
      },
    }}
  >
    <AntdApp>
      <BrowserRouter>
        <App />
      </BrowserRouter>
    </AntdApp>
  </ConfigProvider>
);
