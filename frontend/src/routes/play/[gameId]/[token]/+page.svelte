<script lang="ts">
	import { page } from '$app/stores';
	import { onDestroy } from 'svelte';
	import { GameWebSocket } from '$lib/websocket';

	let playerNum = $state(0);
	let status = $state<'connecting' | 'waiting' | 'playing' | 'submitted' | 'generating' | 'result' | 'gameover'>('connecting');
	let prompt = $state('');
	let timeRemaining = $state(60);
	let round = $state(1);
	let myScore = $state(0);
	let opponentScore = $state(0);
	let winner = $state(0);
	let errorMsg = $state('');

	let gameId = $derived($page.params.gameId);
	let token = $derived($page.params.token);
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
				timeRemaining = msg.data.time_remaining as number;
				status = 'playing';
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
				myScore = msg.data.score as number;
				opponentScore = msg.data.opponent_score as number;
				winner = msg.data.winner as number;
				round = msg.data.round as number;
				status = 'result';
				break;
			case 'round_start':
				round = msg.data.round as number;
				timeRemaining = msg.data.time_seconds as number;
				prompt = '';
				status = 'playing';
				break;
			case 'time_up':
				if (status === 'playing') {
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

	$effect(() => {
		if (gameId && token && !ws) {
			ws = new GameWebSocket(handleMessage);
			ws.connectPlayer(gameId, token);
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
		<div class="flex flex-1 items-center justify-center">
			<div class="text-center">
				<div class="mx-auto mb-4 h-12 w-12 animate-spin rounded-full border-4 border-neon-blue/30 border-t-neon-blue"></div>
				<p class="text-gray-400">Verbinde...</p>
			</div>
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
					class="text-5xl font-mono font-bold"
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
