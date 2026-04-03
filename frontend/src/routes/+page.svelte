<script lang="ts">
	import { onDestroy } from 'svelte';
	import { GameWebSocket } from '$lib/websocket';
	import {
		uiState, gameMode, gameId, currentRound, threshold, timeRemaining,
		targetImage, generatedImage, generationError, generationStep, generationTotal,
		currentScore, currentPassed, history, resetGame, resetMultiRound,
		joinToken, connectedPlayerCount, isPhoneControl,
		playerTokens, player1Image, player2Image, player1Score, player2Score,
		player1Prompt, player2Prompt, player1Reason, player2Reason,
		player1Submitted, player2Submitted,
		generatingPlayer, roundWinner, player1Wins, player2Wins,
		player1Connected, player2Connected, player1Typing, player2Typing,
		player1Error, player2Error,
		autoCountdown, compareCountdown,
		player1RevealedScore, player2RevealedScore, revealActive,
		roundTimeSeconds, lobbyTimeoutSeconds,
		type RoundResult, type GameMode as GM
	} from '$lib/stores/gameStore';
	import Timer from '$lib/components/Timer.svelte';
	import PromptInput from '$lib/components/PromptInput.svelte';
	import TargetImage from '$lib/components/TargetImage.svelte';
	import GeneratedImage from '$lib/components/GeneratedImage.svelte';
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
	let singlePlayerPrompt = $state('');
	let singleResultCountdown = $state(0);
	let singleResultCountdownTimer: ReturnType<typeof setInterval> | null = null;

	// Display password protection
	let displayPasswordRequired = $state(false);
	let displayAuthenticated = $state(false);
	let passwordInput = $state('');
	let passwordError = $state('');
	let passwordLoading = $state(false);

	// Comparing phase: progress bar from 0 to 100
	let compareProgress = $state(0);
	// Score reveal: animated score growing from 0 to actual value
	let revealedScore = $state(0);
	let scoreRevealed = $state(false);

	// Timing config (defaults, overridden by /api/config)
	let IMAGE_DISPLAY_MS = 3000;
	let COMPARE_MS = 3000;
	let SCORE_REVEAL_MS = 2500;
	let RESULT_DISPLAY_SECONDS = 8;
	let GAMEOVER_RESTART_SECONDS = 5;

	// Fetch timing config from backend
	if (browser) {
		fetch('/api/config').then(r => r.json()).then(async cfg => {
			IMAGE_DISPLAY_MS = (cfg.image_display_seconds ?? 3) * 1000;
			COMPARE_MS = (cfg.compare_bar_seconds ?? 3) * 1000;
			SCORE_REVEAL_MS = (cfg.score_reveal_seconds ?? 2.5) * 1000;
			RESULT_DISPLAY_SECONDS = cfg.result_display_seconds ?? 8;
			GAMEOVER_RESTART_SECONDS = cfg.gameover_restart_seconds ?? 5;
			if (cfg.round_time_seconds) roundTimeSeconds.set(cfg.round_time_seconds);
			if (cfg.lobby_timeout_seconds) lobbyTimeoutSeconds.set(cfg.lobby_timeout_seconds);
			displayPasswordRequired = cfg.display_password_required ?? false;
			if (!displayPasswordRequired) {
				displayAuthenticated = true;
			} else {
				// Auto-login wenn Passwort per URL-Parameter übergeben wird (?pw=...)
				const urlPw = new URLSearchParams(window.location.search).get('pw');
				if (urlPw) {
					const res = await fetch('/api/display/login', {
						method: 'POST',
						headers: { 'Content-Type': 'application/json' },
						body: JSON.stringify({ password: urlPw }),
					});
					if (res.ok) displayAuthenticated = true;
				}
			}
		}).catch(() => {});
	}

	// Countdown for image display phase and gameover
	let imageDisplayCountdown = $state(0);
	let gameoverCountdown = $state(0);

	function startImageDisplayPhase() {
		// Show generated images for a few seconds before starting comparison
		const totalSeconds = Math.ceil(IMAGE_DISPLAY_MS / 1000);
		imageDisplayCountdown = totalSeconds;
		const countdownTimer = setInterval(() => {
			imageDisplayCountdown--;
			if (imageDisplayCountdown <= 0) {
				clearInterval(countdownTimer);
			}
		}, 1000);
		setTimeout(() => {
			clearInterval(countdownTimer);
			imageDisplayCountdown = 0;
			startComparePhase();
		}, IMAGE_DISPLAY_MS);
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

	function startSingleResultCountdown() {
		if (singleResultCountdownTimer) clearInterval(singleResultCountdownTimer);
		singleResultCountdown = Math.ceil(RESULT_DISPLAY_SECONDS);
		singleResultCountdownTimer = setInterval(() => {
			singleResultCountdown--;
			if (singleResultCountdown <= 0) {
				clearInterval(singleResultCountdownTimer!);
				singleResultCountdownTimer = null;
			}
		}, 1000);
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
			// Single player (both traditional and phone-controlled)
			const targetScore = $currentScore;
			const passed = $currentPassed;
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
					if ($isPhoneControl) {
						// Phone-controlled: backend handles auto-advance for passed rounds
						// For game over (not passed), restart via frontend
						if (pendingGameOver && !resultDisplayTimer) {
							resultDisplayTimer = setTimeout(() => playAgain(), RESULT_DISPLAY_SECONDS * 1000);
						}
					} else {
						// Traditional single-player: frontend handles auto-advance
						if (pendingGameOver) {
							startSingleResultCountdown();
							resultDisplayTimer = setTimeout(() => playAgain(), RESULT_DISPLAY_SECONDS * 1000);
						} else if (passed) {
							startSingleResultCountdown();
							resultDisplayTimer = setTimeout(() => nextRound(), RESULT_DISPLAY_SECONDS * 1000);
						}
					}
				}
			}, stepMs);
		}
	}

	// Auto-start kiosk mode on page load (once, after authentication)
	$effect(() => {
		if (browser && $uiState === 'title' && !autoStarted && displayAuthenticated) {
			autoStarted = true;
			startGame('multi');
		}
	});

	async function submitDisplayPassword() {
		passwordError = '';
		passwordLoading = true;
		try {
			const res = await fetch('/api/display/login', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ password: passwordInput }),
			});
			if (res.ok) {
				displayAuthenticated = true;
			} else {
				passwordError = 'Falsches Passwort';
			}
		} catch {
			passwordError = 'Verbindungsfehler';
		} finally {
			passwordLoading = false;
		}
	}

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
					if (p === 1) {
						player1Image.set(msg.data.image as string);
						if (msg.data.error) player1Error.set(msg.data.error as string);
					} else {
						player2Image.set(msg.data.image as string);
						if (msg.data.error) player2Error.set(msg.data.error as string);
					}
					// For single-player-via-phone: show images then compare
					if ($isPhoneControl && p === 1 && $uiState !== 'comparing') {
						startImageDisplayPhase();
					}
					// Multiplayer: show images then compare when both ready
					if (!$isPhoneControl && $gameMode === 'multi' && $uiState === 'generating') {
						const otherReady = p === 1 ? !!$player2Image : !!$player1Image;
						if (otherReady) {
							startImageDisplayPhase();
						}
					}
				} else {
					generatedImage.set(msg.data.image as string);
					if (msg.data.error) generationError.set(msg.data.error as string);
					// Single-player traditional: show images then compare (like multiplayer)
					if (!$isPhoneControl && $gameMode === 'single') {
						startImageDisplayPhase();
					}
				}
				break;
			case 'score_result':
				currentScore.set(msg.data.score as number);
				currentPassed.set(msg.data.passed as boolean);
				player1Reason.set((msg.data.reason as string) || '');
				if ($isPhoneControl) {
					player1Score.set(msg.data.score as number);
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
					const st = $uiState;
					if (st === 'generating' || st === 'comparing' || st === 'result') {
						// Don't interrupt generation/scoring flow
						pendingGameOver = true;
					} else {
						uiState.set('gameover');
					}
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
				pendingGameOver = true;
				// Always schedule a restart — long enough for animations to finish
				if (!resultDisplayTimer) {
					const delayMs = ($uiState === 'comparing' || $uiState === 'generating')
						? (COMPARE_MS + SCORE_REVEAL_MS + RESULT_DISPLAY_SECONDS * 1000 + 2000)
						: RESULT_DISPLAY_SECONDS * 1000;
					resultDisplayTimer = setTimeout(() => playAgain(), delayMs);
				}
				// If not in an animation phase, go to gameover screen immediately
				if ($uiState !== 'comparing' && $uiState !== 'generating' && $uiState !== 'result') {
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
		singlePlayerPrompt = prompt;
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

	// Kiosk auto-restart: when gameover state is reached (all modes)
	$effect(() => {
		if ($uiState === 'gameover') {
			const totalSeconds = Math.ceil(GAMEOVER_RESTART_SECONDS);
			gameoverCountdown = totalSeconds;
			const countdownTimer = setInterval(() => {
				gameoverCountdown--;
				if (gameoverCountdown <= 0) clearInterval(countdownTimer);
			}, 1000);
			const timer = setTimeout(() => {
				clearInterval(countdownTimer);
				gameoverCountdown = 0;
				playAgain();
			}, GAMEOVER_RESTART_SECONDS * 1000);
			return () => { clearTimeout(timer); clearInterval(countdownTimer); };
		}
	});

	onDestroy(() => {
		ws?.close();
		if (compareTimer) clearInterval(compareTimer);
		if (resultDisplayTimer) clearTimeout(resultDisplayTimer);
		if (singleResultCountdownTimer) clearInterval(singleResultCountdownTimer);
	});

	let state = $derived($uiState);
	let mode = $derived($gameMode);
	let roundHistory = $derived($history);
</script>

<div class="mx-auto max-w-6xl px-4 py-4">
	{#if state === 'title'}
		{#if displayPasswordRequired && !displayAuthenticated}
			<!-- Display password login -->
			<div class="flex min-h-[80vh] items-center justify-center">
				<form onsubmit={(e) => { e.preventDefault(); submitDisplayPassword(); }} class="flex flex-col items-center gap-6 rounded-2xl border border-gray-700 bg-bg-card p-10">
					<h1 class="font-pixel text-4xl text-neon-green">PROMPT BATTLE</h1>
					<p class="text-lg text-gray-400">Passwort eingeben, um das Display zu starten</p>
					<input
						type="password"
						bind:value={passwordInput}
						placeholder="Passwort"
						class="w-72 rounded-lg border border-gray-600 bg-bg-main px-4 py-3 text-center text-xl text-white placeholder-gray-500 focus:border-neon-green focus:outline-none"
						autofocus
					/>
					{#if passwordError}
						<p class="text-red-400">{passwordError}</p>
					{/if}
					<button
						type="submit"
						disabled={passwordLoading || !passwordInput}
						class="rounded-lg bg-neon-green px-8 py-3 text-xl font-bold text-black transition hover:brightness-110 disabled:opacity-50"
					>
						{passwordLoading ? 'Prüfe...' : 'Starten'}
					</button>
				</form>
			</div>
		{:else}
			<!-- Loading — auto-redirects to kiosk -->
			<div class="flex min-h-[80vh] items-center justify-center">
				<div class="h-12 w-12 animate-spin rounded-full border-4 border-neon-blue/30 border-t-neon-blue"></div>
			</div>
		{/if}

	{:else if state === 'lobby'}
		<QRLobby onstart={startGameFromLobby} />

	{:else if (state === 'playing' || state === 'generating' || state === 'comparing' || state === 'result') && (mode === 'multi' || $isPhoneControl)}
		<div class="flex h-[calc(100vh-2rem)] flex-col">
		<!-- Images area: shrinks to make room for info below -->
		<div class="min-h-0 flex-1 overflow-hidden">
			<MultiplayerGame />
		</div>

		<!-- Info area below images: always visible -->
		{#if state === 'generating' && imageDisplayCountdown > 0}
			<div class="shrink-0 py-3 flex flex-col items-center">
				<p class="text-lg text-gray-400">
					Vergleich startet in <span class="font-bold text-neon-yellow">{imageDisplayCountdown}</span>
				</p>
			</div>
		{/if}

		{#if state === 'comparing'}
			<div class="shrink-0 py-3 flex flex-col items-center gap-3">
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
			<div class="shrink-0 py-3 flex flex-col items-center gap-3">
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
			<div class="shrink-0 py-3 flex flex-col items-center gap-3">
				{#if $isPhoneControl}
					{#if $currentPassed}
						<h2 class="font-pixel text-4xl text-neon-green">GESCHAFFT!</h2>
					{:else}
						<h2 class="font-pixel text-4xl text-red-500">NICHT GESCHAFFT</h2>
					{/if}
					<span class="font-pixel text-5xl" class:text-neon-green={$currentPassed} class:text-red-500={!$currentPassed}>
						{$currentScore.toFixed(1)}%
					</span>
					<p class="text-gray-400">Mindestscore: {$threshold}%</p>
					{#if $player1Prompt}
						<p class="max-w-lg text-center text-lg italic text-gray-300">„{$player1Prompt}"</p>
					{/if}
					{#if $player1Reason}
						<p class="max-w-lg text-center text-base text-gray-500">{$player1Reason}</p>
					{/if}
				{:else}
					{#if $roundWinner === 1}
						<h2 class="font-pixel text-4xl text-neon-pink">Spieler 1 gewinnt!</h2>
					{:else if $roundWinner === 2}
						<h2 class="font-pixel text-4xl text-neon-blue">Spieler 2 gewinnt!</h2>
					{:else}
						<h2 class="font-pixel text-4xl text-neon-yellow">Unentschieden!</h2>
					{/if}
					<div class="flex gap-12 items-center">
						<div class="text-center">
							<h3 class="font-pixel text-lg text-neon-pink">Spieler 1</h3>
							<span class="font-pixel text-4xl {$roundWinner === 1 ? 'text-neon-green' : $roundWinner === 2 ? 'text-red-500' : 'text-neon-yellow'}">
								{$player1Score.toFixed(1)}%
							</span>
						</div>
						<span class="font-pixel text-2xl text-gray-500">VS</span>
						<div class="text-center">
							<h3 class="font-pixel text-lg text-neon-blue">Spieler 2</h3>
							<span class="font-pixel text-4xl {$roundWinner === 2 ? 'text-neon-green' : $roundWinner === 1 ? 'text-red-500' : 'text-neon-yellow'}">
								{$player2Score.toFixed(1)}%
							</span>
						</div>
					</div>
					{#if $player1Reason || $player2Reason}
						<div class="grid grid-cols-2 gap-8 w-full max-w-3xl">
							<p class="text-center text-base text-gray-500">{$player1Reason}</p>
							<p class="text-center text-base text-gray-500">{$player2Reason}</p>
						</div>
					{/if}
					<div class="flex gap-4 text-xl font-bold">
						<span class="text-neon-pink">{$player1Wins}</span>
						<span class="text-gray-500">:</span>
						<span class="text-neon-blue">{$player2Wins}</span>
					</div>
				{/if}
				{#if $autoCountdown > 0}
					<p class="text-lg text-gray-400">
						Nächste Runde in <span class="font-bold text-neon-green">{$autoCountdown}</span>
					</p>
				{/if}
			</div>
		{/if}
		</div>

	{:else if state === 'playing' || state === 'generating' || state === 'comparing' || state === 'result'}
		<!-- Einzelspieler -->
		<div class="flex flex-col gap-6">
			<div class="flex items-center justify-between">
				<RoundInfo />
				{#if state === 'playing' || state === 'generating'}
					<Timer />
				{/if}
			</div>
			<div class="grid grid-cols-1 gap-8 md:grid-cols-2">
				<TargetImage />
				<GeneratedImage />
			</div>

			{#if state === 'playing'}
				<PromptInput onsubmit={submitPrompt} />
			{/if}

			{#if state === 'generating' && imageDisplayCountdown > 0}
				<div class="flex flex-col items-center py-3">
					<p class="text-lg text-gray-400">
						Vergleich startet in <span class="font-bold text-neon-yellow">{imageDisplayCountdown}</span>
					</p>
				</div>
			{/if}

			{#if state === 'comparing'}
				<div class="flex flex-col items-center gap-3 py-3">
					<h2 class="font-pixel text-2xl text-neon-yellow animate-pulse-glow">
						BILDER WERDEN VERGLICHEN...
					</h2>
					<div class="w-full max-w-lg mx-auto">
						<div class="h-4 w-full overflow-hidden rounded-full bg-bg-card border border-gray-700">
							<div
								class="h-full rounded-full bg-neon-yellow transition-all duration-100"
								style="width: {compareProgress}%"
							></div>
						</div>
					</div>
				</div>
			{/if}

			{#if state === 'result' && !scoreRevealed}
				<div class="flex flex-col items-center gap-3 py-3">
					<h2 class="font-pixel text-2xl text-neon-green">ERGEBNIS</h2>
					<div class="w-full max-w-lg mx-auto">
						<div class="h-6 w-full overflow-hidden rounded-full bg-bg-card border border-gray-700">
							<div
								class="h-full rounded-full transition-all duration-75"
								class:bg-neon-green={$currentPassed}
								class:bg-red-500={!$currentPassed}
								style="width: {revealedScore}%"
							></div>
						</div>
						<p class="mt-2 text-center font-pixel text-3xl" class:text-neon-green={$currentPassed} class:text-red-500={!$currentPassed}>
							{revealedScore.toFixed(1)}%
						</p>
					</div>
				</div>
			{/if}

			{#if state === 'result' && scoreRevealed}
				<div class="flex flex-col items-center gap-3 py-3">
					{#if $currentPassed}
						<h2 class="font-pixel text-4xl text-neon-green">GESCHAFFT!</h2>
					{:else}
						<h2 class="font-pixel text-4xl text-red-500">NICHT BESTANDEN</h2>
					{/if}
					<span class="font-pixel text-5xl" class:text-neon-green={$currentPassed} class:text-red-500={!$currentPassed}>
						{$currentScore.toFixed(1)}%
					</span>
					<p class="text-gray-400">Mindestscore: {$threshold}%</p>
					{#if singlePlayerPrompt}
						<p class="max-w-lg text-center text-lg italic text-gray-300">„{singlePlayerPrompt}"</p>
					{/if}
					{#if $player1Reason}
						<p class="max-w-lg text-center text-base text-gray-500">{$player1Reason}</p>
					{/if}
					{#if singleResultCountdown > 0}
						<p class="text-lg text-gray-400">
							{#if $currentPassed}
								Nächste Runde in <span class="font-bold text-neon-green">{singleResultCountdown}</span>
							{:else}
								Neues Spiel in <span class="font-bold text-neon-green">{singleResultCountdown}</span>
							{/if}
						</p>
					{/if}
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

			{#if roundHistory.length > 0}
				<div class="w-full max-w-2xl">
					<h3 class="mb-4 text-lg font-semibold text-gray-300">Rundenverlauf</h3>
					<div class="flex flex-col gap-3">
						{#each roundHistory as round}
							<div class="flex items-center justify-between rounded-lg bg-bg-card p-4 border border-gray-800">
								<div class="flex items-center gap-4">
									<span class="text-base font-bold text-gray-500">R{round.round}</span>
									<span class="text-base text-gray-400 max-w-md truncate">{round.prompt}</span>
								</div>
								<div class="flex items-center gap-3">
									<span class="text-base text-gray-500">mind. {round.threshold}%</span>
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

			<p class="text-lg text-gray-400">
				Neues Spiel in <span class="font-bold text-neon-green">{gameoverCountdown}</span>
			</p>
		</div>
	{/if}
</div>
