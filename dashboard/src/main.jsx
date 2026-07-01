import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './theme.css'
import App from './App'
// index.css removed — variables conflicted with theme.css

createRoot(document.getElementById('root')).render(
  <StrictMode><App /></StrictMode>
)
