import LocalDiningIcon from '@mui/icons-material/LocalDining';
import {Box, Button, Typography} from '@mui/material';
import {useCallback, useEffect, useState} from 'react';
import {useNavigate} from 'react-router-dom';
import {deleteRecipes} from '../api';
import RecipeBulkDelete from '../components/RecipeBulkDelete';
import RecipeCollection from '../components/RecipeCollection';
import RecipeFilterChips from '../components/RecipeFilterChips';
import RecipeFiltersDrawer from '../components/RecipeFiltersDrawer';
import RecipeToolbar from '../components/RecipeToolbar';
import {useRecipeSearch} from '../hooks/useRecipeSearch';

const RecipesPage = () => {
    const navigate = useNavigate();
    const {
        filters,
        recipes,
        loading,
        availableCategories,
        availableSources,
        loadMoreRef,
        setSearchTerm,
        setCategories,
        setTags,
        setSource,
        setMaxTime,
        setSortOrder,
        clearFilters,
        removeRecipesById,
    } = useRecipeSearch();

    const [isFilterDrawerOpen, setIsFilterDrawerOpen] = useState(false);
    const [isGridView, setIsGridView] = useState(true);
    const [deleteMode, setDeleteMode] = useState(false);
    const [selectedRecipeIds, setSelectedRecipeIds] = useState<Set<string>>(new Set());
    const [isMouseDown, setIsMouseDown] = useState(false);

    useEffect(() => {
        const handleMouseUp = () => setIsMouseDown(false);
        document.addEventListener('mouseup', handleMouseUp);
        return () => {
            document.removeEventListener('mouseup', handleMouseUp);
        };
    }, []);

    const toggleRecipeSelection = useCallback((id: string) => {
        setSelectedRecipeIds(prev => {
            const next = new Set(prev);
            if (next.has(id)) {
                next.delete(id);
            } else {
                next.add(id);
            }
            return next;
        });
    }, []);

    const handleStartSelection = useCallback((id: string) => {
        if (!deleteMode) {
            return;
        }
        setIsMouseDown(true);
        toggleRecipeSelection(id);
    }, [deleteMode, toggleRecipeSelection]);

    const handleHoverSelection = useCallback((id: string) => {
        if (!deleteMode || !isMouseDown) {
            return;
        }
        toggleRecipeSelection(id);
    }, [deleteMode, isMouseDown, toggleRecipeSelection]);

    const handleEnterDeleteMode = useCallback(() => {
        setDeleteMode(true);
    }, []);

    const handleCancelDelete = useCallback(() => {
        setDeleteMode(false);
        setSelectedRecipeIds(new Set());
    }, []);

    const handleConfirmDelete = useCallback(async () => {
        const ids = Array.from(selectedRecipeIds);
        try {
            await deleteRecipes(ids);
            removeRecipesById(ids);
            setSelectedRecipeIds(new Set());
            setDeleteMode(false);
        } catch (error) {
            console.error('Failed to delete recipes', error);
            alert('Error deleting recipes.');
        }
    }, [removeRecipesById, selectedRecipeIds]);

    const handleClearFilters = useCallback(() => {
        clearFilters();
    }, [clearFilters]);

    const handleClearAllFilters = useCallback(() => {
        setSearchTerm('');
        clearFilters();
    }, [clearFilters, setSearchTerm]);

    return (
        <Box>
            <Typography variant="h4" component="h1" gutterBottom>
                Recipes
            </Typography>

            <RecipeToolbar
                searchTerm={filters.search}
                onSearchChange={setSearchTerm}
                onOpenFilters={() => setIsFilterDrawerOpen(true)}
                sortOrder={filters.sort}
                onSortChange={setSortOrder}
                isGridView={isGridView}
                onToggleView={() => setIsGridView(prev => !prev)}
            />

            <RecipeFilterChips
                filters={filters}
                onRemoveCategory={category => setCategories(filters.categories.filter(cat => cat !== category))}
                onRemoveTag={tag => setTags(filters.tags.filter(t => t !== tag))}
                onClearSource={() => setSource('')}
                onClearMaxTime={() => setMaxTime('')}
                onClearAll={handleClearFilters}
            />

            <Box sx={{display: 'flex', justifyContent: 'space-between', mb: 2}}>
                <Button variant="contained" color="primary" onClick={() => navigate('/recipes/new')}>
                    Create Recipe
                </Button>
                <RecipeBulkDelete
                    deleteMode={deleteMode}
                    selectedCount={selectedRecipeIds.size}
                    onEnterDeleteMode={handleEnterDeleteMode}
                    onConfirmDelete={handleConfirmDelete}
                    onCancelDelete={handleCancelDelete}
                />
            </Box>

            {recipes.length > 0 ? (
                <RecipeCollection
                    recipes={recipes}
                    viewMode={isGridView ? 'grid' : 'list'}
                    deleteMode={deleteMode}
                    selectedIds={selectedRecipeIds}
                    onToggleSelection={toggleRecipeSelection}
                    onStartSelection={handleStartSelection}
                    onHoverSelection={handleHoverSelection}
                    loadMoreRef={loadMoreRef}
                    loading={loading}
                />
            ) : (
                <Box sx={{textAlign: 'center', py: 8}}>
                    <LocalDiningIcon sx={{fontSize: 60, color: 'text.disabled', mb: 2}}/>
                    <Typography variant="h6" color="text.secondary">
                        No recipes found matching your filters
                    </Typography>
                    <Button variant="outlined" sx={{mt: 2}} onClick={handleClearAllFilters}>
                        Clear all filters
                    </Button>
                </Box>
            )}

            <RecipeFiltersDrawer
                open={isFilterDrawerOpen}
                onClose={() => setIsFilterDrawerOpen(false)}
                filters={filters}
                availableCategories={availableCategories}
                availableSources={availableSources}
                onCategoriesChange={setCategories}
                onTagsChange={setTags}
                onSourceChange={setSource}
                onMaxTimeChange={setMaxTime}
                onClearFilters={handleClearFilters}
            />
        </Box>
    );
};

export default RecipesPage;
