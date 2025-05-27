import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.jsx'
import './index.css'

// Add global styles for enhanced UI
const globalStyles = `
  /* Custom scrollbar styles */
  ::-webkit-scrollbar {
    width: 8px;
    height: 8px;
  }

  ::-webkit-scrollbar-track {
    background: #f1f5f9;
    border-radius: 4px;
  }

  ::-webkit-scrollbar-thumb {
    background: #cbd5e1;
    border-radius: 4px;
  }

  ::-webkit-scrollbar-thumb:hover {
    background: #94a3b8;
  }

  /* Line clamp utility */
  .line-clamp-2 {
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
  }

  .line-clamp-3 {
    display: -webkit-box;
    -webkit-line-clamp: 3;
    -webkit-box-orient: vertical;
    overflow: hidden;
  }

  /* Enhanced transitions */
  .transition-all {
    transition-property: all;
    transition-timing-function: cubic-bezier(0.4, 0, 0.2, 1);
    transition-duration: 150ms;
  }

  /* Custom animations */
  @keyframes fadeIn {
    from {
      opacity: 0;
      transform: translateY(10px);
    }
    to {
      opacity: 1;
      transform: translateY(0);
    }
  }

  .animate-fadeIn {
    animation: fadeIn 0.3s ease-out;
  }

  @keyframes pulse {
    0%, 100% {
      opacity: 1;
    }
    50% {
      opacity: 0.5;
    }
  }

  .animate-pulse {
    animation: pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;
  }

  /* Enhanced button styles */
  .btn-primary {
    @apply bg-blue-600 text-white px-4 py-2 rounded-lg font-medium hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 transition-colors disabled:bg-gray-400 disabled:cursor-not-allowed;
  }

  .btn-secondary {
    @apply bg-gray-100 text-gray-700 px-4 py-2 rounded-lg font-medium hover:bg-gray-200 focus:outline-none focus:ring-2 focus:ring-gray-500 focus:ring-offset-2 transition-colors;
  }

  .btn-success {
    @apply bg-green-600 text-white px-4 py-2 rounded-lg font-medium hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-green-500 focus:ring-offset-2 transition-colors;
  }

  /* Card styles */
  .card {
    @apply bg-white rounded-xl shadow-lg border border-gray-200 overflow-hidden;
  }

  .card-header {
    @apply p-6 border-b border-gray-200 bg-gray-50;
  }

  .card-body {
    @apply p-6;
  }

  /* Form styles */
  .form-input {
    @apply block w-full px-3 py-2 border border-gray-300 rounded-lg shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors;
  }

  .form-label {
    @apply block text-sm font-medium text-gray-700 mb-2;
  }

  .form-error {
    @apply text-sm text-red-600 mt-1;
  }

  /* Alert styles */
  .alert {
    @apply p-4 rounded-lg border-l-4;
  }

  .alert-info {
    @apply bg-blue-50 border-blue-400 text-blue-700;
  }

  .alert-success {
    @apply bg-green-50 border-green-400 text-green-700;
  }

  .alert-warning {
    @apply bg-yellow-50 border-yellow-400 text-yellow-700;
  }

  .alert-error {
    @apply bg-red-50 border-red-400 text-red-700;
  }

  /* Loading spinner */
  .spinner {
    @apply inline-block w-4 h-4 border-2 border-current border-t-transparent rounded-full animate-spin;
  }

  /* Tooltip styles for Cytoscape */
  .qtip-bootstrap {
    background: #333;
    color: white;
    border-radius: 6px;
    font-size: 12px;
    padding: 8px 12px;
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    max-width: 200px;
    word-wrap: break-word;
  }

  .qtip-bootstrap .qtip-tip {
    border-color: #333;
  }

  /* Enhanced graph container */
  .graph-container {
    position: relative;
    background: linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%);
    border-radius: 12px;
    overflow: hidden;
    box-shadow: inset 0 2px 4px 0 rgba(0, 0, 0, 0.06);
  }

  /* Custom file input styling */
  .file-input-wrapper {
    position: relative;
    overflow: hidden;
    display: inline-block;
    cursor: pointer;
  }

  .file-input-wrapper input[type=file] {
    position: absolute;
    left: -9999px;
  }

  .file-input-label {
    @apply inline-flex items-center px-4 py-2 bg-white border border-gray-300 rounded-lg shadow-sm text-sm font-medium text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 cursor-pointer transition-colors;
  }

  /* Progress bar */
  .progress-bar {
    @apply w-full bg-gray-200 rounded-full h-2 overflow-hidden;
  }

  .progress-bar-fill {
    @apply h-full bg-blue-600 transition-all duration-300 ease-out;
  }

  /* Badge styles */
  .badge {
    @apply inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium;
  }

  .badge-blue {
    @apply bg-blue-100 text-blue-800;
  }

  .badge-green {
    @apply bg-green-100 text-green-800;
  }

  .badge-yellow {
    @apply bg-yellow-100 text-yellow-800;
  }

  .badge-red {
    @apply bg-red-100 text-red-800;
  }

  .badge-gray {
    @apply bg-gray-100 text-gray-800;
  }

  /* Responsive utilities */
  @media (max-width: 640px) {
    .container {
      padding-left: 1rem;
      padding-right: 1rem;
    }
    
    .card {
      margin-left: -0.5rem;
      margin-right: -0.5rem;
      border-radius: 0.5rem;
    }
    
    .graph-container {
      height: 300px !important;
    }
  }

  /* Dark mode support (optional) */
  @media (prefers-color-scheme: dark) {
    .dark-mode {
      @apply bg-gray-900 text-white;
    }
    
    .dark-mode .card {
      @apply bg-gray-800 border-gray-700;
    }
    
    .dark-mode .form-input {
      @apply bg-gray-700 border-gray-600 text-white;
    }
  }

  /* Print styles */
  @media print {
    .no-print {
      display: none !important;
    }
    
    .print-full-width {
      width: 100% !important;
      max-width: none !important;
    }
  }

  /* Accessibility improvements */
  .sr-only {
    position: absolute;
    width: 1px;
    height: 1px;
    padding: 0;
    margin: -1px;
    overflow: hidden;
    clip: rect(0, 0, 0, 0);
    white-space: nowrap;
    border: 0;
  }

  /* Focus styles for better accessibility */
  .focus-visible:focus {
    outline: 2px solid #3b82f6;
    outline-offset: 2px;
  }

  /* High contrast mode support */
  @media (prefers-contrast: high) {
    .high-contrast {
      border-width: 2px;
      border-color: currentColor;
    }
  }

  /* Reduced motion support */
  @media (prefers-reduced-motion: reduce) {
    .animate-spin {
      animation: none;
    }
    
    .transition-all,
    .transition-colors,
    .transition-transform {
      transition: none;
    }
  }
`;

