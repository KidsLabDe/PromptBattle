<script lang="ts">
	import { onDestroy } from 'svelte';
	import { GameWebSocket } from '$lib/websocket';
	import {
		uiState, gameMode, gameId, currentRound, threshold, timeRemaining,
		targetImage, generatedImage, generationStep, generationTotal,
		currentScore, currentPassed, history, resetGame, resetMultiRound,
		joinToken, connectedPlayerCount, isPhoneControl,
		playerTokens, player1Image, player2Image, player1Score, player2Score,
		player1Prompt, player2Prompt, player1Reason, player2Reason,
		player1Submitted, player2Submitted,
		generatingPlayer, roundWinner, player1Wins, player2Wins,
		player1Connected, player2Connected, player1Typing, player2Typing,
		autoCountdown, compareCountdown,
		player1RevealedScore, player2RevealedScore, revealActive,
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

	import { browser } from '$app/environment';

	let ws: GameWebSocket | null = null;
	let compareTimer: ReturnType<typeof setInterval> | null = null;
	let pendingGameOver = false;
	let resultDisplayTimer: ReturnType<typeof setTimeout> | null = null;
	let autoStarted = false;
	let scoresReceived = false;
	let compareAnimDone = false;

	// Comparing phase: progress bar from 0 to 100
	let compareProgress = $state(0);
	// Score reveal: animated score growing from 0 to actual value
	let revealedScore = $state(0);
	let scoreRevealed = $state(false);

	// Timing config (defaults, overridden by /api/config)
	let COMPARE_MS = 3000;
	let SCORE_REVEAL_MS = 2500;
	let RESULT_DISPLAY_SECONDS = 8;

	// Fetch timing config from backend
	if (browser) {
		fetch('/api/config').then(r => r.json()).then(cfg => {
			COMPARE_MS = (cfg.compare_bar_seconds ?? 3) * 1000;
			SCORE_REVEAL_MS = (cfg.score_reveal_seconds ?? 2.5) * 1000;
			RESULT_DISPLAY_SECONDS = cfg.result_display_seconds ?? 8;
		}).catch(() => {});
	}

	function startComparePhase() {
		pendingGameOver = false;
		compareProgress = 0;
		revealedScore = 0;
		scoreRevealed = false;
		compareAnimDone = false;
		uiState.set('comparing');

		if (compareTimer) clearInterval(compareTimer);
		const stepMs = 50;
		const fastSteps = COMPARE_MS / stepMs;
		let step = 0;
		compareTimer = setInterval(() => {
			step++;
			if (step <= fastSteps) {
				// Fast phase: 0% to 90%
				compareProgress = Math.min(90, Math.round((step / fastSteps) * 90));
			} else {
				// Slow crawl: 90% → 99% (waiting for scores)
				compareProgress = Math.min(99, 90 + (step - fastSteps) * 0.05);
			}
			// As soon as scores arrive and bar is at least 80%, finish immediately
			if (scoresReceived && compareProgress >= 80) {
				clearInterval(compareTimer!);
				compareTimer = null;
				compareProgress = 100;
				compareAnimDone = true;
				startScoreReveal();
			}
		}, stepMs);
	}

	function startScoreReveal() {
		uiState.set('result');
		revealedScore = 0;
		scoreRevealed = false;

		if (!$isPhoneControl && $gameMode === 'multi') {
			// Multiplayer: animate per-player score bars under images
			const target1 = $player1Score;
			const target2 = $player2Score;
			const maxScore = Math.max(target1, target2, 1);
			player1RevealedScore.set(0);
			player2RevealedScore.set(0);
			revealActive.set(true);

			const stepMs = 30;
			const steps = SCORE_REVEAL_MS / stepMs;
			let step = 0;
			const revealTimer = setInterval(() => {
				step++;
				const currentValue = (step / steps) * maxScore;
				player1RevealedScore.set(Math.round(Math.min(target1, currentValue) * 10) / 10);
				player2RevealedScore.set(Math.round(Math.min(target2, currentValue) * 10) / 10);
				if (step >= steps) {
					clearInterval(revealTimer);
					player1RevealedScore.set(target1);
					player2RevealedScore.set(target2);
					scoreRevealed = true;
					if (pendingGameOver) {
						resultDisplayTimer = setTimeout(() => playAgain(), RESULT_DISPLAY_SECONDS * 1000);
					}
				}
			}, stepMs);
		} else {
			// Single player
			const targetScore = $currentScore;
			const stepMs = 30;
			const steps = SCORE_REVEAL_MS / stepMs;
			let step = 0;
			const revealTimer = setInterval(() => {
				step++;
				revealedScore = Math.min(targetScore, (step / steps) * targetScore);
				if (step >= steps) {
					clearInterval(revealTimer);
					revealedScore = targetScore;
					scoreRevealed = true;
					if (pendingGameOver) {
						resultDisplayTimer = setTimeout(() => playAgain(), RESULT_DISPLAY_SECONDS * 1000);
					}
				}
			}, stepMs);
		}
	}

	// Auto-start kiosk mode on page load (once)
	$effect(() => {
		if (browser && $uiState === 'title' && !autoStarted) {
			autoStarted = true;
			startGame('multi');
		}
	});

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
					// For single-player-via-phone: start comparing bar right after image is done
					if ($isPhoneControl && p === 1 && $uiState !== 'comparing') {
						startComparePhase();
					}
					// Multiplayer: start comparing when both images ready
					if (!$isPhoneControl && $gameMode === 'multi' && $uiState === 'generating') {
						const otherReady = p === 1 ? !!$player2Image : !!$player1Image;
						if (otherReady) {
							startComparePhase();
						}
					}
				} else {
					generatedImage.set(msg.data.image as string);
				}
				break;
			case 'score_result':
				currentScore.set(msg.data.score as number);
				currentPassed.set(msg.data.passed as boolean);
				player1Reason.set((msg.data.reason as string) || '');
				if ($isPhoneControl) {
					player1Score.set(msg.data.score as number);
					player1Prompt.set('');
				}
				scoresReceived = true;
				if ($uiState === 'comparing' && compareAnimDone) {
					startScoreReveal();
				} else if ($uiState !== 'comparing' && $uiState !== 'result') {
					startComparePhase();
				}
				break;
			case 'multi_score_result':
				player1Score.set((msg.data.player1 as Record<string, unknown>).score as number);
				player2Score.set((msg.data.player2 as Record<string, unknown>).score as number);
				player1Prompt.set((msg.data.player1 as Record<string, unknown>).prompt as string);
				player2Prompt.set((msg.data.player2 as Record<string, unknown>).prompt as string);
				player1Reason.set(((msg.data.player1 as Record<string, unknown>).reason as string) || '');
				player2Reason.set(((msg.data.player2 as Record<string, unknown>).reason as string) || '');
				roundWinner.set(msg.data.winner as number);
				player1Wins.set(msg.data.player1_wins as number);
				player2Wins.set(msg.data.player2_wins as number);
				scoresReceived = true;
				if ($uiState === 'comparing' && compareAnimDone) {
					startScoreReveal();
				} else if ($uiState !== 'comparing' && $uiState !== 'result') {
					startComparePhase();
				}
				break;
			case 'player_connected':
				if (msg.data.player === 1) player1Connected.set(true);
				else player2Connected.set(true);
				connectedPlayerCount.update(n => n + 1);
				break;
			case 'player_disconnected':
				if (msg.data.player === 1) player1Connected.set(false);
				else player2Connected.set(false);
				connectedPlayerCount.update(n => Math.max(0, n - 1));
				break;
			case 'game_mode_set':
				gameMode.set(msg.data.mode as GM);
				if (msg.data.num_players === 1) {
					isPhoneControl.set(true);
				}
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
				pendingGameOver = false;
				scoresReceived = false;
				compareAnimDone = false;
				if (resultDisplayTimer) { clearTimeout(resultDisplayTimer); resultDisplayTimer = null; }
				targetImage.set(msg.data.target_image as string);
				currentRound.set(msg.data.round as number);
				threshold.set(msg.data.threshold as number);
				timeRemaining.set(msg.data.time_seconds as number);
				generatedImage.set('');
				generationStep.set(0);
				uiState.set('playing');
				break;
			case 'time_up':
				if ($gameMode === 'single' && !$isPhoneControl) {
					uiState.set('gameover');
				}
				break;
			case 'auto_restart':
				// Nobody submitted — auto-restart
				playAgain();
				break;
			case 'new_game':
				// Server created a fresh game — reconnect
				handleNewGame(msg.data);
				break;
			case 'game_over':
				history.set((msg.data.history as RoundResult[]) || []);
				// Buffer game_over during comparing/generating/result — don't interrupt the display
				const currentState = $uiState;
				if (currentState === 'comparing' || currentState === 'generating') {
					pendingGameOver = true;
				} else if (currentState === 'result') {
					// Already showing result — restart after display time
					resultDisplayTimer = setTimeout(() => playAgain(), RESULT_DISPLAY_SECONDS * 1000);
				} else {
					// Not in score display — handle normally
					uiState.set('gameover');
				}
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
		joinToken.set(data.join_token as string);
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
			joinToken.set(data.join_token);
			uiState.set('lobby');
		} else {
			uiState.set('playing');
		}
	}

	function startGameFromLobby() {
		ws?.send('start_game');
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
		startGame('multi');
	}

	// Kiosk auto-restart: when gameover state is reached (only for cases not handled by buffering)
	$effect(() => {
		if ($uiState === 'gameover' && ($isPhoneControl || $gameMode === 'multi')) {
			// Delay restart so the gameover screen briefly shows
			const timer = setTimeout(() => playAgain(), 3000);
			return () => clearTimeout(timer);
		}
	});

	onDestroy(() => {
		ws?.close();
		if (compareTimer) clearInterval(compareTimer);
		if (resultDisplayTimer) clearTimeout(resultDisplayTimer);
	});

	let state = $derived($uiState);
	let mode = $derived($gameMode);
	let roundHistory = $derived($history);
