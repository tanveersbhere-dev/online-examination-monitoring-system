/**
 * API and WebSocket URL Configuration
 */
export const API_BASE = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
  ? 'http://localhost:8000'
  : `${window.location.protocol}//${window.location.host}`;

export const WS_BASE = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
  ? 'ws://localhost:8000'
  : `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}`;

export const WS_URL = `${WS_BASE}/ws/monitor`;

export const getAuthImageUrl = (path: string | null | undefined): string => {
  if (!path) return '';
  if (path.startsWith('data:')) return path;
  const token = localStorage.getItem('access_token') || localStorage.getItem('token') || '';
  const tokenQuery = token ? `?token=${encodeURIComponent(token)}` : '';
  if (path.startsWith('http://') || path.startsWith('https://')) {
    if (token && !path.includes('token=')) {
      return path.includes('?') ? `${path}&token=${encodeURIComponent(token)}` : `${path}${tokenQuery}`;
    }
    return path;
  }
  const clean = path.replace(/\\/g, '/').replace(/^\/+/, '');
  return `${API_BASE}/${clean}${tokenQuery}`;
};

export const getAuthVideoUrl = (path: string | null | undefined): string => {
  return getAuthImageUrl(path);
};

