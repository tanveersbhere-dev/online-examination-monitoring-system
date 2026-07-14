export class WebSocketClient {
  private ws: WebSocket | null = null;
  private url: string;
  private onMessageCallback: ((data: any) => void) | null = null;
  private pingInterval: ReturnType<typeof setInterval> | null = null;

  constructor(examSessionId: number) {
    const token = localStorage.getItem('access_token');
    const baseUrl = import.meta.env.VITE_WS_BASE_URL || 'ws://localhost:8000/api/v1/ws';
    this.url = `${baseUrl}/${examSessionId}?token=${token}`;
  }

  connect() {
    this.ws = new WebSocket(this.url);

    this.ws.onopen = () => {
      console.log(`WebSocket connected to ${this.url}`);
      // Start pinging to keep connection alive
      this.pingInterval = setInterval(() => {
        if (this.ws?.readyState === WebSocket.OPEN) {
          this.ws.send('ping');
        }
      }, 30000); // 30 seconds
    };

    this.ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.event !== 'HEARTBEAT') {
          console.log('WS Event Received:', data);
        }
        if (this.onMessageCallback) {
          this.onMessageCallback(data);
        }
      } catch (err) {
        console.error('Failed to parse WS message:', event.data);
      }
    };

    this.ws.onclose = (event) => {
      console.log('WebSocket closed:', event.code, event.reason);
      this.cleanup();
    };

    this.ws.onerror = (error) => {
      console.error('WebSocket error:', error);
    };
  }

  onMessage(callback: (data: any) => void) {
    this.onMessageCallback = callback;
  }

  disconnect() {
    if (this.ws) {
      this.ws.close();
    }
    this.cleanup();
  }

  private cleanup() {
    if (this.pingInterval) {
      clearInterval(this.pingInterval);
      this.pingInterval = null;
    }
    this.ws = null;
  }
}
