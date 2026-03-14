<script lang="ts">
	import { onDestroy } from 'svelte';
	import { GameWebSocket } from '$lib/websocket';
	import {
		uiState, gameMode, gameId, currentRound, threshold, timeRemaining,
		targetImage, generatedImage, generationStep, generationTotal,
		currentScore, currentPassed, history, resetGame, resetMultiRound,
		playerTokens, player1Image, player2Image, player1Score, player2Score,
		player1Prompt, player2Prompt, player1Submitted, player2Submitted,
		generatingPlayer, roundWinner, player1Wins, player2Wins,
		player1Connected, player2Connected, player1Typing, player2Typing,
		autoCountdown,
		type RoundResult, type GameMode as GM
	} from '$lib/stores/gameStore';
	import Timer from '$lib/components/Timer.svelte';
	import PromptInput from '$lib/components/PromptInput.svelte';
	import TargetImage from '$lib/components/TargetImage.svelte';
	import GeneratedImage from '$lib/components/GeneratedImage.svelte';
	import ScoreDisplay from '$lib/components/ScoreDisplay.svelte';
	import RoundInfo from '$lib/components/RoundInfo.svelte';
	import QRLobby from '$lib/components/QRLobby.svelte';
	import MultiplayerGame from '$lib/components/MultiplayerGame.svelte';
	import MultiplayerResult from '$lib/components/MultiplayerResult.svelte';

	let ws: GameWebSocket | null = null;

	function handleWsMessage(msg: { type: string; data: Record<string, unknown> }) {
		switch (msg.type) {
			case 'timer_tick':
				timeRemaining.set(msg.data.remaining as number);
				break;
			case 'generation_progress':
				if (msg.data.player) {
					generatingPlayer.set(msg.data.player as number);
				}
				generationStep.set(msg.data.step as number);
				generationTotal.set(msg.data.total as number);
				break;
			case 'generation_start':
				generatingPlayer.set(msg.data.player as number);
				uiState.set('generating');
				break;
			case 'generation_complete':
				if (msg.data.player) {
					const p = msg.data.player as number;
					if (p === 1) player1Image.set(msg.data.image as string);
					else player2Image.set(msg.data.image as string);
				} else {
					generatedImage.set(msg.data.image as string);
				}
				break;
			case 'score_result':
				currentScore.set(msg.data.score as number);
				currentPassed.set(msg.data.passed as boolean);
				uiState.set('result');
				break;
			case 'multi_score_result':
				player1Score.set((msg.data.player1 as Record<string, unknown>).score as number);
				player2Score.set((msg.data.player2 as Record<string, unknown>).score as number);
				player1Prompt.set((msg.data.player1 as Record<string, unknown>).prompt as string);
				player2Prompt.set((msg.data.player2 as Record<string, unknown>).prompt as string);
				roundWinner.set(msg.data.winner as number);
				player1Wins.set(msg.data.player1_wins as number);
				player2Wins.set(msg.data.player2_wins as number);
				uiState.set('result');
				break;
			case 'player_connected':
				if (msg.data.player === 1) player1Connected.set(true);
				else player2Connected.set(true);
				break;
			case 'player_disconnected':
				if (msg.data.player === 1) player1Connected.set(false);
				else player2Connected.set(false);
				break;
			case 'all_players_connected':
				uiState.set('playing');
				break;
			case 'prompt_submitted':
				if (msg.data.player === 1) {
					player1Submitted.set(true);
					player1Prompt.set(msg.data.prompt as string);
				} else {
					player2Submitted.set(true);
					player2Prompt.set(msg.data.prompt as string);
				}
				break;
			case 'player_typing':
				if (msg.data.player === 1) player1Typing.set(msg.data.text as string);
				else player2Typing.set(msg.data.text as string);
				break;
			case 'auto_countdown':
				autoCountdown.set(msg.data.seconds as number);
				break;
			case 'round_start':
				resetMultiRound();
				targetImage.set(msg.data.target_image as string);
				currentRound.set(msg.data.round as number);
				threshold.set(msg.data.threshold as number);
				timeRemaining.set(msg.data.time_seconds as number);
				generatedImage.set('');
				generationStep.set(0);
				uiState.set('playing');
				break;
			case 'time_up':
				if ($gameMode === 'single') {
					uiState.set('gameover');
				}
				break;
			case 'auto_restart':
				// Nobody submitted — show brief message then auto-restart
				uiState.set('gameover');
				break;
			case 'new_game':
				// Server created a fresh game — reconnect
				handleNewGame(msg.data);
				break;
			case 'game_over':
				history.set((msg.data.history as RoundResult[]) || []);
				uiState.set('gameover');
				break;
			case 'error':
				console.error('Server error:', msg.data.message);
				break;
		}
	}

	function handleNewGame(data: Record<string, unknown>) {
		// Close old connection, set up new game
		ws?.close();
		resetGame();
		gameMode.set('multi');

		gameId.set(data.game_id as string);
		targetImage.set(data.target_image as string);
		currentRound.set(data.round as number);
		threshold.set(data.threshold as number);
		timeRemaining.set(data.time_seconds as number);
		playerTokens.set(data.player_tokens as { '1': string; '2': string });
		uiState.set('lobby');

		ws = new GameWebSocket(handleWsMessage);
		ws.connect(data.game_id as string);
	}

	async function startGame(mode: GM = 'single') {
		resetGame();
		gameMode.set(mode);
		const res = await fetch('/api/game/start', {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({ mode }),
		});
		const data = await res.json();
		gameId.set(data.game_id);
		targetImage.set(data.target_image);
		currentRound.set(data.round);
		threshold.set(data.threshold);
		timeRemaining.set(data.time_seconds);

		ws = new GameWebSocket(handleWsMessage);
		ws.connect(data.game_id);

		if (mode === 'multi') {
			playerTokens.set(data.player_tokens);
			uiState.set('lobby');
		} else {
			uiState.set('playing');
		}
	}

	function submitPrompt(prompt: string) {
		uiState.set('generating');
		generationStep.set(0);
		generatedImage.set('');
		ws?.send('submit_prompt', { prompt });
	}

	function nextRound() {
		resetMultiRound();
		ws?.send('next_round');
	}

	function playAgain() {
		ws?.close();
		const mode = $gameMode;
		startGame(mode);
	}

	onDestroy(() => {
		ws?.close();
	});

	let state = $derived($uiState);
	let mode = $derived($gameMode);
	let roundHistory = $derived($history);
