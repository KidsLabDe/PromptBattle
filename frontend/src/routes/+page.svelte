<script lang="ts">
	import { onDestroy } from 'svelte';
	import { GameWebSocket } from '$lib/websocket';
	import {
		uiState, gameId, currentRound, threshold, timeRemaining,
		targetImage, generatedImage, generationStep, generationTotal,
		currentScore, currentPassed, history, resetGame,
		type RoundResult
	} from '$lib/stores/gameStore';
	import Timer from '$lib/components/Timer.svelte';
	import PromptInput from '$lib/components/PromptInput.svelte';
	import TargetImage from '$lib/components/TargetImage.svelte';
	import GeneratedImage from '$lib/components/GeneratedImage.svelte';
	import ScoreDisplay from '$lib/components/ScoreDisplay.svelte';
	import RoundInfo from '$lib/components/RoundInfo.svelte';

	let ws: GameWebSocket | null = null;

	function handleWsMessage(msg: { type: string; data: Record<string, unknown> }) {
		switch (msg.type) {
			case 'timer_tick':
				timeRemaining.set(msg.data.remaining as number);
				break;
			case 'generation_progress':
				generationStep.set(msg.data.step as number);
				generationTotal.set(msg.data.total as number);
				break;
			case 'generation_complete':
				generatedImage.set(msg.data.image as string);
				break;
			case 'score_result':
				currentScore.set(msg.data.score as number);
				currentPassed.set(msg.data.passed as boolean);
				uiState.set('result');
				break;
			case 'round_start':
				targetImage.set(msg.data.target_image as string);
				currentRound.set(msg.data.round as number);
				threshold.set(msg.data.threshold as number);
				timeRemaining.set(msg.data.time_seconds as number);
				generatedImage.set('');
				generationStep.set(0);
				uiState.set('playing');
				break;
			case 'time_up':
				uiState.set('gameover');
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

	async function startGame() {
		resetGame();
		const res = await fetch('/api/game/start', { method: 'POST' });
		const data = await res.json();
		gameId.set(data.game_id);
		targetImage.set(data.target_image);
		currentRound.set(data.round);
		threshold.set(data.threshold);
		timeRemaining.set(data.time_seconds);
		uiState.set('playing');

		ws = new GameWebSocket(handleWsMessage);
		ws.connect(data.game_id);
	}

	function submitPrompt(prompt: string) {
		uiState.set('generating');
		generationStep.set(0);
		generatedImage.set('');
		ws?.send('submit_prompt', { prompt });
	}

	function nextRound() {
		ws?.send('next_round');
	}

	function playAgain() {
		ws?.close();
		startGame();
	}

	onDestroy(() => {
		ws?.close();
	});

	let state = $derived($uiState);
	let roundHistory = $derived($history);
</script>

<div class="mx-auto max-w-6xl px-4 py-8">
	{#if state === 'title'}
		<!-- Title Screen -->
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
			<button
				onclick={startGame}
				class="mt-4 cursor-pointer rounded-2xl bg-neon-green px-12 py-4 text-xl font-black
					text-black transition-all duration-200
					hover:scale-105 hover:shadow-xl hover:shadow-neon-green/30"
			>
				SPIEL STARTEN
			</button>
		</div>

	{:else if state === 'playing' || state === 'generating'}
		<!-- Game Screen -->
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
		<!-- Result Screen -->
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
		<!-- Game Over Screen -->
		<div class="flex min-h-[80vh] flex-col items-center justify-center gap-8">
			<h2 class="text-5xl font-black text-red-500">GAME OVER</h2>
			<p class="text-2xl text-gray-400">
				Du hast <span class="font-bold text-neon-yellow">Runde {$currentRound}</span> erreicht
			</p>

			{#if roundHistory.length > 0}
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

			<button
				onclick={playAgain}
				class="mt-4 cursor-pointer rounded-2xl bg-neon-pink px-12 py-4 text-xl font-black
					text-white transition-all duration-200
					hover:scale-105 hover:shadow-xl hover:shadow-neon-pink/30"
			>
				NOCHMAL SPIELEN
			</button>
		</div>
	{/if}
</div>
