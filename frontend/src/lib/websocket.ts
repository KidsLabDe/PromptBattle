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

		this.ws.onmessage = (event) => {
			const msg = JSON.parse(event.data);
			this.handler(msg);
		};

		this.ws.onclose = () => {
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
