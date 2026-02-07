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

export function matchImages(payload) {
    return post('/api/match', payload);
}

export function augmentDataset(payload) {
    return post('/api/augment', payload);
}

export function findDuplicates(payload) {
    return post('/api/find-duplicates', payload);
}

export function removeDuplicates(payload) {
    return post('/api/remove-duplicates', payload);
}

export function cleanDataset(payload) {
    return post('/api/clean-dataset', payload);
}

export function scanYoloClasses(payload) {
    return post('/api/scan-yolo-classes', payload);
}

export function modifyLabels(payload) {
    return post('/api/modify-labels', payload);
}

export function visualizeAnnotations(payload) {
    return post('/api/visualize', payload);
}

export function generateGrid(payload) {
    return post('/api/generate-grid', payload);
}
