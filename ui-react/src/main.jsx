import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { Toaster } from 'react-hot-toast'
import './index.css'
import App from './App.jsx'

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <App />
    <Toaster 
      position="top-right" 
      toastOptions={{
        duration: 6000,
        error: {
          duration: 6000,
          style: {
            background: '#dc2626',
            color: '#fff',
            fontWeight: '500',
          },
        },
        success: {
          duration: 4000,
        },
      }} 
    />
  </StrictMode>,
)
