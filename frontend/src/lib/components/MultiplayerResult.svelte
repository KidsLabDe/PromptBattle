<script lang="ts">
	import {
		targetImage, currentRound, threshold,
		player1Image, player2Image,
		player1Score, player2Score,
		player1Prompt, player2Prompt,
		player1Reason, player2Reason,
		roundWinner, player1Wins, player2Wins,
		autoCountdown, isPhoneControl,
		currentScore, currentPassed,
	} from '$lib/stores/gameStore';

	let src = $derived($targetImage ? `/api/images/target/${$targetImage}` : '');
	let winner = $derived($roundWinner);
	let countdown = $derived($autoCountdown);
	let singleMode = $derived($isPhoneControl);
</script>

<div class="flex h-full flex-col gap-4 overflow-hidden">
	{#if singleMode}
		<!-- Single player via phone result -->
		<div class="flex items-center justify-between">
			<span class="rounded-lg bg-neon-pink/20 px-3 py-1 font-bold text-neon-pink">
				Runde {$currentRound}
			</span>
		</div>

		<div class="text-center">
			{#if $currentPassed}
				<h2 class="font-pixel text-5xl text-neon-green">GESCHAFFT!</h2>
			{:else}
				<h2 class="font-pixel text-5xl text-red-500">NICHT GESCHAFFT</h2>
			{/if}
		</div>

		<div class="grid grid-cols-2 gap-8">
			<div class="flex flex-col items-center gap-3">
				<h4 class="text-sm font-semibold uppercase tracking-widest text-neon-yellow">Zielbild</h4>
				<div class="aspect-square w-full overflow-hidden rounded-xl border-2 border-neon-yellow/30 bg-bg-card">
					{#if src}
						<img {src} alt="Zielbild" class="h-full w-full object-cover" />
					{/if}
				</div>
			</div>

			<div class="flex flex-col items-center gap-3">
				<h4 class="text-sm font-semibold uppercase tracking-widest text-neon-pink">Dein Bild</h4>
				<div class="aspect-square w-full overflow-hidden rounded-xl border-2 border-neon-pink/30 bg-bg-card">
					{#if $player1Image}
						<img src="data:image/webp;base64,{$player1Image}" alt="Generiert" class="h-full w-full object-cover" />
					{/if}
				</div>
			</div>
		</div>

		<div class="text-center">
			<span class="font-pixel text-5xl" class:text-neon-green={$currentPassed} class:text-red-500={!$currentPassed}>
				{$currentScore.toFixed(1)}%
			</span>
			<p class="mt-2 text-gray-400">Mindestscore: {$threshold}%</p>
			<p class="mt-1 text-sm text-gray-500 italic">"{$player1Prompt}"</p>
			{#if $player1Reason}
				<p class="mt-1 text-xs text-gray-500">{$player1Reason}</p>
			{/if}
		</div>

		{#if $currentPassed && countdown > 0}
			<div class="text-center">
				<p class="text-lg text-gray-400">
					Nächste Runde in <span class="font-bold text-neon-green">{countdown}</span>
				</p>
			</div>
		{/if}
	{:else}
		<!-- Multiplayer result -->
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

		<div class="text-center">
			{#if winner === 1}
				<h2 class="font-pixel text-5xl text-neon-pink">Spieler 1 gewinnt!</h2>
			{:else if winner === 2}
				<h2 class="font-pixel text-5xl text-neon-blue">Spieler 2 gewinnt!</h2>
			{:else}
				<h2 class="font-pixel text-5xl text-neon-yellow">Unentschieden!</h2>
			{/if}
		</div>

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

		<div class="grid min-h-0 flex-1 grid-cols-2 gap-8">
			<div class="flex min-h-0 flex-col items-center gap-2 {winner === 1 ? 'ring-4 ring-neon-pink rounded-2xl p-2' : ''}">
				<h3 class="font-pixel text-xl text-neon-pink">Spieler 1</h3>
				<div class="aspect-square w-full max-h-[45vh] overflow-hidden rounded-xl border-2 border-neon-pink/30 bg-bg-card">
					{#if $player1Image}
						<img src="data:image/webp;base64,{$player1Image}" alt="Spieler 1" class="h-full w-full object-cover" />
					{/if}
				</div>
				<span class="font-pixel text-4xl {winner === 1 ? 'text-neon-green' : winner === 2 ? 'text-red-500' : 'text-neon-yellow'}">
					{$player1Score.toFixed(1)}%
				</span>
				<p class="max-w-xs text-center text-sm text-gray-400 italic">"{$player1Prompt}"</p>
				{#if $player1Reason}
					<p class="max-w-xs text-center text-xs text-gray-500">{$player1Reason}</p>
				{/if}
			</div>

			<div class="flex min-h-0 flex-col items-center gap-2 {winner === 2 ? 'ring-4 ring-neon-blue rounded-2xl p-2' : ''}">
				<h3 class="font-pixel text-xl text-neon-blue">Spieler 2</h3>
				<div class="aspect-square w-full max-h-[45vh] overflow-hidden rounded-xl border-2 border-neon-blue/30 bg-bg-card">
					{#if $player2Image}
						<img src="data:image/webp;base64,{$player2Image}" alt="Spieler 2" class="h-full w-full object-cover" />
					{/if}
				</div>
				<span class="font-pixel text-4xl {winner === 2 ? 'text-neon-green' : winner === 1 ? 'text-red-500' : 'text-neon-yellow'}">
					{$player2Score.toFixed(1)}%
				</span>
				<p class="max-w-xs text-center text-sm text-gray-400 italic">"{$player2Prompt}"</p>
				{#if $player2Reason}
					<p class="max-w-xs text-center text-xs text-gray-500">{$player2Reason}</p>
				{/if}
			</div>
		</div>

		{#if countdown > 0}
			<div class="text-center">
				<p class="text-lg text-gray-400">
					Nächste Runde in <span class="font-bold text-neon-green">{countdown}</span>
				</p>
			</div>
		{/if}
	{/if}
</div>
