import {FC} from 'react';
import {Box, Rating, TextField} from '@mui/material';
import {RecipeFormState, RecipeTextUpdater, RecipeValueUpdater} from '../types';

interface RecipeMetadataFieldsProps {
    state: RecipeFormState;
    onChangeValue: RecipeValueUpdater;
    onChangeText: RecipeTextUpdater;
}

export const RecipeMetadataFields: FC<RecipeMetadataFieldsProps> = ({state, onChangeValue, onChangeText}) => (
    <Box sx={{display: 'flex', flexDirection: 'column', gap: 2}}>
        <TextField
            label="Title"
            fullWidth
            value={state.values.title}
            onChange={event => onChangeValue('title', event.target.value)}
        />
        <TextField
            label="Description"
            fullWidth
            multiline
            minRows={3}
            value={state.values.description}
            onChange={event => onChangeValue('description', event.target.value)}
        />
            <Rating
                name="rating"
                value={state.values.rating ?? 0}
                precision={1} // integer stars since backend uses SmallInteger
                onChange={(_, val) => onChangeValue("rating", val ?? null)}
            />
        <TextField
            label="Prep Time (min)"
            type="number"
            fullWidth
            value={state.values.prep_time}
            onChange={event => onChangeValue('prep_time', Number(event.target.value))}
        />
        <TextField
            label="Cook Time (min)"
            type="number"
            fullWidth
            value={state.values.cook_time}
            onChange={event => onChangeValue('cook_time', Number(event.target.value))}
        />
        <TextField
            label="Source"
            fullWidth
            value={state.values.source}
            onChange={event => onChangeValue('source', event.target.value)}
        />
        <TextField
            label="Categories"
            multiline
            fullWidth
            minRows={2}
            value={state.text.categories}
            onChange={event => onChangeText('categories', event.target.value)}
        />
    </Box>
);
