import React, { useState } from 'react';
import { Box, Typography, Button, SxProps, Theme } from '@mui/material';
import { CloudUpload } from '@mui/icons-material';
import { overlays, palette } from '../../theme';

interface FileUploadBoxProps {
    file: File | null;
    onFileChange: (file: File | null) => void;
    onError: (error: string | null) => void;
    disabled?: boolean;
    sx?: SxProps<Theme>;
    title?: string;
    accept?: string;
    acceptedTypes?: string[];
    acceptedExtensions?: string[];
}

export function FileUploadBox({
    file,
    onFileChange,
    onError,
    disabled = false,
    sx = {},
    title = 'Drag and drop a ZIP file here, or Browse Files',
    accept = '.zip,application/zip',
    acceptedTypes = ['application/zip', 'application/x-zip-compressed'],
    acceptedExtensions = ['.zip']
}: FileUploadBoxProps) {
    const [isDragging, setIsDragging] = useState(false);

    const handleDragOver = (e: React.DragEvent<HTMLDivElement>) => {
        e.preventDefault();
        setIsDragging(true);
    };

    const handleDragLeave = (e: React.DragEvent<HTMLDivElement>) => {
        e.preventDefault();
        setIsDragging(false);
    };

    const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
        e.preventDefault();
        setIsDragging(false);
        
        if (disabled) return;

        const nextFile = e.dataTransfer.files?.[0] ?? null;
        if (nextFile) {
            const isValidExtension = acceptedExtensions.some(ext => nextFile.name.toLowerCase().endsWith(ext));
            const isValidType = acceptedTypes.includes(nextFile.type);
            
            if (isValidExtension || isValidType) {
                onFileChange(nextFile);
                onError(null);
            } else {
                onError('Please upload a valid file type.');
            }
        }
    };

    const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        const nextFile = e.target.files?.[0] ?? null;
        onFileChange(nextFile);
        onError(null);
    };

    return (
        <Box 
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
            sx={{
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                justifyContent: 'center',
                p: 6,
                border: '2px dashed',
                borderColor: isDragging || file ? 'primary.main' : 'divider',
                borderRadius: 2,
                backgroundColor: isDragging ? `${palette.primary}20` : (file ? `${palette.primary}10` : overlays.overlayLight),
                transition: 'all 0.2s',
                ...sx
            }}
        >
            <CloudUpload sx={{ fontSize: 48, color: isDragging || file ? 'primary.main' : 'text.secondary', mb: 2 }} />
            <Typography variant="body1" sx={{ mb: 1, fontWeight: 500, textAlign: 'center' }}>
                {file ? file.name : title}
            </Typography>
            {file && (
                <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
                    {file.size < 1024
                        ? `${file.size} Bytes`
                        : file.size < 1024 * 1024
                            ? `${(file.size / 1024).toFixed(2)} KB`
                            : `${(file.size / 1024 / 1024).toFixed(2)} MB`}
                </Typography>
            )}
            <Button variant={file ? 'outlined' : 'contained'} component="label" disabled={disabled}>
                {file ? 'Change File' : 'Browse Files'}
                <input
                    type="file"
                    hidden
                    accept={accept}
                    onChange={handleFileChange}
                />
            </Button>
        </Box>
    );
}
