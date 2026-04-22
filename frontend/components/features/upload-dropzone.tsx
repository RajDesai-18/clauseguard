"use client";

import { useRouter } from "next/navigation";
import { useCallback, useRef, useState } from "react";
import { FileText, Upload as UploadIcon, X } from "lucide-react";
import { uploadContract, ApiError } from "@/lib/api/api-client";

const ACCEPTED_MIME = [
  "application/pdf",
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
];
const ACCEPTED_EXT = [".pdf", ".docx"];
const MAX_SIZE = 10 * 1024 * 1024;

type State =
  | { kind: "idle" }
  | { kind: "selected"; file: File }
  | { kind: "uploading"; file: File }
  | { kind: "error"; message: string };

export function UploadDropzone() {
  const router = useRouter();
  const inputRef = useRef<HTMLInputElement>(null);
  const [state, setState] = useState<State>({ kind: "idle" });
  const [isDragging, setIsDragging] = useState(false);

  const validate = useCallback((file: File): string | null => {
    const nameLower = file.name.toLowerCase();
    const extOk = ACCEPTED_EXT.some((ext) => nameLower.endsWith(ext));
    const mimeOk = ACCEPTED_MIME.includes(file.type);
    if (!extOk && !mimeOk) {
      return "Only PDF and DOCX files are accepted.";
    }
    if (file.size > MAX_SIZE) {
      return `File is too large. Maximum size is 10 MB.`;
    }
    if (file.size === 0) {
      return "File is empty.";
    }
    return null;
  }, []);

  const handleFile = useCallback(
    (file: File) => {
      const error = validate(file);
      if (error) {
        setState({ kind: "error", message: error });
        return;
      }
      setState({ kind: "selected", file });
    },
    [validate]
  );

  const handleDrop = useCallback(
    (e: React.DragEvent<HTMLDivElement>) => {
      e.preventDefault();
      setIsDragging(false);
      const file = e.dataTransfer.files?.[0];
      if (file) handleFile(file);
    },
    [handleFile]
  );

  const handleDragOver = useCallback((e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(false);
  }, []);

  const handleChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (file) handleFile(file);
      e.target.value = "";
    },
    [handleFile]
  );

  const handleSubmit = useCallback(async () => {
    if (state.kind !== "selected") return;
    const { file } = state;
    setState({ kind: "uploading", file });
    try {
      const response = await uploadContract(file);
      router.push(`/contract/${response.id}`);
    } catch (err) {
      const message = err instanceof ApiError ? err.message : "Upload failed. Please try again.";
      setState({ kind: "error", message });
    }
  }, [state, router]);

  const reset = useCallback(() => setState({ kind: "idle" }), []);

  if (state.kind === "selected" || state.kind === "uploading") {
    return (
      <FileSelected
        file={state.file}
        uploading={state.kind === "uploading"}
        onSubmit={handleSubmit}
        onClear={reset}
      />
    );
  }

  return (
    <div className="space-y-4">
      <div
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onClick={() => inputRef.current?.click()}
        role="button"
        tabIndex={0}
        aria-label="Drop a contract here or click to choose a file"
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            inputRef.current?.click();
          }
        }}
        className={`relative flex min-h-[320px] cursor-pointer flex-col items-center justify-center rounded-sm border transition-colors duration-150 ease-[cubic-bezier(0.23,1,0.32,1)] ${
          isDragging
            ? "border-foreground bg-muted/60"
            : "border-border bg-card hover:border-foreground/60 hover:bg-muted/30"
        }`}
      >
        <input
          ref={inputRef}
          type="file"
          accept=".pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
          onChange={handleChange}
          className="sr-only"
          tabIndex={-1}
        />

        <UploadIcon
          className={`mb-6 size-8 transition-colors duration-150 ease-[cubic-bezier(0.23,1,0.32,1)] ${
            isDragging ? "text-foreground" : "text-muted-foreground"
          }`}
          strokeWidth={1.25}
        />
        <p className="text-heading-lg font-display text-foreground mb-2 font-medium">
          Drop a contract here
        </p>
        <p className="text-body-sm text-muted-foreground max-w-[40ch] text-center">
          PDF or DOCX, up to 10 MB. Click anywhere in this box to choose a file, or drag one in.
        </p>
      </div>

      {state.kind === "error" && <ErrorMessage message={state.message} />}
    </div>
  );
}

function FileSelected({
  file,
  uploading,
  onSubmit,
  onClear,
}: {
  file: File;
  uploading: boolean;
  onSubmit: () => void;
  onClear: () => void;
}) {
  return (
    <div className="space-y-6">
      <div className="border-border bg-card flex items-center gap-4 rounded-sm border p-6">
        <FileText className="text-muted-foreground size-6 shrink-0" strokeWidth={1.25} />
        <div className="min-w-0 flex-1">
          <p className="text-body-sm text-foreground truncate font-medium">{file.name}</p>
          <p className="text-caption text-muted-foreground mt-1 font-mono uppercase">
            {formatSize(file.size)} &middot; {fileKind(file)}
          </p>
        </div>
        {!uploading && (
          <button
            type="button"
            onClick={onClear}
            aria-label="Remove file"
            className="text-muted-foreground hover:text-foreground transition-colors duration-150 ease-[cubic-bezier(0.23,1,0.32,1)]"
          >
            <X className="size-5" strokeWidth={1.5} />
          </button>
        )}
      </div>

      <div className="flex items-center gap-4">
        <button
          type="button"
          onClick={onSubmit}
          disabled={uploading}
          className="border-foreground bg-foreground text-background hover:bg-foreground/90 font-display rounded-sm border px-5 py-2.5 text-[14px] font-medium transition-colors duration-200 ease-[cubic-bezier(0.23,1,0.32,1)] active:scale-[0.99] disabled:cursor-not-allowed disabled:opacity-60"
        >
          {uploading ? "Uploading…" : "Analyze contract"}
        </button>
        {!uploading && (
          <button
            type="button"
            onClick={onClear}
            className="text-body-sm text-muted-foreground hover:text-foreground transition-colors duration-150 ease-[cubic-bezier(0.23,1,0.32,1)]"
          >
            Choose a different file
          </button>
        )}
      </div>
    </div>
  );
}

function ErrorMessage({ message }: { message: string }) {
  return (
    <div className="border-destructive/40 bg-destructive/5 rounded-sm border px-4 py-3">
      <p className="text-caption text-destructive mb-1 font-mono uppercase">Upload error</p>
      <p className="text-body-sm text-foreground">{message}</p>
    </div>
  );
}

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function fileKind(file: File): string {
  const name = file.name.toLowerCase();
  if (name.endsWith(".pdf") || file.type === "application/pdf") return "PDF";
  if (name.endsWith(".docx")) return "DOCX";
  return "Document";
}
