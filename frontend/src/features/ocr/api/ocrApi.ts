import api from '../../../utils/api';
import {SegmentationApproval} from '../../../lib/model';

export const approveImage = (id: string, result: SegmentationApproval) =>
    api.post(`/recipescanner/approve_segmentation/${id}`, result);

export const redoOCR = (id: string) =>
    api.post(`/recipescanner/trigger_ocr/${id}`);

export const redoSegmentation = (id: string) =>
    api.post(`/recipescanner/trigger_seg/${id}`);

export const fetchBookImages = (bookId: string) =>
    api.get(`/recipescanner/book_scans/${bookId}/pages`);

export const uploadImages = (bookId: string, files: File[]) => {
    const formData = new FormData();
    files.forEach((file) => formData.append('files', file));
    return api.post(`/recipescanner/upload/${bookId}`, formData, {
        headers: {'Content-Type': 'multipart/form-data'},
    });
};

export const deletePage = (id: string) =>
    api.delete(`/recipescanner/images/${id}`);

export const updatePageNumber = (id: string, newPageNumber: number) =>
    api.post(`/recipescanner/update_page_number/${id}`, null, {
        params: {target_number: newPageNumber},
    });
