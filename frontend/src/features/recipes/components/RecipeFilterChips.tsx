import {Box, Button, Chip} from '@mui/material';
import type {RecipeFilters} from '../types';

interface RecipeFilterChipsProps {
    filters: RecipeFilters;
    onRemoveCategory: (category: string) => void;
    onRemoveTag: (tag: string) => void;
    onClearSource: () => void;
    onClearMaxTime: () => void;
    onClearAll: () => void;
}

const RecipeFilterChips = ({
                               filters,
                               onRemoveCategory,
                               onRemoveTag,
                               onClearSource,
                               onClearMaxTime,
                               onClearAll,
                           }: RecipeFilterChipsProps) => {
    const hasFilters =
        filters.categories.length > 0 ||
        filters.tags.length > 0 ||
        filters.source.length > 0 ||
        filters.maxTime !== '';

    if (!hasFilters) {
        return null;
    }

    return (
        <Box sx={{display: 'flex', flexWrap: 'wrap', gap: 1, mb: 3}}>
            {filters.categories.map(category => (
                <Chip
                    key={category}
                    label={category}
                    onDelete={() => onRemoveCategory(category)}
                    color="primary"
                    variant="outlined"
                />
            ))}
            {filters.tags.map(tag => (
                <Chip
                    key={tag}
                    label={tag}
                    onDelete={() => onRemoveTag(tag)}
                    color="secondary"
                    variant="outlined"
                />
            ))}
            {filters.source && (
                <Chip
                    label={`Source: ${filters.source}`}
                    onDelete={onClearSource}
                    color="info"
                    variant="outlined"
                />
            )}
            {filters.maxTime !== '' && (
                <Chip
                    label={`Prep time: ≤ ${filters.maxTime} min`}
                    onDelete={onClearMaxTime}
                    color="default"
                    variant="outlined"
                />
            )}
            <Button size="small" onClick={onClearAll}>
                Clear All
            </Button>
        </Box>
    );
};

export default RecipeFilterChips;
