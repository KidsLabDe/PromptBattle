<script lang="ts">
	import {
		targetImage, currentRound, threshold, timeRemaining,
		player1Image, player2Image, player1Submitted, player2Submitted,
		player1Typing, player2Typing, player1Prompt, player2Prompt,
		generatingPlayer, generationStep, generationTotal,
		player1Wins, player2Wins,
	} from '$lib/stores/gameStore';
	import Timer from './Timer.svelte';

	let src = $derived($targetImage ? `/api/images/target/${$targetImage}` : '');
	let genPlayer = $derived($generatingPlayer);
</script>

<div class="flex flex-col gap-6">
	<!-- Header -->
	<div class="flex items-center justify-between">
		<span class="rounded-lg bg-neon-pink/20 px-3 py-1 font-bold text-neon-pink">
			Runde {$currentRound}
		</span>
		<div class="flex gap-4 text-lg font-bold">
			<span class="text-neon-pink">{$player1Wins}</span>
			<span class="text-gray-500">:</span>
			<span class="text-neon-blue">{$player2Wins}</span>
		</div>
		<Timer />
	</div>

	<!-- Target image centered -->
	<div class="flex justify-center">
		<div class="w-56">
			<h3 class="mb-2 text-center text-sm font-semibold uppercase tracking-widest text-neon-yellow">Zielbild</h3>
			<div class="aspect-square w-full overflow-hidden rounded-xl border-2 border-neon-yellow/30 bg-bg-card">
				{#if src}
					<img {src} alt="Zielbild" class="h-full w-full object-cover" />
				{/if}
			</div>
		</div>
	</div>

	<!-- Two player columns -->
	<div class="grid grid-cols-2 gap-8">
		<!-- Spieler 1 -->
		<div class="flex flex-col items-center gap-3">
			<h3 class="text-xl font-bold text-neon-pink">Spieler 1</h3>
			<div class="aspect-square w-full overflow-hidden rounded-xl border-2 border-neon-pink/30 bg-bg-card">
				{#if genPlayer === 1 && !$player1Image}
					<div class="flex h-full flex-col items-center justify-center gap-4">
						<div class="h-12 w-12 animate-spin rounded-full border-4 border-neon-pink/30 border-t-neon-pink"></div>
						<p class="text-neon-pink">Schritt {$generationStep} / {$generationTotal}</p>
					</div>
				{:else if $player1Image}
					<img src="data:image/webp;base64,{$player1Image}" alt="Spieler 1" class="h-full w-full object-cover" />
				{:else if $player1Submitted}
					<div class="flex h-full flex-col items-center justify-center gap-2 p-4">
						<span class="text-4xl text-neon-green">&#x2714;</span>
						<p class="text-center text-sm text-gray-400 italic break-words max-w-full">"{$player1Prompt}"</p>
					</div>
				{:else}
					<div class="flex h-full items-center justify-center p-4">
						{#if $player1Typing}
							<p class="text-center text-gray-400 italic break-words max-w-full animate-pulse">
								{$player1Typing}<span class="text-neon-pink">|</span>
							</p>
						{:else}
							<p class="text-gray-600">Warte auf Prompt...</p>
						{/if}
					</div>
				{/if}
			</div>
		</div>

		<!-- Spieler 2 -->
		<div class="flex flex-col items-center gap-3">
			<h3 class="text-xl font-bold text-neon-blue">Spieler 2</h3>
			<div class="aspect-square w-full overflow-hidden rounded-xl border-2 border-neon-blue/30 bg-bg-card">
				{#if genPlayer === 2 && !$player2Image}
					<div class="flex h-full flex-col items-center justify-center gap-4">
						<div class="h-12 w-12 animate-spin rounded-full border-4 border-neon-blue/30 border-t-neon-blue"></div>
						<p class="text-neon-blue">Schritt {$generationStep} / {$generationTotal}</p>
					</div>
				{:else if $player2Image}
					<img src="data:image/webp;base64,{$player2Image}" alt="Spieler 2" class="h-full w-full object-cover" />
				{:else if $player2Submitted}
					<div class="flex h-full flex-col items-center justify-center gap-2 p-4">
						<span class="text-4xl text-neon-green">&#x2714;</span>
						<p class="text-center text-sm text-gray-400 italic break-words max-w-full">"{$player2Prompt}"</p>
					</div>
				{:else}
					<div class="flex h-full items-center justify-center p-4">
						{#if $player2Typing}
							<p class="text-center text-gray-400 italic break-words max-w-full animate-pulse">
								{$player2Typing}<span class="text-neon-blue">|</span>
							</p>
						{:else}
							<p class="text-gray-600">Warte auf Prompt...</p>
						{/if}
					</div>
				{/if}
			</div>
		</div>
	</div>
</div>
