import {components} from '../../../types/api';

export type RecipeRead = components['schemas']['RecipeRead'];
export type RecipeUpdate = Omit<components['schemas']['RecipeUpdate'], 'image_url'>;

export interface RecipeFormTextFields {
    ingredients: string;
    instructions: string;
    categories: string;
}

export interface RecipeFormState {
    values: RecipeUpdate;
    text: RecipeFormTextFields;
    newImage: File | null;
    removeImage: boolean;
}

export type RecipeValueUpdater = <Key extends keyof RecipeUpdate>(
    key: Key,
    value: RecipeUpdate[Key]
) => void;

export type RecipeTextUpdater = (
    key: keyof RecipeFormTextFields,
    value: string
) => void;
