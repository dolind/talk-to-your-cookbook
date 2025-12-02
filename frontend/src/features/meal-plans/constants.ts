export const MEDIA_BASE_URL = import.meta.env.VITE_MEDIA_BASE_URL;

export type MealType = 'breakfast' | 'lunch' | 'dinner' | 'snack';

export const MEAL_TYPES: MealType[] = ['breakfast', 'lunch', 'dinner'];

export const formatDate = (date: Date) => date.toISOString().slice(0, 10);
