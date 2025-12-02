import {
    Box,
    Button,
    Chip,
    Divider,
    Drawer,
    FormControl,
    InputLabel,
    MenuItem,
    OutlinedInput,
    Select,
    TextField,
    Typography,
} from '@mui/material';
import type {SelectChangeEvent} from '@mui/material/Select';
import {RECIPE_TAGS} from '../constants';
import type {RecipeFilters} from '../types';

interface RecipeFiltersDrawerProps {
    open: boolean;
    onClose: () => void;
    filters: RecipeFilters;
    availableCategories: string[];
    availableSources: string[];
    onCategoriesChange: (categories: string[]) => void;
    onTagsChange: (tags: string[]) => void;
    onSourceChange: (source: string) => void;
    onMaxTimeChange: (value: number | '') => void;
    onClearFilters: () => void;
}

const RecipeFiltersDrawer = ({
                                 open,
                                 onClose,
                                 filters,
                                 availableCategories,
                                 availableSources,
                                 onCategoriesChange,
                                 onTagsChange,
                                 onSourceChange,
                                 onMaxTimeChange,
                                 onClearFilters,
                             }: RecipeFiltersDrawerProps) => {
    const handleCategoryChange = (event: SelectChangeEvent<string[]>) => {
        const value = event.target.value;
        onCategoriesChange(typeof value === 'string' ? value.split(',') : value);
    };

    const handleTagsChange = (event: SelectChangeEvent<string[]>) => {
        const value = event.target.value;
        onTagsChange(typeof value === 'string' ? value.split(',') : value);
    };

    return (
        <Drawer
            anchor="right"
            open={open}
            onClose={onClose}
            sx={{
                '& .MuiDrawer-paper': {
                    width: {xs: '100%', sm: 400},
                    p: 3,
                },
            }}
        >
            <Typography variant="h6" sx={{mb: 3}}>
                Filter Recipes
            </Typography>

            <FormControl fullWidth sx={{mb: 3}}>
                <InputLabel id="categories-label">Categories</InputLabel>
                <Select
                    labelId="categories-label"
                    multiple
                    value={filters.categories}
                    onChange={handleCategoryChange}
                    input={<OutlinedInput label="Categories"/>}
                    renderValue={selected => (
                        <Box sx={{display: 'flex', flexWrap: 'wrap', gap: 0.5}}>
                            {selected.map(value => (
                                <Chip key={value} label={value} size="small"/>
                            ))}
                        </Box>
                    )}
                >
                    {availableCategories.map(category => (
                        <MenuItem key={category} value={category}>
                            {category}
                        </MenuItem>
                    ))}
                </Select>
            </FormControl>

            <FormControl fullWidth sx={{mb: 3}}>
                <InputLabel id="tags-label">Tags</InputLabel>
                <Select
                    labelId="tags-label"
                    multiple
                    value={filters.tags}
                    onChange={handleTagsChange}
                    input={<OutlinedInput label="Tags"/>}
                    renderValue={selected => (
                        <Box sx={{display: 'flex', flexWrap: 'wrap', gap: 0.5}}>
                            {selected.map(value => (
                                <Chip key={value} label={value} size="small"/>
                            ))}
                        </Box>
                    )}
                >
                    {RECIPE_TAGS.map(tag => (
                        <MenuItem key={tag} value={tag}>
                            {tag}
                        </MenuItem>
                    ))}
                </Select>
            </FormControl>

            <FormControl fullWidth sx={{mb: 3}}>
                <InputLabel id="source-label">Source</InputLabel>
                <Select
                    labelId="source-label"
                    value={filters.source}
                    onChange={event => onSourceChange(event.target.value)}
                    label="Source"
                >
                    {availableSources.map(source => (
                        <MenuItem key={source} value={source}>
                            {source}
                        </MenuItem>
                    ))}
                </Select>
            </FormControl>

            <FormControl fullWidth sx={{mb: 4}}>
                <TextField
                    label="Max Preparation Time (minutes)"
                    type="number"
                    value={filters.maxTime}
                    onChange={event => {
                        const value = event.target.value;
                        onMaxTimeChange(value === '' ? '' : Number(value));
                    }}
                    InputProps={{inputProps: {min: 0}}}
                />
            </FormControl>

            <Divider sx={{mb: 3}}/>

            <Box sx={{display: 'flex', justifyContent: 'space-between'}}>
                <Button onClick={onClearFilters}>
                    Clear All
                </Button>
                <Button variant="contained" onClick={onClose}>
                    Apply
                </Button>
            </Box>
        </Drawer>
    );
};

export default RecipeFiltersDrawer;
