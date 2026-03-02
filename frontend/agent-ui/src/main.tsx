import { ConfigProvider, theme } from 'antd';
import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
import './index.css';

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <ConfigProvider
      theme={{
        algorithm: theme.darkAlgorithm,
        token: {
          colorPrimary: '#52c41a',
          borderRadius: 8,
          colorBgBase: '#0d1117',
        },
      }}
    >
      <App />
    </ConfigProvider>
  </React.StrictMode>
);
