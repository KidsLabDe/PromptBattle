<script lang="ts">
	import { onDestroy } from 'svelte';
	import { GameWebSocket } from '$lib/websocket';
	import { browser } from '$app/environment';

	let playerNum = $state(0);
	let status = $state<'connecting' | 'waiting' | 'playing' | 'submitted' | 'generating' | 'result' | 'gameover'>('connecting');
	let prompt = $state('');
	let timeRemaining = $state(60);
	let round = $state(1);
	let myScore = $state(0);
	let opponentScore = $state(0);
	let myThreshold = $state(0);
	let myPassed = $state(false);
	let isSingleViaPhone = $state(false);
	let winner = $state(0);
	let errorMsg = $state('');
	let urgent = $derived(timeRemaining <= 10);

	let formattedTime = $derived(() => {
		const m = Math.floor(timeRemaining / 60);
		const s = timeRemaining % 60;
		return `${m}:${s.toString().padStart(2, '0')}`;
	});

	let ws: GameWebSocket | null = null;

	function handleMessage(msg: { type: string; data: Record<string, unknown> }) {
		switch (msg.type) {
			case 'connected':
				playerNum = msg.data.player as number;
				round = msg.data.round as number;
				status = 'waiting';
				break;
			case 'timer_tick':
				timeRemaining = msg.data.remaining as number;
				break;
			case 'prompt_accepted':
				status = 'submitted';
				break;
			case 'generation_start':
				status = 'generating';
				break;
			case 'generation_progress':
				// Just keep showing generating status
				break;
			case 'player_result':
				// Delay showing result on phone so it syncs with main screen comparing animation
				{
					const score = msg.data.score as number;
					const rnd = msg.data.round as number;
					const hasThreshold = msg.data.threshold !== undefined;
					const thresh = msg.data.threshold as number;
					const pass = msg.data.passed as boolean;
					const oppScore = msg.data.opponent_score as number;
					const win = msg.data.winner as number;
					setTimeout(() => {
						myScore = score;
						round = rnd;
						if (hasThreshold) {
							isSingleViaPhone = true;
							myThreshold = thresh;
							myPassed = pass;
						} else {
							opponentScore = oppScore;
							winner = win;
						}
						status = 'result';
					}, 7000); // ~4s comparing + ~2.5s score reveal on main screen
				}
				break;
			case 'round_start':
				round = msg.data.round as number;
				timeRemaining = msg.data.time_seconds as number;
				prompt = '';
				status = 'playing';
				break;
			case 'time_up':
				if (status === 'playing') {
					if (prompt.trim() && ws) {
						ws.send('submit_prompt', { prompt: prompt.trim() });
					}
					status = 'submitted';
				}
				break;
			case 'game_over':
				status = 'gameover';
				break;
			case 'error':
				errorMsg = msg.data.message as string;
				setTimeout(() => errorMsg = '', 3000);
				break;
		}
	}

	let retryCount = 0;
	const MAX_RETRIES = 5;

	function connectWs() {
		const pathname = window.location.pathname;
		const match = pathname.match(/\/play\/([^/]+)\/([^/]+)/);
		if (!match) return;

		ws = new GameWebSocket((msg) => {
			if (msg.type === '_ws_open') {
				retryCount = 0;
				errorMsg = '';
			} else if (msg.type === '_ws_close') {
				ws = null;
				// Auto-reconnect if not a rejection (4xxx) and game not over
				if ((msg.data.code as number) < 4000 && status !== 'gameover' && retryCount < MAX_RETRIES) {
					retryCount++;
					errorMsg = `Verbindung verloren. Reconnect ${retryCount}/${MAX_RETRIES}...`;
					setTimeout(() => connectWs(), 1000 * retryCount);
				} else if (retryCount >= MAX_RETRIES) {
					errorMsg = 'Verbindung fehlgeschlagen. Bitte Seite neu laden.';
				}
			} else {
				handleMessage(msg);
			}
		});
		ws.connectPlayer(match[1], match[2]);
	}

	// Connect WebSocket - use $effect to ensure it runs in browser
	$effect(() => {
		if (browser && !ws && status === 'connecting') {
			connectWs();
		}
	});

	let typingTimer: ReturnType<typeof setTimeout> | null = null;

	function handleInput() {
		// Debounced typing broadcast so audience can see live input
		if (typingTimer) clearTimeout(typingTimer);
		typingTimer = setTimeout(() => {
			ws?.send('typing', { text: prompt });
		}, 150);
	}

	function submitPrompt() {
		if (prompt.trim() && ws) {
			ws.send('submit_prompt', { prompt: prompt.trim() });
		}
	}

	function handleKeydown(e: KeyboardEvent) {
		if (e.key === 'Enter' && !e.shiftKey) {
			e.preventDefault();
			submitPrompt();
		}
	}

	onDestroy(() => {
		ws?.close();
	});

	let playerColor = $derived(playerNum === 1 ? 'text-neon-pink' : 'text-neon-blue');
	let iWon = $derived(winner === playerNum);
	let isDraw = $derived(winner === 0);
</script>

<svelte:head>
	<title>Prompt Battle - Spieler {playerNum}</title>
	<meta name="viewport" content="width=device-width, initial-scale=1" />
</svelte:head>

