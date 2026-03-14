<script lang="ts">
	import {
		targetImage, currentRound,
		player1Image, player2Image,
		player1Score, player2Score,
		player1Prompt, player2Prompt,
		roundWinner, player1Wins, player2Wins,
		autoCountdown,
	} from '$lib/stores/gameStore';

	let src = $derived($targetImage ? `/api/images/target/${$targetImage}` : '');
	let winner = $derived($roundWinner);
	let countdown = $derived($autoCountdown);
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
	</div>

	<!-- Winner announcement -->
	<div class="text-center">
		{#if winner === 1}
			<h2 class="text-5xl font-black text-neon-pink">Spieler 1 gewinnt!</h2>
		{:else if winner === 2}
			<h2 class="text-5xl font-black text-neon-blue">Spieler 2 gewinnt!</h2>
		{:else}
			<h2 class="text-5xl font-black text-neon-yellow">Unentschieden!</h2>
		{/if}
	</div>

	<!-- Target image small -->
	<div class="flex justify-center">
		<div class="w-36">
			<h4 class="mb-1 text-center text-xs font-semibold uppercase tracking-widest text-neon-yellow">Zielbild</h4>
			<div class="aspect-square overflow-hidden rounded-lg border border-neon-yellow/30 bg-bg-card">
				{#if src}
					<img {src} alt="Zielbild" class="h-full w-full object-cover" />
				{/if}
			</div>
		</div>
	</div>

	<!-- Two player results -->
	<div class="grid grid-cols-2 gap-8">
		<!-- Spieler 1 -->
		<div class="flex flex-col items-center gap-3 {winner === 1 ? 'ring-4 ring-neon-pink rounded-2xl p-2' : ''}">
			<h3 class="text-xl font-bold text-neon-pink">Spieler 1</h3>
			<div class="aspect-square w-full overflow-hidden rounded-xl border-2 border-neon-pink/30 bg-bg-card">
				{#if $player1Image}
					<img src="data:image/webp;base64,{$player1Image}" alt="Spieler 1" class="h-full w-full object-cover" />
				{/if}
			</div>
			<span class="text-4xl font-bold {winner === 1 ? 'text-neon-green' : winner === 2 ? 'text-red-500' : 'text-neon-yellow'}">
				{$player1Score.toFixed(1)}%
			</span>
			<p class="max-w-xs text-center text-sm text-gray-400 italic">"{$player1Prompt}"</p>
		</div>

		<!-- Spieler 2 -->
		<div class="flex flex-col items-center gap-3 {winner === 2 ? 'ring-4 ring-neon-blue rounded-2xl p-2' : ''}">
			<h3 class="text-xl font-bold text-neon-blue">Spieler 2</h3>
			<div class="aspect-square w-full overflow-hidden rounded-xl border-2 border-neon-blue/30 bg-bg-card">
				{#if $player2Image}
					<img src="data:image/webp;base64,{$player2Image}" alt="Spieler 2" class="h-full w-full object-cover" />
				{/if}
			</div>
			<span class="text-4xl font-bold {winner === 2 ? 'text-neon-green' : winner === 1 ? 'text-red-500' : 'text-neon-yellow'}">
				{$player2Score.toFixed(1)}%
			</span>
			<p class="max-w-xs text-center text-sm text-gray-400 italic">"{$player2Prompt}"</p>
		</div>
	</div>

	<!-- Auto-advance countdown -->
	{#if countdown > 0}
		<div class="text-center">
			<p class="text-lg text-gray-400">
				Nächste Runde in <span class="font-bold text-neon-green">{countdown}</span>
			</p>
		</div>
	{/if}
</div>
