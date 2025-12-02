import {Box, Rating, Typography} from '@mui/material';
import {RecipeMetadataFields} from './components/RecipeMetadataFields';
import {RecipeContentFields} from './components/RecipeContentFields';
import {RecipeImageField} from './components/RecipeImageField';
import {RecipeFormActions} from './components/RecipeFormActions';
import {useRecipeForm} from './hooks/useRecipeForm';
import {RecipeRead} from './types';

interface RecipeFormProps {
    initialData?: RecipeRead;
    onSuccess: (recipe: RecipeRead) => void;
    onCancel: () => void;
}

const RecipeForm = ({initialData, onSuccess, onCancel}: RecipeFormProps) => {
    const {state, isNew, updateValue, updateText, setNewImage, setRemoveImage, saveRecipe} = useRecipeForm(initialData);

    const handleSave = async () => {
        try {
            const saved = await saveRecipe();
            onSuccess(saved);
        } catch (error) {
            console.error('Failed to save recipe', error);
            alert('Save failed');
        }
    };

    return (
        <Box sx={{maxWidth: 800, mx: 'auto', p: 4, display: 'flex', flexDirection: 'column', gap: 3}}>
            <Typography variant="h4" gutterBottom>
                {isNew ? 'Create New Recipe' : 'Edit Recipe'}
            </Typography>

            <RecipeMetadataFields state={state} onChangeValue={updateValue} onChangeText={updateText}/>

            <RecipeImageField
                imageUrl={initialData?.image_url}
                removeImage={state.removeImage}
                onUpload={setNewImage}
                onRemove={setRemoveImage}
            />
            {state.newImage && (
                <Typography variant="caption" color="text.secondary">
                    Selected file: {state.newImage.name}
                </Typography>
            )}

            <RecipeContentFields state={state} onChangeText={updateText}/>

            <RecipeFormActions onSave={handleSave} onCancel={onCancel}/>
        </Box>
    );
};

export default RecipeForm;