<div class="flex min-h-screen flex-col bg-bg-dark p-4 text-white">
	{#if status === 'connecting'}
		<div class="flex flex-1 flex-col items-center justify-center gap-4">
			<div class="text-center">
				<div class="mx-auto mb-4 h-12 w-12 animate-spin rounded-full border-4 border-neon-blue/30 border-t-neon-blue"></div>
				<p class="text-gray-400">Verbinde...</p>
				{#if retryCount > 0}
					<p class="mt-2 text-sm text-neon-yellow">Versuch {retryCount}/{MAX_RETRIES}</p>
				{/if}
			</div>
		</div>

	{:else if status === 'waiting'}
		<div class="flex flex-1 flex-col items-center justify-center gap-6">
			<h1 class="font-pixel text-5xl tracking-tight">
				<span class="text-neon-pink">PROMPT</span>
				<span class="text-neon-blue">BATTLE</span>
			</h1>
			<p class="font-pixel text-2xl text-neon-green">Spieler {playerNum}</p>
			<div class="mx-auto h-12 w-12 animate-spin rounded-full border-4 border-neon-yellow/30 border-t-neon-yellow"></div>
			<p class="text-xl text-gray-400">Warte auf Spielbeginn...</p>
		</div>

	{:else if status === 'playing'}
		<div class="flex flex-1 flex-col gap-6">
			<!-- Header -->
			<div class="flex items-center justify-between">
				<span class="text-lg font-bold {playerColor}">Spieler {playerNum}</span>
				<span class="rounded-lg bg-bg-card px-3 py-1 text-sm font-bold">Runde {round}</span>
			</div>

			<!-- Timer -->
			<div class="text-center">
				<span
					class="font-pixel text-5xl"
					class:text-neon-green={!urgent}
					class:text-red-500={urgent}
					class:animate-pulse={urgent}
				>
					{formattedTime()}
				</span>
			</div>

			<!-- Prompt input -->
			<div class="mt-auto flex flex-col gap-3">
				<textarea
					bind:value={prompt}
					onkeydown={handleKeydown}
					oninput={handleInput}
					placeholder="Beschreibe das Zielbild..."
					rows="4"
					class="w-full rounded-xl border-2 border-neon-blue/30 bg-bg-card p-4 text-lg text-white
						placeholder-gray-500 focus:border-neon-blue focus:outline-none"
				></textarea>
				<button
					onclick={submitPrompt}
					disabled={!prompt.trim()}
					class="w-full cursor-pointer rounded-xl bg-neon-blue px-6 py-4 text-xl font-bold
						text-black transition-all duration-200
						hover:bg-neon-blue/80
						disabled:cursor-not-allowed disabled:opacity-50"
				>
					Absenden
				</button>
			</div>
		</div>

	{:else if status === 'submitted'}
		<div class="flex flex-1 flex-col items-center justify-center gap-4">
			<div class="text-6xl">&#x2714;</div>
			<p class="text-xl font-bold {playerColor}">Prompt gesendet!</p>
			<p class="text-gray-400">Warte auf Gegner...</p>
		</div>

	{:else if status === 'generating'}
		<div class="flex flex-1 flex-col items-center justify-center gap-4">
			<div class="h-16 w-16 animate-spin rounded-full border-4 border-neon-green/30 border-t-neon-green"></div>
			<p class="text-xl font-bold text-neon-green">Bilder werden generiert...</p>
			<p class="text-gray-400">Schau auf den Hauptbildschirm!</p>
		</div>

	{:else if status === 'result'}
		<div class="flex flex-1 flex-col items-center justify-center gap-6">
			{#if isSingleViaPhone}
				{#if myPassed}
					<h2 class="text-5xl font-black text-neon-green">GESCHAFFT!</h2>
				{:else}
					<h2 class="text-5xl font-black text-red-500">NICHT GESCHAFFT</h2>
				{/if}

				<div class="text-center">
					<p class="text-sm text-gray-400">Dein Score</p>
					<p class="text-4xl font-bold" class:text-neon-green={myPassed} class:text-red-500={!myPassed}>
						{myScore.toFixed(1)}%
					</p>
					<p class="mt-2 text-sm text-gray-500">Mindestscore: {myThreshold}%</p>
				</div>

				{#if myPassed}
					<p class="text-gray-400">Warte auf nächste Runde...</p>
				{:else}
					<p class="text-gray-400">Spiel vorbei!</p>
				{/if}
			{:else}
				{#if iWon}
					<h2 class="text-5xl font-black text-neon-green">GEWONNEN!</h2>
				{:else if isDraw}
					<h2 class="text-5xl font-black text-neon-yellow">UNENTSCHIEDEN</h2>
				{:else}
					<h2 class="text-5xl font-black text-red-500">VERLOREN</h2>
				{/if}

				<div class="flex gap-8 text-center">
					<div>
						<p class="text-sm text-gray-400">Dein Score</p>
						<p class="text-3xl font-bold" class:text-neon-green={iWon} class:text-red-500={!iWon && !isDraw} class:text-neon-yellow={isDraw}>
							{myScore.toFixed(1)}%
						</p>
					</div>
					<div>
						<p class="text-sm text-gray-400">Gegner</p>
						<p class="text-3xl font-bold text-gray-400">{opponentScore.toFixed(1)}%</p>
					</div>
				</div>

				<p class="text-gray-400">Warte auf nächste Runde...</p>
			{/if}
		</div>

	{:else if status === 'gameover'}
		<div class="flex flex-1 flex-col items-center justify-center gap-4">
			<h2 class="text-4xl font-black text-red-500">SPIEL VORBEI</h2>
			<p class="text-gray-400">Danke fürs Mitspielen!</p>
		</div>
	{/if}

	{#if errorMsg}
		<div class="fixed bottom-4 left-4 right-4 rounded-lg bg-red-500/20 p-3 text-center text-red-400">
			{errorMsg}
		</div>
	{/if}
</div>
