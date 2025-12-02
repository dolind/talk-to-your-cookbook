import {Grid, Skeleton} from '@mui/material';
import RecipeCard, {RecipeViewMode} from './RecipeCard';
import type {RecipeRead} from '../types';

interface RecipeCollectionProps {
    recipes: RecipeRead[];
    viewMode: RecipeViewMode;
    deleteMode: boolean;
    selectedIds: Set<string>;
    onToggleSelection: (id: string) => void;
    onStartSelection: (id: string) => void;
    onHoverSelection: (id: string) => void;
    loadMoreRef: (node?: Element | null) => void;
    loading: boolean;
}

const RecipeCollection = ({
                              recipes,
                              viewMode,
                              deleteMode,
                              selectedIds,
                              onToggleSelection,
                              onStartSelection,
                              onHoverSelection,
                              loadMoreRef,
                              loading,
                          }: RecipeCollectionProps) => {
    if (recipes.length === 0) {
        return null;
    }

    return (
        <Grid container spacing={3} direction={viewMode === 'grid' ? 'row' : 'column'}>
            {recipes.map(recipe => (
                <Grid
                    item
                    xs={12}
                    sm={viewMode === 'grid' ? 6 : 12}
                    md={viewMode === 'grid' ? 4 : 12}
                    key={recipe.id}
                >
                    <RecipeCard
                        recipe={recipe}
                        viewMode={viewMode}
                        deleteMode={deleteMode}
                        selected={selectedIds.has(recipe.id)}
                        onToggleSelection={onToggleSelection}
                        onStartSelection={onStartSelection}
                        onHoverSelection={onHoverSelection}
                    />
                </Grid>
            ))}
            <Grid item xs={12}>
                <div ref={loadMoreRef}/>
                {loading && (
                    [...Array(6)].map((_, i) => (
                        <Skeleton key={i} variant="rectangular" width={220} height={260}/>
                    ))
                )}
            </Grid>
        </Grid>
    );
};

export default RecipeCollection;
