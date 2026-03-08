import { useEffect } from 'react';
import { getParentDir, joinPaths, normalizePath } from '../utils/path.js';

function inferParentDir(pathValue) {
    const normalized = normalizePath(pathValue);
    if (!normalized) return null;
    return getParentDir(normalized) || normalized;
}

function resolveOutputMode({ mode, imagesDir, outputDir }) {
    if (outputDir) return false;
    if (mode === 'when_images_empty') {
        return !imagesDir;
    }
    return true;
}

export default function useDatasetPathInference({
    imagesDir,
    setImagesDir,
    annotationsDir,
    setAnnotationsDir,
    outputDir,
    setOutputDir,
    outputFolderName,
    annotationsFolderName = 'annotations',
    imagesFolderName = 'images',
    outputFromAnnotationsMode = 'always',
}) {
    useEffect(() => {
        const parentDir = inferParentDir(imagesDir);
        if (!parentDir) return;

        if (!annotationsDir && !outputDir && annotationsFolderName) {
            setAnnotationsDir(joinPaths(parentDir, annotationsFolderName));
        }
        if (!outputDir && outputFolderName) {
            setOutputDir(joinPaths(parentDir, outputFolderName));
        }
    }, [
        annotationsDir,
        annotationsFolderName,
        imagesDir,
        outputDir,
        outputFolderName,
        setAnnotationsDir,
        setOutputDir,
    ]);

    useEffect(() => {
        const parentDir = inferParentDir(annotationsDir);
        if (!parentDir) return;

        if (!imagesDir && !outputDir && imagesFolderName) {
            setImagesDir(joinPaths(parentDir, imagesFolderName));
        }
        if (outputFolderName && resolveOutputMode({
            mode: outputFromAnnotationsMode,
            imagesDir,
            outputDir,
        })) {
            setOutputDir(joinPaths(parentDir, outputFolderName));
        }
    }, [
        annotationsDir,
        imagesDir,
        imagesFolderName,
        outputDir,
        outputFolderName,
        outputFromAnnotationsMode,
        setImagesDir,
        setOutputDir,
    ]);
}

