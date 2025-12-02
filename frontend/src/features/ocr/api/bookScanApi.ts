import api from '../../../utils/api';
import {BookScan} from '../../../lib/model';

export const getBookScans = () => api.get<BookScan[]>('/recipescanner/book_scans');

export const createBookScan = (title: string) =>
    api.post<BookScan>('/recipescanner/book_scans', {title});

export const deleteBookScan = (scanId: string) =>
    api.delete(`/recipescanner/book_scans/${scanId}`);
