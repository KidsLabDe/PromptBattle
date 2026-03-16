export type WSHandler = (msg: { type: string; data: Record<string, unknown> }) => void;

export class GameWebSocket {
	private ws: WebSocket | null = null;
	private handler: WSHandler;

	constructor(handler: WSHandler) {
		this.handler = handler;
	}

	connect(gameId: string): void {
		const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
		const url = `${protocol}//${location.host}/ws/${gameId}`;
		this._open(url);
	}

	connectPlayer(gameId: string, token: string): void {
		const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
		const url = `${protocol}//${location.host}/ws/${gameId}/player/${token}`;
		this._open(url);
	}

	private _open(url: string): void {
		this.ws = new WebSocket(url);

		this.ws.onopen = () => {
			console.log('WebSocket connected:', url);
			this.handler({ type: '_ws_open', data: { url } });
		};

		this.ws.onmessage = (event) => {
			const msg = JSON.parse(event.data);
			this.handler(msg);
		};

		this.ws.onerror = (event) => {
			console.error('WebSocket error:', event);
			this.handler({ type: 'error', data: { message: 'Verbindungsfehler' } });
		};

		this.ws.onclose = (event) => {
			console.log('WebSocket closed:', event.code, event.reason);
			this.handler({ type: '_ws_close', data: { code: event.code, reason: event.reason || '' } });
			if (event.code >= 4000) {
				this.handler({ type: 'error', data: { message: event.reason || 'Verbindung abgelehnt' } });
			}
			this.ws = null;
		};
	}

	send(type: string, data: Record<string, unknown> = {}): void {
		if (this.ws?.readyState === WebSocket.OPEN) {
			this.ws.send(JSON.stringify({ type, data }));
		}
	}

	close(): void {
		this.ws?.close();
		this.ws = null;
	}
}
