import {useEffect} from 'react';
import {useOCRStore} from '../../../store/useOCRStore';
import {useSnackbar} from 'notistack';
import {fetchBookImages} from '../api/ocrApi';
import {PageScanRecord} from '../../../lib/model';

export function usePages() {
    const {selectedBookId, setImages} = useOCRStore();
    const {enqueueSnackbar} = useSnackbar();

    const loadImages = async () => {
        if (!selectedBookId) return;
        try {
            const res = await fetchBookImages(selectedBookId);
            setImages(res.data as PageScanRecord[]);
        } catch (err) {
            console.error(err);
            enqueueSnackbar('Failed to fetch images', {variant: 'error'});
        }
    };

    useEffect(() => {
        loadImages();
    }, [selectedBookId]);

    return {fetchPages: loadImages};
}