// Inject global styles
const styleSheet = document.createElement('style');
styleSheet.textContent = globalStyles;
document.head.appendChild(styleSheet);

// Enhanced error boundary component
class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null, errorInfo: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true };
  }

  componentDidCatch(error, errorInfo) {
    this.setState({
      error: error,
      errorInfo: errorInfo
    });
    
    // Log error to console in development
    if (import.meta.env.DEV) {
      console.error('Error caught by boundary:', error, errorInfo);
    }
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
          <div className="max-w-md w-full bg-white rounded-lg shadow-lg p-6 text-center">
            <div className="w-16 h-16 mx-auto mb-4 bg-red-100 rounded-full flex items-center justify-center">
              <svg className="w-8 h-8 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.732 16.5c-.77.833.192 2.5 1.732 2.5z" />
              </svg>
            </div>
            <h2 className="text-xl font-semibold text-gray-900 mb-2">Something went wrong</h2>
            <p className="text-gray-600 mb-4">
              The application encountered an unexpected error. Please refresh the page to try again.
            </p>
            <div className="space-y-2">
              <button
                onClick={() => window.location.reload()}
                className="w-full btn-primary"
              >
                Refresh Page
              </button>
              {import.meta.env.DEV && (
                <details className="text-left">
                  <summary className="cursor-pointer text-sm text-gray-500 hover:text-gray-700">
                    Show Error Details
                  </summary>
                  <div className="mt-2 p-3 bg-gray-100 rounded text-xs font-mono text-gray-700 overflow-auto max-h-32">
                    <div className="font-semibold mb-1">Error:</div>
                    <div className="mb-2">{this.state.error && this.state.error.toString()}</div>
                    <div className="font-semibold mb-1">Stack Trace:</div>
                    <div>{this.state.errorInfo.componentStack}</div>
                  </div>
                </details>
              )}
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

// Performance monitoring (optional)
if (import.meta.env.PROD) {
  // Add performance monitoring for production
  window.addEventListener('load', () => {
    if ('performance' in window) {
      const perfData = performance.getEntriesByType('navigation')[0];
      console.log('Page load time:', perfData.loadEventEnd - perfData.loadEventStart, 'ms');
    }
  });
}

// Service worker registration (optional)
if ('serviceWorker' in navigator && import.meta.env.PROD) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/sw.js')
      .then((registration) => {
        console.log('SW registered: ', registration);
      })
      .catch((registrationError) => {
        console.log('SW registration failed: ', registrationError);
      });
  });
}

// Initialize React application
ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <ErrorBoundary>
      <App />
    </ErrorBoundary>
  </React.StrictMode>,
);