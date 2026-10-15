import React, { Component } from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.jsx'
import './styles/global.css'

class ErrorBoundary extends Component {
  constructor(props) {
    super(props)
    this.state = { hasError: false, error: null }
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error }
  }

  componentDidCatch(error, errorInfo) {
    console.error('UI Render Error caught by ErrorBoundary:', error, errorInfo)
  }

  render() {
    if (this.state.hasError) {
      return (
        <div style={{
          padding: '32px',
          margin: '32px auto',
          maxWidth: '800px',
          background: '#1a1012',
          border: '1px solid #ff1744',
          borderRadius: '8px',
          color: '#ffcdd2',
          fontFamily: 'Inter, sans-serif'
        }}>
          <h2 style={{ color: '#ff1744', margin: '0 0 16px' }}>Dashboard Render Exception</h2>
          <pre style={{
            background: '#07080e',
            padding: '16px',
            borderRadius: '4px',
            overflowX: 'auto',
            color: '#ff8a80',
            fontFamily: 'monospace'
          }}>
            {String(this.state.error?.stack || this.state.error)}
          </pre>
          <button
            onClick={() => window.location.reload()}
            style={{
              marginTop: '16px',
              padding: '8px 16px',
              background: '#ff1744',
              color: '#ffffff',
              border: 'none',
              borderRadius: '4px',
              cursor: 'pointer',
              fontWeight: '600'
            }}
          >
            Reload Dashboard
          </button>
        </div>
      )
    }
    return this.props.children
  }
}

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <ErrorBoundary>
      <App />
    </ErrorBoundary>
  </React.StrictMode>
)
