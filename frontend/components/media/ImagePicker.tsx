'use client';

import { useState, useRef } from 'react';
import {
  Upload,
  X,
  RefreshCw,
  Image as ImageIcon,
  Loader2,
  FolderOpen,
  Check,
} from 'lucide-react';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import { cn } from '@/lib/utils';

export type PickedImage = {
  id: string;
  url: string;
  originalFilename: string;
  mimeType: string;
  sizeBytes: number;
};

type ImagePickerProps = {
  /** Currently attached image (null if none) */
  image: PickedImage | null;
  /** Called when user selects/uploads an image */
  onSelect: (image: PickedImage) => void;
  /** Called when user removes the image */
  onRemove: () => void;
  /** Fetch previously uploaded images for the browse dialog */
  onBrowse?: () => Promise<PickedImage[]>;
  /** Upload a new file and return the image record */
  onUpload?: (file: File) => Promise<PickedImage>;
  /** Whether the picker is disabled */
  disabled?: boolean;
  /** Optional copy overrides for the empty/upload UI */
  emptyLabel?: string;
  emptyHint?: string;
  browseLabel?: string;
  browseDialogTitle?: string;
  emptyBrowseLabel?: string;
  replaceLabel?: string;
};

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export default function ImagePicker({
  image,
  onSelect,
  onRemove,
  onBrowse,
  onUpload,
  disabled = false,
  emptyLabel = 'Drop an image here or click to upload',
  emptyHint = 'JPG, PNG, WebP (Max 10MB)',
  browseLabel = 'Browse Uploaded Images',
  browseDialogTitle = 'Select an Image',
  emptyBrowseLabel = 'No images uploaded yet',
  replaceLabel = 'Replace',
}: ImagePickerProps) {
  const [isUploading, setIsUploading] = useState(false);
  const [isDragging, setIsDragging] = useState(false);
  const [browseOpen, setBrowseOpen] = useState(false);
  const [browseImages, setBrowseImages] = useState<PickedImage[]>([]);
  const [browseLoading, setBrowseLoading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const openFileDialog = () => {
    if (disabled || isUploading) return;
    fileInputRef.current?.click();
  };

  const handleFile = async (file: File) => {
    if (!file.type.startsWith('image/')) {
      toast.error('Only image files are supported (JPG, PNG, WebP).');
      return;
    }
    if (!onUpload) {
      toast.error('Save the assignment template first to enable image uploads.');
      return;
    }

    setIsUploading(true);
    try {
      const uploaded = await onUpload(file);
      onSelect(uploaded);
    } catch {
      // Error handled by caller via toast
    } finally {
      setIsUploading(false);
    }
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      void handleFile(file);
    }
    e.target.value = '';
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    if (!e.dataTransfer.files?.[0]) return;
    if (disabled) return;
    handleFile(e.dataTransfer.files[0]);
  };

  const openBrowse = async () => {
    if (!onBrowse) return;
    setBrowseOpen(true);
    setBrowseLoading(true);
    try {
      const images = await onBrowse();
      setBrowseImages(images);
    } catch {
      setBrowseImages([]);
    } finally {
      setBrowseLoading(false);
    }
  };

  // No image attached — show upload zone
  if (!image) {
    return (
      <div className="space-y-3">
        <div
          role="button"
          tabIndex={disabled ? -1 : 0}
          aria-label={emptyLabel}
          onClick={openFileDialog}
          onKeyDown={(e) => {
            if (e.key === 'Enter' || e.key === ' ') {
              e.preventDefault();
              openFileDialog();
            }
          }}
          onDragOver={(e) => {
            e.preventDefault();
            if (!disabled) setIsDragging(true);
          }}
          onDragLeave={() => setIsDragging(false)}
          onDrop={handleDrop}
          className={cn(
            'relative border-2 border-dashed rounded-lg p-8 transition-all flex flex-col items-center justify-center text-center min-h-[160px]',
            isDragging
              ? 'border-primary bg-primary/5'
              : 'border-border hover:border-muted-foreground/50',
            isUploading && 'pointer-events-none opacity-60',
            disabled && 'opacity-50 cursor-not-allowed',
          )}
        >
          <input
            ref={fileInputRef}
            type="file"
            className="hidden"
            onChange={handleInputChange}
            accept="image/jpeg,image/png,image/webp"
            disabled={disabled}
            aria-label="Upload image file"
          />

          {isUploading ? (
            <div className="flex flex-col items-center">
              <Loader2 className="h-8 w-8 text-primary animate-spin mb-3" />
              <p className="text-sm font-medium text-foreground">Uploading...</p>
            </div>
          ) : (
            <>
              <Upload className="h-8 w-8 mx-auto mb-3 text-muted-foreground" />
              <Button
                type="button"
                variant="outline"
                size="sm"
                className="mb-3 gap-2"
                onClick={(e) => {
                  e.stopPropagation();
                  openFileDialog();
                }}
                disabled={disabled}
              >
                <FolderOpen className="h-4 w-4" />
                Choose File
              </Button>
              <p className="text-sm font-medium text-foreground">
                {emptyLabel}
              </p>
              <p className="text-xs text-muted-foreground mt-1">
                {emptyHint}
              </p>
            </>
          )}
        </div>

        {/* Browse existing images */}
        {onBrowse && (
          <Dialog open={browseOpen} onOpenChange={setBrowseOpen}>
            <DialogTrigger asChild>
              <Button
                type="button"
                variant="outline"
                className="w-full gap-2"
                onClick={openBrowse}
                disabled={disabled}
              >
                <FolderOpen className="h-4 w-4" />
                {browseLabel}
              </Button>
            </DialogTrigger>
            <DialogContent className="max-w-2xl max-h-[70vh] overflow-y-auto">
              <DialogHeader>
                <DialogTitle>{browseDialogTitle}</DialogTitle>
              </DialogHeader>
              {browseLoading ? (
                <div className="flex items-center justify-center py-12">
                  <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
                </div>
              ) : browseImages.length === 0 ? (
                <div className="text-center py-12 text-muted-foreground">
                  <ImageIcon className="h-10 w-10 mx-auto mb-3 opacity-50" />
                  <p className="text-sm">{emptyBrowseLabel}</p>
                </div>
              ) : (
                <div className="grid grid-cols-3 gap-3">
                  {browseImages.map((img) => (
                    <button
                      key={img.id}
                      type="button"
                      onClick={() => {
                        onSelect(img);
                        setBrowseOpen(false);
                      }}
                      className="group relative aspect-square rounded-lg border border-border overflow-hidden hover:ring-2 hover:ring-primary transition-all"
                    >
                      <img
                        src={img.url}
                        alt={img.originalFilename}
                        className="w-full h-full object-cover"
                      />
                      <div className="absolute inset-0 bg-background/60 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
                        <div className="bg-primary text-primary-foreground rounded-full p-2">
                          <Check className="h-5 w-5" />
                        </div>
                      </div>
                      <div className="absolute bottom-0 inset-x-0 bg-background/80 px-2 py-1">
                        <p className="text-[10px] truncate text-foreground font-medium">
                          {img.originalFilename}
                        </p>
                      </div>
                    </button>
                  ))}
                </div>
              )}
            </DialogContent>
          </Dialog>
        )}
      </div>
    );
  }

  // Image attached — show preview with replace/remove
  return (
    <div className="relative rounded-lg overflow-hidden border border-border bg-card group shadow-sm">
      <div className="aspect-video bg-muted flex items-center justify-center overflow-hidden">
        <img
          src={image.url}
          alt={image.originalFilename}
          className="w-full h-full object-contain"
        />
      </div>

      {/* Overlay actions on hover */}
      <div className="absolute inset-0 bg-background/50 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center gap-3">
        <div className="relative">
          <input
            type="file"
            className="absolute inset-0 opacity-0 cursor-pointer"
            onChange={(e) => e.target.files?.[0] && handleFile(e.target.files[0])}
            accept="image/jpeg,image/png,image/webp"
            disabled={disabled}
          />
          <Button type="button" size="sm" className="gap-2" disabled={disabled}>
            <RefreshCw className="h-4 w-4" />
            {replaceLabel}
          </Button>
        </div>
        <Button
          type="button"
          variant="destructive"
          size="sm"
          onClick={onRemove}
          disabled={disabled}
          className="gap-2"
        >
          <X className="h-4 w-4" />
          Remove
        </Button>
      </div>

      {/* File info bar */}
      <div className="px-3 py-2 flex items-center justify-between bg-muted/50 border-t border-border">
        <div className="flex items-center gap-2 min-w-0">
          <ImageIcon className="h-4 w-4 text-muted-foreground flex-shrink-0" />
          <p className="text-sm font-medium text-foreground truncate">
            {image.originalFilename}
          </p>
        </div>
        <span className="text-xs font-mono text-muted-foreground flex-shrink-0 ml-2">
          {formatSize(image.sizeBytes)} &middot; {image.mimeType.split('/')[1]?.toUpperCase()}
        </span>
      </div>
    </div>
  );
}
