// src/index.js
import React from 'react';
import ReactDOM from 'react-dom/client';
import './index.css';
import App from './App';
import reportWebVitals from './reportWebVitals';

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);

// Optional: Log environment configuration in development
if (process.env.NODE_ENV === 'development') {
  console.log('Recipe Genie Frontend Configuration:');
  console.log('API URL:', process.env.REACT_APP_API_URL || 'http://localhost:8080');
  console.log('Port:', process.env.PORT || '3000');
}
reportWebVitals();
