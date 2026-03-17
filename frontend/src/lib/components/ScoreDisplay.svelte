<script lang="ts">
	import { currentScore, threshold, currentPassed, player1Reason } from '$lib/stores/gameStore';

	let score = $derived($currentScore);
	let thresh = $derived($threshold);
	let passed = $derived($currentPassed);
</script>

<div class="flex flex-col items-center gap-4">
	<div class="w-full max-w-md">
		<!-- Score bar -->
		<div class="relative h-8 w-full overflow-hidden rounded-full bg-bg-card border border-gray-700">
			<!-- Threshold marker -->
			<div
				class="absolute top-0 h-full w-0.5 bg-white/60 z-10"
				style="left: {thresh}%"
			></div>
			<div
				class="absolute top-[-1.5rem] text-xs text-gray-400 z-10"
				style="left: {thresh}%; transform: translateX(-50%)"
			>
				{thresh}%
			</div>
			<!-- Score fill -->
			<div
				class="h-full rounded-full transition-all duration-1000 animate-score-fill"
				class:bg-neon-green={passed}
				class:bg-red-500={!passed}
				style="width: {score}%"
			></div>
		</div>
		<!-- Score text -->
		<div class="mt-4 text-center">
			<span
				class="font-pixel text-5xl"
				class:text-neon-green={passed}
				class:text-red-500={!passed}
			>
				{score.toFixed(1)}%
			</span>
		</div>
		<p class="font-pixel mt-2 text-center text-lg" class:text-neon-green={passed} class:text-red-500={!passed}>
			{passed ? 'GESCHAFFT!' : 'NICHT BESTANDEN'}
		</p>
		{#if $player1Reason}
			<p class="mt-2 text-center text-sm text-gray-500">{$player1Reason}</p>
		{/if}
	</div>
</div>
