<script lang="ts">
	import { onDestroy } from 'svelte';
	import QRCode from 'qrcode';
	import { gameId, joinToken, player1Connected, player2Connected, connectedPlayerCount } from '$lib/stores/gameStore';

	let canvas: HTMLCanvasElement | undefined = $state();
	let lobbyCountdown = $state(60);
	let started = $state(false);

	let p1Connected = $derived($player1Connected);
	let p2Connected = $derived($player2Connected);
	let playerCount = $derived($connectedPlayerCount);

	// Animated hint rotator
	const hints = [
		'Triff das Zielbild mit deinem Prompt',
		'60 Sekunden pro Runde',
		'Schwelle steigt jede Runde',
		'Beschreibe das Bild so genau wie möglich',
		'Je ähnlicher, desto mehr Punkte',
	];
	let hintIndex = $state(0);
	let hintTimer = setInterval(() => {
		hintIndex = (hintIndex + 1) % hints.length;
	}, 4000);

	interface Props {
		onstart: () => void;
	}
	let { onstart }: Props = $props();

	function doStart() {
		if (started) return;
		started = true;
		onstart();
	}

	// Auto-start when 2 players connect
	$effect(() => {
		if (playerCount >= 2) {
			doStart();
		}
	});

	// Lobby countdown timer - only ticks when at least 1 player connected
	let timer = setInterval(() => {
		if (playerCount >= 1) {
			lobbyCountdown--;
			if (lobbyCountdown <= 0) {
				doStart();
			}
		}
	}, 1000);

	onDestroy(() => {
		clearInterval(timer);
		clearInterval(hintTimer);
	});

	let joinUrl = $state('');

	$effect(() => {
		const token = $joinToken;
		const id = $gameId;
		if (token && id && canvas) {
			joinUrl = `${location.origin}/play/${id}/${token}`;
			const opts = { width: 350, margin: 2, color: { dark: '#ffffff', light: '#00000000' } };
			QRCode.toCanvas(canvas, joinUrl, opts);
		}
	});
</script>

<div class="flex min-h-[90vh] flex-col items-center justify-center gap-6">
	<!-- Big title -->
	<h1 class="font-pixel text-8xl tracking-tight">
		<span class="text-neon-pink">PROMPT</span>
		<span class="text-neon-blue">BATTLE</span>
	</h1>

	<p class="max-w-2xl text-center text-2xl text-gray-400">
		Scannt den QR-Code und beschreibt das Zielbild mit einem Prompt.
		KI generiert euer Bild — wer am nächsten dran ist, gewinnt!
	</p>

	<!-- Main content: QR + rules side by side -->
	<div class="flex items-center gap-16">
		<!-- Rules -->
		<div class="flex flex-col gap-4 text-2xl text-gray-300">
			<p class="font-pixel text-neon-yellow">SO GEHT'S:</p>
			<p>&#x1F3AF; Triff das Zielbild mit deinem Prompt</p>
			<p>&#x23F1;&#xFE0F; 60 Sekunden pro Runde</p>
			<p>&#x1F4C8; Schwelle steigt jede Runde</p>
			<p>&#x1F916; KI generiert &amp; bewertet</p>
		</div>

		<!-- QR Code -->
		<div class="flex flex-col items-center gap-4">
			<a href={joinUrl} target="_blank" class="rounded-2xl border-2 p-6 transition-colors duration-300 {playerCount > 0 ? 'border-neon-green shadow-lg shadow-neon-green/20' : 'border-neon-pink/30'} cursor-pointer hover:scale-105">
				<canvas bind:this={canvas}></canvas>
			</a>

			<!-- Player status -->
			<div class="flex flex-col gap-2 text-center">
				{#if p1Connected}
					<span class="flex items-center gap-2 text-neon-green text-xl font-pixel">
						<span class="inline-block h-3 w-3 rounded-full bg-neon-green animate-pulse"></span>
						Spieler 1 verbunden
					</span>
				{/if}
				{#if p2Connected}
					<span class="flex items-center gap-2 text-neon-blue text-xl font-pixel">
						<span class="inline-block h-3 w-3 rounded-full bg-neon-blue animate-pulse"></span>
						Spieler 2 verbunden
					</span>
				{/if}
				{#if playerCount === 0}
					<span class="font-pixel text-xl text-gray-500">Warte auf Spieler...</span>
				{/if}
			</div>
		</div>
	</div>

	<!-- Animated hints -->
	<div class="h-20 flex items-center justify-center">
		{#key hintIndex}
			<p class="font-pixel text-5xl text-neon-yellow animate-hint-fade">{hints[hintIndex]}</p>
		{/key}
	</div>

	<!-- Start button + countdown -->
	<div class="flex flex-col items-center gap-4">
		{#if playerCount >= 1}
			<button
				onclick={doStart}
				class="font-pixel cursor-pointer rounded-2xl bg-neon-green px-20 py-6 text-3xl
					text-black transition-all duration-200
					hover:scale-105 hover:shadow-xl hover:shadow-neon-green/30"
			>
				STARTEN
			</button>
			<p class="font-pixel text-lg text-gray-500">
				{#if playerCount === 1}
					1 Spieler — Einzelspieler
				{:else}
					2 Spieler — Mehrspieler
				{/if}
			</p>
		{/if}

		<p class="text-xl text-gray-500">
			{#if playerCount === 0}
				Auto-Start in <span class="font-pixel font-bold text-neon-yellow">{lobbyCountdown}s</span> wenn Spieler verbunden
			{:else}
				Auto-Start in <span class="font-pixel font-bold text-neon-yellow">{lobbyCountdown}s</span>
			{/if}
		</p>
	</div>

	<p class="text-sm text-gray-600">
		Bilder werden über Google Gemini API generiert und bewertet
	</p>
</div>
