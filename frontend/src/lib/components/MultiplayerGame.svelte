<script lang="ts">
	import {
		targetImage, currentRound, threshold, timeRemaining,
		player1Image, player2Image, player1Submitted, player2Submitted,
		player1Typing, player2Typing, player1Prompt, player2Prompt,
		generatingPlayer, generationStep, generationTotal,
		player1Wins, player2Wins, isPhoneControl,
		player1RevealedScore, player2RevealedScore, revealActive,
	} from '$lib/stores/gameStore';
	import Timer from './Timer.svelte';

	let src = $derived($targetImage ? `/api/images/target/${$targetImage}` : '');
	let genPlayer = $derived($generatingPlayer);
	let singleMode = $derived($isPhoneControl);

	// Switch to generation layout when both submitted or generation started
	let generatingPhase = $derived(
		($player1Submitted && $player2Submitted) || genPlayer > 0 || !!$player1Image || !!$player2Image
	);
</script>

<div class="flex h-full flex-col gap-4">
	<!-- Header -->
	<div class="flex items-center justify-between">
		<span class="rounded-lg bg-neon-pink/20 px-3 py-1 font-bold text-neon-pink">
			Runde {$currentRound}
		</span>
		{#if !singleMode}
			<div class="flex gap-4 text-lg font-bold">
				<span class="text-neon-pink">{$player1Wins}</span>
				<span class="text-gray-500">:</span>
				<span class="text-neon-blue">{$player2Wins}</span>
			</div>
		{:else}
			<span class="text-sm text-gray-400">Mindestscore: {$threshold}%</span>
		{/if}
		<Timer />
	</div>

	{#if singleMode}
		<!-- Single player via phone: target + player area side by side -->
		<div class="grid grid-cols-2 gap-8">
			<div class="flex flex-col items-center gap-3">
				<h3 class="text-sm font-semibold uppercase tracking-widest text-neon-yellow">Zielbild</h3>
				<div class="aspect-square w-full overflow-hidden rounded-xl border-2 border-neon-yellow/30 bg-bg-card">
					{#if src}
						<img {src} alt="Zielbild" class="h-full w-full object-cover" />
					{/if}
				</div>
			</div>

			<div class="flex flex-col items-center gap-3">
				<h3 class="text-sm font-semibold uppercase tracking-widest text-neon-pink">Dein Bild</h3>
				<div class="aspect-square w-full overflow-hidden rounded-xl border-2 border-neon-pink/30 bg-bg-card">
					{#if genPlayer > 0 && !$player1Image}
						<div class="flex h-full flex-col items-center justify-center gap-4">
							<div class="h-12 w-12 animate-spin rounded-full border-4 border-neon-pink/30 border-t-neon-pink"></div>
							<p class="font-pixel text-neon-pink">Bild wird generiert...</p>
							<div class="w-3/4 h-1.5 rounded-full bg-gray-800 overflow-hidden">
								<div class="h-full w-full rounded-full bg-neon-pink/50 animate-pulse"></div>
							</div>
						</div>
					{:else if $player1Image}
						<img src="data:image/webp;base64,{$player1Image}" alt="Generiert" class="h-full w-full object-cover" />
					{:else if $player1Submitted}
						<div class="flex h-full flex-col items-center justify-center gap-2 p-4">
							<span class="text-4xl text-neon-green">&#x2714;</span>
							<p class="text-center text-xl text-gray-400 italic break-words max-w-full">"{$player1Prompt}"</p>
						</div>
					{:else}
						<div class="flex h-full items-center justify-center p-4">
							{#if $player1Typing}
								<p class="text-center text-xl text-gray-400 italic break-words max-w-full animate-pulse">
									{$player1Typing}<span class="text-neon-pink">|</span>
								</p>
							{:else}
								<p class="text-gray-600">Warte auf Prompt...</p>
							{/if}
						</div>
					{/if}
				</div>
			</div>
		</div>

	{:else if !generatingPhase}
		<!-- Multiplayer Phase 1: Prompt-Eingabe — großes Zielbild -->
		<div class="flex flex-col items-center gap-8">
			<div class="w-full max-w-2xl">
				<h3 class="mb-3 text-center font-semibold uppercase tracking-widest text-neon-yellow">Zielbild</h3>
				<div class="aspect-square w-full overflow-hidden rounded-2xl border-2 border-neon-yellow/30 bg-bg-card">
					{#if src}
						<img {src} alt="Zielbild" class="h-full w-full object-cover" />
					{/if}
				</div>
			</div>

			<!-- Player status -->
			<div class="grid grid-cols-2 gap-12 w-full max-w-2xl">
				<div class="flex flex-col items-center gap-2">
					<h3 class="font-pixel text-2xl text-neon-pink">Spieler 1</h3>
					{#if $player1Submitted}
						<div class="flex items-center gap-2">
							<span class="text-3xl text-neon-green">&#x2714;</span>
							<p class="text-xl text-gray-400 italic break-words max-w-xs text-center">"{$player1Prompt}"</p>
						</div>
					{:else if $player1Typing}
						<p class="text-xl text-gray-400 italic break-words max-w-xs text-center animate-pulse">
							{$player1Typing}<span class="text-neon-pink">|</span>
						</p>
					{:else}
						<p class="text-lg text-gray-600">Warte auf Prompt...</p>
					{/if}
				</div>
				<div class="flex flex-col items-center gap-2">
					<h3 class="font-pixel text-2xl text-neon-blue">Spieler 2</h3>
					{#if $player2Submitted}
						<div class="flex items-center gap-2">
							<span class="text-3xl text-neon-green">&#x2714;</span>
							<p class="text-xl text-gray-400 italic break-words max-w-xs text-center">"{$player2Prompt}"</p>
						</div>
					{:else if $player2Typing}
						<p class="text-xl text-gray-400 italic break-words max-w-xs text-center animate-pulse">
							{$player2Typing}<span class="text-neon-blue">|</span>
						</p>
					{:else}
						<p class="text-lg text-gray-600">Warte auf Prompt...</p>
					{/if}
				</div>
			</div>
		</div>

	{:else}
		<!-- Multiplayer Phase 2: Generation/Result — kleines Zielbild, große Spielerbilder -->
		<div class="flex justify-center">
			<div class="w-40">
				<h3 class="mb-1 text-center text-sm font-semibold uppercase tracking-widest text-neon-yellow">Zielbild</h3>
				<div class="aspect-square w-full overflow-hidden rounded-xl border-2 border-neon-yellow/30 bg-bg-card">
					{#if src}
						<img {src} alt="Zielbild" class="h-full w-full object-cover" />
					{/if}
				</div>
			</div>
		</div>

		<!-- Two player columns -->
		<div class="grid min-h-0 flex-1 grid-cols-2 gap-8">
			<!-- Spieler 1 -->
			<div class="flex min-h-0 flex-col items-center gap-2">
				<h3 class="font-pixel text-xl text-neon-pink">Spieler 1</h3>
				<div class="aspect-square w-full max-h-[50vh] overflow-hidden rounded-xl border-2 border-neon-pink/30 bg-bg-card">
					{#if genPlayer > 0 && !$player1Image}
						<div class="flex h-full flex-col items-center justify-center gap-4">
							<div class="h-12 w-12 animate-spin rounded-full border-4 border-neon-pink/30 border-t-neon-pink"></div>
							<p class="font-pixel text-neon-pink">Bild wird generiert...</p>
							<div class="w-3/4 h-1.5 rounded-full bg-gray-800 overflow-hidden">
								<div class="h-full w-full rounded-full bg-neon-pink/50 animate-pulse"></div>
							</div>
						</div>
					{:else if $player1Image}
						<img src="data:image/webp;base64,{$player1Image}" alt="Spieler 1" class="h-full w-full object-cover" />
					{:else}
						<div class="flex h-full flex-col items-center justify-center gap-2 p-4">
							<span class="text-4xl text-neon-green">&#x2714;</span>
							<p class="text-center text-xl text-gray-400 italic break-words max-w-full">"{$player1Prompt}"</p>
						</div>
					{/if}
				</div>
				{#if $revealActive}
					<div class="w-full mt-2">
						<div class="h-3 w-full overflow-hidden rounded-full bg-gray-800 border border-gray-700">
							<div class="h-full rounded-full bg-neon-pink transition-all duration-[75ms]"
								style="width: {$player1RevealedScore}%"></div>
						</div>
						<p class="mt-1 text-center font-pixel text-2xl text-neon-pink">
							{$player1RevealedScore.toFixed(1)}%
						</p>
					</div>
				{/if}
			</div>

			<!-- Spieler 2 -->
			<div class="flex min-h-0 flex-col items-center gap-2">
				<h3 class="font-pixel text-xl text-neon-blue">Spieler 2</h3>
				<div class="aspect-square w-full max-h-[50vh] overflow-hidden rounded-xl border-2 border-neon-blue/30 bg-bg-card">
					{#if genPlayer > 0 && !$player2Image}
						<div class="flex h-full flex-col items-center justify-center gap-4">
							<div class="h-12 w-12 animate-spin rounded-full border-4 border-neon-blue/30 border-t-neon-blue"></div>
							<p class="font-pixel text-neon-blue">Bild wird generiert...</p>
							<div class="w-3/4 h-1.5 rounded-full bg-gray-800 overflow-hidden">
								<div class="h-full w-full rounded-full bg-neon-blue/50 animate-pulse"></div>
							</div>
						</div>
					{:else if $player2Image}
						<img src="data:image/webp;base64,{$player2Image}" alt="Spieler 2" class="h-full w-full object-cover" />
					{:else}
						<div class="flex h-full flex-col items-center justify-center gap-2 p-4">
							<span class="text-4xl text-neon-green">&#x2714;</span>
							<p class="text-center text-xl text-gray-400 italic break-words max-w-full">"{$player2Prompt}"</p>
						</div>
					{/if}
				</div>
				{#if $revealActive}
					<div class="w-full mt-2">
						<div class="h-3 w-full overflow-hidden rounded-full bg-gray-800 border border-gray-700">
							<div class="h-full rounded-full bg-neon-blue transition-all duration-[75ms]"
								style="width: {$player2RevealedScore}%"></div>
						</div>
						<p class="mt-1 text-center font-pixel text-2xl text-neon-blue">
							{$player2RevealedScore.toFixed(1)}%
						</p>
					</div>
				{/if}
			</div>
		</div>
	{/if}
</div>