</script>

<div class="mx-auto max-w-6xl px-4 py-8">
	{#if state === 'title'}
		<!-- Titelbildschirm -->
		<div class="flex min-h-[80vh] flex-col items-center justify-center gap-8 text-center">
			<h1 class="text-7xl font-black tracking-tight">
				<span class="text-neon-pink">PROMPT</span>
				<span class="text-neon-blue">BATTLE</span>
			</h1>
			<p class="max-w-lg text-lg text-gray-400">
				Du siehst ein Zielbild. Schreibe einen Prompt, um etwas Ähnliches zu generieren.
				Erreiche den Mindestscore, um weiterzukommen. Jede Runde wird schwieriger.
			</p>
			<div class="flex flex-col gap-3 text-left text-sm text-gray-500">
				<p>&#x1F3AF; Triff das Zielbild mit deinem Prompt</p>
				<p>&#x23F1;&#xFE0F; 60 Sekunden pro Runde</p>
				<p>&#x1F4C8; Schwelle steigt jede Runde (25% &rarr; 75%)</p>
				<p>&#x1F6AB; Schwelle verfehlt = Game Over</p>
			</div>
			<div class="mt-4 flex gap-6">
				<button
					onclick={() => startGame('single')}
					class="cursor-pointer rounded-2xl bg-neon-green px-12 py-4 text-xl font-black
						text-black transition-all duration-200
						hover:scale-105 hover:shadow-xl hover:shadow-neon-green/30"
				>
					EINZELSPIELER
				</button>
				<button
					onclick={() => startGame('multi')}
					class="cursor-pointer rounded-2xl bg-neon-blue px-12 py-4 text-xl font-black
						text-black transition-all duration-200
						hover:scale-105 hover:shadow-xl hover:shadow-neon-blue/30"
				>
					MEHRSPIELER
				</button>
			</div>
		</div>

	{:else if state === 'lobby'}
		<QRLobby />

	{:else if (state === 'playing' || state === 'generating') && mode === 'multi'}
		<MultiplayerGame />

	{:else if state === 'result' && mode === 'multi'}
		<MultiplayerResult />

	{:else if state === 'playing' || state === 'generating'}
		<!-- Einzelspieler -->
		<div class="flex flex-col gap-6">
			<div class="flex items-center justify-between">
				<RoundInfo />
				<Timer />
			</div>
			<div class="grid grid-cols-1 gap-8 md:grid-cols-2">
				<TargetImage />
				<GeneratedImage />
			</div>
			<PromptInput onsubmit={submitPrompt} />
		</div>

	{:else if state === 'result'}
		<!-- Einzelspieler Ergebnis -->
		<div class="flex flex-col gap-6">
			<RoundInfo />
			<div class="grid grid-cols-1 gap-8 md:grid-cols-2">
				<TargetImage />
				<GeneratedImage />
			</div>
			<ScoreDisplay />
			{#if $currentPassed}
				<div class="flex justify-center">
					<button
						onclick={nextRound}
						class="cursor-pointer rounded-xl bg-neon-green px-10 py-3 text-lg font-bold
							text-black transition-all duration-200
							hover:scale-105 hover:shadow-lg hover:shadow-neon-green/30"
					>
						Nächste Runde
					</button>
				</div>
			{:else}
				<div class="flex justify-center">
					<button
						onclick={playAgain}
						class="cursor-pointer rounded-xl bg-neon-pink px-10 py-3 text-lg font-bold
							text-white transition-all duration-200
							hover:scale-105 hover:shadow-lg hover:shadow-neon-pink/30"
					>
						Nochmal spielen
					</button>
				</div>
			{/if}
		</div>

	{:else if state === 'gameover'}
		<!-- Game Over -->
		<div class="flex min-h-[80vh] flex-col items-center justify-center gap-8">
			<h2 class="text-5xl font-black text-red-500">GAME OVER</h2>
			{#if mode === 'multi'}
				<div class="flex gap-8 text-2xl font-bold">
					<span class="text-neon-pink">Spieler 1: {$player1Wins}</span>
					<span class="text-gray-500">–</span>
					<span class="text-neon-blue">Spieler 2: {$player2Wins}</span>
				</div>
				<p class="text-gray-400">Neues Spiel startet automatisch...</p>
			{:else}
				<p class="text-2xl text-gray-400">
					Du hast <span class="font-bold text-neon-yellow">Runde {$currentRound}</span> erreicht
				</p>
			{/if}

			{#if mode === 'single' && roundHistory.length > 0}
				<div class="w-full max-w-2xl">
					<h3 class="mb-4 text-lg font-semibold text-gray-300">Rundenverlauf</h3>
					<div class="flex flex-col gap-3">
						{#each roundHistory as round}
							<div class="flex items-center justify-between rounded-lg bg-bg-card p-4 border border-gray-800">
								<div class="flex items-center gap-4">
									<span class="text-sm font-bold text-gray-500">R{round.round}</span>
									<span class="text-sm text-gray-400 max-w-xs truncate">{round.prompt}</span>
								</div>
								<div class="flex items-center gap-3">
									<span class="text-sm text-gray-500">mind. {round.threshold}%</span>
									<span
										class="font-bold"
										class:text-neon-green={round.passed}
										class:text-red-500={!round.passed}
									>
										{round.score}%
									</span>
								</div>
							</div>
						{/each}
					</div>
				</div>
			{/if}

			{#if mode === 'single'}
				<button
					onclick={playAgain}
					class="mt-4 cursor-pointer rounded-2xl bg-neon-pink px-12 py-4 text-xl font-black
						text-white transition-all duration-200
						hover:scale-105 hover:shadow-xl hover:shadow-neon-pink/30"
				>
					NOCHMAL SPIELEN
				</button>
			{/if}
		</div>
	{/if}
</div>
