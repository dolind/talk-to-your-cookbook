import {FC} from 'react';
import {Box, TextField} from '@mui/material';
import {RecipeFormState, RecipeTextUpdater} from '../types';

interface RecipeContentFieldsProps {
    state: RecipeFormState;
    onChangeText: RecipeTextUpdater;
}

export const RecipeContentFields: FC<RecipeContentFieldsProps> = ({state, onChangeText}) => (
    <Box sx={{display: 'flex', flexDirection: 'column', gap: 2}}>
        <TextField
            label="Ingredients (one per line)"
            multiline
            fullWidth
            minRows={4}
            value={state.text.ingredients}
            onChange={event => onChangeText('ingredients', event.target.value)}
        />
        <TextField
            label="Instructions (one step per block, separated by empty lines)"
            multiline
            fullWidth
            minRows={4}
            value={state.text.instructions}
            onChange={event => onChangeText('instructions', event.target.value)}
            helperText="Separate each instruction block with a blank line"
        />
    </Box>
);
