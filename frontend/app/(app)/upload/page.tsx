import { UploadDropzone } from "@/components/features/upload-dropzone";

export default function UploadPage() {
  return (
    <div className="space-y-10">
      <header>
        <p className="text-caption text-muted-foreground mb-3 font-mono uppercase">New contract</p>
        <h2 className="text-heading-lg font-display text-foreground font-medium">
          Upload for <span className="font-editorial">analysis</span>
        </h2>
        <p className="text-body text-muted-foreground mt-2 max-w-[60ch]">
          ClauseGuard will parse the document, classify every clause, and return a risk breakdown
          with suggested redlines. The whole pass usually finishes in under a minute.
        </p>
      </header>

      <UploadDropzone />
    </div>
  );
}
