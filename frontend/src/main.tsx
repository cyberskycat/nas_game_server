import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'
import './index.css'
import { ConfigProvider, theme } from 'antd'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <ConfigProvider
      theme={{
        algorithm: theme.darkAlgorithm,
        token: {
          colorPrimary: '#1890ff',
          borderRadius: 8,
          colorBgBase: '#0d1117',
          colorTextBase: 'rgba(255, 255, 255, 0.85)',
        },
      }}
    >
      <App />
    </ConfigProvider>
  </React.StrictMode>,
)
