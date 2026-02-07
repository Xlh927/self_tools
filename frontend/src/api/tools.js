import { post } from './http.js';

export function convertDataset(payload) {
    return post('/api/convert', payload);
}

export function scanVocClasses(payload) {
    return post('/api/scan-voc-classes', payload);
}

export function scanClasses(payload) {
    return post('/api/scan-classes', payload);
}

export function cropImages(payload) {
    return post('/api/crop', payload);
}

export function generateDataset(payload) {
    return post('/api/generate', payload);
}

export function splitDataset(payload) {
    return post('/api/split', payload);
}