</script>

<div class="mx-auto max-w-6xl px-4 py-8">
	{#if state === 'title'}
		<!-- Loading — auto-redirects to kiosk -->
		<div class="flex min-h-[80vh] items-center justify-center">
			<div class="h-12 w-12 animate-spin rounded-full border-4 border-neon-blue/30 border-t-neon-blue"></div>
		</div>

	{:else if state === 'lobby'}
		<QRLobby onstart={startGameFromLobby} />

	{:else if (state === 'playing' || state === 'generating' || state === 'comparing' || state === 'result') && (mode === 'multi' || $isPhoneControl)}
		<MultiplayerGame />

		{#if state === 'comparing'}
			<!-- Below images: compare progress -->
			<div class="mt-6 flex flex-col items-center gap-3">
				<h2 class="font-pixel text-2xl text-neon-yellow animate-pulse-glow">
					BILDER WERDEN VERGLICHEN...
				</h2>
				<div class="w-full max-w-lg">
					<div class="h-4 w-full overflow-hidden rounded-full bg-bg-card border border-gray-700">
						<div
							class="h-full rounded-full bg-neon-yellow transition-all duration-100"
							style="width: {compareProgress}%"
						></div>
					</div>
				</div>
			</div>
		{/if}

		{#if state === 'result' && $isPhoneControl && !scoreRevealed}
			<!-- Single player: score bar below -->
			<div class="mt-6 flex flex-col items-center gap-3">
				<h2 class="font-pixel text-2xl text-neon-green">ERGEBNIS</h2>
				<div class="w-full max-w-lg">
					<div class="h-6 w-full overflow-hidden rounded-full bg-bg-card border border-gray-700">
						<div
							class="h-full rounded-full bg-neon-green transition-all duration-75"
							style="width: {revealedScore}%"
						></div>
					</div>
					<p class="mt-2 text-center font-pixel text-3xl text-neon-green">{revealedScore.toFixed(1)}%</p>
				</div>
			</div>
		{/if}

		{#if state === 'result' && scoreRevealed}
			<!-- Winner announcement below -->
			<div class="mt-6 flex flex-col items-center gap-4">
				{#if $isPhoneControl}
					{#if $currentPassed}
						<h2 class="font-pixel text-5xl text-neon-green">GESCHAFFT!</h2>
					{:else}
						<h2 class="font-pixel text-5xl text-red-500">NICHT GESCHAFFT</h2>
					{/if}
					<span class="font-pixel text-6xl" class:text-neon-green={$currentPassed} class:text-red-500={!$currentPassed}>
						{$currentScore.toFixed(1)}%
					</span>
					<p class="text-gray-400">Mindestscore: {$threshold}%</p>
					{#if $player1Reason}
						<p class="max-w-md text-center text-sm text-gray-500">{$player1Reason}</p>
					{/if}
				{:else}
					{#if $roundWinner === 1}
						<h2 class="font-pixel text-5xl text-neon-pink">Spieler 1 gewinnt!</h2>
					{:else if $roundWinner === 2}
						<h2 class="font-pixel text-5xl text-neon-blue">Spieler 2 gewinnt!</h2>
					{:else}
						<h2 class="font-pixel text-5xl text-neon-yellow">Unentschieden!</h2>
					{/if}
					<div class="flex gap-12 items-center">
						<div class="text-center">
							<h3 class="font-pixel text-xl text-neon-pink mb-1">Spieler 1</h3>
							<span class="font-pixel text-5xl {$roundWinner === 1 ? 'text-neon-green' : $roundWinner === 2 ? 'text-red-500' : 'text-neon-yellow'}">
								{$player1Score.toFixed(1)}%
							</span>
							{#if $player1Reason}
								<p class="mt-1 max-w-xs text-xs text-gray-500">{$player1Reason}</p>
							{/if}
						</div>
						<span class="font-pixel text-3xl text-gray-500">VS</span>
						<div class="text-center">
							<h3 class="font-pixel text-xl text-neon-blue mb-1">Spieler 2</h3>
							<span class="font-pixel text-5xl {$roundWinner === 2 ? 'text-neon-green' : $roundWinner === 1 ? 'text-red-500' : 'text-neon-yellow'}">
								{$player2Score.toFixed(1)}%
							</span>
							{#if $player2Reason}
								<p class="mt-1 max-w-xs text-xs text-gray-500">{$player2Reason}</p>
							{/if}
						</div>
					</div>
					<div class="flex gap-4 text-2xl font-bold">
						<span class="text-neon-pink">{$player1Wins}</span>
						<span class="text-gray-500">:</span>
						<span class="text-neon-blue">{$player2Wins}</span>
					</div>
				{/if}
				{#if $autoCountdown > 0}
					<p class="mt-2 text-lg text-gray-400">
						Nächste Runde in <span class="font-bold text-neon-green">{$autoCountdown}</span>
					</p>
				{/if}
			</div>
		{/if}

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
			<h2 class="font-pixel text-6xl text-red-500">GAME OVER</h2>
			{#if mode === 'multi'}
				<div class="flex gap-8 text-2xl font-bold">
					<span class="text-neon-pink">Spieler 1: {$player1Wins}</span>
					<span class="text-gray-500">–</span>
					<span class="text-neon-blue">Spieler 2: {$player2Wins}</span>
				</div>
			{:else}
				<p class="text-2xl text-gray-400">
					Du hast <span class="font-bold text-neon-yellow">Runde {$currentRound}</span> erreicht
				</p>
			{/if}

			{#if $isPhoneControl || mode === 'multi'}
				<p class="text-gray-400">Neues Spiel startet automatisch...</p>
			{/if}

			{#if !$isPhoneControl && mode === 'single' && roundHistory.length > 0}
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

			{#if !$isPhoneControl && mode === 'single'}
				<button
					onclick={playAgain}
					class="font-pixel mt-4 cursor-pointer rounded-2xl bg-neon-pink px-12 py-4 text-xl
						text-white transition-all duration-200
						hover:scale-105 hover:shadow-xl hover:shadow-neon-pink/30"
				>
					NOCHMAL SPIELEN
				</button>
			{/if}
		</div>
	{/if}
</div>
