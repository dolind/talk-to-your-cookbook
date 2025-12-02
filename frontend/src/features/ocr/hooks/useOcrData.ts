import {useEffect, useState} from 'react';
import api from '../../../utils/api';
import {useOCRStore} from '../../../store/useOCRStore';

export function useOcrData() {
    const {pages, editingImageId} = useOCRStore();
    const [ocrData, setOcrData] = useState<any | null>(null);

    useEffect(() => {
        if (!editingImageId) return;
        const current = pages.find((img) => img.id === editingImageId);
        if (!current) return;

        setOcrData(null);

        const fetchOCR = async () => {
            try {
                const res = await api.get(`/recipescanner/ocr_data/${editingImageId}`);
                setOcrData(res.data);
            } catch (err) {
                console.error('Failed to load OCR data:', err);
                setOcrData(null);
            }
        };

        fetchOCR();
    }, [editingImageId, pages]);

    return {ocrData, setOcrData};
}
