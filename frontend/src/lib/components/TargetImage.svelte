<script lang="ts">
	import { targetImage } from '$lib/stores/gameStore';

	let src = $derived($targetImage ? `/api/images/target/${$targetImage}` : '');
</script>

<div class="flex flex-col items-center gap-2">
	<h3 class="text-sm font-semibold uppercase tracking-widest text-neon-pink">Zielbild</h3>
	<div class="aspect-square w-full overflow-hidden rounded-xl border-2 border-neon-pink/30 bg-bg-card">
		{#if src}
			<img {src} alt="Zielbild" class="h-full w-full object-cover" />
		{:else}
			<div class="flex h-full items-center justify-center text-gray-600">Kein Bild</div>
		{/if}
	</div>
</div>
