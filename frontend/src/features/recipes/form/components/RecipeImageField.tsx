import {ChangeEvent, FC} from 'react';
import {Box, Button, Typography} from '@mui/material';

interface RecipeImageFieldProps {
    imageUrl?: string | null;
    removeImage: boolean;
    onUpload: (file: File | null) => void;
    onRemove: (remove: boolean) => void;
}

export const RecipeImageField: FC<RecipeImageFieldProps> = ({
                                                                imageUrl,
                                                                removeImage,
                                                                onUpload,
                                                                onRemove,
                                                            }) => {
    const mediaBaseUrl = import.meta.env.VITE_MEDIA_BASE_URL;

    const handleFileChange = (event: ChangeEvent<HTMLInputElement>) => {
        const file = event.target.files?.[0] ?? null;
        onUpload(file);
    };

    return (
        <Box sx={{display: 'flex', flexDirection: 'column', gap: 2}}>
            {imageUrl && !removeImage && (
                <Box>
                    <img
                        src={`${mediaBaseUrl}/${imageUrl}`}
                        alt="Current recipe"
                        style={{maxWidth: '100%', maxHeight: 200}}
                    />
                    <Button color="error" onClick={() => onRemove(true)}>
                        Delete Image
                    </Button>
                </Box>
            )}

            <Button component="label" sx={{alignSelf: 'flex-start'}}>
                Upload Image
                <input type="file" hidden accept="image/*" onChange={handleFileChange}/>
            </Button>

            {removeImage && (
                <Box sx={{display: 'flex', flexDirection: 'column', gap: 1}}>
                    <Typography variant="caption" color="text.secondary">
                        The existing image will be removed when you save.
                    </Typography>
                    <Button size="small" onClick={() => onRemove(false)}>
                        Keep current image
                    </Button>
                </Box>
            )}
        </Box>
    );
};
