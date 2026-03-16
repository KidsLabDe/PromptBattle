import { writable, derived } from 'svelte/store';

export type UIState = 'title' | 'lobby' | 'playing' | 'generating' | 'comparing' | 'result' | 'gameover';
export type GameMode = 'single' | 'multi';

export interface RoundResult {
	round: number;
	prompt: string;
	score: number;
	threshold: number;
	passed: boolean;
	generated_image: string;
	target_image: string;
}

export const uiState = writable<UIState>('title');
export const gameMode = writable<GameMode>('single');
export const gameId = writable<string>('');
export const currentRound = writable<number>(1);
export const threshold = writable<number>(25);
export const timeRemaining = writable<number>(60);
export const targetImage = writable<string>('');
export const generatedImage = writable<string>('');
export const generationStep = writable<number>(0);
export const generationTotal = writable<number>(4);
export const currentScore = writable<number>(0);
export const currentPassed = writable<boolean>(false);
export const history = writable<RoundResult[]>([]);

// Multiplayer stores
export const joinToken = writable<string>('');
export const playerTokens = writable<{ '1': string; '2': string } | null>(null);
export const connectedPlayerCount = writable<number>(0);
export const isPhoneControl = writable<boolean>(false);
export const player1Image = writable<string>('');
export const player2Image = writable<string>('');
export const player1Score = writable<number>(0);
export const player2Score = writable<number>(0);
export const player1Prompt = writable<string>('');
export const player2Prompt = writable<string>('');
export const player1Submitted = writable<boolean>(false);
export const player2Submitted = writable<boolean>(false);
export const generatingPlayer = writable<number>(0);
export const roundWinner = writable<number>(0);
export const player1Wins = writable<number>(0);
export const player2Wins = writable<number>(0);
export const player1Connected = writable<boolean>(false);
export const player2Connected = writable<boolean>(false);
export const player1Typing = writable<string>('');
export const player2Typing = writable<string>('');
export const autoCountdown = writable<number>(0);
export const compareCountdown = writable<number>(0);
export const player1RevealedScore = writable<number>(0);
export const player2RevealedScore = writable<number>(0);
export const revealActive = writable<boolean>(false);

export const formattedTime = derived(timeRemaining, ($t) => {
	const m = Math.floor($t / 60);
	const s = $t % 60;
	return `${m}:${s.toString().padStart(2, '0')}`;
});

export function resetGame() {
	uiState.set('title');
	gameMode.set('single');
	gameId.set('');
	currentRound.set(1);
	threshold.set(25);
	timeRemaining.set(60);
	targetImage.set('');
	generatedImage.set('');
	generationStep.set(0);
	currentScore.set(0);
	currentPassed.set(false);
	history.set([]);
	joinToken.set('');
	connectedPlayerCount.set(0);
	isPhoneControl.set(false);
	playerTokens.set(null);
	player1Image.set('');
	player2Image.set('');
	player1Score.set(0);
	player2Score.set(0);
	player1Prompt.set('');
	player2Prompt.set('');
	player1Submitted.set(false);
	player2Submitted.set(false);
	generatingPlayer.set(0);
	roundWinner.set(0);
	player1Wins.set(0);
	player2Wins.set(0);
	player1Connected.set(false);
	player2Connected.set(false);
	player1Typing.set('');
	player2Typing.set('');
	autoCountdown.set(0);
	compareCountdown.set(0);
}

export function resetMultiRound() {
	player1Image.set('');
	player2Image.set('');
	player1Score.set(0);
	player2Score.set(0);
	player1Prompt.set('');
	player2Prompt.set('');
	player1Submitted.set(false);
	player2Submitted.set(false);
	generatingPlayer.set(0);
	roundWinner.set(0);
	generationStep.set(0);
	player1Typing.set('');
	player2Typing.set('');
	autoCountdown.set(0);
	compareCountdown.set(0);
	player1RevealedScore.set(0);
	player2RevealedScore.set(0);
	revealActive.set(false);
}
