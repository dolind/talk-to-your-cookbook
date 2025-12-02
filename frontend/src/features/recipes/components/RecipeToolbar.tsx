import FilterListIcon from '@mui/icons-material/FilterList';
import SearchIcon from '@mui/icons-material/Search';
import {Box, Button, FormControl, InputAdornment, InputLabel, MenuItem, Select, TextField,} from '@mui/material';
import type {ChangeEvent} from 'react';
import type {SortOrder} from '../types';

interface RecipeToolbarProps {
    searchTerm: string;
    onSearchChange: (value: string) => void;
    onOpenFilters: () => void;
    sortOrder: SortOrder;
    onSortChange: (value: SortOrder) => void;
    isGridView: boolean;
    onToggleView: () => void;
}

const RecipeToolbar = ({
                           searchTerm,
                           onSearchChange,
                           onOpenFilters,
                           sortOrder,
                           onSortChange,
                           isGridView,
                           onToggleView,
                       }: RecipeToolbarProps) => {
    const handleSearchChange = (event: ChangeEvent<HTMLInputElement>) => {
        onSearchChange(event.target.value);
    };

    return (
        <Box sx={{display: 'flex', flexDirection: 'column', gap: 2, mb: 3}}>
            <Box sx={{display: 'flex', gap: 2, flexWrap: 'wrap'}}>
                <TextField
                    placeholder="Search recipes..."
                    variant="outlined"
                    value={searchTerm}
                    onChange={handleSearchChange}
                    sx={{flexGrow: 1, minWidth: {xs: '100%', sm: 280}}}
                    InputProps={{
                        startAdornment: (
                            <InputAdornment position="start">
                                <SearchIcon/>
                            </InputAdornment>
                        ),
                    }}
                />
                <Button
                    variant="outlined"
                    onClick={onOpenFilters}
                    startIcon={<FilterListIcon/>}
                >
                    Filters
                </Button>
            </Box>

            <Box sx={{display: 'flex', justifyContent: 'space-between', flexWrap: 'wrap', gap: 2}}>
                <FormControl size="small" sx={{minWidth: 160}}>
                    <InputLabel id="sort-label">Sort By</InputLabel>
                    <Select
                        labelId="sort-label"
                        value={sortOrder}
                        label="Sort By"
                        onChange={event => onSortChange(event.target.value as SortOrder)}
                    >
                        <MenuItem value="recent">Most Recent</MenuItem>
                        <MenuItem value="name">Name</MenuItem>
                        <MenuItem value="rating">Rating</MenuItem>
                    </Select>
                </FormControl>

                <Button variant="outlined" onClick={onToggleView}>
                    {isGridView ? 'Switch to List View' : 'Switch to Grid View'}
                </Button>
            </Box>
        </Box>
    );
};

export default RecipeToolbar;
