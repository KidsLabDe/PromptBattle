<script lang="ts">
	import { generatedImage, generationStep, generationTotal, uiState } from '$lib/stores/gameStore';

	let isGenerating = $derived($uiState === 'generating');
	let hasImage = $derived(!!$generatedImage);
</script>

<div class="flex flex-col items-center gap-2">
	<h3 class="text-sm font-semibold uppercase tracking-widest text-neon-green">Generiert</h3>
	<div class="aspect-square w-full overflow-hidden rounded-xl border-2 border-neon-green/30 bg-bg-card">
		{#if isGenerating}
			<div class="flex h-full flex-col items-center justify-center gap-4">
				<div class="h-12 w-12 animate-spin rounded-full border-4 border-neon-green/30 border-t-neon-green"></div>
				<p class="text-neon-green">
					Schritt {$generationStep} / {$generationTotal}
				</p>
			</div>
		{:else if hasImage}
			<img src="data:image/webp;base64,{$generatedImage}" alt="Generiert" class="h-full w-full object-cover" />
		{:else}
			<div class="flex h-full items-center justify-center text-gray-600">
				Warte auf Prompt...
			</div>
		{/if}
	</div>
</div>
