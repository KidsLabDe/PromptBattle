<script lang="ts">
	import QRCode from 'qrcode';
	import { gameId, playerTokens, player1Connected, player2Connected } from '$lib/stores/gameStore';

	let canvas1: HTMLCanvasElement | undefined = $state();
	let canvas2: HTMLCanvasElement | undefined = $state();

	let p1Connected = $derived($player1Connected);
	let p2Connected = $derived($player2Connected);

	$effect(() => {
		const tokens = $playerTokens;
		const id = $gameId;
		if (tokens && id && canvas1 && canvas2) {
			const base = `${location.origin}/play/${id}`;
			const opts = { width: 280, margin: 2, color: { dark: '#ffffff', light: '#00000000' } };
			QRCode.toCanvas(canvas1, `${base}/${tokens['1']}`, opts);
			QRCode.toCanvas(canvas2, `${base}/${tokens['2']}`, opts);
		}
	});
</script>

<div class="flex min-h-[80vh] flex-col items-center justify-center gap-10">
	<h2 class="text-4xl font-black tracking-tight">
		<span class="text-neon-pink">SPIELER</span> SCANNEN
	</h2>
	<p class="text-lg text-gray-400">Scannt den QR-Code mit eurem Handy</p>

	<div class="grid grid-cols-2 gap-16">
		<!-- Spieler 1 -->
		<div class="flex flex-col items-center gap-4">
			<h3 class="text-2xl font-bold text-neon-pink">Spieler 1</h3>
			<div class="rounded-2xl border-2 p-4 transition-colors duration-300 {p1Connected ? 'border-neon-green shadow-lg shadow-neon-green/20' : 'border-neon-pink/30'}">
				<canvas bind:this={canvas1}></canvas>
			</div>
			{#if p1Connected}
				<span class="flex items-center gap-2 text-neon-green font-bold">
					<span class="inline-block h-3 w-3 rounded-full bg-neon-green animate-pulse"></span>
					Verbunden
				</span>
			{:else}
				<span class="text-gray-500">Warte auf Spieler...</span>
			{/if}
		</div>

		<!-- Spieler 2 -->
		<div class="flex flex-col items-center gap-4">
			<h3 class="text-2xl font-bold text-neon-blue">Spieler 2</h3>
			<div class="rounded-2xl border-2 p-4 transition-colors duration-300 {p2Connected ? 'border-neon-green shadow-lg shadow-neon-green/20' : 'border-neon-blue/30'}">
				<canvas bind:this={canvas2}></canvas>
			</div>
			{#if p2Connected}
				<span class="flex items-center gap-2 text-neon-green font-bold">
					<span class="inline-block h-3 w-3 rounded-full bg-neon-green animate-pulse"></span>
					Verbunden
				</span>
			{:else}
				<span class="text-gray-500">Warte auf Spieler...</span>
			{/if}
		</div>
	</div>

	{#if p1Connected && p2Connected}
		<p class="text-xl text-neon-green font-bold animate-pulse">
			Beide Spieler verbunden — Runde startet!
		</p>
	{/if}
</div>
